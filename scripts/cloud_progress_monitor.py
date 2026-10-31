#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only progress observation. Never dispatch, restart, cancel or repair CAD jobs."""
import argparse
import copy
import base64
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = "Melihakbulut221/nssoc"
WORKFLOW = ".github/workflows/cloud-progress-monitor.yml"
WORKFLOW_ID = 394905294
MONITOR_JOBS = frozenset(("controls", "observe"))
ARTIFACT = "cloud-progress-snapshot"
LIMIT = 8 * 1024 * 1024
TERMINAL_BAD = {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}
UTC = dt.timezone.utc

def time_value(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

def utc_now():
    return dt.datetime.now(UTC)

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or not (
            host == "api.github.com" or host.endswith(".githubusercontent.com")
            or host.endswith(".blob.core.windows.net")
        ):
            raise ValueError("Unexpected GitHub download redirect")
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if parsed.netloc != urllib.parse.urlparse(req.full_url).netloc:
            result.remove_header("Authorization")
        return result

class API:
    """Only bounded GET requests against this repository."""
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(SafeRedirect())

    def raw(self, path, limit=LIMIT, binary=False):
        budget = getattr(self, "read_budget", None)
        if budget is not None:
            budget.before(path)
        try:
            value = self._raw(path, limit, binary)
        except BaseException as error:
            if budget is not None:
                budget.after(path, type(error).__name__)
            raise
        if budget is not None:
            budget.after(path, None)
        return value

    def _raw(self, path, limit=LIMIT, binary=False):
        assert path and not path.startswith("/") and ".." not in path and "://" not in path
        url = "https://api.github.com/repos/" + REPO + "/" + path
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/octet-stream" if binary else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nssoc-cloud-progress-monitor",
        }
        request = urllib.request.Request(url, headers=headers, method="GET")
        with self.opener.open(request, timeout=60) as stream:
            size = stream.headers.get("Content-Length")
            if size and int(size) > limit:
                raise ValueError("Metadata exceeds bounded monitor size")
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Metadata exceeds bounded monitor size")
        return raw

    def get(self, path):
        return json.loads(self.raw(path))

    def maybe(self, path):
        try:
            return self.get(path)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def pages(self, path, key, maximum=1000):
        rows = []
        separator = "&" if "?" in path else "?"
        for page in range(1, 11):
            data = self.get(path + separator + "per_page=100&page=" + str(page))
            batch = data if key is None else data[key]
            rows.extend(batch)
            if len(rows) > maximum:
                raise ValueError("Unexpectedly large metadata inventory")
            if len(batch) < 100:
                return rows
        raise ValueError("Metadata pagination incomplete")

def check_config(config):
    assert config["schema"] == 1 and config["repository"] == REPO
    assert type(config.get("inventory_version")) is int and config["inventory_version"] > 0
    assert config.get("inventory_updated_at") and time_value(config["inventory_updated_at"])
    assert config["target_branch"] == "codex/complete-open-work"
    assert config["stall_seconds"] == 21600
    seen = set()
    for item in config["runs"]:
        assert type(item["run"]) is int and item["run"] > 0 and item["run"] not in seen
        seen.add(item["run"])
        assert item["label"] and re.fullmatch(r"[0-9a-f]{40}", item["head_sha"])
        assert type(item["branch"]) is str and (item["branch"].startswith("codex/") or item["branch"] == "main"), "Unapproved inventory branch: " + repr(item.get("branch"))
    for item in config["latest_workflows"]:
        assert re.fullmatch(r"[a-z0-9-]+\.yml", item["workflow"])
        assert item["branch"] == config["target_branch"]
        assert isinstance(item["optional"], bool)
        assert item.get("event") in (None, "push", "workflow_dispatch")
        assert isinstance(item.get("production_jobs", []), list)
    assert config["automatic_native_dispatch"] is False

INVENTORY_LIMIT = 65536
MAX_RUN_FILES = 16
INVENTORY_PATH = ".github/cloud-progress-monitor.json"
RUN_FILE_PATHS = (
    ".github/cloud-progress-monitor-runs-000.json",
    ".github/cloud-progress-monitor-runs-001.json",
)


