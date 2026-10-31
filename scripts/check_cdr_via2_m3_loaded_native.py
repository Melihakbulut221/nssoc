#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic subprocess controls for exact merged-stream loaded entry."""
import copy,json,os,signal,sys,types
from pathlib import Path
import cdr_via2_m3_loaded_native as n
import cdr_v59_tail_access_runtime as runtime
q=n.q

def refuse(fn,label,records):
    try:fn()
    except BaseException as error:
        if isinstance(error,(KeyboardInterrupt,SystemExit)):raise
        records.append(dict(name=label,error=type(error).__name__));return error
    raise AssertionError('expected refusal '+label)

def plan_fixture(root,script):
    root.mkdir(parents=True,exist_ok=False);native=root/'native';native.mkdir()
    engine=Path(sys.executable).resolve()
    plan=dict(argv=[str(engine),'-u','-c',script],cwd=str(native),remove_environment_keys=['LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN'],environment=dict(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1'),stdout=str(native/'native.log'),stderr='STDOUT',engine=q.file_pin(engine),prepared_state=dict(scope='EXPLICIT_SYNTHETIC_FIXTURE'),case='nominal_late',context=dict(scope='EXPLICIT_SYNTHETIC_FIXTURE'))
    return plan

def no_process(pid):
    try:os.kill(pid,0)
    except ProcessLookupError:return True
    return False

def controls(out,gate):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);records=[];positive=[]
    def execute(name,script,seconds=2):
        folder=out/name;plan=plan_fixture(folder,script)
        result=n.execute_engine(plan,folder,seconds)
        stored=q.decode((folder/'engine-result.json').read_bytes())
        assert stored==result and no_process(stored['engine_pid'])
        return folder,plan,stored
    folder,plan,r=execute('merged','import os;os.write(1,b"A\\n");os.write(2,b"B\\n");os.write(1,b"C\\n")')
    assert Path(plan['stdout']).read_bytes()==b'A\nB\nC\n'
    assert n.validate_engine_result(folder,plan,r,0)==0
    positive.append('real_synthetic_process_exact_merged_order')
    for name,script,rc,wrapper in [('nonzero','raise SystemExit(7)',7,1),('signal','import os,signal;os.kill(os.getpid(),signal.SIGTERM)',-signal.SIGTERM,1)]:
        folder,plan,r=execute(name,script)
        assert r['actual_engine_returncode']==rc and r['wrapper_returncode']==wrapper
        assert n.validate_engine_result(folder,plan,r,wrapper)==rc
        positive.append(name+'_authentic_engine_receipt')
        refuse(lambda:n.validate_engine_result(folder,plan,r,0),name+'_wrong_wrapper_code',records)
    for mode in('timeout','output-limit'):
        folder=out/mode
        script='import os,time;os.write(1,b"PARTIAL\\n");time.sleep(10)'if mode=='timeout'else'import os;os.write(1,b"X"*(16*1024*1024+1))'
        plan=plan_fixture(folder,script)
        error=refuse(lambda:n.execute_engine(plan,folder,.2 if mode=='timeout'else 2),mode,records)
        r=q.decode((folder/'engine-result.json').read_bytes())
        assert r['status']=='FAIL_OR_ERROR_ENGINE'and r['actual_engine_started']is True and no_process(r['engine_pid'])
        assert Path(plan['stdout']).stat().st_size>0 and r['retained_native_log']==q.file_pin(Path(plan['stdout']))
        refuse(lambda:n.validate_engine_result(folder,plan,r,1),mode+'_cannot_be_success',records)
        positive.append(mode+'_partial_stream_retained')
    folder=out/'diagnostic-primary';plan=plan_fixture(folder,'import os,time;os.write(1,b"PARTIAL\\n");time.sleep(10)')
    def file_pin(path):
        if Path(path)==Path(plan['stdout']):raise OSError('FORCED_DIAGNOSTIC_READ_FAILURE')
        return q.file_pin(path)
    globals_copy=dict(n.execute_engine.__globals__,q=types.SimpleNamespace(file_pin=file_pin))
    clone=types.FunctionType(n.execute_engine.__code__,globals_copy,n.execute_engine.__name__,n.execute_engine.__defaults__)
    error=refuse(lambda:clone(plan,folder,.2),'primary_with_observation_failure',records)
    r=q.decode((folder/'engine-result.json').read_bytes())
    assert 'engine elapsed limit'in str(error)and 'engine elapsed limit'in r['error']and any('FORCED_DIAGNOSTIC_READ_FAILURE'in v for v in r['observation_errors'])
    assert no_process(r['engine_pid']);positive.append('secondary_observation_never_replaces_primary')
    folder=out/'save-primary';plan=plan_fixture(folder,'import os,time;os.write(1,b"PARTIAL\\n");time.sleep(10)')
    def broken_write(path,value):
        if Path(path).name=='engine-result.json':raise OSError('FORCED_RECEIPT_SAVE_FAILURE')
        return n.write(path,value)
    clone=types.FunctionType(n.execute_engine.__code__,dict(n.execute_engine.__globals__,write=broken_write),n.execute_engine.__name__,n.execute_engine.__defaults__)
    error=refuse(lambda:clone(plan,folder,.2),'primary_with_receipt_save_failure',records)
    assert 'engine elapsed limit'in str(error)and Path(plan['stdout']).read_bytes()==b'PARTIAL\n'
    started=q.decode((folder/'engine-started.json').read_bytes());assert no_process(started['engine_pid']);positive.append('secondary_save_never_replaces_primary')
    folder,plan,r=execute('tamper-base','print("synthetic only")')
    for name,mutate in [('missing',lambda v:v.clear()),('returncode',lambda v:v.update(actual_engine_returncode=-9)),('wrapper',lambda v:v.update(wrapper_returncode=1)),('group',lambda v:v.update(engine_process_group=v['parent_process_group']+1)),('cleanup',lambda v:v.update(cleanup_errors=['failed'])),('observation',lambda v:v.update(observation_errors=['failed'])),('command',lambda v:v['command'].update(argv=['/bin/true'])),('stream',lambda v:v['native_log'].update(sha256='0'*64))]:
        bad=copy.deepcopy(r);mutate(bad);refuse(lambda:n.validate_engine_result(folder,plan,bad,0),'receipt_'+name,records)
    scope=out/'supervised-orphan';scope.mkdir();trace=scope/'trace';trace.mkdir()
    supervisor=runtime.supervisor(n.a.ROOT,scope,trace,gate,runtime.SAMPLER_SHA)
    engine_dir=scope/'owned-engine'
    plan=plan_fixture(engine_dir,'import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);print("orphan fixture")')
    plan_path=scope/'synthetic-plan.json';plan_path.write_bytes(q.encode(plan))
    wrapper=scope/'synthetic-wrapper.py';wrapper.write_text('import json,sys\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(n.a.ROOT/'scripts'))+')\nimport cdr_via2_m3_loaded_native as n\np=json.loads(Path(sys.argv[1]).read_bytes())\nr=n.execute_engine(p,Path(sys.argv[2]),2)\nraise SystemExit(r["wrapper_returncode"])\n')
    refuse(lambda:supervisor.supervised([sys.executable,'-B',str(wrapper),str(plan_path),str(engine_dir)],'orphan-fixture',seconds=3,cwd=scope),'supervised_orphan_rejected',records)
    command=q.decode((trace/'orphan-fixture.command.json').read_bytes())
    assert command['supervision_failure']=='orphan_descendant_after_leader_exit'
    assert not command['process_group_cleanup']['remaining_live'];positive.append('unchanged_supervisor_removes_orphan_group')
    assert n.execute_engine.__globals__['q']is q and n.execute_engine.__globals__['write']is n.write
    result=dict(schema='cdr-via2-m3-loaded-native-source-controls-v1',scope='REAL_PYTHON_SYNTHETIC_PROCESSES_ONLY_NO_NATIVE_ENGINE_OR_MODEL',positive=len(positive),refusals=len(records),positive_cases=positive,refusal_cases=records,real_original_ngspice_executed=False,native_model_acquired=False,loaded_simulation_executed=False)
    n.write(out/'result.json',result)
    return result

if __name__=='__main__':raise SystemExit('Invoke through exact-source hosted controls only')
