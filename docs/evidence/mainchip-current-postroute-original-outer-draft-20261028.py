#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled hosted wrapper around the exact original repaired-route analysis."""
import argparse,contextlib,importlib.util,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_repaired_postroute_admission as admission
import mainchip_repaired_postroute_bridge as bridge
import cdr_v59_tail_access_runtime as runtime
import cloud_mainchip_original_clock_restoration as shared
ROOT=admission.ROOT
OUT=ROOT/'cloud-mainchip-repaired-postroute'
INNER=ROOT/'cloud-mainchip-route12-postroute'
PROGRAM=ROOT/'cloud-mainchip-repaired-postroute-program'
METHOD=ROOT/'scripts/mainchip-repaired-postroute-cloud-methods.json'
GROUP='mainchip-repaired-postroute'
APP_SHA=admission.APP
BUDGETS={'bootstrap-exact-runtime':1200,'actual-runtime-version':1200,
         'original-repaired-postroute-chain':14400}
def save(path,value):shared.save(path,value)
def methods():
    m=admission.json_value(admission.c.regular(METHOD).read_bytes())
    assert m['bridge_methods_sha256']==admission.c.file_sha(admission.METHOD)
    admission.methods()
    for p,h in m['protected'].items():
        assert admission.c.file_sha(ROOT/p)==h,('Changed outer source',p)
    assert m['command_seconds']==BUDGETS
    for k in ('native_routing_authorized','simulation_authorized','timing_accepted','qualified_pex','full_phy_accepted'):
        assert m[k]is False
    for k in ('source_controls_authorized','cloud_restore_authorized','native_execution_authorized','rc_sta_execution_authorized'):
        assert type(m[k])is bool
    return m
def authorize():
    m=methods();base=admission.methods()
    for k in ('cloud_restore_authorized','native_execution_authorized','rc_sta_execution_authorized'):
        assert m[k]is base[k]is True,('Execution not authorized',k)
    pin=admission.require_terminal_binding(base)
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_RUN_ATTEMPT')=='1'and os.environ.get('ImageOS')=='ubuntu22'
    return m,pin
def inventory(root):
    assert root.is_dir()and not root.is_symlink()
    result={}
    for p in root.rglob('*'):
        assert not p.is_symlink()and(p.is_file()or p.is_dir()),('Nonregular evidence',str(p))
        if p.is_file():result[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=admission.c.file_sha(p))
    return result
def space(stage):
    assert stage in ('initial','command','publication')
    required=24*1024**3 if stage=='initial'else 4*1024**3
    if stage=='publication'and OUT.exists():
        required=max(required,sum(x['bytes']for x in inventory(OUT).values())+1024**3)
    free=shutil.disk_usage(ROOT).free
    assert free>=required,('Insufficient postroute storage',stage,free,required)
    return dict(stage=stage,free_bytes=free,required_bytes=required)
def command_seconds(label):
    assert type(label)is str and label in BUDGETS,('Unknown postroute command',label)
    return BUDGETS[label]
def terminal_record(sup,label):
    path=sup.TRACE/(label+'.command.json')
    record=admission.json_value(admission.c.regular(path).read_bytes())
    assert record['label']==label and record['process_group_cleanup']['remaining_live']==[]
    for key in ('stdout','stderr'):
        p=admission.c.regular(sup.TRACE/(label+'.'+key))
        assert p.stat().st_size==record[key+'_bytes']and admission.c.file_sha(p)==record[key+'_sha256']
    record['requested_timeout_seconds']=command_seconds(label)
    return record
