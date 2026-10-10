# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual owned upload children: timeout, immutable races and full readback."""
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from test_pcie_native_publisher_v3 import http_fixture, payload

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
m = importlib.import_module("publish_pcie_native_capture_v4")


def upload_fixture(tmp_path, monkeypatch, source, asset, modes):
    state = tmp_path / "upload-state.json"
    state.write_text(json.dumps(dict(uploads=0, assets=[], calls=[], metadata=0)))
    config = tmp_path / "upload-config.json"
    config.write_text(json.dumps(dict(state=str(state), source=str(source), asset=asset, modes=modes)))
    gh = tmp_path / "gh"
    gh.write_text("#!" + sys.executable + "\n" + '''
import json,sys,time
from pathlib import Path
c=json.loads(Path(''' + repr(str(config)) + ''').read_text())
p=Path(c['state']);s=json.loads(p.read_text());s['calls'].append(sys.argv[1:])
if sys.argv[1:3]==['release','upload']:
 assert '--clobber' not in sys.argv
 n=s['uploads'];s['uploads']+=1;mode=c['modes'][min(n,len(c['modes'])-1)]
 if mode in ['success','uncertain_present','collision','corrupt','duplicate','hidden']:
  a=dict(c['asset'])
  if mode=='corrupt':a['digest']='sha256:'+'0'*64
  s['assets']=[a,a] if mode=='duplicate' else [a]
 if mode=='hidden':s['hidden_remaining']=2
 p.write_text(json.dumps(s))
 if mode=='timeout_absent':time.sleep(60)
 if mode in ['uncertain_present','corrupt','duplicate','transient_absent']:
  print('TLS handshake timeout',file=sys.stderr);raise SystemExit(1)
 if mode=='collision':print('HTTP 422 already_exists',file=sys.stderr);raise SystemExit(1)
 if mode=='unauthorized':print('HTTP 401',file=sys.stderr);raise SystemExit(1)
 raise SystemExit(0)
if '/releases/tags/' in ' '.join(sys.argv):
 s['metadata']+=1;assets=s['assets']
 if s.get('hidden_remaining',0):assets=[];s['hidden_remaining']-=1
 p.write_text(json.dumps(s));print(json.dumps({'assets':assets}));raise SystemExit(0)
if '/releases/assets/' in ' '.join(sys.argv):
 p.write_text(json.dumps(s));sys.stdout.buffer.write(Path(c['source']).read_bytes());raise SystemExit(0)
raise SystemExit(2)
''')
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    return state


def row(source, expected):
    return dict(path=str(source), name=source.name, **expected)


@pytest.mark.parametrize("mode", ["timeout_absent", "transient_absent"])
def test_real_uncertain_absent_upload_is_reconciled_then_retried(tmp_path, monkeypatch, mode):
    p, e, a = payload(tmp_path)
    state = upload_fixture(tmp_path, monkeypatch, p, a, [mode, "success"])
    client = m.Client(tmp_path / "evidence", attempts=2, timeout=.3, backoff=0)
    assert client.resolve_asset("tag", row(p, e)) == a
    assert json.loads(state.read_text())["uploads"] == 2
    attempts = json.loads((client.directory / "attempts.json").read_text())
    uploads = [x for x in attempts if x["kind"] == "upload"]
    assert [x["status"] for x in uploads] == ["TRANSPORT_FAILURE", "PASS"]
    if mode == "timeout_absent":
        assert uploads[0]["deadline_triggered"] and uploads[0]["returncode"] == -signal.SIGTERM
        owner = json.loads(Path(uploads[0]["owned_processes"]).read_text())
        for process in owner["processes"]:
            assert not any(x["state"] != "Z" for x in m.lifecycle.group_members(process["process_group"]))
    assert m.pin(p) == e


@pytest.mark.parametrize("mode", ["uncertain_present", "collision", "hidden"])
def test_real_upload_present_or_visibility_delay_never_reuploads(tmp_path, monkeypatch, mode):
    p, e, a = payload(tmp_path)
    state = upload_fixture(tmp_path, monkeypatch, p, a, [mode])
    client = m.Client(tmp_path / "evidence", attempts=3, timeout=3, backoff=0)
    assert client.resolve_asset("tag", row(p, e)) == a
    assert json.loads(state.read_text())["uploads"] == 1
    assert m.pin(p) == e


@pytest.mark.parametrize("mode", ["corrupt", "duplicate", "unauthorized"])
def test_real_integrity_or_permanent_failure_never_retries_upload(tmp_path, monkeypatch, mode):
    p, e, a = payload(tmp_path)
    state = upload_fixture(tmp_path, monkeypatch, p, a, [mode, "success"])
    client = m.Client(tmp_path / "evidence", attempts=4, timeout=3, backoff=0)
    with pytest.raises((m.IntegrityError, RuntimeError)):
        client.resolve_asset("tag", row(p, e))
    assert json.loads(state.read_text())["uploads"] == 1


