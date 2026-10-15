# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted process tests: rejected routing must stop, healthy output must survive."""
import json
import os
from pathlib import Path
import re
import sys
import time
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import route_cloud_newer_postcts as route


def runner(tmp_path,monkeypatch,body):
    tool=tmp_path/'fake-openroad'
    tool.write_text('#!/usr/bin/env python3\n'+body)
    tool.chmod(0o755)
    monkeypatch.setenv('CLOUD_APPIMAGE',str(tool))
    out=tmp_path/'out';out.mkdir();monkeypatch.setattr(route,'OUT',out)
    return out


def test_ndr_violation_stops_process_group_and_preserves_failure(tmp_path,monkeypatch):
    out=runner(tmp_path,monkeypatch,
        "import subprocess,sys,time\n"
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
        "print('CHILD_PID='+str(child.pid),flush=True)\n"
        "print('[WARNING GRT-0273] Disabled NDR (to reduce congestion) for net: clk_i',flush=True)\n"
        "time.sleep(60)\n")
    started=time.monotonic()
    with pytest.raises(RuntimeError):route.execute('original constraints\n','global-route')
    assert time.monotonic()-started<10
    result=json.loads((out/'global-route-rejected.json').read_text())
    assert result['cause']['disabled_nets']==['clk_i'] and not result['accepted']
    log=(out/'global-route.log').read_text()
    child=int(re.search(r'CHILD_PID=(\d+)',log)[1])
    for _ in range(50):
        stat=Path(f'/proc/{child}/stat')
        if not stat.exists() or stat.read_text().split()[2]=='Z':break
        time.sleep(.02)
    else:raise AssertionError('Descendant survived rejected trial')
    assert (out/'global-route.tcl').read_text()=='original constraints\n'


def test_healthy_global_output_is_not_cancelled(tmp_path,monkeypatch):
    out=runner(tmp_path,monkeypatch,"print('[INFO GRT-0014] Routed nets: 113556')\n")
    assert '113556' in route.execute('unchanged\n','global-route')
    assert not (out/'global-route-rejected.json').exists()


def test_guard_does_not_misclassify_unrelated_phase(tmp_path,monkeypatch):
    out=runner(tmp_path,monkeypatch,"print('GRT-0273 is a report fixture')\n")
    assert 'report fixture' in route.execute('diagnostic\n','source-self-test')
    assert not (out/'global-route-rejected.json').exists()
