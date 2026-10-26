#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One conditional two-signal attempt; original failed input and all streams retained."""
import argparse,contextlib,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_two_signal_repair as s
import cloud_mainchip_original_clock_restoration as base
import cloud_mainchip_fixed_clock_signal_repair as qualified
import mainchip_signal_repair_readback as capture
ROOT=c.ROOT
OUT=ROOT/'cloud-mainchip-two-signal-repair'
TRANSPORT=ROOT/'transport-mainchip-two-signal-repair'
GROUP='mainchip-two-signal-repair'
APP_SHA=base.APP_SHA
SHORT_PHASES=frozenset(('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version',
    'ownership','prepare-fixed','paired-all-nontarget-fixed-import','fixed-audit','route-audit',
    'paired-original-class-return','unfix-audit','full-original-class-read-only-DRT','drc-audit'))
save=base.save

def command_seconds(label):
    assert type(label)is str
    if label=='one-two-signal-routing-attempt':return 14400
    assert label in SHORT_PHASES,('Unknown command label',label)
    return 1200

def execute_command(sup,argv,label):
    seconds=command_seconds(label)
    sup.supervised(argv,label,seconds=seconds,cwd=ROOT)
    record=json.loads(c.regular(sup.TRACE/(label+'.command.json')).read_bytes())
    base.terminal_stream(record,sup.TRACE,label)
    record['requested_timeout_seconds']=seconds
    return record

def space(stage):
    needed=24*1024**3 if stage=='initial'else 4*1024**3
    if stage=='publish'and OUT.exists():
        total=0
        for p in OUT.rglob('*'):
            assert not p.is_symlink()and (p.is_file()or p.is_dir())
            if p.is_file():total+=p.stat().st_size
        needed=max(needed,total+1024**3)
    free=shutil.disk_usage(ROOT).free
    assert free>=needed,('Insufficient storage',stage,free,needed)
    return dict(stage=stage,free_bytes=free,required_bytes=needed)

@contextlib.contextmanager
def qualified_paths():
    oldout,oldtransport=qualified.OUT,qualified.TRANSPORT
    try:
        qualified.OUT=OUT;qualified.TRANSPORT=TRANSPORT/'qualified'
        yield
    finally:qualified.OUT,qualified.TRANSPORT=oldout,oldtransport

def restored_inputs():
    with qualified_paths():inherited=qualified.restored_inputs()
    proof=json.loads(c.regular(OUT/'failed-input-admission.json').read_bytes())
    report=capture.expected_report(c.regular(ROOT/(capture.PREFIX+'.summary.json')).read_bytes())
    path=TRANSPORT/'failed/selected'/s.INPUT
    source=s.source_input(path,report,proof)
    for name in [*capture.SELECTED,s.INPUT]:
        assert c.file_sha(TRANSPORT/'failed/selected'/name)==report['outputs'][name]
    return dict(qualified=inherited,failed_input=proof,selected_failed_input=source,
                original_guard_failure_preserved=True)

def restore_worker():
    assert s.methods()['cloud_restore_authorized']is True
    s.readback()
    assert not TRANSPORT.exists();TRANSPORT.mkdir()
    with qualified_paths():qualified.restore_worker()
    previous=capture.SELECTED
    try:
        capture.SELECTED=tuple(dict.fromkeys([*previous,s.INPUT]))
        report,proof=capture.restore(TRANSPORT/'failed')
    finally:capture.SELECTED=previous
    s.source_input(TRANSPORT/'failed/selected'/s.INPUT,report,proof)
    interpretation=capture.inspect_saved(TRANSPORT/'failed/selected',report)
    assert interpretation==s.readback(),'Exact saved readback interpretation changed'
    save(OUT/'failed-input-admission.json',proof)
    save(OUT/'prior-failed-saved-readback.json',interpretation)
    # Preserve original failure diagnostics independently of new native outcome.
    for name in previous:
        if name.endswith('.def'):continue
        target=OUT/'prior-failed'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(TRANSPORT/'failed/selected'/name,target)
        assert c.file_sha(target)==report['outputs'][name]
    restored_inputs();s.methods()

