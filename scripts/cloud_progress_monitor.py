#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only progress observation. Never dispatch, restart, cancel or repair CAD jobs."""
import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = "Melihakbulut221/nssoc"
WORKFLOW = ".github/workflows/cloud-progress-monitor.yml"
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
        assert item["branch"].startswith("codex/")
    for item in config["latest_workflows"]:
        assert re.fullmatch(r"[a-z0-9-]+\.yml", item["workflow"])
        assert item["branch"] == config["target_branch"]
        assert isinstance(item["optional"], bool)
        assert item.get("event") in (None, "push", "workflow_dispatch")
        assert isinstance(item.get("production_jobs", []), list)
    assert config["automatic_native_dispatch"] is False

def load_config(api, bootstrap):
    """Pin the small working-branch inventory to one exact Git commit/blob."""
    branch = "codex/complete-open-work"
    head = api.get("git/ref/heads/" + branch)["object"]["sha"]
    path = ".github/cloud-progress-monitor.json"
    data = api.maybe("contents/" + path + "?ref=" + head)
    if data is None:
        check_config(bootstrap)
        return bootstrap, dict(branch=branch, head_sha=head, bootstrap=True,
            note="Working-branch inventory absent; using explicit reviewed bootstrap inventory")
    assert data["encoding"] == "base64" and data["size"] <= 65536
    raw = base64.b64decode(data["content"], validate=False)
    assert len(raw) == data["size"] <= 65536
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest() == data["sha"]
    config = json.loads(raw)
    check_config(config)
    return config, dict(branch=branch, head_sha=head, blob_sha=data["sha"],
        sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), bootstrap=False)

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
            assert len(matches) == 1, "Ambiguous terminal descriptor"
            asset = matches[0]
            assert 0 < asset["size"] <= LIMIT, "Oversized metadata; no bulk download"
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
        if not record["complete_descriptor"]:
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
        packed = api.raw("actions/artifacts/" + str(artifact["id"]) + "/zip", binary=True)
        with zipfile.ZipFile(io.BytesIO(packed)) as archive:
            assert archive.namelist() == ["result.json"], "Unexpected monitor artifact contents"
            item = archive.getinfo("result.json")
            assert item.file_size <= LIMIT and ((item.external_attr >> 16) & 0o170000) != 0o120000
            data = json.loads(archive.read(item))
        assert data["schema"] == 1 and data["repository"] == REPO
        assert data["target_branch"] == "codex/complete-open-work"
        return data
    return None

def progress_signature(item):
    return (
        item["status"], item.get("conclusion"), item["classification"],
        tuple((j["id"], j["status"], j["conclusion"], tuple((s["number"], s["status"], s["conclusion"]) for s in j["steps"])) for j in item["jobs"]),
        tuple((r["tag"], r.get("native_status"), tuple(sorted((k, v["sha256"]) for k, v in r["metadata"].items()))) for r in item["reports"]),
    )

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
        "inventory_version": config["inventory_version"],
        "inventory_updated_at": config["inventory_updated_at"],
        "observed_at": now.isoformat(), "monitor_source": os.environ.get("GITHUB_SHA"),
        "monitor_run": os.environ.get("GITHUB_RUN_ID"), "runs": [], "missing_selectors": missing,
        "automatic_native_dispatch": False, "full_phy_accepted": False, "final_timing_accepted": False,
        "scope": "Read-only progress and terminal metadata. No native restart, cancellation, dispatch, acceptance or arbitrary engineering repair.",
    }
    for item in selected:
        run = api.get("actions/runs/" + str(item["run"]))
        assert run["id"] == item["run"] and run["head_sha"] == item["head_sha"] and run["head_branch"] == item["branch"]
        jobs = api.pages("actions/runs/" + str(run["id"]) + "/attempts/" + str(run["run_attempt"]) + "/jobs", "jobs")
        category, reason = classify(run, jobs, now, config["stall_seconds"])
        required_jobs = item.get("production_jobs", [])
        production = [j for j in jobs if j["name"] in required_jobs and j.get("conclusion") != "skipped"]
        if required_jobs and not production and category == "COMPLETED_ACTIONS":
            category, reason = "NOT_EXECUTED", "Production job absent or skipped; control-job success is not native completion"
        reports = terminal_reports(api, run) if run["status"] == "completed" else []
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
        if category == "COMPLETED_ACTIONS" and not record["publication_verified"]:
            record["classification"] = "INCOMPLETE_PUBLICATION"
            record["reason"] = "Actions succeeded without every expected terminal summary/parts pair"
        record["changed_since_previous"] = run["id"] not in old or progress_signature(record) != progress_signature(old[run["id"]])
        result["runs"].append(record)
    problems = [r["id"] for r in result["runs"] if r["classification"].startswith(("FAILED", "STALLED", "INCOMPLETE"))]
    absent_required = [m["workflow"] for m in missing if not m["optional"]]
    result["problem_runs"] = problems
    result["missing_required_workflows"] = absent_required
    result["status"] = "ATTENTION_REQUIRED" if problems or absent_required else "OBSERVED_NO_CURRENT_FAILURE"
    result["routine_unchanged"] = previous is not None and all(not r["changed_since_previous"] for r in result["runs"]) and previous["target_head"] == head
    return result

def markdown(result):
    lines = [
        "# Cloud progress observation", "",
        "Target branch: `" + result["target_branch"] + "`; HEAD `" + result["target_head"] + "`.",
        "Observed: " + result["observed_at"], "",
        "| Tracked work | Run | Observed state | Change |",
        "|---|---|---|---|",
    ]
    for row in result["runs"]:
        lines.append("| " + row["label"].replace("|", "/") + " | [" + str(row["id"]) + "](" + row["html_url"] + ") | " + row["classification"] + " / " + str(row["conclusion"]) + " | " + ("changed" if row["changed_since_previous"] else "unchanged") + " |")
        for report in row["reports"]:
            lines.append("| terminal metadata | [" + report["tag"] + "](" + report["url"] + ") | " + str(report.get("native_status", "missing summary")).replace("|", "/") + " | " + ("summary+parts present" if report["complete_descriptor"] else "incomplete publication") + " |")
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
    try:
        config, configuration_source = load_config(api, config)
        previous = previous_snapshot(api, int(os.environ["GITHUB_RUN_ID"]))
        result = collect(api, config, utc_now(), previous, configuration_source)
    except Exception as exc:
        result = {"schema": 1, "repository": REPO, "target_branch": config["target_branch"],
                  "target_head": None, "runs": [], "observed_at": utc_now().isoformat(),
                  "status": "MONITOR_ERROR", "error": str(exc), "automatic_native_dispatch": False,
                  "full_phy_accepted": False, "problem_runs": []}
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text("Cloud observation failed: " + str(exc) + "\nNo native work was changed.\n")
        raise
    (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(markdown(result))
    print(json.dumps({"status": result["status"], "problem_runs": result["problem_runs"], "automatic_native_dispatch": False}))
    return 1 if result["status"] == "ATTENTION_REQUIRED" else 0

if __name__ == "__main__":
    raise SystemExit(main())
