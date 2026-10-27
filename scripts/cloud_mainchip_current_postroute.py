#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Disabled current original-class postroute worker; no routing or broad acceptance."""
import argparse,contextlib,importlib.util,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_current_postroute_admission as admission
import mainchip_current_postroute_bridge as bridge
import mainchip_current_postroute_terminal as terminal
import cdr_v59_tail_access_runtime as runtime
ROOT=admission.ROOT
OUT=ROOT/'cloud-mainchip-current-postroute'
INNER=ROOT/'cloud-mainchip-route12-postroute'
PROGRAM=ROOT/'cloud-mainchip-current-postroute-program'
METHOD=admission.METHOD
GROUP='mainchip-current-postroute'
APP_SHA=admission.APP
BUDGETS={'bootstrap-exact-runtime':1200,'actual-runtime-version':1200,
         'original-current-postroute-chain':14400}
save=terminal.write
def methods():
    m=admission.methods()
    assert m['command_seconds']==BUDGETS
    return m
def authorize():
    m=methods()
    assert all(m[k]is True for k in admission.EXECUTION_FLAGS)
    pin=admission.require_terminal_binding(m)
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
@contextlib.contextmanager
def tokenless_native_environment():
    previous={key:os.environ.get(key)for key in ('GH_TOKEN','GITHUB_TOKEN')}
    try:
        for key in previous:os.environ.pop(key,None)
        yield
    finally:
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
def execute(sup,argv,label,result):
    seconds=command_seconds(label)
    result['storage'].append(space('command'))
    save(OUT/'result.json',result)
    primary=None;secondary=[];record=None
    try:sup.supervised(argv,label,seconds=seconds,cwd=ROOT)
    except BaseException as error:primary=error
    try:
        record=terminal_record(sup,label)
        result['phase_results'].append(record)
        assert record['returncode']==0 and record['supervision_failure']is None
    except BaseException as error:
        secondary.append(error)
        result.setdefault('command_terminal_failures',[]).append(dict(label=label,**terminal.error_record(error)))
    if primary is not None or secondary:
        result['status']='FAIL_CURRENT_POSTROUTE_COMMAND'
    try:save(OUT/'result.json',result)
    except BaseException as error:
        secondary.append(error)
        result.setdefault('command_terminal_failures',[]).append(dict(label=label,action='save_result',**terminal.error_record(error)))
    if primary is not None:raise primary
    if secondary:raise secondary[0]
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
    assert admission.c.file_sha(ppath)==proof['postroute_derived_sha256']
    name='cloud_mainchip_route12_postroute_geometry'
    prior=sys.modules.get(name);argv=list(sys.argv)
    previous_bytecode=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:
        g=load_module(name,gpath);sys.modules[name]=g
        p=load_module('nssoc_exact_current_postroute',ppath)
        assert p.geometry is g and p.ROOT==g.ROOT==ROOT
        assert p.OUT==INNER
        sys.argv=[str(ppath)];save(PROGRAM/'derivation.json',proof)
        yield p,proof
    finally:
        sys.argv[:]=argv;sys.dont_write_bytecode=previous_bytecode
        if prior is None:sys.modules.pop(name,None)
        else:sys.modules[name]=prior
