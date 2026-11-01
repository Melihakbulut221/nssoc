#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-current loaded entry; all engine bytes and native streams stay on runner."""
import argparse,json,os,signal,subprocess,time,traceback
from pathlib import Path
import cdr_via2_m3_loaded_admission as a
import cdr_via2_m3_loaded_core as core
q=a.q;require=a.require
CASE='case-nominal_late'

def write(path,value):q.write_new(path,q.encode(value))

def authorize(out):
    ctx=a.context(os.environ);c,p=a.source_guard(ctx);a.authorize_native(ctx,c)
    require(out.is_absolute()and out.resolve()==out==a.OUT,'exact owned loaded output')
    a.native_preflight(out/'preflight.json',ctx,c,p)
    return ctx,c,p

def current_paths(p):
    return {key:str(a.ORIGINAL/p[key]['path'])for key in('model','composition','planes')}

def preparation(out,ctx,c,p):
    runtime=q.decode(q.regular(out/'runtime','result.json').read_bytes())
    require(runtime['status']=='PASS_FROZEN_ORIGINAL_LOADED_RUNTIME_BYTES_NO_TRANSIENT'and runtime['context']==ctx,'complete source-bound runtime acquisition')
    value=core.prepare_case(out/CASE,current_paths(p),runtime['runtime_paths'],{k:ctx[k]for k in('source','run_id','attempt')})
    require(value['status']==core.PREPARED_STATUS and value['report']['transient_executed']is False,'complete frozen preparation only')
    write(out/'prepared-result.json',value)
    return value

def prepared_contract(out,ctx,plan_pin,prepared_pin):
    case=out/CASE;plan_path=q.regular(case,'transient-command.json');state_path=q.regular(case,'prepared-state.json')
    require(q.file_pin(plan_path)==plan_pin and q.file_pin(state_path)==prepared_pin,'host-retained complete plan and prepared bytes')
    plan=q.decode(plan_path.read_bytes());state=q.decode(state_path.read_bytes());key={k:ctx[k]for k in('source','run_id','attempt')}
    require(state['context']==key and state['case']=='nominal_late'and state['report']['status']==core.PREPARED_STATUS,'same actual prepared case')
    proof=core.verify_runtime(state['runtime'])
    expected=dict(argv=[state['runtime']['engine'],'-n','-b','bench.cir'],cwd=str(case/'native'),remove_environment_keys=['LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN'],environment=dict(SPICE_SCRIPTS=str(case/'native'),OMP_NUM_THREADS='1'),stdout=str(case/'native'/'native.log'),stderr='STDOUT',engine=proof['engine'],prepared_state=prepared_pin,case='nominal_late',context=key)
    require(plan==expected,'entire exact original transient plan')
    require(all(core.sha(Path(name))==digest for name,digest in state['report']['protected_inputs'].items()),'complete prepared inputs unchanged')
    return plan,state