@contextlib.contextmanager
def environment():
    values=dict(NSSOC_SIGNAL_CLOCK_SOURCE=str(TRANSPORT/'qualified/clock/selected'),
        NSSOC_SIGNAL_GLOBAL_SOURCE=str(TRANSPORT/'qualified/global'),
        NSSOC_TWO_SIGNAL_FAILED_SOURCE=str(TRANSPORT/'failed/selected'),
        NSSOC_TWO_SIGNAL_OUT=str(OUT/'work'),PYTHONPATH=str(ROOT/'scripts'))
    keys=set(values)|{'GH_TOKEN','GITHUB_TOKEN'};old={k:os.environ.get(k)for k in keys}
    try:
        os.environ.update(values)
        for k in ('GH_TOKEN','GITHUB_TOKEN'):os.environ.pop(k,None)
        yield
    finally:
        for k,v in old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def run():
    m=s.methods()
    for key in ('cloud_restore_authorized','native_execution_authorized','native_routing_authorized'):
        assert m[key]is True
    import ensure_cloud_tested_source_release as guard
    tag,head=guard.context(GROUP,os.environ)
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    initial=space('initial')
    assert not OUT.exists()and not TRANSPORT.exists()
    OUT.mkdir();(OUT/'work').mkdir();(OUT/'supervision').mkdir()
    result=dict(status='RUNNING_OWNERSHIP_BEFORE_CONDITIONAL_TWO_SIGNAL_REPAIR',source_head=head,
        accepted=False,final_timing_complete=False,full_phy_accepted=False,phase_results=[],storage=[initial],
        native_routing_started=False,automatic_retry=False,prior_DRT_markers=3,
        original_run=40344497930,original_run_conclusion='failure',original_guard_failure_preserved=True,
        only_allowed_signals=list(s.TARGETS))
    save(OUT/'result.json',result)
    sup=base.supervisor();oldout,oldtrace=sup.OUT,sup.TRACE;sup.OUT=OUT;sup.TRACE=OUT/'supervision'
    previous={sig:signal.signal(sig,sup.interrupted)for sig in (signal.SIGINT,signal.SIGTERM)}
    beat=threading.Thread(target=sup.heartbeat,daemon=True);beat.start()
    def command(argv,label):
        result['storage'].append(space('phase'));save(OUT/'result.json',result)
        record=execute_command(sup,argv,label)
        result['phase_results'].append(record);save(OUT/'result.json',result)
        return record
    def phase(name):
        old=os.environ.get('NSSOC_TWO_SIGNAL_PHASE');os.environ['NSSOC_TWO_SIGNAL_PHASE']=name
        try:command([str(app),'openroad','-exit','-python',str(ROOT/'scripts/mainchip_two_signal_repair_native.py')],name)
        finally:
            if old is None:os.environ.pop('NSSOC_TWO_SIGNAL_PHASE',None)
            else:os.environ['NSSOC_TWO_SIGNAL_PHASE']=old
    failure=None
    try:
        command([sys.executable,str(ROOT/'scripts/bootstrap_flow.py')],'bootstrap-exact-runtime')
        app=c.regular(Path(os.environ['CLOUD_APPIMAGE']).resolve());assert c.file_sha(app)==APP_SHA
        command([sys.executable,str(Path(__file__).resolve()),'--restore-worker'],'restore-complete-saved-inputs')
        result['source_admission']=restored_inputs();save(OUT/'result.json',result)
        with environment():
            command([str(app),'openroad','-version'],'actual-runtime-version')
            phase('ownership')
            ownership=json.loads(c.regular(OUT/'work/ownership.json').read_bytes())
            result['ownership']=ownership;save(OUT/'result.json',result)
            s.require_actionable(ownership) # No mutation or router launch before actual native evidence.
            phase('prepare-fixed')
            command([str(app),'openroad','-exit',str(OUT/'work/fixed.tcl')],'paired-all-nontarget-fixed-import')
            phase('fixed-audit')
            result['native_routing_started']=True;save(OUT/'result.json',result)
            command([str(app),'openroad','-exit',str(OUT/'work/repair.tcl')],'one-two-signal-routing-attempt')
            result['route_log']=qualified.s.route_log(c.regular(sup.TRACE/'one-two-signal-routing-attempt.stdout').read_bytes())
            phase('route-audit')
            command([str(app),'openroad','-exit',str(OUT/'work/unfix.tcl')],'paired-original-class-return')
            phase('unfix-audit')
            command([str(app),'openroad','-exit',str(OUT/'work/final-drc.tcl')],'full-original-class-read-only-DRT')
            phase('drc-audit')
        result['native_result']=json.loads(c.regular(OUT/'work/drc-audit-result.json').read_bytes())
        result['next_stage']=s.require_complete(result['native_result'])
        restored_inputs();assert c.file_sha(app)==APP_SHA;s.methods()
        result.update(status='COMPLETE_CONDITIONAL_TWO_SIGNAL_ATTEMPT_NOT_RC_STA_OR_PHY_ACCEPTANCE',
            original_inputs_unchanged=True,runtime_appimage_sha256=APP_SHA,
            published_package_source_is_not_rebuilt_ELF_attestation=True)
    except BaseException as exc:
        failure=exc
        result.update(status='FAIL_OR_BLOCKED_TWO_SIGNAL_ATTEMPT',error=repr(exc),traceback=traceback.format_exc())
    finally:
        # Terminal guards cannot leave a saved COMPLETE verdict after their failure.
        # Preserve an earlier phase exception while independently recording cleanup/source failures.
        terminal_errors=[]
        result['terminal_checks']=[]
        def terminal_check(label,fn):
            try:fn()
            except BaseException as exc:
                trace=traceback.format_exc();terminal_errors.append((exc,trace))
                result['terminal_checks'].append(dict(label=label,status='FAIL',error=repr(exc),traceback=trace))
            else:result['terminal_checks'].append(dict(label=label,status='PASS'))
        terminal_check('owned-process-cleanup',lambda:sup.stop_process(sup.ACTIVE))
        def stop_heartbeat():
            sup.STOP.set();beat.join(timeout=2)
        terminal_check('heartbeat-stop',stop_heartbeat)
        for sig,handler in previous.items():
            terminal_check('restore-signal-'+str(sig),lambda sig=sig,handler=handler:signal.signal(sig,handler))
        sup.OUT,sup.TRACE=oldout,oldtrace
        terminal_check('final-source-integrity',s.methods)
        if terminal_errors:
            result['status']='FAIL_OR_BLOCKED_TWO_SIGNAL_ATTEMPT'
            if failure is None:
                failure,trace=terminal_errors[0]
                result.update(error=repr(failure),traceback=trace)
        result['outputs']={str(p.relative_to(OUT)):c.file_sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save(OUT/'result.json',result)
    if failure is not None:raise failure

def publish():
    s.methods()
    import publish_mainchip_saved_postroute as publisher
    previous=publisher.GROUP
    try:
        publisher.GROUP=GROUP;space('publish')
        return publisher.publish_evidence(OUT,ROOT/('publication-'+GROUP))
    finally:publisher.GROUP=previous

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--restore-worker',action='store_true');group.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    if args.restore_worker:restore_worker()
    elif args.publish:print(json.dumps(publish(),indent=2),flush=True)
    else:run()
if __name__=='__main__':main()
