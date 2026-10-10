# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native-recipe guards and actual process-group cleanup, without PDK fixtures."""

import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_pcie_gen3_block_cdc_native_v1.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("block_cdc_native", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_frozen_sources_and_exact_seven_cases():
    m.check_sources()
    assert len(m.CASES) == 7 and len(set(m.CASES)) == 7


def test_source_drift_rejects(monkeypatch):
    original = m.pin

    def wrong(path):
        value = original(path)
        if Path(path).name == "axis_async_fifo.v":
            value["sha256"] = "0" * 64
        return value

    monkeypatch.setattr(m, "pin", wrong)
    with pytest.raises(RuntimeError, match="Frozen complete-block source changed"):
        m.check_sources()


def test_mapping_reuses_exact_vendor_and_full_default_depth(tmp_path):
    flow = m.map_script(tmp_path, tmp_path / "cells.lib")
    assert "axis_async_fifo.v" in flow and m.TOP in flow
    assert " -nofsm -noabc" in flow and "check -assert" in flow
    assert (
        "chparam" not in flow and "async2sync" not in flow and "clk2fflogic" not in flow
    )
    assert m.ABC_RECIPE == "strash; balance -x; &get -n; &nf; &put\n"
    assert m.AS_BYTES == 2 * 1024**3 and m.ENTRY_BYTES == 1024**3
    assert m.FLOOR_BYTES == 528 * 1024**2


def xml(path, names, fail=False, skip=False):
    root = ET.Element("testsuites")
    suite = ET.SubElement(root, "testsuite")
    for index, name in enumerate(names):
        case = ET.SubElement(suite, "testcase", name=name)
        if index == 0 and fail:
            ET.SubElement(case, "failure", message="actual fault")
        if index == 0 and skip:
            ET.SubElement(case, "skipped")
    ET.ElementTree(root).write(path)


def test_all_exact_cases_accepted(tmp_path):
    path = tmp_path / "results.xml"
    xml(path, m.CASES)
    assert m.verify_tests(path) == dict(passed=7, failed=0, skipped=0)


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "wrong", "failure", "skipped"]
)
def test_bad_native_disposition_rejected(tmp_path, fault):
    names = list(m.CASES)
    if fault == "missing":
        names.pop()
    elif fault == "duplicate":
        names[-1] = names[0]
    elif fault == "wrong":
        names[-1] = "invented_positive"
    path = tmp_path / "results.xml"
    xml(path, names, fail=fault == "failure", skip=fault == "skipped")
    with pytest.raises(RuntimeError, match="every exact frozen native case"):
        m.verify_tests(path)


def identity(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    fields = text[text.rfind(")") + 2 :].split()
    return fields[0], int(fields[19])


@pytest.mark.parametrize("trigger", ["parent_term", "ledger_io", "floor"])
def test_actual_cleanup_stops_descendant_after_leader_exit(tmp_path, trigger):
    tool = tmp_path / "tool.py"
    tool.write_text("""import json,os,signal,time
from pathlib import Path
leader=os.getpid()
child=os.fork()
if child==0:
 signal.signal(signal.SIGTERM,signal.SIG_IGN)
 text=Path('/proc/self/stat').read_text()
 start=int(text[text.rfind(')')+2:].split()[19])
 deadline=time.monotonic()+8
 Path('descendant.json').write_text(json.dumps(dict(pid=os.getpid(),start=start,group=os.getpgrp(),leader=leader,deadline=deadline)))
 while time.monotonic()<deadline:time.sleep(.02)
 Path('late-write').write_text('escaped')
 time.sleep(30)
else:
 while True:time.sleep(.1)
""")
    harness = tmp_path / "harness.py"
    harness.write_text(f"""import json,os,signal,sys,time,shutil
from pathlib import Path
sys.path.insert(0,{str(ROOT / "scripts")!r})
import check_pcie_gen3_block_cdc_native_v1 as m
signal.signal(signal.SIGTERM,m.interrupted)
signal.signal(signal.SIGINT,m.interrupted)
out=Path({str(tmp_path)!r})
trigger={trigger!r}
record=dict(commands=[])
def save():
 if record.get('active_group'):
  deadline=time.monotonic()+3
  while not (out/'descendant.json').exists():
   if time.monotonic()>deadline:raise RuntimeError('Synthetic child not ready')
   time.sleep(.01)
  (out/'entered').write_text('ready')
  if trigger=='ledger_io':raise OSError('Injected ledger I/O failure')
usage=m.shutil.disk_usage
def floor(path):
 value=usage(path)
 if trigger=='floor' and (out/'entered').exists():
  return shutil._ntuple_diskusage(value.total,value.used,m.FLOOR_BYTES-1)
 return shutil._ntuple_diskusage(value.total,value.used,max(value.free,2*m.ENTRY_BYTES))
m.shutil.disk_usage=floor
try:
 m.execute([sys.executable,str(out/'tool.py')],out/'tool.log',out,dict(os.environ),record,save)
except BaseException as error:
 (out/'observed-error.json').write_text(json.dumps(dict(error=repr(error))))
 raise
""")
    child = None
    with (tmp_path / "parent.log").open("w") as log:
        parent = subprocess.Popen(
            [sys.executable, str(harness)],
            cwd=tmp_path,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        try:
            deadline = time.monotonic() + 10
            while not (tmp_path / "entered").exists():
                assert parent.poll() is None, (tmp_path / "parent.log").read_text()
                assert time.monotonic() < deadline
                time.sleep(0.02)
            child = json.loads((tmp_path / "descendant.json").read_text())
            assert identity(child["pid"])[1] == child["start"]
            if trigger == "parent_term":
                parent.send_signal(signal.SIGTERM)
            assert parent.wait(timeout=12) != 0
            deadline = time.monotonic() + 2
            while True:
                state = identity(child["pid"])
                if state is None or state[1] != child["start"] or state[0] == "Z":
                    break
                assert time.monotonic() < deadline, "Original descendant survived"
                time.sleep(0.02)
            while time.monotonic() <= child["deadline"] + 0.15:
                time.sleep(0.02)
            assert not (tmp_path / "late-write").exists()
            error = json.loads((tmp_path / "observed-error.json").read_text())["error"]
            assert {
                "parent_term": "External process signal 15",
                "ledger_io": "ledger I/O failure",
                "floor": "Shared528MiB storage floor",
            }[trigger] in error
            (tmp_path / "lifecycle-observation.json").write_text(
                json.dumps(
                    dict(
                        trigger=trigger,
                        child=child,
                        stopped_identity=state,
                        late_write=False,
                        original_error=error,
                        returncode=parent.returncode,
                    ),
                    indent=2,
                )
                + "\n"
            )
        finally:
            if parent.poll() is None:
                os.killpg(parent.pid, signal.SIGKILL)
                parent.wait()
            if child is not None:
                try:
                    os.killpg(child["group"], signal.SIGKILL)
                except ProcessLookupError:
                    pass
