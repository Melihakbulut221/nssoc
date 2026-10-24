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
        with self.assertRaises(AssertionError): m.collect(api, config(), NOW)
        self.assertFalse(any(kind == "raw" for kind, _ in api.calls))

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

if __name__ == "__main__":
    unittest.main(verbosity=2)
