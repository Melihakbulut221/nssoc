# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real process signals at the exact outer/native ownership boundary."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import pytest

B=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('loaded455_compact_launcher01',B/'launch_probe01.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)


@pytest.mark.parametrize('signum',[signal.SIGTERM,signal.SIGINT])
def test_real_stop_before_native_owner_entry_prevents_launch(tmp_path,monkeypatch,signum):
    attempts=[]
    original={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def future_native(*args):
        # Exact position where the old empty outer-owner check had passed but
        # the nested native owner had not installed its handler or launched.
        os.kill(os.getpid(),signum)
        attempts.append('would-launch-native')
        raise AssertionError('stop was lost')
    monkeypatch.setattr(launcher.m,'run',future_native)
    with pytest.raises(RuntimeError,match=signal.Signals(signum).name):launcher.run_with_boundary_signals()
    assert not attempts
    assert all(signal.getsignal(s)==h for s,h in original.items())
    (tmp_path/'handoff-result.json').write_text(json.dumps({'status':'PASS_REAL_SIGNAL_PREVENTED_LAUNCH','signal':signal.Signals(signum).name,'launch_attempts':attempts,'handlers_restored':True},indent=2)+'\n')


@pytest.mark.parametrize('signum',[signal.SIGTERM,signal.SIGINT])
def test_real_stop_after_native_owner_exit_cannot_be_lost(tmp_path,monkeypatch,signum):
    original={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def finite_native(*args):
        with launcher.m.life.ProcessOwner(tmp_path/'actual-inner-owner.json') as owner:
            process=owner.launch('native',[sys.executable,'-c','print("actual child complete")'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            process.wait()
            owner.complete(process)
            owner.check()
        owner.check()
        os.kill(os.getpid(),signum)
        raise AssertionError('post-native stop was lost')
    monkeypatch.setattr(launcher.m,'run',finite_native)
    with pytest.raises(RuntimeError,match=signal.Signals(signum).name):launcher.run_with_boundary_signals()
    assert all(signal.getsignal(s)==h for s,h in original.items())
    record=json.loads((tmp_path/'actual-inner-owner.json').read_text())
    assert record['processes'][0]['status']=='REAPED_NO_LIVE_MEMBERS'
    (tmp_path/'handoff-result.json').write_text(json.dumps({'status':'PASS_REAL_SIGNAL_AFTER_NATIVE_OWNERSHIP_EXIT','signal':signal.Signals(signum).name,'child_status':record['processes'][0]['status'],'handlers_restored':True},indent=2)+'\n')