def execute(sup,argv,label,result):
    seconds=command_seconds(label)
    result['storage'].append(space('command'))
    save(OUT/'result.json',result)
    try:
        sup.supervised(argv,label,seconds=seconds,cwd=ROOT)
    finally:
        path=sup.TRACE/(label+'.command.json')
        if path.exists():
            record=terminal_record(sup,label)
            result['phase_results'].append(record)
        else:
            result.setdefault('phase_without_terminal_record',[]).append(label)
        save(OUT/'result.json',result)
    record=result['phase_results'][-1]
    assert record['returncode']==0 and record['supervision_failure']is None
    return record
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
@contextlib.contextmanager
def loaded_program():
    methods()
    assert not PROGRAM.exists()
    geometry,postroute,proof=bridge.derive((ROOT/bridge.GEOMETRY).read_bytes(),(ROOT/bridge.POSTROUTE).read_bytes())
    PROGRAM.mkdir()
    gpath=PROGRAM/'geometry.py';ppath=PROGRAM/'postroute.py'
    gpath.write_bytes(geometry);ppath.write_bytes(postroute)
    assert admission.c.file_sha(gpath)==proof['geometry_derived_sha256']
    assert admission.c.file_sha(ppath)==bridge.POSTROUTE_SHA
    name='cloud_mainchip_route12_postroute_geometry'
    prior=sys.modules.get(name);argv=list(sys.argv)
    try:
        g=load_module(name,gpath);sys.modules[name]=g
        p=load_module('nssoc_exact_repaired_postroute',ppath)
        assert p.geometry is g and p.ROOT==g.ROOT==ROOT
        assert p.OUT==INNER
        sys.argv=[str(ppath)]
        save(PROGRAM/'derivation.json',proof)
        yield p,proof
    finally:
        sys.argv[:]=argv
        if prior is None:sys.modules.pop(name,None)
        else:sys.modules[name]=prior
