#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Deterministic controls; network and native CAD execution are forbidden here."""
import copy
import base64
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cloud_progress_monitor as m

NOW = dt.datetime(2026, 10, 24, 12, tzinfo=dt.timezone.utc)
HEAD = "a" * 40

def config():
    return dict(schema=1, inventory_version=1, inventory_updated_at="2026-10-24T07:25:00Z", repository=m.REPO, target_branch="codex/complete-open-work",
                stall_seconds=21600, automatic_native_dispatch=False,
                runs=[dict(run=123, label="fixture", branch="codex/complete-open-work", head_sha=HEAD)],
                latest_workflows=[])

def run(status="in_progress", conclusion=None):
    return dict(id=123, name="native", head_sha=HEAD, head_branch="codex/complete-open-work",
                run_attempt=1, path=".github/workflows/native.yml", status=status, conclusion=conclusion,
                event="push", created_at="2026-10-24T10:00:00Z", run_started_at="2026-10-24T10:00:00Z",
                updated_at="2026-10-24T10:01:00Z", html_url="https://github.com/Melihakbulut221/nssoc/actions/runs/123")

def job(status="in_progress", started="2026-10-24T10:00:00Z", conclusion=None):
    return dict(id=456, name="native simulation", status=status, started_at=started,
                completed_at=None, conclusion=conclusion, steps=[
                    dict(name="native", number=1, status=status, conclusion=conclusion,
                         started_at=started, completed_at=None)])

class Mock:
    def __init__(self, state=None, jobs=None, summary=None, parts=None):
        self.state = state or run()
        self.jobs = jobs if jobs is not None else [job()]
        self.summary = summary if summary is not None else dict(status="PASS_NATIVE_FIXTURE", source_head=HEAD, sources_unchanged=True)
        self.parts = parts if parts is not None else dict(parts=[dict(name="forbidden.raw.part000")])
        self.calls = []
        self.payloads = {100: json.dumps(self.summary).encode(), 101: json.dumps(self.parts).encode()}
        self.assets = [dict(id=i, name="fixture" + suffix, size=len(self.payloads[i]),
                            digest="sha256:" + hashlib.sha256(self.payloads[i]).hexdigest())
                       for i, suffix in ((100, ".summary.json"), (101, ".parts.json"))]
        self.assets.append(dict(id=102, name="forbidden.raw.part000", size=999999999))
        self.refs = [dict(ref="refs/tags/cloud-results-123-1-native")]
        self.latest = dict(workflow_runs=[self.state])
        self.remote_config = None

    def get(self, path):
        self.calls.append(("get", path))
        if path == "git/ref/heads/codex/complete-open-work": return dict(object=dict(sha=HEAD))
        if path == "actions/runs/123": return copy.deepcopy(self.state)
        if path == "releases/tags/cloud-results-123-1-native":
            return dict(html_url="https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-123-1-native", assets=self.assets)
        raise AssertionError("Unexpected GET: " + path)

    def maybe(self, path):
        self.calls.append(("maybe", path))
        if path == "git/matching-refs/tags/cloud-results-123-1-": return self.refs
        if path.startswith("actions/workflows/"): return self.latest
        if path.startswith("contents/"): return self.remote_config
        raise AssertionError("Unexpected optional GET: " + path)

    def pages(self, path, key, maximum=1000):
        self.calls.append(("pages", path))
        assert path == "actions/runs/123/attempts/1/jobs" and key == "jobs"
        return copy.deepcopy(self.jobs)

    def raw(self, path, limit=m.LIMIT, binary=False):
        self.calls.append(("raw", path))
        assert binary and path in ("releases/assets/100", "releases/assets/101"), "Bulk asset access forbidden"
        return self.payloads[int(path.rsplit("/", 1)[1])]

class SmallResponse:
    def __init__(self, raw, declared=None):
        self.raw = io.BytesIO(raw)
        self.headers = {} if declared is None else {"Content-Length": str(declared)}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size): return self.raw.read(size)

class CaptureOpener:
    def __init__(self, response): self.response = response; self.requests = []
    def open(self, request, timeout):
        self.requests.append(request)
        return self.response

class SnapshotAPI:
    def __init__(self, members=None):
        body = m.collect(Mock(), config(), NOW)
        raw = io.BytesIO()
        with m.zipfile.ZipFile(raw, "w") as archive:
            for name, value in (members or {"result.json": json.dumps(body)}).items():
                archive.writestr(name, value)
        self.packed = raw.getvalue()
        self.artifact = dict(id=789, name=m.ARTIFACT, expired=False, size_in_bytes=len(self.packed),
            digest="sha256:" + hashlib.sha256(self.packed).hexdigest(),
            created_at="2026-10-24T11:00:00Z", workflow_run=dict(id=100))
        self.calls = []

    def pages(self, path, key, maximum=1000):
        assert path == "actions/artifacts?name=" + m.ARTIFACT and key == "artifacts"
        return [self.artifact]

    def get(self, path):
        assert path == "actions/runs/100"
        return dict(id=100, path=m.WORKFLOW, status="completed", head_branch="main")

    def raw(self, path, limit=m.LIMIT, binary=False):
        assert path == "actions/artifacts/789/zip"
        assert binary is False, "Actions artifact endpoint rejects release-asset octet-stream Accept header"
        self.calls.append(path)
        return self.packed