def worker():
    authorize()
    assert not INNER.exists()and not PROGRAM.exists()
    record=dict(status='RUNNING_CURRENT_POSTROUTE_WORKER',source_head=os.environ['GITHUB_SHA'],
        accepted=False,native_routing_started=False,final_timing_complete=False,full_phy_accepted=False)
    primary=None
    try:
        with bridge.original_input_context(),loaded_program()as(postroute,proof):
            record['derivation']=proof
            postroute.main()
            r=admission.json_value(admission.c.regular(INNER/'result.json').read_bytes())
            assert r['status']in ('PASS_NATIVE_POSTROUTE_NOMINAL_GATES_REQUIRES_SIGNOFF',
                'COMPLETE_NATIVE_POSTROUTE_WITH_UNCLOSED_GATES')
            assert r['sources_unchanged']is True and r['native_routing_started']is False
            assert r['terminal_finalization_complete']is True and r['terminal_inventory_complete']is True
            assert all(r[k]is False for k in ('accepted','final_timing_complete','full_phy_accepted','qualified_pex'))
            record.update(status='COMPLETE_CURRENT_ORIGINAL_POSTROUTE_CHAIN',
                original_result_sha256=admission.c.file_sha(INNER/'result.json'),original_status=r['status'],
                numerical_predicates_unchanged=True,terminal_orchestration_explicitly_derived=True)
    except BaseException as error:
        primary=error
        record.update(status='FAIL_CURRENT_POSTROUTE_WORKER',**terminal.error_record(error))
    finally:
        failure=terminal.finalize(PROGRAM,record,lambda:save(PROGRAM/'worker-result.json',record),
            [('evidence_directory',lambda:PROGRAM.mkdir(exist_ok=True)),('protected_sources',methods)],
            primary,result_name='worker-result.json')
    if failure is not None:raise failure
    return record
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
    r=dict(status='RUNNING_CURRENT_POSTROUTE',source_head=head,run_id=int(os.environ['GITHUB_RUN_ID']),
        run_attempt=1,group=GROUP,method_sha256=admission.c.file_sha(METHOD),release_prerequisite=reserved,
        accepted=False,final_timing_complete=False,full_phy_accepted=False,qualified_pex=False,
        qualified_RC_minmax=False,native_routing_started=False,automatic_retry=False,
        storage=[initial],phase_results=[],terminal_repair_binding=pin,original_input_package=admission.INPUT_PACKAGE)
    sup=None;beat=None;previous={};primary=None
    try:
        save(OUT/'result.json',r)
        sup=runtime.supervisor(ROOT,OUT,OUT/'supervision',methods,m['protected'][runtime.SAMPLER])
        for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,sup.interrupted)
        beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
        execute(sup,[sys.executable,str(ROOT/'scripts/bootstrap_flow.py')],'bootstrap-exact-runtime',r)
        app=admission.c.regular(Path(os.environ['CLOUD_APPIMAGE']).resolve())
        assert admission.c.file_sha(app)==APP_SHA
        with tokenless_native_environment():
            execute(sup,[str(app),'openroad','-version'],'actual-runtime-version',r)
        execute(sup,[sys.executable,str(Path(__file__).resolve()),'--worker'],'original-current-postroute-chain',r)
        raw=admission.c.regular(INNER/'result.json').read_bytes();inner=admission.json_value(raw)
        worker_record=admission.json_value(admission.c.regular(PROGRAM/'worker-result.json').read_bytes())
        assert worker_record['status']=='COMPLETE_CURRENT_ORIGINAL_POSTROUTE_CHAIN'
        assert worker_record['original_result_sha256']==admission.digest(raw)
        assert worker_record['terminal_finalization_complete']is True
        assert inner['status']==worker_record['original_status']and inner['source_head']==head
        assert inner['sources_unchanged']is True and inner['terminal_finalization_complete']is True
        assert [x['label']for x in r['phase_results']]==list(BUDGETS)
        assert all(x['returncode']==0 and x['supervision_failure']is None for x in r['phase_results'])
        assert admission.c.file_sha(app)==APP_SHA
        r.update(status='COMPLETE_CURRENT_ORIGINAL_POSTROUTE_GATES_NOT_PHY_ACCEPTANCE',
            original_result_sha256=admission.digest(raw),original_status=inner['status'],
            original_native_physical_gates_met=inner['native_physical_gates_met'],
            original_timing_and_electrical_gates_met=inner['all_reported_timing_and_electrical_gates_met'],
            original_numeric_flow_sha256=bridge.POSTROUTE_SHA,runtime_appimage_sha256=APP_SHA,
            historical_sources_unchanged_proven=False,old_scheduling_perturbation_retained=True)
    except BaseException as error:
        primary=error;r.update(status='FAIL_OR_INTERRUPTED_CURRENT_POSTROUTE',**terminal.error_record(error))
    finally:
        actions=[]
        if sup is not None:
            def cleanup():r['outer_process_group_cleanup']=sup.stop_process(sup.ACTIVE)
            actions += [('owned_process_cleanup',cleanup),('heartbeat_stop',sup.STOP.set)]
        if beat is not None:actions.append(('heartbeat_join',lambda:beat.join(timeout=2)))
        for sig,handler in previous.items():
            def restore(sig=sig,handler=handler):signal.signal(sig,handler)
            actions.append(('restore_signal_'+str(sig),restore))
        actions.append(('protected_sources',methods))
        def collect():
            r['evidence_collection']=collect_evidence()
            assert r['evidence_collection']['complete'],'Incomplete native evidence collection'
        actions.append(('collect_complete_original_evidence',collect))
        failure=terminal.finalize(OUT,r,lambda:save(OUT/'result.json',r),actions,primary)
    if failure is not None:raise failure
    return r