def test_real_upload_retry_budget_is_finite(tmp_path, monkeypatch):
    p, e, a = payload(tmp_path)
    state = upload_fixture(tmp_path, monkeypatch, p, a, ["transient_absent"])
    client = m.Client(tmp_path / "evidence", attempts=3, timeout=3, backoff=0)
    with pytest.raises(m.TransportError, match="budget exhausted"):
        client.resolve_asset("tag", row(p, e))
    assert json.loads(state.read_text())["uploads"] == 3
    assert len(client.reconciliations) == 3


def test_successful_but_missing_asset_has_bounded_metadata_only_retries(tmp_path, monkeypatch):
    p, e, a = payload(tmp_path)
    state = upload_fixture(tmp_path, monkeypatch, p, a, ["success_absent"])
    client = m.Client(tmp_path / "evidence", attempts=3, timeout=3, backoff=0)
    with pytest.raises(m.IntegrityError, match="Successful upload remains absent"):
        client.resolve_asset("tag", row(p, e))
    assert json.loads(state.read_text())["uploads"] == 1
    assert len(client.reconciliations) == 3


def test_current_capture_change_refuses_upload(tmp_path, monkeypatch):
    p, e, a = payload(tmp_path)
    state = upload_fixture(tmp_path, monkeypatch, p, a, ["success"])
    client = m.Client(tmp_path / "evidence", attempts=3, timeout=3, backoff=0)
    p.write_bytes(b"changed")
    with pytest.raises(m.IntegrityError, match="Local capture changed"):
        client.resolve_asset("tag", row(p, e))
    assert json.loads(state.read_text())["uploads"] == 0


def test_real_cli_retries_upload_and_requires_both_full_readbacks(tmp_path, monkeypatch):
    p, e, a = payload(tmp_path)
    with http_fixture(p.read_bytes(), [{}]) as (url, calls):
        a["browser_download_url"] = url
        state = upload_fixture(tmp_path, monkeypatch, p, a, ["transient_absent", "success"])
        receipt = tmp_path / "receipt.json"
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/publish_pcie_native_capture_v4.py"),
                               "--out", str(receipt), str(p)], capture_output=True, timeout=12)
        assert proc.returncode == 0, proc.stderr.decode()
        result = json.loads(receipt.read_text())
        assert result["status"] == "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
        assert result["publisher_revision"] == 4 and result["physical_acceptance"] is False
        assert result["publisher_v3"]["sha256"] == m.PREVIOUS_SHA
        assert result["assets"][0]["authenticated_roundtrip"] and result["assets"][0]["anonymous_roundtrip"]
        assert len(result["upload_reconciliations"]) == 2
        assert len(calls) == 1 and json.loads(state.read_text())["uploads"] == 2
        assert m.pin(p) == e


@pytest.mark.parametrize("phase", ["backoff", "upload"])
def test_real_signal_stops_owned_upload_and_prevents_new_attempt(tmp_path, monkeypatch, phase):
    p, e, a = payload(tmp_path)
    mode = "transient_absent" if phase == "backoff" else "timeout_absent"
    state = upload_fixture(tmp_path, monkeypatch, p, a, [mode, "success"])
    receipt = tmp_path / "receipt.json"
    proc = subprocess.Popen([sys.executable, str(ROOT / "scripts/publish_pcie_native_capture_v4.py"),
                             "--out", str(receipt), str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        record = receipt.with_suffix(".transport") / "reconciliation.json"
        start = time.monotonic()
        while time.monotonic() - start < 6:
            ready = record.exists() and json.loads(record.read_text())[-1]["status"] == "ABSENT_AFTER_UNCERTAIN_UPLOAD"
            if phase == "upload":
                ready = json.loads(state.read_text())["uploads"] == 1
            if ready:
                break
            time.sleep(.01)
        else:
            pytest.fail("No completed upload reconciliation")
        proc.send_signal(signal.SIGTERM)
        assert proc.wait(timeout=3) != 0
        result = json.loads(receipt.read_text())
        assert result["explicit_stop"] and result["status"] == "FAIL"
        assert json.loads(state.read_text())["uploads"] == 1
        for path in receipt.with_suffix(".transport").glob("*/owned-processes.json"):
            for process in json.loads(path.read_text())["processes"]:
                assert not any(x["state"] != "Z" for x in m.lifecycle.group_members(process["process_group"]))
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_cli_source_bridge_preserves_every_other_v3_byte():
    source = m.original_source
    for before, after in m.replacements:
        assert source.count(before) == 1
        source = source.replace(before, after)
    assert source == m.main_source
    assert m.pin(m.previous.__file__)["sha256"] == m.PREVIOUS_SHA