def worker():
    authorize()
    assert not INNER.exists()and not PROGRAM.exists()
    record=dict(status='RUNNING_EXACT_POSTROUTE_WORKER',source_head=os.environ['GITHUB_SHA'],
        accepted=False,native_routing_started=False,final_timing_complete=False,full_phy_accepted=False)
    try:
        with bridge.original_input_context(),loaded_program()as(postroute,proof):
            record['derivation']=proof
            postroute.main()
            r=admission.json_value(admission.c.regular(INNER/'result.json').read_bytes())
            assert r['status']in ('PASS_NATIVE_POSTROUTE_NOMINAL_GATES_REQUIRES_SIGNOFF',
                'COMPLETE_NATIVE_POSTROUTE_WITH_UNCLOSED_GATES')
            assert r['sources_unchanged']is True and r['native_routing_started']is False
            assert all(r[k]is False for k in ('accepted','final_timing_complete','full_phy_accepted','qualified_pex'))
            record.update(status='COMPLETE_EXACT_ORIGINAL_POSTROUTE_CHAIN',
                original_result_sha256=admission.c.file_sha(INNER/'result.json'),
                original_status=r['status'],original_result_unmodified=True)
    except BaseException as error:
        record.update(status='FAIL_EXACT_POSTROUTE_WORKER',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        if PROGRAM.is_dir():save(PROGRAM/'worker-result.json',record)
        methods()
def collect_evidence():
    records=[];errors=[]
    for label,source in (('original-postroute',INNER),('derived-program',PROGRAM)):
        if not source.exists():continue
        destination=OUT/label
        try:
            before=inventory(source)
            assert not destination.exists(),('Occupied evidence destination',label)
            shutil.move(str(source),str(destination))
            assert inventory(destination)==before,('Collected evidence changed',label)
            records.append(dict(label=label,files=before,all_bytes_preserved=True))
        except BaseException as error:
            errors.append(dict(label=label,error=repr(error),traceback=traceback.format_exc(),
                source_remaining=source.exists(),destination_present=destination.exists()))
    return dict(collected=records,errors=errors,complete=not errors)
def run():
    m,pin=authorize()
    import ensure_cloud_tested_source_release as guard
    tag,head=guard.context(GROUP,os.environ)
    reserved=guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    initial=space('initial')
    assert not OUT.exists()and not INNER.exists()and not PROGRAM.exists()
    OUT.mkdir();(OUT/'supervision').mkdir()
    r=dict(status='RUNNING_REPAIRED_POSTROUTE',source_head=head,release_prerequisite=reserved,
        accepted=False,final_timing_complete=False,full_phy_accepted=False,qualified_pex=False,
        native_routing_started=False,automatic_retry=False,storage=[initial],phase_results=[],
        terminal_repair_binding=pin,original_input_package=admission.INPUT_PACKAGE)
    save(OUT/'result.json',r)
    sup=runtime.supervisor(ROOT,OUT,OUT/'supervision',methods,m['protected'][runtime.SAMPLER])
    previous={s:signal.signal(s,sup.interrupted)for s in (signal.SIGINT,signal.SIGTERM)}
    beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
    failure=None
    try:
        execute(sup,[sys.executable,str(ROOT/'scripts/bootstrap_flow.py')],'bootstrap-exact-runtime',r)
        app=admission.c.regular(Path(os.environ['CLOUD_APPIMAGE']).resolve())
        assert admission.c.file_sha(app)==APP_SHA
        execute(sup,[str(app),'openroad','-version'],'actual-runtime-version',r)
        execute(sup,[sys.executable,str(Path(__file__).resolve()),'--worker'],'original-repaired-postroute-chain',r)
        raw=admission.c.regular(INNER/'result.json').read_bytes();inner=admission.json_value(raw)
        worker_record=admission.json_value(admission.c.regular(PROGRAM/'worker-result.json').read_bytes())
        assert worker_record['status']=='COMPLETE_EXACT_ORIGINAL_POSTROUTE_CHAIN'
        assert worker_record['original_result_sha256']==admission.digest(raw)
        assert inner['status']==worker_record['original_status']and inner['source_head']==head
        assert inner['sources_unchanged']is True
        assert [x['label']for x in r['phase_results']]==list(BUDGETS)
        assert all(x['returncode']==0 and x['supervision_failure']is None for x in r['phase_results'])
        assert admission.c.file_sha(app)==APP_SHA
        r.update(status='COMPLETE_ORIGINAL_REPAIRED_POSTROUTE_GATES_NOT_PHY_ACCEPTANCE',
            original_result_sha256=admission.digest(raw),original_status=inner['status'],
            original_native_physical_gates_met=inner['native_physical_gates_met'],
            original_timing_and_electrical_gates_met=inner['all_reported_timing_and_electrical_gates_met'],
            original_numeric_flow_sha256=bridge.POSTROUTE_SHA,runtime_appimage_sha256=APP_SHA,
            historical_sources_unchanged_proven=False,old_scheduling_perturbation_retained=True)
    except BaseException as error:
        failure=error
        r.update(status='FAIL_OR_INTERRUPTED_REPAIRED_POSTROUTE',error=repr(error),traceback=traceback.format_exc())
    finally:
        try:
            r['outer_process_group_cleanup']=sup.stop_process(sup.ACTIVE)
        except BaseException as error:
            r.update(status='FAIL_OR_INTERRUPTED_REPAIRED_POSTROUTE',cleanup_error=repr(error))
            if failure is None:failure=error
        finally:
            sup.STOP.set();beat.join(timeout=2)
            for signum,handler in previous.items():signal.signal(signum,handler)
        r['evidence_collection']=collect_evidence()
        if not r['evidence_collection']['complete']:
            r['status']='FAIL_OR_INTERRUPTED_REPAIRED_POSTROUTE'
            if failure is None:failure=RuntimeError('Incomplete native evidence collection')
        r['outputs']={p:x['sha256']for p,x in inventory(OUT).items()if p!='result.json'}
        save(OUT/'result.json',r)
        methods()
    if failure is not None:raise failure
    return r
def publish():
    methods()
    import publish_mainchip_saved_postroute as publisher
    old=publisher.GROUP
    try:
        publisher.GROUP=GROUP
        space('publication')
        return publisher.publish_evidence(OUT,ROOT/('publication-'+GROUP))
    finally:publisher.GROUP=old
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group()
    g.add_argument('--worker',action='store_true');g.add_argument('--publish',action='store_true')
    args=p.parse_args()
    if args.worker:worker()
    elif args.publish:print(json.dumps(publish(),indent=2),flush=True)
    else:run()
if __name__=='__main__':main()