def publication_gate():
    # Publication after a recorded analysis-source failure uses only the immutable
    # startup method and pinned publication implementation. It never qualifies success.
    m=admission.json_value(admission.c.regular(METHOD).read_bytes())
    admission.validate_authorizations(m)
    assert m['source_controls_authorized']is True and m['native_execution_authorized']is True
    r=admission.json_value(admission.c.regular(OUT/'result.json').read_bytes())
    assert r['method_sha256']==admission.c.file_sha(METHOD)
    assert (r['group'],r['source_head'],r['run_id'],r['run_attempt'])==(
        GROUP,os.environ['GITHUB_SHA'],int(os.environ['GITHUB_RUN_ID']),1)
    for key in ('accepted','final_timing_complete','full_phy_accepted','qualified_pex',
                'qualified_RC_minmax','native_routing_started','automatic_retry'):assert r[key]is False
    if r['status'].startswith('COMPLETE_'):methods()
    assert m['publication_dependencies']
    for path in m['publication_dependencies']:
        assert admission.c.file_sha(ROOT/path)==m['protected'][path],('Changed publication source',path)
    assert r['outputs']==terminal.inventory(OUT),'Publication requires exact current output inventory'
    return m,r
DIRECT={'original-postroute/result.json':'native-result.json',
    'original-postroute/geometry/result.json':'geometry.json',
    'derived-program/worker-result.json':'worker-result.json',
    'derived-program/derivation.json':'derivation.json'}
def publication_files(root,transport,stem,manifest,summary,result):
    from cloud_chunked_results import verify_parts
    assert manifest['stem']==stem and manifest['source_directory']==root.name
    verify_parts(manifest,transport)
    assert summary.read_bytes()==(root/'result.json').read_bytes()
    part_path=transport/(stem+'.parts.json')
    assert admission.json_value(part_path.read_bytes())==manifest
    paths=[summary,part_path,*[transport/p['name']for p in manifest['parts']]]
    assert all(p.stat().st_size>0 for p in paths)
    if result['status'].startswith('COMPLETE_'):assert set(DIRECT)<=set(result['outputs'])
    for relative,label in DIRECT.items():
        path=root/relative
        if relative not in result['outputs']:
            assert not path.exists()and not path.is_symlink(),'Unrecorded direct result'
            continue
        assert admission.c.file_sha(path)==result['outputs'][relative]
        if result['status'].startswith('COMPLETE_'):admission.json_value(path.read_bytes())
        target=transport/(stem+'.'+label);assert not target.exists()
        shutil.copyfile(path,target)
        assert target.read_bytes()==path.read_bytes()
        paths.append(target)
    assert len({p.name for p in paths})==len(paths)
    assert all(p.is_file()and not p.is_symlink()and p.parent==transport for p in paths)
    return paths
def publish():
    _,r=publication_gate()
    from mainchip_saved_postroute_publisher_base import publish_files
    from cloud_chunked_results import pack
    import ensure_cloud_tested_source_release as guard
    tag,source=guard.context(GROUP,os.environ)
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,source)
    space('publication')
    transport=ROOT/('publication-'+GROUP);transport.mkdir(exist_ok=False)
    stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-1'
    summary=transport/(stem+'.summary.json');summary.write_bytes((OUT/'result.json').read_bytes())
    manifest=pack(OUT,stem,transport)
    paths=publication_files(OUT,transport,stem,manifest,summary,r)
    proof=publish_files(GROUP,paths)
    assert r['outputs']==terminal.inventory(OUT)
    assert summary.read_bytes()==(OUT/'result.json').read_bytes()
    report=dict(status='PUBLISHED_EXACT_CURRENT_POSTROUTE_EVIDENCE_NOT_ACCEPTANCE',
        original_status=r['status'],source_head=source,publication=proof,
        raw_failed_direct_JSON_kept_uninterpreted=not r['status'].startswith('COMPLETE_'),
        files=[dict(name=p.name,bytes=p.stat().st_size,sha256=admission.c.file_sha(p))for p in paths])
    save(transport/'publication.json',report)
    return report
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group()
    g.add_argument('--worker',action='store_true');g.add_argument('--publish',action='store_true')
    args=p.parse_args()
    if args.worker:worker()
    elif args.publish:print(json.dumps(publish(),indent=2),flush=True)
    else:run()
if __name__=='__main__':main()
