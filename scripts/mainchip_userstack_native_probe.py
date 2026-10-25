#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Controller-side observer lifecycle; no route-progress acceptance."""
import json,os,shutil,subprocess,sys,time
from pathlib import Path
from mainchip_userstack_identity import snapshot,file_sha
from mainchip_userstack_observer import write
from mainchip_userstack_native_binding import inventory,inspect,bound,verify_live
ROOT=Path(__file__).resolve().parents[1]
PROBE=None
def start_probe(name,inv,case,out,r):
    global PROBE
    assert PROBE is None
    c=inspect(name);assert c['running']and c['image']==r['image_id']
    expect={k:c[k]for k in ('id','image','pid','started_at','cpuset')}
    expect.update(route_tcl=str(case/'route.tcl'))
    bound(c,expect)
    folder=out/'native-userstack';folder.mkdir()
    expected_path=folder/'expect.json';write(expected_path,expect)
    inv_path=ROOT/'cloud-mainchip-route12-drt-runtime/input/runtime-inventory.json'
    assert inventory(inv_path.read_bytes())==inv
    gdb=shutil.which('gdb');assert gdb
    from mainchip_userstack_native_observer import GDB_SHA
    assert file_sha(gdb)==GDB_SHA
    command=['sudo','env','GITHUB_ACTIONS=true',sys.executable,str(ROOT/'scripts/mainchip_userstack_native_observer.py'),
        '--expect',str(expected_path),'--inventory',str(inv_path),'--out',str(folder),'--gdb',gdb]
    stream=(folder/'driver.log').open('xb')
    child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    PROBE=dict(process=child,stream=stream,folder=folder,expect=expect,inventory=inv,start=time.monotonic(),finished=False)
    deadline=PROBE['start']+60
    while not(folder/'ready.json').exists()and child.poll()is None and time.monotonic()<deadline:time.sleep(.25)
    if(folder/'ready.json').exists():
        ready=json.loads((folder/'ready.json').read_text())
        if ready['status']=='BOUND_EXACT_NATIVE_PROCESS':
            expect['identity']=ready['identity'];write(expected_path,expect)
    r['native_userstack_started']=dict(expected=expect,ready=(folder/'ready.json').exists(),
        scheduling_perturbed=True,normal_continuation_accepted=False)
def probe_rejected():
    if PROBE is None:return True
    p=PROBE;folder=p['folder']
    if time.monotonic()-p['start']>500 and p['process'].poll()is None:return True
    if not(folder/'ready.json').exists():return True
    if json.loads((folder/'ready.json').read_text())['status']!='BOUND_EXACT_NATIVE_PROCESS':return True
    if(folder/'result.json').exists():
        return json.loads((folder/'result.json').read_text())['status']!='PASS_20_EXACT_SAVED_NATIVE_STACK_SAMPLES'
    return p['process'].poll()is not None
def finish_probe(r,out):
    if PROBE is None:return
    p=PROBE;folder=p['folder'];child=p['process']
    if p['finished']:
        assert child.poll()is not None
        r['native_userstack_finished']=p['finished_report'];return
    if not p['finished']:
        remaining=max(.1,500-(time.monotonic()-p['start']))
        try:rc=child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            (folder/'stop').touch(exist_ok=True)
            child.terminate()
            # The supervised GDB command has its own10s deadline and mandatory group cleanup.
            # Never signal the native target or an unowned numeric debugger PID.
            try:rc=child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                raise AssertionError('Observer cleanup exceeded envelope; native checkpoint admission rejected')
        finally:
            if child.poll()is not None:p['stream'].close()
        p['returncode']=rc
    command=['sudo','env','GITHUB_ACTIONS=true',sys.executable,str(ROOT/'scripts/mainchip_userstack_native_binding.py'),
        '--verify','--expect',str(folder/'expect.json'),'--inventory',str(ROOT/'cloud-mainchip-route12-drt-runtime/input/runtime-inventory.json')]
    detached=json.loads(subprocess.check_output(command,timeout=30))
    assert detached['status']=='PASS_EXACT_NATIVE_DETACHED_IDENTITY'and detached['target_detached']is True
    info=dict(returncode=p['returncode'],scheduling_perturbed=True,
        target_detached_before_checkpoint=True,identity=detached['identity'],normal_continuation_accepted=False)
    if(folder/'result.json').exists():
        info['report']=json.loads((folder/'result.json').read_text());info['report_sha256']=file_sha(folder/'result.json')
    else:info['missing_report']=True
    r['native_userstack_finished']=info
    p['finished_report']=info
    assert p['process'].poll()is not None,'Observer still active at native checkpoint'
    for path in folder.glob('sample-*/command/command.json'):
        command=json.loads(path.read_text())
        assert command.get('cleanup',{}).get('live_remaining')is False,'Debugger group cleanup not proved'
    p['finished']=True
def validate_observations():
    assert PROBE is not None and PROBE['finished']and PROBE['returncode']==0
    folder=PROBE['folder'];r=json.loads((folder/'result.json').read_text())
    assert r['status']=='PASS_20_EXACT_SAVED_NATIVE_STACK_SAMPLES'and r['one_pidfd_held_for_full_collection']is True
    assert r['runtime_closure']['full_declared_closure_verified']is True and r['elapsed_s']<480
    samples=r['samples'];assert len(samples)==20 and [s['index']for s in samples]==list(range(20))
    assert all(s['status']=='PASS_BOUNDED_EXACT_NATIVE_ATTACHMENT'for s in samples)
    from mainchip_userstack_native_observer import accepted_reader
    assert all(accepted_reader(s['reader'])for s in samples)
    assert all(s['reader']['identity']==PROBE['expect']['identity']for s in samples)
    return dict(samples=20,result_sha256=file_sha(folder/'result.json'),identity=PROBE['expect']['identity'],
        scheduling_perturbed=True,full_runtime_closure_verified=True,normal_continuation_accepted=False,
        route_progress_accepted=False,caller_stacks_are_diagnostics_not_causal_proof=True)