class Controls(unittest.TestCase):
    def test_previous_snapshot_roundtrip_and_digest(self):
        api = SnapshotAPI(); snapshot = m.previous_snapshot(api, 200)
        self.assertEqual(snapshot["_artifact_source"]["id"], 789)
        self.assertEqual(snapshot["_artifact_source"]["sha256"], hashlib.sha256(api.packed).hexdigest())
        self.assertEqual(snapshot["runs"][0]["id"], 123)

    def test_previous_snapshot_corrupt_digest_rejected(self):
        api = SnapshotAPI(); api.artifact["digest"] = "sha256:" + "f" * 64
        with self.assertRaises(AssertionError): m.previous_snapshot(api, 200)

    def test_previous_snapshot_unexpected_archive_member_rejected(self):
        api = SnapshotAPI({"unexpected.json": "{}"})
        with self.assertRaises(AssertionError): m.previous_snapshot(api, 200)

    def test_previous_monitor_error_not_used_as_progress_baseline(self):
        body = dict(schema=1, repository=m.REPO, target_branch="codex/complete-open-work",
                    status="MONITOR_ERROR", runs=[])
        self.assertIsNone(m.previous_snapshot(SnapshotAPI({"result.json": json.dumps(body)}), 200))

    def test_current_snapshot_never_reused(self):
        api = SnapshotAPI()
        self.assertIsNone(m.previous_snapshot(api, 100))
        self.assertEqual(api.calls, [])

    def test_real_api_request_is_repository_scoped_get(self):
        api = m.API("fixture-token"); api.opener = CaptureOpener(SmallResponse(b"{}", 2))
        self.assertEqual(api.get("actions/runs/123"), {})
        request = api.opener.requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, "https://api.github.com/repos/" + m.REPO + "/actions/runs/123")

    def test_path_escape_rejected_before_request(self):
        api = m.API("fixture-token"); api.opener = CaptureOpener(SmallResponse(b"{}"))
        for path in ("../other", "/outside", "https://attacker.invalid/"):
            with self.assertRaises(AssertionError): api.get(path)
        self.assertEqual(api.opener.requests, [])

    def test_http_body_limit_even_without_content_length(self):
        api = m.API("fixture-token"); api.opener = CaptureOpener(SmallResponse(b"12345"))
        with self.assertRaises(ValueError): api.raw("actions/runs/123", limit=4)

    def test_redirect_removes_authorization(self):
        request = m.urllib.request.Request("https://api.github.com/repos/" + m.REPO,
            headers={"Authorization": "Bearer fixture-secret"})
        redirected = m.SafeRedirect().redirect_request(request, None, 302, "", {},
            "https://release-assets.githubusercontent.com/fixture")
        self.assertIsNone(redirected.get_header("Authorization"))

    def test_redirect_rejects_external_or_unencrypted_host(self):
        request = m.urllib.request.Request("https://api.github.com/repos/" + m.REPO)
        for url in ("https://attacker.invalid/fixture", "http://release-assets.githubusercontent.com/fixture"):
            with self.assertRaises(ValueError): m.SafeRedirect().redirect_request(request, None, 302, "", {}, url)

    def test_real_config(self):
        m.check_config(json.loads(Path(".github/cloud-progress-monitor.json").read_text()))

    def test_remote_config_is_commit_and_blob_bound(self):
        api = Mock(); raw = json.dumps(config()).encode()
        api.remote_config = dict(encoding="base64", size=len(raw), content=base64.b64encode(raw).decode(),
                                 sha=hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest())
        actual, proof = m.load_config(api, config())
        self.assertEqual(actual, config()); self.assertFalse(proof["bootstrap"])
        self.assertEqual(proof["head_sha"], HEAD)
        self.assertEqual(proof["sha256"], hashlib.sha256(raw).hexdigest())

    def test_remote_config_corrupt_blob_rejected(self):
        api = Mock(); raw = json.dumps(config()).encode()
        api.remote_config = dict(encoding="base64", size=len(raw), content=base64.b64encode(raw).decode(), sha="f" * 40)
        with self.assertRaises(AssertionError): m.load_config(api, config())

    def test_absent_remote_config_explicit_bootstrap(self):
        actual, proof = m.load_config(Mock(), config())
        self.assertTrue(proof["bootstrap"])
        self.assertEqual(actual, config())

    def test_inventory_version_required(self):
        c = config(); del c["inventory_version"]
        with self.assertRaises(AssertionError): m.check_config(c)

    def test_push_controls_not_manual_reader(self):
        c = config(); c["latest_workflows"] = [dict(label="reader", workflow="reader.yml",
            branch=c["target_branch"], optional=True, event="workflow_dispatch", production_jobs=["completed-reader"])]
        api = Mock(); api.latest = dict(workflow_runs=[run("completed", "success")])
        r = m.collect(api, c, NOW)
        self.assertEqual(len(r["runs"]), 1)
        self.assertEqual(len(r["missing_selectors"]), 1)
        self.assertIn("No production event", r["missing_selectors"][0]["reason"])

    def test_skipped_production_is_not_native_completion(self):
        c = config(); c["runs"][0]["production_jobs"] = ["native simulation"]
        r = m.collect(Mock(run("completed", "success"), [job("completed", conclusion="skipped")]), c, NOW)
        self.assertEqual(r["runs"][0]["classification"], "NOT_EXECUTED")
        self.assertFalse(r["full_phy_accepted"])

    def test_failed_missing_or_skipped_production_stays_failed(self):
        c = config(); c["runs"][0]["production_jobs"] = ["native simulation"]
        for conclusion in ("failure", "cancelled", "timed_out", "action_required"):
            for jobs in ([], [job("completed", conclusion="skipped")]):
                with self.subTest(conclusion=conclusion, jobs=jobs):
                    r = m.collect(Mock(run("completed", conclusion), jobs), c, NOW)
                    self.assertEqual(r["runs"][0]["classification"], "FAILED")
                    self.assertEqual(r["status"], "ATTENTION_REQUIRED")
                    self.assertEqual(r["problem_runs"], [123])

    def test_duplicate_pinned_run_rejected(self):
        c = config(); c["runs"] *= 2
        with self.assertRaises(AssertionError): m.check_config(c)

    def test_wrong_repository_rejected(self):
        c = config(); c["repository"] = "other/repo"
        with self.assertRaises(AssertionError): m.check_config(c)

    def test_native_dispatch_rejected(self):
        c = config(); c["automatic_native_dispatch"] = True
        with self.assertRaises(AssertionError): m.check_config(c)

    def test_short_stall_threshold_rejected(self):
        c = config(); c["stall_seconds"] = 10
        with self.assertRaises(AssertionError): m.check_config(c)

    def test_live_does_not_read_releases(self):
        api = Mock(); r = m.collect(api, config(), NOW)
        self.assertEqual(r["status"], "OBSERVED_NO_CURRENT_FAILURE")
        self.assertEqual(r["runs"][0]["classification"], "RUNNING")
        self.assertFalse(any("release" in p for _, p in api.calls))

    def test_pending_not_failed(self):
        r = m.collect(Mock(run("queued"), []), config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "PENDING")
        self.assertEqual(r["problem_runs"], [])

    def test_active_six_hour_boundary_not_stalled(self):
        r = m.collect(Mock(jobs=[job(started="2026-10-24T06:00:00Z")]), config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "RUNNING")

    def test_active_beyond_six_hours_stalled(self):
        r = m.collect(Mock(jobs=[job(started="2026-10-24T05:59:59Z")]), config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "STALLED_OVER_6H")
        self.assertEqual(r["problem_runs"], [123])

    def test_old_workflow_new_running_job_not_stalled(self):
        state = run(); state["run_started_at"] = "2026-10-23T00:00:00Z"
        r = m.collect(Mock(state), config(), NOW)
        self.assertEqual(r["problem_runs"], [])

    def test_completed_failed_job_in_live_workflow(self):
        r = m.collect(Mock(jobs=[job("completed", conclusion="failure"), job()]), config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "FAILED_JOB")

    def test_failure_conclusions(self):
        for conclusion in sorted(m.TERMINAL_BAD):
            with self.subTest(conclusion=conclusion):
                r = m.collect(Mock(run("completed", conclusion)), config(), NOW)
                self.assertEqual(r["runs"][0]["classification"], "FAILED")

    def test_overall_success_does_not_hide_failed_job(self):
        r = m.collect(Mock(run("completed", "success"), [job("completed", conclusion="failure")]), config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "FAILED_JOB")
        self.assertEqual(r["status"], "ATTENTION_REQUIRED")

    def test_terminal_native_failure(self):
        api = Mock(run("completed", "success"), summary=dict(status="FAIL_OR_ERROR", source_head=HEAD))
        r = m.collect(api, config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "FAILED_NATIVE_REPORT")

    def test_terminal_success_is_not_phy_acceptance(self):
        api = Mock(run("completed", "success"))
        r = m.collect(api, config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "COMPLETED_ACTIONS")
        self.assertFalse(r["full_phy_accepted"])
        self.assertFalse(r["final_timing_accepted"])
        self.assertTrue(r["runs"][0]["publication_verified"])
        self.assertEqual([p for kind, p in api.calls if kind == "raw"], ["releases/assets/100", "releases/assets/101"])

    def test_terminal_partial_publication_not_complete(self):
        api = Mock(run("completed", "success")); api.assets = api.assets[:1]
        r = m.collect(api, config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "INCOMPLETE_PUBLICATION")
        self.assertFalse(r["runs"][0]["publication_verified"])

    def test_terminal_no_publication_not_complete(self):
        api = Mock(run("completed", "success")); api.refs = []
        r = m.collect(api, config(), NOW)
        self.assertEqual(r["runs"][0]["classification"], "INCOMPLETE_PUBLICATION")

    def test_summary_hash_corruption_rejected(self):
        api = Mock(run("completed", "success")); api.assets[0]["digest"] = "sha256:" + "f" * 64
        with self.assertRaises(AssertionError): m.collect(api, config(), NOW)

    def test_summary_size_corruption_rejected(self):
        api = Mock(run("completed", "success")); api.assets[0]["size"] += 1
        with self.assertRaises(AssertionError): m.collect(api, config(), NOW)

    def test_oversize_summary_never_downloaded(self):
        api = Mock(run("completed", "success")); api.assets[0]["size"] = m.LIMIT + 1
        result = m.collect(api, config(), NOW)
        row = result["runs"][0]; report = row["reports"][0]
        self.assertEqual(row["classification"], "UNVERIFIED_TERMINAL_METADATA")
        self.assertFalse(row["publication_verified"])
        self.assertEqual(result["problem_runs"], [123])
        self.assertEqual(report["metadata_skipped"][".summary.json"]["reason"], "OVERSIZED_DESCRIPTOR")
        self.assertNotIn(("raw", "releases/assets/100"), api.calls)
        self.assertIn(("raw", "releases/assets/101"), api.calls)
        self.assertNotIn("native_status", report)

    def test_oversize_parts_preserves_native_failure(self):
        api = Mock(run("completed", "success"), summary=dict(status="FAIL_REAL_GATE", source_head=HEAD))
        api.assets[1]["size"] = m.LIMIT + 1
        result = m.collect(api, config(), NOW)
        self.assertEqual(result["runs"][0]["classification"], "FAILED_NATIVE_REPORT")
        self.assertNotIn(("raw", "releases/assets/101"), api.calls)
        self.assertFalse(result["runs"][0]["publication_verified"])

    def test_exact_own_summary_ignores_prerequisite_descriptor(self):
        api = Mock(run("completed", "success"))
        api.assets[0]["name"] = "native-123-1.summary.json"
        api.assets.append(dict(id=999, name="qualified-zero-OP.summary.json", size=999999999))
        result = m.collect(api, config(), NOW)
        self.assertTrue(result["runs"][0]["publication_verified"])
        self.assertNotIn(("raw", "releases/assets/999"), api.calls)

    def test_ambiguous_summary_is_unverified_without_fetch(self):
        api = Mock(run("completed", "success"))
        api.assets.append(dict(id=999, name="other.summary.json", size=123))
        result = m.collect(api, config(), NOW)
        row = result["runs"][0]
        self.assertEqual(row["classification"], "UNVERIFIED_TERMINAL_METADATA")
        self.assertEqual(row["reports"][0]["metadata_skipped"][".summary.json"]["reason"], "AMBIGUOUS_DESCRIPTOR")
        self.assertNotIn(("raw", "releases/assets/100"), api.calls)
        self.assertNotIn(("raw", "releases/assets/999"), api.calls)

    def test_changed_skipped_metadata_is_progress_without_download(self):
        before = Mock(run("completed", "success")); before.assets[0]["size"] = m.LIMIT + 1
        old = m.collect(before, config(), NOW)
        same = Mock(run("completed", "success")); same.assets[0]["size"] = m.LIMIT + 1
        self.assertTrue(m.collect(same, config(), NOW, old)["routine_unchanged"])
        same.assets[0]["size"] += 1
        result = m.collect(same, config(), NOW, old)
        self.assertTrue(result["runs"][0]["changed_since_previous"])
        self.assertNotIn(("raw", "releases/assets/100"), same.calls)

    def test_wrong_summary_source_rejected(self):
        api = Mock(run("completed", "success"), summary=dict(status="PASS", source_head="f" * 40))
        with self.assertRaises(AssertionError): m.collect(api, config(), NOW)

    def test_wrong_run_source_rejected(self):
        state = run(); state["head_sha"] = "f" * 40
        with self.assertRaises(AssertionError): m.collect(Mock(state), config(), NOW)

    def test_wrong_run_branch_rejected(self):
        state = run(); state["head_branch"] = "main"
        with self.assertRaises(AssertionError): m.collect(Mock(state), config(), NOW)

    def test_selector_deduplicates_live_pinned_run(self):
        c = config(); c["latest_workflows"] = [dict(label="latest", workflow="native.yml", branch=c["target_branch"], optional=False)]
        r = m.collect(Mock(), c, NOW)
        self.assertEqual(len(r["runs"]), 1)

    def test_missing_optional_pipeline_not_failure(self):
        c = config(); c["latest_workflows"] = [dict(label="latest", workflow="native.yml", branch=c["target_branch"], optional=True)]
        api = Mock(); api.latest = None
        r = m.collect(api, c, NOW)
        self.assertEqual(r["missing_required_workflows"], [])
        self.assertEqual(r["status"], "OBSERVED_NO_CURRENT_FAILURE")

    def test_missing_required_pipeline_is_attention(self):
        c = config(); c["latest_workflows"] = [dict(label="latest", workflow="native.yml", branch=c["target_branch"], optional=False)]
        api = Mock(); api.latest = None
        r = m.collect(api, c, NOW)
        self.assertEqual(r["status"], "ATTENTION_REQUIRED")

    def test_unchanged_observation_quiet(self):
        old = m.collect(Mock(), config(), NOW)
        current = m.collect(Mock(), config(), NOW + dt.timedelta(minutes=1), old)
        self.assertTrue(current["routine_unchanged"])
        self.assertFalse(current["runs"][0]["changed_since_previous"])

    def test_completed_step_is_progress(self):
        old = m.collect(Mock(), config(), NOW)
        api = Mock(); api.jobs[0]["steps"][0]["conclusion"] = "success"
        api.jobs[0]["steps"][0]["status"] = "completed"
        current = m.collect(api, config(), NOW, old)
        self.assertTrue(current["runs"][0]["changed_since_previous"])

    def test_changed_terminal_metadata_is_progress(self):
        old = m.collect(Mock(run("completed", "success")), config(), NOW)
        api = Mock(run("completed", "success"), summary=dict(status="FAIL_FRESH_NATIVE_GATE", source_head=HEAD))
        current = m.collect(api, config(), NOW, old)
        self.assertTrue(current["runs"][0]["changed_since_previous"])

    def test_summary_has_explicit_scope(self):
        text = m.markdown(m.collect(Mock(), config(), NOW))
        self.assertIn("not accepted by this monitor", text)
        self.assertIn("never dispatches", text)