def execute_engine(plan,out,seconds,limit=16*1024*1024):
    """Preserve merged stream order; the parent supervisor owns this process group."""
    require(type(seconds)in(int,float)and 0<seconds<=1200 and limit==16*1024*1024,'original engine timeout/output limits')
    native_log=Path(plan['stdout']);require(not native_log.exists()and not native_log.is_symlink(),'exclusive original merged native.log')
    require(native_log.parent.resolve()==Path(plan['cwd']).resolve()and native_log.parent==Path(plan['cwd']),'exact native cwd/log ownership')
    require(q.file_pin(Path(plan['argv'][0]))==plan['engine'],'actual engine bytes')
    env={k:v for k,v in os.environ.items()if k not in plan['remove_environment_keys']};env.update(plan['environment'])
    require(not any(k in env for k in('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')),'tokenless exact engine environment')
    command=dict(argv=plan['argv'],cwd=plan['cwd'],environment=plan['environment'],removed_environment_keys=plan['remove_environment_keys'],stdout=plan['stdout'],stderr='STDOUT',engine=plan['engine'],seconds=seconds,output_limit_bytes=limit)
    write(out/'engine-command.json',command)
    child=None;primary=None;began=time.monotonic();cleanup=[]
    result=dict(status='RUNNING_ACTUAL_ENGINE',actual_engine_started=False,actual_engine_returncode=None,wrapper_returncode=None,command=command,parent_pid=os.getpid(),parent_process_group=os.getpgrp(),native_acceptance=False)
    try:
        with native_log.open('xb')as stream:
            child=subprocess.Popen(plan['argv'],cwd=plan['cwd'],env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=False)
            result.update(actual_engine_started=True,engine_pid=child.pid,engine_process_group=os.getpgid(child.pid))
            require(result['engine_process_group']==os.getpgrp(),'engine remains in externally supervised owned process group')
            write(out/'engine-started.json',dict(result))
            while child.poll()is None:
                require(time.monotonic()-began<seconds,'engine elapsed limit')
                require(native_log.stat().st_size<=limit,'merged engine log limit')
                time.sleep(.1)
            stream.flush();os.fsync(stream.fileno())
        require(native_log.stat().st_size<=limit,'merged engine log limit')
        result.update(status='COMPLETE_ENGINE_PROCESS_NOT_ELECTRICAL_ACCEPTANCE',actual_engine_returncode=child.returncode,wrapper_returncode=0 if child.returncode==0 else 1,elapsed_seconds=time.monotonic()-began,native_log=q.file_pin(native_log))
        return result
    except BaseException as error:
        primary=error;result.update(status='FAIL_OR_ERROR_ENGINE',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        if child is not None and child.poll()is None:
            try:child.terminate();child.wait(timeout=5)
            except BaseException as error:
                cleanup.append(repr(error))
                try:child.kill();child.wait(timeout=5)
                except BaseException as secondary:cleanup.append(repr(secondary))
        observations=[]
        try:
            if child is not None:result['observed_engine_returncode_at_cleanup']=child.returncode
        except BaseException as error:observations.append(error)
        try:
            if native_log.is_file()and not native_log.is_symlink():result['retained_native_log']=q.file_pin(native_log)
        except BaseException as error:observations.append(error)
        result['observation_errors']=[repr(error)for error in observations]
        result['cleanup_errors']=cleanup
        if observations and primary is None:result['status']='FAIL_ENGINE_DIAGNOSTICS'
        try:write(out/'engine-result.json',result)
        except BaseException as error:
            try:print(json.dumps(dict(unsaved_engine_result=result,secondary_save_error=repr(error)),sort_keys=True),flush=True)
            except BaseException:pass
            if primary is None:raise
        if primary is None and observations:raise observations[0]
        if cleanup and primary is None:raise RuntimeError('engine cleanup failed '+repr(cleanup))

def validate_engine_result(out,plan,record,wrapper_returncode=None):
    require(record['status']=='COMPLETE_ENGINE_PROCESS_NOT_ELECTRICAL_ACCEPTANCE'and record['actual_engine_started']is True,'actual completed engine receipt required')
    rc=record['actual_engine_returncode'];require(type(rc)is int,'authentic engine return code including negative signals')
    require(record['observed_engine_returncode_at_cleanup']==rc and record['wrapper_returncode']==(0 if rc==0 else 1),'engine and explicit wrapper exit semantics')
    if wrapper_returncode is not None:require(wrapper_returncode==record['wrapper_returncode'],'supervised wrapper result matches actual engine receipt')
    require(record['engine_process_group']==record['parent_process_group']and not record['cleanup_errors']and not record['observation_errors'],'same clean externally supervised process group')
    require(record['command']['argv']==plan['argv']and record['command']['cwd']==plan['cwd']and record['command']['engine']==plan['engine'],'exact measured engine command')
    require(record['command']['environment']==plan['environment']and record['command']['removed_environment_keys']==plan['remove_environment_keys']and record['command']['stderr']=='STDOUT'and record['command']['stdout']==plan['stdout'],'exact actual engine environment and merged stream')
    require(q.file_pin(Path(plan['stdout']))==record['native_log']==record['retained_native_log'],'complete original merged native log')
    return rc

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('prepare','transient','measure'),required=True);parser.add_argument('--out',type=Path,required=True)
    for name in('plan','prepared','engine'):
        parser.add_argument('--'+name+'-bytes',type=int);parser.add_argument('--'+name+'-sha256')
    args=parser.parse_args();out=args.out;ctx,c,p=authorize(out)
    if args.phase=='prepare':preparation(out,ctx,c,p);return
    pins={name:dict(bytes=getattr(args,name+'_bytes'),sha256=getattr(args,name+'_sha256'))for name in('plan','prepared')}
    require(all(type(v['bytes'])is int and v['bytes']>0 and isinstance(v['sha256'],str)and len(v['sha256'])==64 for v in pins.values()),'explicit host-retained preparation pins')
    plan,state=prepared_contract(out,ctx,pins['plan'],pins['prepared'])
    if args.phase=='transient':
        record=execute_engine(plan,out,c['resources']['engine_seconds']);raise SystemExit(record['wrapper_returncode'])
    engine_pin=dict(bytes=args.engine_bytes,sha256=args.engine_sha256);path=q.regular(out,'engine-result.json')
    require(q.file_pin(path)==engine_pin,'host-retained actual engine receipt')
    rc=validate_engine_result(out,plan,q.decode(path.read_bytes()))
    report=core.measure_case(out/CASE,{k:ctx[k]for k in('source','run_id','attempt')},rc,pins['prepared'])
    require(report['status']=='PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF'and report['sources_unchanged']is True,'full unchanged loaded measurement')
    write(out/'measured-result.json',report)

if __name__=='__main__':main()