def inventory_document(api, head, path, optional=False):
    """Read one bounded document at the already captured commit, never a child ref."""
    assert re.fullmatch(r"[0-9a-f]{40}", head)
    assert path == INVENTORY_PATH or path in tuple(".github/cloud-progress-monitor-runs-"+str(i).zfill(3)+".json" for i in range(MAX_RUN_FILES)), "Unapproved inventory path"
    data = api.maybe("contents/" + path + "?ref=" + head)
    if data is None:
        assert optional and path == INVENTORY_PATH, ("Missing inventory shard", path)
        return None
    assert data["encoding"] == "base64" and data["size"] <= INVENTORY_LIMIT
    raw = base64.b64decode(data["content"], validate=False)
    assert len(raw) == data["size"] <= INVENTORY_LIMIT
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest() == data["sha"]
    return json.loads(raw), dict(path=path, blob_sha=data["sha"],
        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def assembled_inventory(api, head, manifest):
    """Bounded contiguous shard format; preserve all ordered rows and validate globally."""
    assert set(manifest) == {
        "schema", "repository", "target_branch", "stall_seconds", "automatic_native_dispatch",
        "latest_workflows", "inventory_version", "inventory_updated_at",
        "run_files", "run_count", "runs_sha256",
    }, "Inventory manifest fields"
    assert type(manifest["schema"]) is int and manifest["schema"] == 2
    assert type(manifest["run_files"]) is list and 1 <= len(manifest["run_files"]) <= MAX_RUN_FILES, "Inventory shard count"
    assert type(manifest["run_count"]) is int and manifest["run_count"] > 0, "Inventory run count"
    assert isinstance(manifest["runs_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", manifest["runs_sha256"])
    config = {k:manifest[k] for k in (
        "repository", "target_branch", "stall_seconds", "automatic_native_dispatch",
        "latest_workflows", "inventory_version", "inventory_updated_at",
    )}
    config.update(schema=1, runs=[])
    check_config(config)
    # Validate all descriptors before the first child read.
    paths = tuple(".github/cloud-progress-monitor-runs-"+str(i).zfill(3)+".json" for i in range(len(manifest["run_files"])))
    for path, item in zip(paths, manifest["run_files"], strict=True):
        assert type(item) is dict and set(item) == {"path","blob_sha","sha256","bytes","run_count"}, "Inventory descriptor fields"
        assert item["path"] == path, "Inventory shard order/path"
        assert type(item["bytes"]) is int and 0 < item["bytes"] <= INVENTORY_LIMIT, "Inventory descriptor size"
        assert type(item["run_count"]) is int and item["run_count"] > 0, "Inventory descriptor count"
        assert isinstance(item["blob_sha"], str) and re.fullmatch(r"[0-9a-f]{40}", item["blob_sha"])
        assert isinstance(item["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
    documents = []
    for item in manifest["run_files"]:
        shard, proof = inventory_document(api, head, item["path"])
        assert all(proof[k] == item[k] for k in ("path","blob_sha","sha256","bytes")), ("Inventory shard identity", item["path"])
        assert type(shard) is dict and set(shard) == {"schema","repository","target_branch","runs"}, "Inventory shard fields"
        assert shard["schema"] == "cloud-progress-monitor-runs-v1", "Inventory shard schema"
        assert shard["repository"] == config["repository"] and shard["target_branch"] == config["target_branch"], "Inventory shard scope"
        assert type(shard["runs"]) is list and len(shard["runs"]) == item["run_count"], "Inventory shard run count"
        config["runs"].extend(shard["runs"])
        documents.append(dict(proof, run_count=len(shard["runs"])))
    assert len(config["runs"]) == manifest["run_count"], "Inventory combined run count"
    raw = json.dumps(config["runs"], sort_keys=True, separators=(",",":"), allow_nan=False).encode()
    assert hashlib.sha256(raw).hexdigest() == manifest["runs_sha256"], "Inventory combined run digest"
    # This rejects duplicate IDs across files as well as the original invalid source/policy cases.
    check_config(config)
    return config, documents


def load_config(api, bootstrap):
    """Pin schema-1 or explicit sharded inventory to one exact Git commit."""
    branch = "codex/complete-open-work"
    head = api.get("git/ref/heads/" + branch)["object"]["sha"]
    document = inventory_document(api, head, INVENTORY_PATH, optional=True)
    if document is None:
        check_config(bootstrap)
        return bootstrap, dict(branch=branch, head_sha=head, bootstrap=True,
            note="Working-branch inventory absent; using explicit reviewed bootstrap inventory")
    manifest, first = document
    proof = dict(branch=branch, head_sha=head, blob_sha=first["blob_sha"],
        sha256=first["sha256"], bytes=first["bytes"], bootstrap=False)
    if manifest["schema"] == 1:
        check_config(manifest)
        return manifest, proof
    assert manifest["schema"] == 2, "Unknown inventory schema"
    config, documents = assembled_inventory(api, head, manifest)
    proof.update(inventory_schema=2, documents=[first,*documents],
        resolved_run_count=len(config["runs"]), runs_sha256=manifest["runs_sha256"])
    return config, proof

def classify(run, jobs, now, stall_seconds):
    status = run["status"]
    conclusion = run.get("conclusion")
    if status == "completed":
        if conclusion in TERMINAL_BAD:
            return "FAILED", "Actions conclusion: " + str(conclusion)
        if conclusion == "success":
            bad = [j for j in jobs if j.get("conclusion") in TERMINAL_BAD]
            if bad:
                return "FAILED_JOB", "A failed job remains despite overall success: " + ", ".join(j["name"] for j in bad)
            return "COMPLETED_ACTIONS", "Actions succeeded; native evidence and product gates remain separate"
        return "NOT_EXECUTED", "Terminal Actions conclusion: " + str(conclusion)
    bad = [j for j in jobs if j.get("conclusion") in TERMINAL_BAD]
    if bad:
        return "FAILED_JOB", "A job already failed: " + ", ".join(j["name"] for j in bad)
    for job in jobs:
        if job["status"] == "in_progress" and job.get("started_at"):
            age = (now - time_value(job["started_at"])).total_seconds()
            if age > stall_seconds:
                return "STALLED_OVER_6H", "Running job exceeds six hours: " + job["name"]
    return ("RUNNING" if status == "in_progress" else "PENDING"), "Native work is not restarted or duplicated"

def job_record(job):
    return {
        key: job.get(key) for key in (
            "id", "name", "status", "conclusion", "started_at", "completed_at", "html_url"
        )
    } | {
        "steps": [
            {key: step.get(key) for key in ("name", "number", "status", "conclusion", "started_at", "completed_at")}
            for step in job.get("steps", [])
        ]
    }

def terminal_reports(api, run):
    """Read summary/parts JSON only. Never fetch a native result chunk or archive."""
    prefix = "cloud-results-" + str(run["id"]) + "-" + str(run["run_attempt"]) + "-"
    refs = api.maybe("git/matching-refs/tags/" + prefix) or []
    assert isinstance(refs, list) and len(refs) <= 32
    reports = []
    for ref in refs:
        tag = ref["ref"].removeprefix("refs/tags/")
        assert tag.startswith(prefix) and re.fullmatch(r"[A-Za-z0-9_.-]+", tag)
        release = api.get("releases/tags/" + tag)
        record = {"tag": tag, "url": release["html_url"], "metadata": {}, "complete_descriptor": False}
        for suffix in (".summary.json", ".parts.json"):
            matches = [a for a in release["assets"] if a["name"].endswith(suffix)]
            if not matches:
                continue
            # Some publishers retain prerequisite summaries alongside their own result.
            exact_name = tag.removeprefix(prefix) + "-" + str(run["id"]) + "-" + str(run["run_attempt"]) + suffix
            exact = [a for a in matches if a["name"] == exact_name]
            if len(exact) == 1:
                matches = exact
            if len(matches) != 1:
                record.setdefault("metadata_skipped", {})[suffix] = {
                    "reason": "AMBIGUOUS_DESCRIPTOR", "downloaded": False,
                    "candidates": [{k: a.get(k) for k in ("id", "name", "size", "digest")} for a in matches],
                }
                continue
            asset = matches[0]
            assert type(asset["size"]) is int and asset["size"] > 0, "Invalid metadata size"
            if asset["size"] > LIMIT:
                record.setdefault("metadata_skipped", {})[suffix] = {
                    "reason": "OVERSIZED_DESCRIPTOR", "downloaded": False,
                    "asset": asset["id"], "name": asset["name"], "advertised_bytes": asset["size"],
                    "advertised_digest": asset.get("digest"), "limit_bytes": LIMIT,
                }
                continue
            raw = api.raw("releases/assets/" + str(asset["id"]), binary=True)
            digest = hashlib.sha256(raw).hexdigest()
            assert len(raw) == asset["size"]
            if asset.get("digest"):
                assert asset["digest"] == "sha256:" + digest
            data = json.loads(raw)
            if suffix == ".summary.json":
                assert data.get("source_head") in (None, run["head_sha"]), "Summary belongs to another source"
                record["native_status"] = data.get("status")
                record["native_error"] = str(data.get("error", ""))[:2000]
                record["sources_unchanged"] = data.get("sources_unchanged")
                record["product_acceptance_inferred"] = False
            else:
                record["part_count"] = len(data.get("parts", []))
            record["metadata"][suffix] = {"asset": asset["id"], "bytes": len(raw), "sha256": digest}
        record["complete_descriptor"] = len(record["metadata"]) == 2
        if record.get("metadata_skipped"):
            record["note"] = "Descriptor content remains unverified; bounded observation skipped it without downloading"
        elif not record["complete_descriptor"]:
            record["note"] = "Publication is incomplete; partial assets are not completion evidence"
        reports.append(record)
    return reports

def select_runs(api, config):
    selected = {item["run"]: dict(item, selection="pinned") for item in config["runs"]}
    missing = []
    for item in config["latest_workflows"]:
        path = "actions/workflows/" + item["workflow"] + "/runs?branch=" + urllib.parse.quote(item["branch"], safe="") + "&per_page=10"
        if item.get("event"):
            path += "&event=" + item["event"]
        data = api.maybe(path)
        candidates = [] if data is None else data["workflow_runs"]
        if not candidates:
            missing.append({"workflow": item["workflow"], "optional": item["optional"], "reason": "No run exists; no automatic engineering action"})
            continue
        if item.get("event"):
            candidates = [r for r in candidates if r["event"] == item["event"]]
        if not candidates:
            missing.append({"workflow": item["workflow"], "optional": item["optional"], "reason": "No production event exists; push controls are not native completion"})
            continue
        newest = max(candidates, key=lambda r: (time_value(r["created_at"]), r["id"]))
        assert newest["head_branch"] == item["branch"]
        current = selected.get(newest["id"])
        if current is None:
            selected[newest["id"]] = {
                "run": newest["id"], "label": item["label"], "branch": newest["head_branch"],
                "head_sha": newest["head_sha"], "selection": "latest_workflow",
                "production_jobs": item.get("production_jobs", []),
            }
        else:
            current.setdefault("also_selected_by", []).append(item["workflow"])
    return list(selected.values()), missing

def previous_snapshot(api, current_run):
    artifacts = api.pages("actions/artifacts?name=" + ARTIFACT, "artifacts", maximum=1000)
    for artifact in sorted(artifacts, key=lambda a: a["created_at"], reverse=True):
        if artifact["expired"] or artifact["workflow_run"]["id"] == current_run:
            continue
        if artifact["name"] != ARTIFACT or artifact["size_in_bytes"] > LIMIT:
            continue
        source = api.get("actions/runs/" + str(artifact["workflow_run"]["id"]))
        if source["path"] != WORKFLOW or source["status"] != "completed":
            continue
        if source["head_branch"] not in ("main", "codex/cloud-progress-monitor"):
            continue
        # Actions archive endpoint requires the normal GitHub API Accept header;
        # only release assets use application/octet-stream at the API hop.
        packed = api.raw("actions/artifacts/" + str(artifact["id"]) + "/zip")
        packed_sha = hashlib.sha256(packed).hexdigest()
        if artifact.get("digest"):
            assert artifact["digest"] == "sha256:" + packed_sha, "Monitor artifact digest changed"
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            assert archive.namelist() == ["result.json"], "Unexpected monitor artifact contents"
            item = archive.getinfo("result.json")
            assert item.file_size <= LIMIT and ((item.external_attr >> 16) & 0o170000) != 0o120000
            data = json.loads(archive.read(item))
        assert data["schema"] == 1 and data["repository"] == REPO
        assert data["target_branch"] == "codex/complete-open-work"
        # A failed/partial monitor can still contain verified completed rows.
        # Per-row exact inventory identity gates reuse; status is not authority.
        assert isinstance(data.get("runs"), list), "Snapshot run inventory"
        if data.get("status") == "MONITOR_ERROR" and not data["runs"]:
            continue
        data["_artifact_source"] = dict(id=artifact["id"], run=source["id"], sha256=packed_sha)
        return data
    return None

def progress_signature(item):
    return (
        item["status"], item.get("conclusion"), item["classification"],
        tuple((j["id"], j["status"], j["conclusion"], tuple((s["number"], s["status"], s["conclusion"]) for s in j["steps"])) for j in item["jobs"]),
        tuple((r["tag"], r.get("native_status"), tuple(sorted((k, v["sha256"]) for k, v in r["metadata"].items())),
               json.dumps(r.get("metadata_skipped", {}), sort_keys=True)) for r in item["reports"]),
    )

def main_monitor_refusal(item, run, jobs):
    """Only this repository's actual read-only monitor may be observed on main.

    Other historical main handles remain visible as rejected rows. They are not
    native results and must never trigger release or artifact acquisition.
    """
    required = item.get("production_jobs")
    if not (type(required) is list and len(required) == 2
            and all(type(name) is str for name in required)
            and set(required) == MONITOR_JOBS):
        return "Main observation requires exactly controls/observe inventory jobs"
    if type(run.get("workflow_id")) is not int or run["workflow_id"] != WORKFLOW_ID or run.get("path") != WORKFLOW:
        return "Main run is not the pinned read-only cloud-progress-monitor workflow"
    if run.get("event") not in ("schedule", "workflow_dispatch"):
        return "Main monitor event is not scheduled or manually dispatched observation"
    names = [j.get("name") for j in jobs]
    if any(type(name) is not str or name not in MONITOR_JOBS for name in names) or len(names) != len(set(names)):
        return "Main monitor contains an unrelated or duplicate job name"
    if run["status"] == "completed" and set(names) != MONITOR_JOBS:
        return "Completed main monitor lacks its controls/observe jobs"
    return None


def collect(api, config, now, previous=None, configuration_source=None):
    check_config(config)
    branch = config["target_branch"]
    head = configuration_source["head_sha"] if configuration_source else api.get("git/ref/heads/" + branch)["object"]["sha"]
    assert re.fullmatch(r"[0-9a-f]{40}", head)
    selected, missing = select_runs(api, config)
    old = {} if previous is None else {r["id"]: r for r in previous["runs"]}
    result = {
        "schema": 1, "repository": REPO, "target_branch": branch, "target_head": head,
        "configuration_source": configuration_source,
        "previous_snapshot_source": None if previous is None else previous.get("_artifact_source"),
        "inventory_version": config["inventory_version"],
        "inventory_updated_at": config["inventory_updated_at"],
        "observed_at": now.isoformat(), "monitor_source": os.environ.get("GITHUB_SHA"),
        "monitor_run": os.environ.get("GITHUB_RUN_ID"), "runs": [], "missing_selectors": missing,
        "automatic_native_dispatch": False, "full_phy_accepted": False, "final_timing_accepted": False,
        "scope": "Read-only progress and terminal metadata. No native restart, cancellation, dispatch, acceptance or arbitrary engineering repair.",
    }
    for item in selected:
        run = api.get("actions/runs/" + str(item["run"]))
        assert run["id"] == item["run"] and run["head_sha"] == item["head_sha"] and run["head_branch"] == item["branch"], "Observed run ID/source/branch differs from pinned inventory: " + str(item["run"])
        jobs = api.pages("actions/runs/" + str(run["id"]) + "/attempts/" + str(run["run_attempt"]) + "/jobs", "jobs")
        category, reason = classify(run, jobs, now, config["stall_seconds"])
        main_observation = item["branch"] == "main"
        refusal = main_monitor_refusal(item, run, jobs) if main_observation else None
        required_jobs = [] if refusal else item.get("production_jobs", [])
        production = [j for j in jobs if j["name"] in required_jobs and j.get("conclusion") != "skipped"]
        if required_jobs and not production and category == "COMPLETED_ACTIONS":
            category, reason = "NOT_EXECUTED", "Production job absent or skipped; control-job success is not native completion"
        if refusal:
            category, reason = "UNVERIFIED_REF", refusal
        elif main_observation and category == "COMPLETED_ACTIONS":
            if all(j.get("status") == "completed" and j.get("conclusion") == "success" for j in jobs):
                category, reason = "COMPLETED_MONITOR", "Read-only monitor jobs succeeded; no native or product acceptance"
            else:
                category, reason = "NOT_EXECUTED", "Monitor controls/observe did not both complete successfully"
        reports = terminal_reports(api, run) if run["status"] == "completed" and not main_observation else []
        statuses = [r.get("native_status") or "" for r in reports]
        if any(s.startswith(("FAIL", "ERROR", "REJECT")) for s in statuses):
            category, reason = "FAILED_NATIVE_REPORT", "A terminal native report explicitly failed"
        record = {
            key: run.get(key) for key in (
                "id", "name", "head_branch", "head_sha", "path", "status", "conclusion",
                "run_attempt", "run_started_at", "updated_at", "html_url",
            )
        } | {
            "label": item["label"], "selection": item["selection"], "classification": category,
            "reason": reason, "jobs": [job_record(j) for j in jobs], "reports": reports,
            "publication_verified": bool(reports) and all(r["complete_descriptor"] for r in reports),
        }
        if category == "COMPLETED_ACTIONS" and any(r.get("metadata_skipped") for r in reports):
            record["classification"] = "UNVERIFIED_TERMINAL_METADATA"
            record["reason"] = "Terminal descriptor exceeds the bounded reader or is ambiguous; detailed review required"
        elif category == "COMPLETED_ACTIONS" and not record["publication_verified"]:
            record["classification"] = "INCOMPLETE_PUBLICATION"
            record["reason"] = "Actions succeeded without every expected terminal summary/parts pair"
        record["changed_since_previous"] = run["id"] not in old or progress_signature(record) != progress_signature(old[run["id"]])
        result["runs"].append(record)
    problems = [r["id"] for r in result["runs"] if r["classification"].startswith(("FAILED", "STALLED", "INCOMPLETE", "UNVERIFIED"))]
    absent_required = [m["workflow"] for m in missing if not m["optional"]]
    result["problem_runs"] = problems
    result["missing_required_workflows"] = absent_required
    result["status"] = "ATTENTION_REQUIRED" if problems or absent_required else "OBSERVED_NO_CURRENT_FAILURE"
    result["routine_unchanged"] = previous is not None and all(not r["changed_since_previous"] for r in result["runs"]) and previous["target_head"] == head
    return result

class ObservationLimit(RuntimeError):
    """Expected read-only checkpoint boundary, never a native engineering action."""

class ReadBudget:
    def __init__(self, clock=None, emit=None, max_requests=600, seconds=540):
        self.clock = clock or time.monotonic
        self.emit = emit or (lambda event: None)
        self.started = self.clock()
        self.max_requests = max_requests
        self.seconds = seconds
        self.requests = 0
        self.inflight = None

    def before(self, path):
        # API.raw has a 60-second timeout. Never start a call that cannot fit.
        if self.requests >= self.max_requests or self.clock() - self.started + 60 >= self.seconds:
            raise ObservationLimit("Bounded GET/wall-time budget reached before the next request")
        self.requests += 1
        self.inflight = path
        self.emit(dict(event="GET_START", path=path, **self.report()))

    def after(self, path, error):
        self.inflight = None
        self.emit(dict(event="GET_END", path=path, error_type=error, **self.report()))

    def report(self):
        return dict(requests=self.requests, maximum_requests=self.max_requests,
                    elapsed_seconds=max(0, self.clock()-self.started), maximum_seconds=self.seconds,
                    per_request_timeout_seconds=60, inflight=self.inflight)


def inventory_identity(item):
    """Selection policy is part of identity; a previous target HEAD need not match."""
    return dict(run=item["run"], branch=item["branch"], head_sha=item["head_sha"],
                production_jobs=list(item.get("production_jobs", [])),
                selection=item.get("selection", "pinned"))


def cached_row(item, previous):
    if previous is None:
        return None
    rows = [r for r in previous.get("runs", []) if r.get("id") == item["run"]]
    if len(rows) != 1:
        return None
    row = rows[0]
    if (row.get("inventory_identity") != inventory_identity(item)
            or row.get("head_sha") != item["head_sha"] or row.get("head_branch") != item["branch"]
            or row.get("status") not in ("completed", "in_progress", "queued", "waiting", "pending", "requested")
            or not row.get("last_observed_at") or not isinstance(row.get("jobs"), list)
            or not isinstance(row.get("reports"), list) or not row.get("classification")):
        return None
    try:
        time_value(row["last_observed_at"])
        progress_signature(row)
    except (ValueError, TypeError, KeyError):
        return None
    # Only rows originating in an actual successful observation are reusable.
    if row.get("observation_state") not in ("CURRENT", "CACHED", "REFRESH_ERROR"):
        return None
    value = copy.deepcopy(row)
    value.update(label=item["label"], selection=item.get("selection", "pinned"),
                 observation_state="CACHED", stale=True, changed_since_previous=None,
                 current_publication_reverified=False,
                 cache_source=copy.deepcopy(previous.get("_artifact_source")),
                 cache_note="Historical observation; run attempts and release metadata were not re-read in this observation")
    value.pop("refresh_error", None)
    return value


def unseen_row(item):
    return dict(id=item["run"], label=item["label"], head_sha=item["head_sha"],
                head_branch=item["branch"], selection=item.get("selection", "pinned"),
                inventory_identity=inventory_identity(item), status="unobserved", conclusion=None,
                classification="UNOBSERVED_CURRENT", reason="No authenticated observation of this inventory identity yet",
                html_url="https://github.com/"+REPO+"/actions/runs/"+str(item["run"]),
                jobs=[], reports=[], publication_verified=False, current_publication_reverified=False,
                changed_since_previous=None, observation_state="UNOBSERVED", stale=True, last_observed_at=None)


def initial_snapshot(config, configuration_source=None):
    return dict(schema=1, repository=REPO, target_branch=config["target_branch"],
                target_head=(configuration_source or {}).get("head_sha"), configuration_source=configuration_source,
                inventory_version=config["inventory_version"], inventory_updated_at=config["inventory_updated_at"],
                observed_at=utc_now().isoformat(), monitor_source=os.environ.get("GITHUB_SHA"),
                monitor_run=os.environ.get("GITHUB_RUN_ID"), runs=[unseen_row(r) for r in config["runs"]],
                missing_selectors=[], missing_required_workflows=[], problem_runs=[], current_problem_runs=[],
                errors=[], previous_snapshot_source=None, status="PARTIAL_OBSERVATION", routine_unchanged=False,
                observation_complete=False, selectors_complete=False, phase="bootstrap",
                automatic_native_dispatch=False, full_phy_accepted=False, final_timing_accepted=False,
                scope="Read-only bounded progress. Cached history is explicitly stale; no native repair or product acceptance.")


def finalize_snapshot(result, budget=None):
    rows = result["runs"]
    result["problem_runs"] = [r["id"] for r in rows if r["classification"].startswith(("FAILED", "STALLED", "INCOMPLETE", "UNVERIFIED"))]
    result["current_problem_runs"] = [r["id"] for r in rows if r["id"] in result["problem_runs"] and r["observation_state"] == "CURRENT"]
    result["cached_problem_runs"] = [r["id"] for r in rows if r["id"] in result["problem_runs"] and r["observation_state"] != "CURRENT"]
    result["unobserved_runs"] = [r["id"] for r in rows if r["observation_state"] == "UNOBSERVED"]
    result["cached_runs"] = [r["id"] for r in rows if r["observation_state"] == "CACHED"]
    result["refreshed_runs"] = [r["id"] for r in rows if r["observation_state"] == "CURRENT"]
    result["refresh_error_runs"] = [r["id"] for r in rows if r["observation_state"] == "REFRESH_ERROR"]
    result["missing_required_workflows"] = [m["workflow"] for m in result["missing_selectors"] if not m["optional"]]
    result["observation_complete"] = bool(result["selectors_complete"] and not result["errors"] and all(r["observation_state"] == "CURRENT" for r in rows))
    result["routine_unchanged"] = bool(result["observation_complete"] and result.get("previous_target_head") == result["target_head"] and all(r["changed_since_previous"] is False for r in rows))
    partial = bool(result["unobserved_runs"] or result["refresh_error_runs"] or result["errors"] or not result["selectors_complete"])
    result["status"] = ("PARTIAL_OBSERVATION" if partial else "ATTENTION_REQUIRED" if result["problem_runs"] or result["missing_required_workflows"] else "OBSERVED_WITH_CACHED_HISTORY" if result["cached_runs"] else "OBSERVED_NO_CURRENT_FAILURE")
    result["checkpoint_at"] = utc_now().isoformat()
    if budget is not None:
        result["read_budget"] = budget.report()
    return result


def observation_order(selected, rows, previous):
    """Priority work alternates with history, so a busy active set cannot starve it."""
    by_id = {r["id"]: r for r in rows}
    recent = {r["run"] for r in sorted(selected, key=lambda r: r["run"], reverse=True)[:16]}
    priority = sorted([r for r in selected if r.get("selection") == "latest_workflow"
                       or (by_id[r["run"]]["status"] not in ("completed", "unobserved"))
                       or (r["run"] in recent and by_id[r["run"]]["observation_state"] == "UNOBSERVED")],
                      key=lambda r: (by_id[r["run"]]["status"] in ("completed", "unobserved"), -r["run"]))
    priority_ids = {r["run"] for r in priority}
    history = sorted([r for r in selected if r["run"] not in priority_ids], key=lambda r: r["run"])
    cursor = (previous or {}).get("next_history_run")
    if history and type(cursor) is int:
        offset = next((i for i,r in enumerate(history) if r["run"] >= cursor), 0)
        history = history[offset:] + history[:offset]
    # All unknown history is eligible; completed cached entries get a bounded,
    # rotating refresh quota. The complete cached inventory remains in result.
    cached = 0
    eligible = []
    for item in history:
        if by_id[item["run"]]["observation_state"] == "CACHED":
            cached += 1
            if cached > 16:
                continue
        eligible.append(item)
    order = []
    while priority or eligible:
        order.extend((priority.pop(0), False) for _ in range(min(2, len(priority))))
        if eligible:
            order.append((eligible.pop(0), True))
    return order, history


def observe_incrementally(api, config, previous, configuration_source, save, budget=None):
    check_config(config)
    result = initial_snapshot(config, configuration_source)
    result.update(previous_snapshot_source=None if previous is None else previous.get("_artifact_source"),
                  previous_target_head=None if previous is None else previous.get("target_head"), phase="selecting")
    selected = [dict(r, selection="pinned") for r in config["runs"]]
    result["runs"] = [cached_row(r, previous) or unseen_row(r) for r in selected]
    def checkpoint():
        finalize_snapshot(result, budget)
        save(result)
    checkpoint()
    # One selector per checkpoint; a later failure cannot discard earlier rows.
    for selector in config["latest_workflows"]:
        try:
            subset = dict(config, runs=selected, latest_workflows=[selector])
            candidates, missing = select_runs(api, subset)
            existing = {r["run"] for r in selected}
            for item in candidates:
                if item["run"] not in existing:
                    selected.append(item)
                    result["runs"].append(cached_row(item, previous) or unseen_row(item))
            result["missing_selectors"].extend(missing)
        except ObservationLimit as error:
            result["errors"].append(dict(phase="selecting", type=type(error).__name__, detail=str(error)))
            checkpoint()
            return result
        except Exception as error:
            result["errors"].append(dict(phase="selecting", selector=selector["workflow"], type=type(error).__name__, detail=str(error)))
        checkpoint()
    result["selectors_complete"] = not any(e["phase"] == "selecting" for e in result["errors"])
    result["phase"] = "observing"
    positions = {r["id"]: i for i,r in enumerate(result["runs"])}
    order, history = observation_order(selected, result["runs"], previous)
    result["next_history_run"] = history[0]["run"] if history else None
    checkpoint()
    for item, historical in order:
        rid = item["run"]
        try:
            one = dict(config, runs=[item], latest_workflows=[])
            cached = cached_row(item, previous)
            prior = None if cached is None else dict(previous, runs=[cached])
            observed = collect(api, one, utc_now(), prior, configuration_source)["runs"][0]
            observed.update(inventory_identity=inventory_identity(item), selection=item.get("selection", "pinned"),
                            observation_state="CURRENT", stale=False, last_observed_at=utc_now().isoformat(),
                            current_publication_reverified=observed["publication_verified"], cache_source=None)
            result["runs"][positions[rid]] = observed
        except ObservationLimit as error:
            result["errors"].append(dict(phase="observing", run=rid, type=type(error).__name__, detail=str(error)))
            # Keep the not-yet-read historical item as the next cursor.
            if historical:
                result["next_history_run"] = rid
            checkpoint()
            return result
        except Exception as error:
            row = result["runs"][positions[rid]]
            row.update(refresh_error=dict(type=type(error).__name__, detail=str(error)), changed_since_previous=None)
            if row["observation_state"] != "UNOBSERVED":
                row["observation_state"] = "REFRESH_ERROR"
            result["errors"].append(dict(phase="observing", run=rid, **row["refresh_error"]))
        if historical:
            i = next(i for i,r in enumerate(history) if r["run"] == rid)
            result["next_history_run"] = history[(i+1) % len(history)]["run"]
        checkpoint()
    result["phase"] = "finished"
    checkpoint()
    return result


def atomic_snapshot(path, value):
    encoded = (json.dumps(value, indent=2, allow_nan=False)+"\n").encode()
    temporary = path.with_name(path.name+".pending")
    with temporary.open("wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def signal_limit(signum, frame):
    raise ObservationLimit("Checkpoint requested by signal "+str(signum))


def markdown(result):
    lines = [
        "# Cloud progress observation", "",
        "Target branch: `" + result["target_branch"] + "`; HEAD `" + str(result["target_head"]) + "`.",
        "Observed: " + result["observed_at"],
        "Inventory version: " + str(result["inventory_version"]) + "; bootstrap: " + str((result.get("configuration_source") or {}).get("bootstrap", "fixture")),
        "Previous cloud snapshot: " + str((result.get("previous_snapshot_source") or {}).get("id", "none")), "",
        "| Tracked work | Run | Observed state | Change |",
        "|---|---|---|---|",
    ]
    for row in result["runs"]:
        lines.append("| " + row["label"].replace("|", "/") + " | [" + str(row["id"]) + "](" + row["html_url"] + ") | " + row.get("observation_state", "CURRENT") + ": " + row["classification"] + " / " + str(row["conclusion"]) + " | " + ("not refreshed" if row["changed_since_previous"] is None else "changed" if row["changed_since_previous"] else "unchanged") + " |")
        for report in row["reports"]:
            lines.append("| terminal metadata | [" + report["tag"] + "](" + report["url"] + ") | " + str(report.get("native_status", "missing summary")).replace("|", "/") + " | " + ("summary+parts present" if report["complete_descriptor"] else "unverified descriptor" if report.get("metadata_skipped") else "incomplete publication") + " |")
    lines.extend(["", "Full serial PHY, main-chip integration and final timing are **not accepted by this monitor**.",
                  "This job observes progress. It cannot perform arbitrary engineering repairs and never dispatches, cancels or restarts native jobs."])
    if result["missing_selectors"]:
        lines.extend(["", "Workflows without a run: " + ", ".join(m["workflow"] + (" (optional)" if m["optional"] else " (required)") for m in result["missing_selectors"])])
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(".github/cloud-progress-monitor.json"))
    parser.add_argument("--out", type=Path, default=Path("cloud-progress-monitor"))
    args = parser.parse_args()
    assert os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
    assert os.environ["GITHUB_REPOSITORY"] == REPO
    config = json.loads(args.config.read_text())
    check_config(config)
    api = API(os.environ["GH_TOKEN"])
    args.out.mkdir(parents=True, exist_ok=True)
    state = initial_snapshot(config)
    def save(value):
        nonlocal state
        state = value
        atomic_snapshot(args.out / "result.json", state)
    def progress(event):
        event = dict(event, at=utc_now().isoformat())
        text = json.dumps(event, sort_keys=True)
        with (args.out / "progress.jsonl").open("a") as log:
            log.write(text+"\n")
            log.flush()
        print(text, flush=True)
    budget = ReadBudget(emit=progress)
    api.read_budget = budget
    configuration_source = None
    old_handlers = {}
    save(state)  # Durable even if immutable inventory or prior-artifact GET fails.
    try:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGALRM):
            old_handlers[sig] = signal.signal(sig, signal_limit)
        signal.alarm(600)  # Includes selector/previous-artifact reads; leaves 5 min to upload.
        state["phase"] = "loading_inventory"
        save(state)
        config, configuration_source = load_config(api, config)
        state = initial_snapshot(config, configuration_source)
        state["phase"] = "loading_previous_snapshot"
        save(state)
        previous = previous_snapshot(api, int(os.environ["GITHUB_RUN_ID"]))
        state = observe_incrementally(api, config, previous, configuration_source, save, budget)
    except ObservationLimit as exc:
        state.setdefault("errors", []).append(dict(phase=state.get("phase"), type=type(exc).__name__, detail=str(exc)))
        finalize_snapshot(state, budget)
        save(state)
    except BaseException as exc:
        detail = type(exc).__name__ + ": " + (str(exc) or repr(exc))
        state.setdefault("errors", []).append(dict(phase=state.get("phase"), type=type(exc).__name__, detail=detail))
        finalize_snapshot(state, budget)
        state.update(status="MONITOR_ERROR", error=detail, routine_unchanged=False, observation_complete=False)
        try:
            save(state)
            Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("Cloud observation failed: " + detail + "\nCompleted rows and unread inventory are preserved. No native work was changed.\n")
        except BaseException as secondary:
            print(json.dumps(dict(primary_error=detail, checkpoint_error=repr(secondary))), flush=True)
        raise
    finally:
        signal.alarm(0)
        for sig, previous_handler in old_handlers.items():
            signal.signal(sig, previous_handler)
    Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(markdown(state))
    print(json.dumps({"status": state["status"], "problem_runs": state["problem_runs"],
                      "read_budget": state["read_budget"], "automatic_native_dispatch": False}), flush=True)
    return 1 if state["status"] == "ATTENTION_REQUIRED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