# This is the complete original root inventory, not a reduced demonstration fixture.
FROZEN_INVENTORY = Path(__file__).resolve().parent / "fixtures/cloud-progress-monitor-296-v91.json"
FROZEN_ROOT = "9f641953a87f783e64155fce00891fe475c1b374"
FROZEN_SHA256 = "ce008b7e97abf71705706c0c9bed0d20eb6d6cbec813bf3dcb74e834b712dd37"
FROZEN_RUNS_SHA256 = "e2a69764c478f6d3e71e1f23a287840121849aa7b784d97ada223820315ffcd1"


def content_record(raw):
    return dict(encoding="base64", size=len(raw), content=base64.b64encode(raw).decode(),
        sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest())


def inventory_json(value):
    return (json.dumps(value,separators=(",",":"),allow_nan=False)+"\n").encode()


def small_inventory():
    value=config()
    value["runs"].append(dict(value["runs"][0],run=124,label="second"))
    return value


def shard_bundle(value):
    """Construct explicit synthetic transport around the complete unchanged rows."""
    count=len(value["runs"]); assert count>=2
    bodies={}
    manifest={k:copy.deepcopy(v) for k,v in value.items() if k not in ("schema","runs")}
    manifest.update(schema=2,run_files=[],run_count=count,
        runs_sha256=hashlib.sha256(json.dumps(value["runs"],sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest())
    for path,rows in zip(m.RUN_FILE_PATHS,(value["runs"][:count//2],value["runs"][count//2:]),strict=True):
        raw=inventory_json(dict(schema="cloud-progress-monitor-runs-v1",repository=m.REPO,
            target_branch=value["target_branch"],runs=rows))
        bodies[path]=raw
        manifest["run_files"].append(dict(path=path,bytes=len(raw),blob_sha=content_record(raw)["sha"],
            sha256=hashlib.sha256(raw).hexdigest(),run_count=len(rows)))
    bodies[m.INVENTORY_PATH]=inventory_json(manifest)
    return manifest,bodies


class InventoryAPI:
    """Every request has to retain the first captured commit."""
    def __init__(self,bodies):
        self.bodies=copy.deepcopy(bodies);self.calls=[];self.head_reads=0;self.responses={}
    def get(self,path):
        self.calls.append(("get",path))
        assert path=="git/ref/heads/codex/complete-open-work"
        self.head_reads+=1
        return dict(object=dict(sha=HEAD if self.head_reads==1 else "b"*40))
    def maybe(self,path):
        self.calls.append(("maybe",path))
        prefix,suffix="contents/","?ref="+HEAD
        assert path.startswith(prefix) and path.endswith(suffix),"Mutable or foreign inventory read"
        name=path[len(prefix):-len(suffix)]
        if name in self.responses:return copy.deepcopy(self.responses[name])
        if name not in self.bodies:return None
        return content_record(self.bodies[name])


class FullRunAPI:
    """Actual collect(), all296 handles, explicit non-native metadata transport."""
    def __init__(self,value):
        self.items={r["run"]:r for r in value["runs"]};self.calls=[]
    def get(self,path):
        self.calls.append(("get",path))
        if path=="git/ref/heads/codex/complete-open-work":return dict(object=dict(sha=HEAD))
        assert path.startswith("actions/runs/") and path.count("/")==2
        item=self.items[int(path.rsplit("/",1)[1])]
        state=run()
        state.update(id=item["run"],head_sha=item["head_sha"],head_branch=item["branch"],
            html_url="https://github.com/"+m.REPO+"/actions/runs/"+str(item["run"]))
        return state
    def maybe(self,path):
        self.calls.append(("maybe",path))
        assert path.startswith("actions/workflows/"),"No terminal/native asset reads in active fixture"
        return None
    def pages(self,path,key,maximum=1000):
        self.calls.append(("pages",path))
        assert path.startswith("actions/runs/") and path.endswith("/attempts/1/jobs") and key=="jobs"
        assert int(path.split("/")[2]) in self.items
        return [job()]


class ShardedInventoryControls(unittest.TestCase):
    def test_full_296_fixture_and_complete_collection_equivalence(self):
        raw=FROZEN_INVENTORY.read_bytes()
        self.assertEqual(len(raw),65365)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),FROZEN_SHA256)
        original=json.loads(raw)
        self.assertEqual(len(original["runs"]),296)
        self.assertEqual(len({r["run"] for r in original["runs"]}),296)
        self.assertEqual(len(original["latest_workflows"]),2)
        manifest,bodies=shard_bundle(original)
        self.assertEqual(manifest["runs_sha256"],FROZEN_RUNS_SHA256)
        self.assertEqual([len(bodies[p]) for p in m.RUN_FILE_PATHS],[32294,32656])
        actual,proof=m.load_config(InventoryAPI(bodies),config())
        self.assertEqual(actual,original)
        self.assertEqual(proof["resolved_run_count"],296)
        self.assertEqual(proof["runs_sha256"],FROZEN_RUNS_SHA256)
        self.assertEqual([d["path"] for d in proof["documents"]],[m.INVENTORY_PATH,*m.RUN_FILE_PATHS])
        self.assertEqual([d["run_count"] for d in proof["documents"][1:]],[148,148])
        # Every original label/head/branch/production job and selector reaches actual collect().
        a=FullRunAPI(original);b=FullRunAPI(actual)
        legacy=m.collect(a,original,NOW,configuration_source=dict(head_sha=HEAD))
        current=m.collect(b,actual,NOW,configuration_source=proof)
        self.assertEqual(legacy["runs"],current["runs"])
        self.assertEqual(len(current["runs"]),296)
        self.assertEqual(legacy["missing_selectors"],current["missing_selectors"])
        self.assertEqual(legacy["problem_runs"],current["problem_runs"])
        self.assertEqual(legacy["status"],current["status"])
        self.assertEqual(a.calls,b.calls)
        self.assertFalse(current["automatic_native_dispatch"])
        self.assertFalse(current["full_phy_accepted"])
        self.assertFalse(current["final_timing_accepted"])
        self.assertEqual(current["schema"],1)

    def test_one_captured_head_and_document_proofs(self):
        manifest,bodies=shard_bundle(small_inventory())
        api=InventoryAPI(bodies);actual,proof=m.load_config(api,config())
        self.assertEqual(api.head_reads,1)
        self.assertTrue(all(path.endswith("?ref="+HEAD) for kind,path in api.calls if kind=="maybe"))
        self.assertEqual(proof["head_sha"],HEAD)
        for document in proof["documents"]:
            raw=bodies[document["path"]]
            self.assertEqual(document["bytes"],len(raw))
            self.assertEqual(document["blob_sha"],content_record(raw)["sha"])
            self.assertEqual(document["sha256"],hashlib.sha256(raw).hexdigest())
        for key in ("branch","head_sha","blob_sha","sha256","bytes","bootstrap"):
            self.assertIn(key,proof)
        self.assertFalse(proof["bootstrap"])

    def test_new_manifest_is_not_legacy_configuration(self):
        manifest,_=shard_bundle(small_inventory())
        with self.assertRaises(AssertionError):m.check_config(manifest)

    def test_same64KiB_limit_for_manifest_and_both_children(self):
        self.assertEqual(m.INVENTORY_LIMIT,65536);self.assertEqual(m.LIMIT,8*1024*1024)
        for path in (m.INVENTORY_PATH,*m.RUN_FILE_PATHS):
            for size in (65536,65537):
                with self.subTest(path=path,size=size):
                    manifest,bodies=shard_bundle(small_inventory())
                    bodies[path]+=b" "*(size-len(bodies[path]))
                    if path!=m.INVENTORY_PATH:
                        row=next(x for x in manifest["run_files"] if x["path"]==path)
                        row.update(bytes=len(bodies[path]),blob_sha=content_record(bodies[path])["sha"],
                            sha256=hashlib.sha256(bodies[path]).hexdigest())
                        bodies[m.INVENTORY_PATH]=inventory_json(manifest)
                    if size==65536:
                        got,_=m.load_config(InventoryAPI(bodies),config())
                        self.assertEqual(got,small_inventory())
                    else:
                        with self.assertRaises(AssertionError):m.load_config(InventoryAPI(bodies),config())

    def test_oversized_child_response_even_with_acceptable_descriptor(self):
        manifest,bodies=shard_bundle(small_inventory())
        path=m.RUN_FILE_PATHS[0]; bodies[path]+=b" "*(65537-len(bodies[path]))
        with self.assertRaises(AssertionError):m.load_config(InventoryAPI(bodies),config())

    def test_missing_children_never_use_bootstrap(self):
        for path in m.RUN_FILE_PATHS:
            manifest,bodies=shard_bundle(small_inventory());del bodies[path]
            with self.assertRaisesRegex(AssertionError,"Missing inventory shard"):
                m.load_config(InventoryAPI(bodies),config())

    def test_corrupt_child_git_blob_size_and_digest(self):
        for field in ("blob","size","content","declared_sha256","declared_bytes","declared_blob"):
            with self.subTest(field=field):
                manifest,bodies=shard_bundle(small_inventory());path=m.RUN_FILE_PATHS[0]
                api=InventoryAPI(bodies);response=content_record(bodies[path])
                if field=="blob":response["sha"]="f"*40;api.responses[path]=response
                elif field=="size":response["size"]+=1;api.responses[path]=response
                elif field=="content":response["content"]=base64.b64encode(b"changed").decode();api.responses[path]=response
                else:
                    key={"declared_sha256":"sha256","declared_bytes":"bytes","declared_blob":"blob_sha"}[field]
                    manifest["run_files"][0][key]=manifest["run_files"][0][key]+1 if key=="bytes" else "f"*(64 if key=="sha256" else 40)
                    api.bodies[m.INVENTORY_PATH]=inventory_json(manifest)
                with self.assertRaises(AssertionError):m.load_config(api,config())

    def test_manifest_count_digest_descriptor_and_path_guards(self):
        mutations=(
            ("no_shards",lambda x:x.update(run_files=[])),
            ("extra_shard",lambda x:x["run_files"].append(copy.deepcopy(x["run_files"][0]))),
            ("duplicate_path",lambda x:x["run_files"][1].update(path=m.RUN_FILE_PATHS[0])),
            ("reorder",lambda x:x["run_files"].reverse()),
            ("traversal",lambda x:x["run_files"][0].update(path="../inventory.json")),
            ("absolute",lambda x:x["run_files"][0].update(path="/inventory.json")),
            ("URL",lambda x:x["run_files"][0].update(path="https://example.invalid/data")),
            ("recursive_manifest",lambda x:x["run_files"][0].update(path=m.INVENTORY_PATH)),
            ("child_ref",lambda x:x["run_files"][0].update(ref="main")),
            ("boolean_bytes",lambda x:x["run_files"][0].update(bytes=True)),
            ("boolean_count",lambda x:x["run_files"][0].update(run_count=True)),
            ("wrong_child_count",lambda x:x["run_files"][0].update(run_count=2)),
            ("wrong_total",lambda x:x.update(run_count=3)),
            ("wrong_digest",lambda x:x.update(runs_sha256="0"*64)),
            ("unknown_schema",lambda x:x.update(schema=3)),
            ("wrong_repository",lambda x:x.update(repository="other/project")),
            ("wrong_branch",lambda x:x.update(target_branch="main")),
            ("dispatch",lambda x:x.update(automatic_native_dispatch=True)),
            ("short_stall",lambda x:x.update(stall_seconds=1)),
        )
        for label,mutate in mutations:
            with self.subTest(label=label):
                manifest,bodies=shard_bundle(small_inventory());mutate(manifest)
                bodies[m.INVENTORY_PATH]=inventory_json(manifest)
                with self.assertRaises(AssertionError):m.load_config(InventoryAPI(bodies),config())

    def test_child_scope_schema_and_no_recursive_fields(self):
        for key,value in (("schema","other"),("repository","other/project"),("target_branch","main"),
                          ("runs",{}),("run_files",[])):
            with self.subTest(key=key):
                manifest,bodies=shard_bundle(small_inventory());path=m.RUN_FILE_PATHS[0]
                shard=json.loads(bodies[path]);shard[key]=value;bodies[path]=inventory_json(shard)
                descriptor=manifest["run_files"][0]
                descriptor.update(bytes=len(bodies[path]),blob_sha=content_record(bodies[path])["sha"],
                    sha256=hashlib.sha256(bodies[path]).hexdigest())
                bodies[m.INVENTORY_PATH]=inventory_json(manifest)
                with self.assertRaises(AssertionError):m.load_config(InventoryAPI(bodies),config())

    def test_global_duplicate_id_refused_even_identical_or_conflicting(self):
        for conflict in (False,True):
            value=small_inventory();value["runs"][1]=copy.deepcopy(value["runs"][0])
            if conflict:value["runs"][1]["head_sha"]="b"*40
            _,bodies=shard_bundle(value)
            with self.assertRaises(AssertionError):m.load_config(InventoryAPI(bodies),config())

    def test_global_bad_run_source_refused_after_reassembly(self):
        value=small_inventory();value["runs"][1]["head_sha"]="mutable-main"
        _,bodies=shard_bundle(value)
        with self.assertRaises(AssertionError):m.load_config(InventoryAPI(bodies),config())

    def test_missing_child_actual_main_preserves_monitor_error_before_collection(self):
        import os
        import tempfile
        from unittest.mock import patch
        _,bodies=shard_bundle(small_inventory());del bodies[m.RUN_FILE_PATHS[1]]
        api=InventoryAPI(bodies)
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);bootstrap=base/"bootstrap.json";bootstrap.write_bytes(inventory_json(config()))
            output=base/"result";summary=base/"summary.md"
            with patch.object(m,"API",return_value=api), patch.object(m,"previous_snapshot",side_effect=AssertionError("Unexpected prior read")) as prior, patch.object(m,"collect",side_effect=AssertionError("Unexpected collection")) as collect:
                with patch.dict(os.environ,dict(GITHUB_ACTIONS="true",RUNNER_ENVIRONMENT="github-hosted",
                    GITHUB_REPOSITORY=m.REPO,GH_TOKEN="fixture",GITHUB_RUN_ID="999",GITHUB_STEP_SUMMARY=str(summary))):
                    with patch.object(sys,"argv",["monitor","--config",str(bootstrap),"--out",str(output)]):
                        with self.assertRaisesRegex(AssertionError,"Missing inventory shard"):m.main()
                prior.assert_not_called();collect.assert_not_called()
            saved=json.loads((output/"result.json").read_text())
            self.assertEqual(saved["status"],"MONITOR_ERROR")
            self.assertEqual([r["id"] for r in saved["runs"]], [r["run"] for r in config()["runs"]])
            self.assertTrue(all(r["observation_state"] == "UNOBSERVED" for r in saved["runs"]))
            self.assertFalse(saved["automatic_native_dispatch"])
            self.assertFalse(saved["full_phy_accepted"])
            self.assertIn("No native work was changed",summary.read_text())
            self.assertTrue(all(path.startswith(("contents/","git/ref/heads/")) for _,path in api.calls))



# Exact compact projections of root109's mixed inventory and observed API metadata.
# Source-only fixtures: no live/cloud/native I/O is performed by these controls.
MAIN_OBSERVATION_FIXTURE = json.loads('{\n  "source_commit": "958d59820e2f24e69cbb158d1c9d6dd7f962a081",\n  "rows": [\n    {\n      "label": "Mainchip detailed routing",\n      "run": 40095811631,\n      "branch": "codex/complete-open-work",\n      "head_sha": "4d85722e05fbda8440c6577d7d7baa18a642485b",\n      "production_jobs": [\n        "continuation"\n      ]\n    },\n    {\n      "label": "monitor-live-sharded-inventory",\n      "run": 40783413345,\n      "branch": "main",\n      "head_sha": "5259d3decb710c850a7695940fdc4a7eba9f5154",\n      "production_jobs": [\n        "controls",\n        "observe"\n      ]\n    },\n    {\n      "label": "cdr-selector-width-default-harmless-diagnostic",\n      "run": 40786525718,\n      "branch": "main",\n      "head_sha": "e4b8d914659934617e93c7a99121d4d65d7f3401",\n      "production_jobs": [\n        "register-only"\n      ]\n    }\n  ],\n  "observed": {\n    "40783413345": {\n      "run": {\n        "id": 40783413345,\n        "name": "cloud-progress-monitor",\n        "head_sha": "5259d3decb710c850a7695940fdc4a7eba9f5154",\n        "head_branch": "main",\n        "run_attempt": 1,\n        "path": ".github/workflows/cloud-progress-monitor.yml",\n        "workflow_id": 394905294,\n        "status": "completed",\n        "conclusion": "failure",\n        "event": "workflow_dispatch",\n        "created_at": "2026-10-28T22:53:53Z",\n        "run_started_at": "2026-10-28T22:53:53Z",\n        "updated_at": "2026-10-28T23:01:55Z",\n        "html_url": "https://github.com/Melihakbulut221/nssoc/actions/runs/40783413345"\n      },\n      "jobs": [\n        {\n          "id": 123150507461,\n          "name": "controls",\n          "status": "completed",\n          "started_at": "2026-10-28T22:53:57Z",\n          "completed_at": "2026-10-28T22:54:04Z",\n          "conclusion": "success",\n          "steps": [\n            {\n              "name": "Set up job",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 1,\n              "started_at": "2026-10-28T22:53:58Z",\n              "completed_at": "2026-10-28T22:53:59Z"\n            },\n            {\n              "name": "Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 2,\n              "started_at": "2026-10-28T22:53:59Z",\n              "completed_at": "2026-10-28T22:54:01Z"\n            },\n            {\n              "name": "Mock API controls including duplicates, active work, failures and source corruption",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 3,\n              "started_at": "2026-10-28T22:54:01Z",\n              "completed_at": "2026-10-28T22:54:01Z"\n            },\n            {\n              "name": "Post Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 6,\n              "started_at": "2026-10-28T22:54:01Z",\n              "completed_at": "2026-10-28T22:54:01Z"\n            },\n            {\n              "name": "Complete job",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 7,\n              "started_at": "2026-10-28T22:54:01Z",\n              "completed_at": "2026-10-28T22:54:01Z"\n            }\n          ]\n        },\n        {\n          "id": 123150570369,\n          "name": "observe",\n          "status": "completed",\n          "started_at": "2026-10-28T22:54:07Z",\n          "completed_at": "2026-10-28T23:01:54Z",\n          "conclusion": "failure",\n          "steps": [\n            {\n              "name": "Set up job",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 1,\n              "started_at": "2026-10-28T22:54:08Z",\n              "completed_at": "2026-10-28T22:54:09Z"\n            },\n            {\n              "name": "Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 2,\n              "started_at": "2026-10-28T22:54:09Z",\n              "completed_at": "2026-10-28T22:54:10Z"\n            },\n            {\n              "name": "Observe authoritative cloud work without native dispatch",\n              "status": "completed",\n              "conclusion": "failure",\n              "number": 3,\n              "started_at": "2026-10-28T22:54:10Z",\n              "completed_at": "2026-10-28T23:01:50Z"\n            },\n            {\n              "name": "Require the live working-branch inventory on main",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 4,\n              "started_at": "2026-10-28T23:01:50Z",\n              "completed_at": "2026-10-28T23:01:50Z"\n            },\n            {\n              "name": "Persist the bounded cloud snapshot",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 5,\n              "started_at": "2026-10-28T23:01:50Z",\n              "completed_at": "2026-10-28T23:01:51Z"\n            },\n            {\n              "name": "Post Run actions/checkout@11d5960a326750d5838078e36cf38b85af677262",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 10,\n              "started_at": "2026-10-28T23:01:51Z",\n              "completed_at": "2026-10-28T23:01:52Z"\n            },\n            {\n              "name": "Complete job",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 11,\n              "started_at": "2026-10-28T23:01:52Z",\n              "completed_at": "2026-10-28T23:01:52Z"\n            }\n          ]\n        }\n      ]\n    },\n    "40786525718": {\n      "run": {\n        "id": 40786525718,\n        "name": "CDR selector column width source controls",\n        "head_sha": "e4b8d914659934617e93c7a99121d4d65d7f3401",\n        "head_branch": "main",\n        "run_attempt": 1,\n        "path": ".github/workflows/cdr-v59-selector-column-width-cloud.yml",\n        "workflow_id": 399990996,\n        "status": "completed",\n        "conclusion": "success",\n        "event": "workflow_dispatch",\n        "created_at": "2026-10-28T23:19:23Z",\n        "run_started_at": "2026-10-28T23:19:23Z",\n        "updated_at": "2026-10-28T23:19:31Z",\n        "html_url": "https://github.com/Melihakbulut221/nssoc/actions/runs/40786525718"\n      },\n      "jobs": [\n        {\n          "id": 123160997909,\n          "name": "register-only",\n          "status": "completed",\n          "started_at": "2026-10-28T23:19:27Z",\n          "completed_at": "2026-10-28T23:19:30Z",\n          "conclusion": "success",\n          "steps": [\n            {\n              "name": "Set up job",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 1,\n              "started_at": "2026-10-28T23:19:27Z",\n              "completed_at": "2026-10-28T23:19:27Z"\n            },\n            {\n              "name": "Run printf \'%s\\\\n\' \'Workflow registration only; no checkout, tests, archive retrieval or native execution.\'",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 2,\n              "started_at": "2026-10-28T23:19:27Z",\n              "completed_at": "2026-10-28T23:19:28Z"\n            },\n            {\n              "name": "Complete job",\n              "status": "completed",\n              "conclusion": "success",\n              "number": 3,\n              "started_at": "2026-10-28T23:19:28Z",\n              "completed_at": "2026-10-28T23:19:28Z"\n            }\n          ]\n        }\n      ]\n    }\n  }\n}\n')
FROZEN_CONFIG = 'def check_config(config):\n    assert config["schema"] == 1 and config["repository"] == REPO\n    assert type(config.get("inventory_version")) is int and config["inventory_version"] > 0\n    assert config.get("inventory_updated_at") and time_value(config["inventory_updated_at"])\n    assert config["target_branch"] == "codex/complete-open-work"\n    assert config["stall_seconds"] == 21600\n    seen = set()\n    for item in config["runs"]:\n        assert type(item["run"]) is int and item["run"] > 0 and item["run"] not in seen\n        seen.add(item["run"])\n        assert item["label"] and re.fullmatch(r"[0-9a-f]{40}", item["head_sha"])\n        assert item["branch"].startswith("codex/")\n    for item in config["latest_workflows"]:\n        assert re.fullmatch(r"[a-z0-9-]+\\.yml", item["workflow"])\n        assert item["branch"] == config["target_branch"]\n        assert isinstance(item["optional"], bool)\n        assert item.get("event") in (None, "push", "workflow_dispatch")\n        assert isinstance(item.get("production_jobs", []), list)\n    assert config["automatic_native_dispatch"] is False\n'
FROZEN_CONFIG_SHA256 = "529e02a8e3920de88a0d74dc9b7a6bdd8e7e7b2df627bee0876dee7bf87a9119"


def mixed_main_config():
    value = config()
    value["runs"] = copy.deepcopy(MAIN_OBSERVATION_FIXTURE["rows"])
    return value


class MainObservationAPI(FullRunAPI):
    """Actual collect path; exact main metadata plus one synthetic active codex row."""
    def __init__(self, value=None):
        super().__init__(value or mixed_main_config())
        self.observed = copy.deepcopy(MAIN_OBSERVATION_FIXTURE["observed"])

    def get(self, path):
        if path.startswith("actions/runs/"):
            key = path.rsplit("/", 1)[1]
            if key in self.observed:
                self.calls.append(("get", path))
                return copy.deepcopy(self.observed[key]["run"])
        return super().get(path)

    def pages(self, path, key, maximum=1000):
        rid = path.split("/")[2]
        if rid in self.observed:
            self.calls.append(("pages", path))
            assert path == "actions/runs/" + rid + "/attempts/1/jobs" and key == "jobs"
            return copy.deepcopy(self.observed[rid]["jobs"])
        return super().pages(path, key, maximum)

    def maybe(self, path):
        raise AssertionError("No release/artifact/native request allowed by mixed fixture: " + path)


class MainObservationControls(unittest.TestCase):
    monitor_id = 40783413345
    other_id = 40786525718

    def observed(self, api, value=None):
        result = m.collect(api, value or mixed_main_config(), NOW)
        self.assertEqual([r["id"] for r in result["runs"]], [r["run"] for r in (value or mixed_main_config())["runs"]])
        self.assertFalse(result["automatic_native_dispatch"])
        self.assertFalse(result["full_phy_accepted"])
        self.assertFalse(result["final_timing_accepted"])
        self.assertTrue(all(path.startswith(("git/ref/heads/", "actions/runs/")) for _, path in api.calls))
        return result

    def test_exact_old_main_assertion_and_actual_mixed_rows_retained(self):
        self.assertEqual(hashlib.sha256(FROZEN_CONFIG.encode()).hexdigest(), FROZEN_CONFIG_SHA256)
        namespace = dict(vars(m))
        exec(compile(FROZEN_CONFIG, "frozen-monitor-check-config-46df418b.py", "exec"), namespace)
        value = mixed_main_config()
        with self.assertRaises(AssertionError) as caught:
            namespace["check_config"](value)
        self.assertEqual(str(caught.exception), "")
        m.check_config(value)
        result = self.observed(MainObservationAPI(), value)
        self.assertEqual([r["classification"] for r in result["runs"]], ["RUNNING", "FAILED", "UNVERIFIED_REF"])
        self.assertEqual(result["problem_runs"], [self.monitor_id, self.other_id])
        self.assertEqual(result["status"], "ATTENTION_REQUIRED")
        self.assertEqual(result["runs"][1]["conclusion"], "failure")
        self.assertEqual(result["runs"][2]["conclusion"], "success")
        self.assertIn("exactly controls/observe", result["runs"][2]["reason"])
        self.assertEqual(result["runs"][1]["reports"], [])
        self.assertEqual(result["runs"][2]["reports"], [])

    def test_actual_schema2_assembly_preserves_all_mixed_handles(self):
        value = mixed_main_config()
        _, bodies = shard_bundle(value)
        loaded, proof = m.load_config(InventoryAPI(bodies), config())
        self.assertEqual(loaded, value)
        self.assertFalse(proof["bootstrap"])
        self.assertEqual(self.observed(MainObservationAPI(loaded), loaded)["runs"][2]["classification"], "UNVERIFIED_REF")

    def test_successful_monitor_is_read_only_not_native_publication(self):
        api = MainObservationAPI()
        record = api.observed[str(self.monitor_id)]
        record["run"]["conclusion"] = "success"
        for j in record["jobs"]: j["conclusion"] = "success"
        result = self.observed(api)
        row = result["runs"][1]
        self.assertEqual(row["classification"], "COMPLETED_MONITOR")
        self.assertFalse(row["publication_verified"])
        self.assertEqual(row["reports"], [])
        self.assertEqual(result["problem_runs"], [self.other_id])

    def test_exact_workflow_event_and_job_identity_refusals(self):
        cases = (
            ("workflow-id", lambda i, r, j: r.update(workflow_id=399990996)),
            ("workflow-id-type", lambda i, r, j: r.update(workflow_id=str(m.WORKFLOW_ID))),
            ("workflow-path", lambda i, r, j: r.update(path=".github/workflows/native.yml")),
            ("event", lambda i, r, j: r.update(event="push")),
            ("required-empty", lambda i, r, j: i.update(production_jobs=[])),
            ("required-null", lambda i, r, j: i.update(production_jobs=None)),
            ("required-string", lambda i, r, j: i.update(production_jobs="controls observe")),
            ("required-native", lambda i, r, j: i.update(production_jobs=["controls", "native"])),
            ("required-duplicate", lambda i, r, j: i.update(production_jobs=["controls", "controls"])),
            ("actual-job", lambda i, r, j: j[1].update(name="native")),
            ("actual-duplicate", lambda i, r, j: j[1].update(name="controls")),
            ("completed-missing-job", lambda i, r, j: j.pop()),
        )
        for name, change in cases:
            with self.subTest(name=name):
                value = mixed_main_config(); api = MainObservationAPI(value)
                record = api.observed[str(self.monitor_id)]
                change(value["runs"][1], record["run"], record["jobs"])
                result = self.observed(api, value)
                self.assertEqual(result["runs"][1]["classification"], "UNVERIFIED_REF")
                self.assertTrue(result["runs"][1]["reason"])
                self.assertIn(self.monitor_id, result["problem_runs"])

    def test_unrelated_main_cannot_impersonate_monitor_with_job_names(self):
        value = mixed_main_config(); value["runs"][2]["production_jobs"] = ["controls", "observe"]
        api = MainObservationAPI(value)
        actual = api.observed[str(self.other_id)]
        actual["jobs"] = copy.deepcopy(api.observed[str(self.monitor_id)]["jobs"])
        result = self.observed(api, value)
        self.assertEqual(result["runs"][2]["classification"], "UNVERIFIED_REF")
        self.assertIn("pinned read-only", result["runs"][2]["reason"])

    def test_main_source_branch_and_run_id_mismatch_still_refused(self):
        for key, changed in (("head_sha", "b" * 40), ("head_branch", "codex/other"), ("id", 999)):
            with self.subTest(key=key):
                api = MainObservationAPI(); api.observed[str(self.monitor_id)]["run"][key] = changed
                with self.assertRaisesRegex(AssertionError, "ID/source/branch differs"):
                    m.collect(api, mixed_main_config(), NOW)
                self.assertTrue(all(path.startswith(("git/ref/heads/", "actions/runs/")) for _, path in api.calls))

    def test_other_branch_refs_still_rejected(self):
        for branch in ("master", "refs/heads/main", "release/stable", "", None):
            with self.subTest(branch=branch):
                value = mixed_main_config(); value["runs"][1]["branch"] = branch
                with self.assertRaisesRegex(AssertionError, "Unapproved inventory branch"):
                    m.check_config(value)

    def test_partial_active_and_skipped_monitor_are_not_success(self):
        api = MainObservationAPI(); record = api.observed[str(self.monitor_id)]
        record["run"].update(status="in_progress", conclusion=None)
        record["jobs"] = record["jobs"][:1]
        self.assertEqual(self.observed(api)["runs"][1]["classification"], "RUNNING")
        for skipped in ("observe", "controls"):
            with self.subTest(skipped=skipped):
                api = MainObservationAPI(); record = api.observed[str(self.monitor_id)]
                record["run"]["conclusion"] = "success"
                for j in record["jobs"]: j["conclusion"] = "skipped" if j["name"] == skipped else "success"
                self.assertEqual(self.observed(api)["runs"][1]["classification"], "NOT_EXECUTED")

    def test_actual_main_empty_assertion_has_durable_diagnostic_and_same_error(self):
        import os
        import tempfile
        from unittest.mock import patch
        failure = AssertionError()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); bootstrap = base / "bootstrap.json"
            bootstrap.write_bytes(inventory_json(config()))
            output = base / "result"; summary = base / "summary.md"
            with patch.object(m, "API", return_value=Mock()), patch.object(m, "load_config", side_effect=failure), patch.object(m, "collect") as collect:
                with patch.dict(os.environ, dict(GITHUB_ACTIONS="true", RUNNER_ENVIRONMENT="github-hosted",
                    GITHUB_REPOSITORY=m.REPO, GH_TOKEN="fixture", GITHUB_RUN_ID="999", GITHUB_STEP_SUMMARY=str(summary))):
                    with patch.object(sys, "argv", ["monitor", "--config", str(bootstrap), "--out", str(output)]):
                        with self.assertRaises(AssertionError) as caught: m.main()
                self.assertIs(caught.exception, failure); collect.assert_not_called()
            saved = json.loads((output / "result.json").read_text())
            self.assertEqual(saved["status"], "MONITOR_ERROR")
            self.assertEqual(saved["error"], "AssertionError: AssertionError()")
            self.assertIn(saved["error"], summary.read_text())
            self.assertFalse(saved["automatic_native_dispatch"])
            self.assertFalse(saved["full_phy_accepted"])


class BoundedManyShardControls(unittest.TestCase):
    fixture = Path(__file__).with_name("fixtures") / "cloud-progress-monitor-532-v197.json"

    def captured(self):
        raw = self.fixture.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "1de54815eea5fcf7df63055f6f589bf1a4e2470edfc671b256a52359e8561451")
        f = json.loads(raw)
        self.assertEqual(f["root_source"], "80b1f781ef2e9077ed829e9db1eef04b9864c09b")
        bodies = {p: base64.b64decode(b, validate=True) for p,b in f["bodies_base64"].items()}
        return f, bodies

    def test_actual_three_shards_reproduce_old_failure_then_preserve_all_532_rows(self):
        f,bodies = self.captured()
        old = f["old_assembled_inventory"]
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), f["old_assembled_sha256"])
        namespace = dict(vars(m))
        exec(compile(old, "frozen-main-two-shard-reader.py", "exec"), namespace)
        manifest = json.loads(bodies[m.INVENTORY_PATH])
        with self.assertRaisesRegex(AssertionError, "^Inventory shard count$"):
            namespace["assembled_inventory"](InventoryAPI(bodies), HEAD, manifest)
        actual,proof = m.load_config(InventoryAPI(bodies), config())
        expected = [r for item in manifest["run_files"] for r in json.loads(bodies[item["path"]])["runs"]]
        self.assertEqual(actual["runs"], expected)
        self.assertEqual(len(actual["runs"]), 532)
        self.assertEqual(len({r["run"] for r in actual["runs"]}), 532)
        self.assertEqual(proof["resolved_run_count"], 532)
        self.assertEqual(proof["runs_sha256"], manifest["runs_sha256"])
        self.assertEqual([d["path"] for d in proof["documents"]], [m.INVENTORY_PATH,*[i["path"] for i in manifest["run_files"]]])
        self.assertFalse(actual["automatic_native_dispatch"])
        self.assertFalse(proof["bootstrap"])

    def bundle(self, count):
        value=config()
        value["runs"]=[dict(value["runs"][0],run=1000+i) for i in range(count)]
        manifest={k:copy.deepcopy(v) for k,v in value.items() if k not in ("schema","runs")}
        manifest.update(schema=2,run_files=[],run_count=count,
            runs_sha256=hashlib.sha256(json.dumps(value["runs"],sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest())
        bodies={}
        for i,row in enumerate(value["runs"]):
            path=".github/cloud-progress-monitor-runs-"+str(i).zfill(3)+".json"
            raw=inventory_json(dict(schema="cloud-progress-monitor-runs-v1",repository=m.REPO,target_branch=value["target_branch"],runs=[row]))
            bodies[path]=raw
            manifest["run_files"].append(dict(path=path,bytes=len(raw),blob_sha=content_record(raw)["sha"],sha256=hashlib.sha256(raw).hexdigest(),run_count=1))
        bodies[m.INVENTORY_PATH]=inventory_json(manifest)
        return value,manifest,bodies

    def test_all_bounded_counts_keep_one_head_and_complete_order(self):
        self.assertEqual(m.MAX_RUN_FILES,16)
        self.assertEqual(m.INVENTORY_LIMIT,65536)
        for count in range(1,17):
            with self.subTest(count=count):
                value,manifest,bodies=self.bundle(count)
                api=InventoryAPI(bodies)
                actual,proof=m.load_config(api,config())
                self.assertEqual(actual,value)
                self.assertEqual(api.head_reads,1)
                self.assertEqual(len(proof["documents"]),count+1)
                self.assertTrue(all(p.endswith("?ref="+HEAD) for kind,p in api.calls if kind=="maybe"))

    def test_seventeen_shards_refused_before_child_reads(self):
        _,_,bodies=self.bundle(17)
        api=InventoryAPI(bodies)
        with self.assertRaisesRegex(AssertionError,"Inventory shard count"):
            m.load_config(api,config())
        self.assertEqual(len(api.calls),2)

    def test_third_shard_must_be_contiguous_present_and_byte_exact(self):
        _,bodies=self.captured()
        path=".github/cloud-progress-monitor-runs-002.json"
        for fault in ("missing","changed","reordered","hole","external","too_large"):
            with self.subTest(fault=fault):
                changed=copy.deepcopy(bodies);manifest=json.loads(changed[m.INVENTORY_PATH])
                if fault=="missing":del changed[path]
                elif fault=="changed":changed[path]+=b" "
                elif fault=="reordered":manifest["run_files"][1:]=reversed(manifest["run_files"][1:])
                elif fault=="hole":manifest["run_files"][2]["path"]=".github/cloud-progress-monitor-runs-003.json"
                elif fault=="external":manifest["run_files"][2]["path"]="https://example.invalid/data"
                else:manifest["run_files"][2]["bytes"]=65537
                changed[m.INVENTORY_PATH]=inventory_json(manifest)
                with self.assertRaises(AssertionError):m.load_config(InventoryAPI(changed),config())

    def test_unapproved_child_path_never_reaches_api(self):
        class NoAPI:
            def maybe(self,path):raise RuntimeError("unexpected request")
        for path in (".github/cloud-progress-monitor-runs-016.json",".github/cloud-progress-monitor-runs-2.json",".github/cloud-progress-monitor-runs-002.json?ref=main","../inventory.json"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(AssertionError,"Unapproved inventory path"):
                    m.inventory_document(NoAPI(),HEAD,path)


class BoundedObservationAPI:
    """Independent derived metadata fixture; no network or archive payloads."""
    def __init__(self, items, active=(), stop_after=None, errors=()):
        self.items = {r["run"]: r for r in items}
        self.active = set(active)
        self.stop_after = stop_after
        self.errors = set(errors)
        self.observed = []
        self.selector_calls = 0
        self.selector_error = None
        self.discovery_errors = set()
        self.discovery_calls = []
        self.extra_active = []
        self.active_states = {rid: "in_progress" for rid in self.active}
        self.attempts = {}

    def get(self, path):
        if path.startswith("actions/runs?status="):
            query = m.urllib.parse.parse_qs(path.partition("?")[2])
            status = query["status"][0]
            page = int(query["page"][0])
            self.discovery_calls.append((status, page))
            if status in self.discovery_errors:
                raise RuntimeError("synthetic active discovery failure")
            values = []
            for rid in self.active:
                item = self.items[rid]
                value = run(self.active_states[rid])
                value.update(id=rid, head_sha=item["head_sha"], head_branch=item["branch"], run_attempt=self.attempts.get(rid, 1))
                values.append(value)
            values.extend(copy.deepcopy(self.extra_active))
            values = [r for r in values if r["status"] == status]
            return dict(total_count=len(values), workflow_runs=values[(page-1)*100:page*100])
        assert path.startswith("actions/runs/") and path.rsplit("/", 1)[-1].isdigit()
        rid = int(path.rsplit("/", 1)[-1])
        if self.stop_after is not None and len(self.observed) >= self.stop_after:
            raise m.ObservationLimit("synthetic bounded read stop")
        self.observed.append(rid)
        if rid in self.errors:
            raise RuntimeError("synthetic GET failure "+str(rid))
        item = self.items[rid]
        value = run("in_progress" if rid in self.active else "completed", None if rid in self.active else "success")
        value.update(id=rid, head_sha=item["head_sha"], head_branch=item["branch"])
        return value

    def pages(self, path, key, maximum=1000):
        rid = int(path.split("/")[2])
        return [job("in_progress" if rid in self.active else "completed", conclusion=None if rid in self.active else "success")]

    def maybe(self, path):
        if path.startswith("git/matching-refs/tags/"):
            return []
        assert path.startswith("actions/workflows/")
        self.selector_calls += 1
        if self.selector_error is not None and self.selector_calls >= self.selector_error[0]:
            raise self.selector_error[1]
        item = max(self.items.values(), key=lambda r: r["run"])
        value = run()
        value.update(id=item["run"], head_sha=item["head_sha"], head_branch=item["branch"])
        return dict(workflow_runs=[value])


class IncrementalObservationControls(unittest.TestCase):
    def many(self, count):
        value = config()
        value["runs"] = [dict(value["runs"][0], run=1000+i, label="fixture "+str(i)) for i in range(count)]
        return value

    def observe(self, value, api=None, previous=None):
        saves = []
        api = api or BoundedObservationAPI(value["runs"])
        result = m.observe_incrementally(api, value, previous, dict(head_sha=HEAD, bootstrap=False),
                                         lambda r: saves.append(copy.deepcopy(r)))
        return result, saves, api

    def previous(self, value, active=()):
        result, _, _ = self.observe(value, BoundedObservationAPI(value["runs"], active))
        result["_artifact_source"] = dict(id=777, run=888, sha256="d"*64)
        return result

    def test_533_handles_preserved_with_partial_completed_rows(self):
        value = self.many(533)
        result, saves, api = self.observe(value, BoundedObservationAPI(value["runs"], stop_after=4))
        self.assertEqual(len(result["runs"]), 533)
        self.assertEqual({r["id"] for r in result["runs"]}, {r["run"] for r in value["runs"]})
        self.assertEqual(len(result["refreshed_runs"]), 4)
        self.assertEqual(len(result["unobserved_runs"]), 529)
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION")
        self.assertFalse(result["observation_complete"])
        self.assertFalse(result["routine_unchanged"])
        self.assertEqual(api.observed[:3], [1532, 1531, 1000])
        self.assertEqual(result["next_history_run"], 1001)
        self.assertTrue(any(len(s["refreshed_runs"]) == 3 for s in saves))
        self.assertTrue(all(len(s["runs"]) == 533 for s in saves))

    def test_partial_snapshot_resumes_without_dropping_previous_work(self):
        value = self.many(533)
        first, _, _ = self.observe(value, BoundedObservationAPI(value["runs"], stop_after=4))
        first["_artifact_source"] = dict(id=777, run=888, sha256="d"*64)
        second, _, api = self.observe(value, BoundedObservationAPI(value["runs"], stop_after=4), first)
        self.assertEqual(len(second["runs"]), 533)
        self.assertEqual(api.observed[:3], [1529, 1528, 1001])
        self.assertTrue(set(first["refreshed_runs"]).issubset(set(second["cached_runs"])))
        self.assertEqual(second["next_history_run"], 1002)

    def test_cached_terminal_history_has_bounded_refresh_and_explicit_times(self):
        value = self.many(50)
        previous = self.previous(value)
        previous["target_head"] = "b"*40
        result, _, api = self.observe(value, previous=previous)
        self.assertEqual(len(api.observed), 16)
        self.assertEqual(len(result["cached_runs"]), 34)
        self.assertEqual(len(result["runs"]), 50)
        row = next(r for r in result["runs"] if r["observation_state"] == "CACHED")
        old = next(r for r in previous["runs"] if r["id"] == row["id"])
        self.assertEqual(row["last_observed_at"], old["last_observed_at"])
        self.assertEqual(row["cache_source"], previous["_artifact_source"])
        self.assertTrue(row["stale"])
        self.assertIsNone(row["changed_since_previous"])
        self.assertFalse(row["current_publication_reverified"])
        self.assertFalse(result["routine_unchanged"])
        self.assertFalse(result["observation_complete"])
        self.assertEqual(result["next_history_run"], 1016)

    def test_historical_cursor_rotates_across_snapshots(self):
        value = self.many(50)
        previous = self.previous(value)
        first, _, api1 = self.observe(value, previous=previous)
        second, _, api2 = self.observe(value, previous=first)
        self.assertEqual(api1.observed, list(range(1000, 1016)))
        self.assertEqual(api2.observed, list(range(1016, 1032)))
        self.assertTrue(set(api1.observed).isdisjoint(api2.observed))

    def test_active_cached_work_prioritized_without_starving_history(self):
        value = self.many(50)
        previous = self.previous(value, active=range(1030, 1050))
        result, _, api = self.observe(value, BoundedObservationAPI(value["runs"], range(1030, 1050), stop_after=9), previous)
        self.assertEqual(api.observed[:6], [1049, 1048, 1000, 1047, 1046, 1001])
        self.assertEqual(result["next_history_run"], 1003)

    def test_cache_requires_every_exact_identity_and_selection_policy(self):
        value = self.many(1)
        previous = self.previous(value)
        item = dict(value["runs"][0], selection="pinned")
        self.assertIsNotNone(m.cached_row(item, previous))
        for change in (dict(head_sha="b"*40), dict(branch="codex/other"), dict(production_jobs=["native"]), dict(selection="latest_workflow")):
            with self.subTest(change=change):
                self.assertIsNone(m.cached_row(dict(item, **change), previous))
        for field, bad in (("last_observed_at", "bad"), ("inventory_identity", {}), ("observation_state", "UNOBSERVED"), ("jobs", None), ("reports", [{}])):
            with self.subTest(field=field):
                mutated = copy.deepcopy(previous)
                mutated["runs"][0][field] = bad
                self.assertIsNone(m.cached_row(item, mutated))

    def test_legacy_rows_without_identity_are_observed_again(self):
        value = self.many(1)
        previous = self.previous(value)
        previous["runs"][0].pop("inventory_identity")
        _, _, api = self.observe(value, previous=previous)
        self.assertEqual(api.observed, [1000])

    def test_failed_row_does_not_discard_prior_rows_or_stop_later_work(self):
        value = self.many(3)
        result, saves, api = self.observe(value, BoundedObservationAPI(value["runs"], errors=[1001]))
        self.assertEqual(api.observed, [1002, 1001, 1000])
        self.assertEqual(set(result["refreshed_runs"]), {1000, 1002})
        self.assertEqual(result["unobserved_runs"], [1001])
        self.assertEqual(result["errors"][0]["run"], 1001)
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION")
        self.assertEqual(len(saves[-1]["runs"]), 3)

    def test_cached_failed_refresh_keeps_evidence_and_marks_error(self):
        value = self.many(1)
        previous = self.previous(value)
        result, _, _ = self.observe(value, BoundedObservationAPI(value["runs"], errors=[1000]), previous)
        row = result["runs"][0]
        self.assertEqual(row["observation_state"], "REFRESH_ERROR")
        self.assertEqual(row["reports"], previous["runs"][0]["reports"])
        self.assertEqual(row["last_observed_at"], previous["runs"][0]["last_observed_at"])
        self.assertIsNone(row["changed_since_previous"])
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION")

    def test_signal_during_latest_selector_preserves_inventory_and_first_selection(self):
        value = self.many(2)
        selector = dict(workflow="native.yml", label="latest", branch=value["target_branch"], optional=False)
        value["latest_workflows"] = [selector, dict(selector, workflow="other.yml")]
        api = BoundedObservationAPI(value["runs"])
        api.selector_error = (2, m.ObservationLimit("synthetic signal"))
        result, saves, _ = self.observe(value, api)
        self.assertEqual(len(result["runs"]), 2)
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION")
        self.assertFalse(result["selectors_complete"])
        self.assertEqual(result["errors"][0]["phase"], "selecting")
        self.assertTrue(any(s["phase"] == "selecting" for s in saves))
        self.assertEqual(api.observed, [])

    def test_partial_monitor_error_archive_is_resumable_but_not_accepted(self):
        value = self.many(1)
        previous = self.previous(value)
        previous.update(status="MONITOR_ERROR", error="synthetic later failure")
        restored = m.previous_snapshot(SnapshotAPI({"result.json": json.dumps(previous)}), 200)
        self.assertEqual(restored["status"], "MONITOR_ERROR")
        self.assertEqual(restored["runs"], previous["runs"])
        self.assertIsNotNone(m.cached_row(value["runs"][0], restored))
        self.assertFalse(restored["full_phy_accepted"])

    def test_get_budget_stops_before_next_request_and_keeps_60_second_reserve(self):
        clock = [0.0]
        events = []
        budget = m.ReadBudget(clock=lambda: clock[0], emit=events.append, max_requests=2, seconds=120)
        api = m.API("fixture")
        api.read_budget = budget
        api.opener = CaptureOpener(SmallResponse(b"{}"))
        self.assertEqual(api.raw("actions/runs/123"), b"{}")
        clock[0] = 60.0
        with self.assertRaises(m.ObservationLimit):
            api.raw("actions/runs/124")
        self.assertEqual(len(api.opener.requests), 1)
        self.assertEqual(budget.requests, 1)
        self.assertEqual([e["event"] for e in events], ["GET_START", "GET_END"])
        self.assertEqual(budget.report()["per_request_timeout_seconds"], 60)

    def test_request_count_limit_and_failed_request_accounting(self):
        budget = m.ReadBudget(clock=lambda: 0, max_requests=1)
        api = m.API("fixture")
        api.read_budget = budget
        class BadOpener:
            def open(self, request, timeout):
                raise RuntimeError("synthetic network failure")
        api.opener = BadOpener()
        with self.assertRaisesRegex(RuntimeError, "synthetic network"):
            api.raw("actions/runs/123")
        self.assertIsNone(budget.inflight)
        self.assertEqual(budget.requests, 1)
        with self.assertRaises(m.ObservationLimit):
            api.raw("actions/runs/124")

    def main_failure(self, phase):
        import tempfile, os
        from unittest.mock import patch
        value = self.many(3)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap = root/"config.json"
            bootstrap.write_text(json.dumps(value))
            output = root/"out"
            summary = root/"summary.md"
            primary = RuntimeError("synthetic "+phase)
            loader = primary if phase == "inventory" else (value, dict(head_sha=HEAD, bootstrap=False))
            api = BoundedObservationAPI(value["runs"])
            with patch.object(m, "API", return_value=api), patch.object(m, "load_config", **({"side_effect": loader} if isinstance(loader, BaseException) else {"return_value": loader})), patch.object(m, "previous_snapshot", side_effect=primary):
                with patch.dict(os.environ, dict(GITHUB_ACTIONS="true", RUNNER_ENVIRONMENT="github-hosted", GITHUB_REPOSITORY=m.REPO,
                                               GH_TOKEN="fixture", GITHUB_RUN_ID="999", GITHUB_STEP_SUMMARY=str(summary))):
                    with patch.object(sys, "argv", ["monitor", "--config", str(bootstrap), "--out", str(output)]):
                        with self.assertRaises(RuntimeError) as caught:
                            m.main()
                self.assertIs(caught.exception, primary)
            saved = json.loads((output/"result.json").read_text())
            self.assertEqual(saved["status"], "MONITOR_ERROR")
            self.assertEqual(len(saved["runs"]), 3)
            self.assertEqual(len(saved["unobserved_runs"]), 3)
            self.assertFalse(saved["observation_complete"])
            self.assertFalse(saved["routine_unchanged"])
            self.assertIn(phase, saved["error"])
            self.assertFalse(saved["automatic_native_dispatch"])
            return saved

    def test_inventory_read_failure_preserves_early_bootstrap_snapshot(self):
        self.assertEqual(self.main_failure("inventory")["phase"], "loading_inventory")


    def test_atomic_snapshot_failure_keeps_previous_complete_file(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/"result.json"
            first = dict(status="PARTIAL_OBSERVATION", rows=[1, 2])
            m.atomic_snapshot(path, first)
            with patch.object(m.os, "replace", side_effect=RuntimeError("synthetic atomic replace failure")):
                with self.assertRaisesRegex(RuntimeError, "atomic replace"):
                    m.atomic_snapshot(path, dict(rows=[1, 2, 3]))
            self.assertEqual(json.loads(path.read_text()), first)

    def test_signal_handler_only_raises_checkpoint_boundary(self):
        with self.assertRaisesRegex(m.ObservationLimit, "Checkpoint requested by signal"):
            m.signal_limit(m.signal.SIGTERM, None)

    def test_markdown_distinguishes_cached_and_unobserved_from_unchanged(self):
        value = self.many(30)
        previous = self.previous(value)
        result, _, _ = self.observe(value, BoundedObservationAPI(value["runs"], stop_after=1), previous)
        rendered = m.markdown(result)
        self.assertIn("CACHED:", rendered)
        self.assertIn("not refreshed", rendered)
        self.assertFalse(result["routine_unchanged"])


    def test_actual_old_active_outside_newest16_is_first_without_cache(self):
        value = self.many(533)
        api = BoundedObservationAPI(value["runs"], active=[1001], stop_after=4)
        result, _, _ = self.observe(value, api)
        self.assertEqual(api.observed[0], 1001)
        self.assertEqual(result["discovered_active_runs"], [1001])
        self.assertEqual(api.discovery_calls, [(s, 1) for s in m.ACTIVE_STATUSES])
        self.assertTrue(result["active_discovery_complete"])
        self.assertEqual(len(result["runs"]), 533)

    def test_actual_rerun_of_cached_completed_old_run_is_prioritized(self):
        value = self.many(50)
        previous = self.previous(value)
        api = BoundedObservationAPI(value["runs"], active=[1002], stop_after=3)
        api.attempts[1002] = 2
        result, _, _ = self.observe(value, api, previous)
        self.assertEqual(api.observed[0], 1002)
        row = next(r for r in result["runs"] if r["id"] == 1002)
        self.assertEqual(row["status"], "in_progress")
        self.assertEqual(row["run_attempt"], 2)
        self.assertEqual(row["observation_state"], "CURRENT")
        self.assertTrue(row["changed_since_previous"])
        self.assertFalse(row["stale"])

    def test_all_five_actual_active_filters_prioritize_exact_pinned_identity(self):
        value = self.many(100)
        api = BoundedObservationAPI(value["runs"], active=range(1000, 1005), stop_after=5)
        api.active_states = {1000+i: status for i, status in enumerate(m.ACTIVE_STATUSES)}
        result, _, _ = self.observe(value, api)
        self.assertEqual(result["discovered_active_runs"], list(range(1000, 1005)))
        self.assertEqual(api.observed[:3], [1004, 1003, 1005])
        self.assertTrue(all(result["active_discovery"][s]["complete"] for s in m.ACTIVE_STATUSES))

    def test_untracked_active_is_visible_without_jobs_or_native_acquisition(self):
        value = self.many(2)
        api = BoundedObservationAPI(value["runs"])
        unknown = run()
        unknown.update(id=999999, head_sha="c"*40, head_branch="codex/untracked")
        api.extra_active = [unknown]
        result, _, _ = self.observe(value, api)
        self.assertEqual(result["untracked_active_runs"][0]["id"], 999999)
        self.assertFalse(result["untracked_active_runs"][0]["inventory_verified"])
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION")
        self.assertNotIn(999999, api.observed)
        self.assertEqual(len(result["runs"]), 2)
        self.assertFalse(result["observation_complete"])

    def test_discovery_identity_conflict_never_promotes_unmatched_source(self):
        value = self.many(30)
        api = BoundedObservationAPI(value["runs"], stop_after=2)
        wrong = run()
        wrong.update(id=1000, head_sha="c"*40)
        api.extra_active = [wrong]
        result, _, _ = self.observe(value, api)
        self.assertNotIn(1000, result["discovered_active_runs"])
        self.assertEqual(result["errors"][0]["type"], "IdentityMismatch")
        self.assertEqual(api.observed, [1029, 1028])
        self.assertFalse(result["active_discovery_complete"])

    def test_discovery_failure_keeps_prior_known_active_priority(self):
        value = self.many(50)
        previous = self.previous(value, active=[1001])
        api = BoundedObservationAPI(value["runs"], active=[1001], stop_after=3)
        api.discovery_errors.add("in_progress")
        result, _, _ = self.observe(value, api, previous)
        self.assertEqual(api.observed[0], 1001)
        self.assertFalse(result["active_discovery_complete"])
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION")
        self.assertTrue(any(e["phase"] == "active_discovery" for e in result["errors"]))

    def test_active_pagination_is_bounded_and_partial_if_more_remain(self):
        value = self.many(1)
        api = BoundedObservationAPI(value["runs"])
        api.extra_active = [dict(run(), id=9000+i) for i in range(205)]
        result, _, _ = self.observe(value, api)
        self.assertEqual(len(result["untracked_active_runs"]), 200)
        self.assertEqual(result["active_discovery"]["in_progress"]["pages"], 2)
        self.assertFalse(result["active_discovery_complete"])
        self.assertTrue(any(e["type"] == "PageLimit" for e in result["errors"]))
        self.assertEqual(api.observed, [1000])

    def test_cache_subbudget_does_not_exhaust_live_get_budget(self):
        clock = [0.0]
        api = m.API("fixture")
        api.read_budget = m.ReadBudget(clock=lambda: clock[0])
        api.cache_read_budget = m.ReadBudget(clock=lambda: clock[0], seconds=90, limit_type=m.CacheLookupLimit)
        api.opener = CaptureOpener(SmallResponse(b"{}"))
        api.raw("actions/artifacts?name=fixture")
        clock[0] = 30.0
        with self.assertRaises(m.CacheLookupLimit):
            api.raw("actions/artifacts/1/zip")
        self.assertEqual(len(api.opener.requests), 1)
        api.cache_read_budget = None
        api.opener = CaptureOpener(SmallResponse(b"{}"))
        self.assertEqual(api.raw("actions/runs?status=in_progress"), b"{}")
        self.assertLess(api.read_budget.report()["elapsed_seconds"], 540)
        self.assertEqual(api.read_budget.requests, 3)  # Conservative attempted-GET count.

    def test_prior_snapshot_source_candidate_cap_prevents_unbounded_lookup(self):
        class ManyUntrusted:
            def __init__(self): self.sources = []
            def pages(self, path, key, maximum=1000):
                return [dict(id=i, expired=False, name=m.ARTIFACT, size_in_bytes=100, created_at="2026-10-24T11:00:00Z", workflow_run=dict(id=i)) for i in range(1, 30)]
            def get(self, path):
                self.sources.append(path)
                return dict(path=m.WORKFLOW, status="completed", head_branch="codex/untrusted")
            def raw(self, *args, **kwargs): raise AssertionError("Untrusted artifact acquired")
        api = ManyUntrusted()
        with self.assertRaises(m.CacheLookupLimit):
            m.previous_snapshot(api, 999)
        self.assertEqual(len(api.sources), 16)

    def test_previous_artifact_refusal_continues_live_observation_with_partial_provenance(self):
        import tempfile, os
        from unittest.mock import patch
        value = self.many(3)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap = root/"config.json"
            bootstrap.write_text(json.dumps(value))
            output = root/"out"
            api = BoundedObservationAPI(value["runs"], active=[1000])
            with patch.object(m, "API", return_value=api), patch.object(m, "load_config", return_value=(value, dict(head_sha=HEAD, bootstrap=False))), patch.object(m, "previous_snapshot", side_effect=AssertionError("synthetic prior digest refusal")):
                with patch.dict(os.environ, dict(GITHUB_ACTIONS="true", RUNNER_ENVIRONMENT="github-hosted", GITHUB_REPOSITORY=m.REPO, GH_TOKEN="fixture", GITHUB_RUN_ID="999", GITHUB_STEP_SUMMARY=str(root/"summary.md"))):
                    with patch.object(sys, "argv", ["monitor", "--config", str(bootstrap), "--out", str(output)]):
                        self.assertEqual(m.main(), 0)
            saved = json.loads((output/"result.json").read_text())
            self.assertEqual(saved["status"], "PARTIAL_OBSERVATION")
            self.assertEqual(len(saved["refreshed_runs"]), 3)
            self.assertEqual(api.observed[0], 1000)
            self.assertIn("prior digest refusal", saved["cache_lookup"]["error"]["detail"])
            self.assertIsNone(saved["previous_snapshot_source"])
            self.assertFalse(saved["routine_unchanged"])
            self.assertFalse(saved["full_phy_accepted"])

    def test_signal_during_prior_artifact_stops_with_complete_unread_inventory(self):
        import tempfile, os
        from unittest.mock import patch
        value = self.many(3)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap = root/"config.json"
            bootstrap.write_text(json.dumps(value))
            output = root/"out"
            api = BoundedObservationAPI(value["runs"])
            with patch.object(m, "API", return_value=api), patch.object(m, "load_config", return_value=(value, dict(head_sha=HEAD, bootstrap=False))), patch.object(m, "previous_snapshot", side_effect=m.ObservationLimit("synthetic SIGTERM boundary")):
                with patch.dict(os.environ, dict(GITHUB_ACTIONS="true", RUNNER_ENVIRONMENT="github-hosted", GITHUB_REPOSITORY=m.REPO, GH_TOKEN="fixture", GITHUB_RUN_ID="999", GITHUB_STEP_SUMMARY=str(root/"summary.md"))):
                    with patch.object(sys, "argv", ["monitor", "--config", str(bootstrap), "--out", str(output)]):
                        self.assertEqual(m.main(), 0)
            saved = json.loads((output/"result.json").read_text())
            self.assertEqual(saved["status"], "PARTIAL_OBSERVATION")
            self.assertEqual(saved["unobserved_runs"], [1000, 1001, 1002])
            self.assertEqual(api.observed, [])
            self.assertEqual(saved["read_budget"]["maximum_requests"], 600)
            self.assertEqual(saved["cache_lookup"]["read_budget"]["maximum_requests"], 24)
            self.assertFalse(saved["observation_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
