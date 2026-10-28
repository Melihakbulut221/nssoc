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
            self.assertEqual(saved["runs"],[])
            self.assertFalse(saved["automatic_native_dispatch"])
            self.assertFalse(saved["full_phy_accepted"])
            self.assertIn("No native work was changed",summary.read_text())
            self.assertTrue(all(path.startswith(("contents/","git/ref/heads/")) for _,path in api.calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
