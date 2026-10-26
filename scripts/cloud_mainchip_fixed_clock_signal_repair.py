#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One cloud-only, supervised signal-routing attempt with exact fixed-clock barriers."""
import argparse,contextlib,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as s
import cloud_mainchip_original_clock_restoration as base
import mainchip_clock_marker_capture as capture
ROOT=c.ROOT
OUT=ROOT/'cloud-mainchip-fixed-clock-signal-repair'
TRANSPORT=ROOT/'transport-mainchip-fixed-clock-signal-repair'
GROUP='mainchip-fixed-clock-signal-repair'
APP_SHA=base.APP_SHA

def save(path,value):base.save(path,value)

SHORT_PHASES=frozenset(('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version',
    'prepare','load-exact-saved-guides','guide-audit','route-audit','paired-original-class-return',
    'unfix-audit','full-original-class-read-only-DRT','drc-audit'))

def command_seconds(label):
    assert type(label)is str,'Command label must be an exact string'
    if label=='one-signal-routing-attempt':return 14400
    assert label in SHORT_PHASES,('Unknown command label',label)
    return 1200

def execute_command(sup,argv,label):
    seconds=command_seconds(label) # Reject unknown labels before any process launch.
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

def restored_inputs():
    r=json.loads(c.regular(OUT/'source-admission.json').read_bytes())
    assert r['complete_clock_archive_verified']is True
    assert set(r['clock_inputs'])==set(s.CLOCK_INPUTS)
    assert set(r['global_inputs'])==set(s.GLOBAL_INPUTS)
    for name,h in r['clock_inputs'].items():
        assert h==s.CLOCK_INPUTS[name]and c.file_sha(TRANSPORT/'clock/selected'/name)==h
    for name,h in r['global_inputs'].items():
        assert h==s.GLOBAL_INPUTS[name]and c.file_sha(TRANSPORT/'global'/name)==h
    return r

def restore_worker():
    m=s.methods();assert m['cloud_restore_authorized']is True
    classification=s.classification_admission()
    assert not TRANSPORT.exists();TRANSPORT.mkdir()
    old=capture.SELECTED
    # Only the extraction projection expands; every original107 member is still hashed.
    try:
        capture.SELECTED=tuple(dict.fromkeys([*old,*s.CLOCK_INPUTS]))
        report,clock_proof=capture.restore(TRANSPORT/'clock')
    finally:capture.SELECTED=old
    assert set(s.CLOCK_INPUTS)<=set(report['outputs'])
    for name,h in s.CLOCK_INPUTS.items():assert report['outputs'][name]==h
    assert len(clock_proof['inventory']['all_original_files'])==107
    assert clock_proof['inventory']['total_unpacked_bytes']==5856459026
    assert clock_proof['inventory']['complete_original_inventory_verified_before_analysis']is True
    import compare_cloud_routed_endpoints as reports
    import ensure_cloud_tested_source_release as guard
    assert c.file_sha(ROOT/s.GLOBAL_PROOF)==s.GLOBAL_PROOF_SHA
    pin=json.loads(c.regular(ROOT/s.GLOBAL_PROOF).read_bytes())
    assert (pin['run'],pin['source_head'],pin['group'])==(39910632183,'639b5b8aee64347620420c1f7f60001255a754b5','mainchip-route12-global')
    live=guard.api('actions/runs/'+str(pin['run']))
    assert live['run_attempt']==1 and live['head_sha']==pin['source_head']
    assert live['status']=='completed'and live['conclusion']=='success'
    assert live['path']=='.github/workflows/mainchip-route12-global-cloud.yml'
    oldout=reports.OUT
    try:
        reports.OUT=OUT
        original,global_proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],
            pin['parts_sha256'],TRANSPORT/'global',list(s.GLOBAL_INPUTS))
    finally:reports.OUT=oldout
    assert original==pin['report']and original['sources_unchanged']is True
    assert original['global_guides_sha256']==s.GLOBAL_INPUTS[s.GLOBAL_PREFIX+'fresh-fanout.guide']
    assert global_proof['restore']['full_archive_verified_before_extraction']is True
    for name,h in s.GLOBAL_INPUTS.items():assert original['outputs'][name]==h
    save(OUT/'source-admission.json',dict(clock_proof=clock_proof,global_proof=global_proof,
        clock_inputs=s.CLOCK_INPUTS,global_inputs=s.GLOBAL_INPUTS,complete_clock_archive_verified=True,
        prior_DRT_markers=762,prior_all_clock_signal=True,classification_is_not_feasibility=True,
        classification=classification))
    restored_inputs();s.methods()

@contextlib.contextmanager
def environment():
    values=dict(NSSOC_SIGNAL_CLOCK_SOURCE=str(TRANSPORT/'clock/selected'),
        NSSOC_SIGNAL_GLOBAL_SOURCE=str(TRANSPORT/'global'),NSSOC_SIGNAL_OUT=str(OUT/'work'),
        PYTHONPATH=str(ROOT/'scripts'))
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
    result=dict(status='RUNNING_ONE_FIXED_CLOCK_SIGNAL_REPAIR',source_head=head,accepted=False,
        final_timing_complete=False,full_phy_accepted=False,phase_results=[],storage=[initial],
        native_routing_started=False,automatic_retry=False,prior_DRT_markers=762)
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
        old=os.environ.get('NSSOC_SIGNAL_PHASE');os.environ['NSSOC_SIGNAL_PHASE']=name
        try:command([str(app),'openroad','-exit','-python',str(ROOT/'scripts/mainchip_fixed_clock_signal_repair_native.py')],name)
        finally:
            if old is None:os.environ.pop('NSSOC_SIGNAL_PHASE',None)
            else:os.environ['NSSOC_SIGNAL_PHASE']=old
    try:
        command([sys.executable,str(ROOT/'scripts/bootstrap_flow.py')],'bootstrap-exact-runtime')
        app=c.regular(Path(os.environ['CLOUD_APPIMAGE']).resolve());assert c.file_sha(app)==APP_SHA
        command([sys.executable,str(Path(__file__).resolve()),'--restore-worker'],'restore-complete-saved-inputs')
        result['source_admission']=restored_inputs();save(OUT/'result.json',result)
        with environment():
            command([str(app),'openroad','-version'],'actual-runtime-version')
            phase('prepare')
            command([str(app),'openroad','-exit',str(OUT/'work/load-guides.tcl')],'load-exact-saved-guides')
            phase('guide-audit')
            result['native_routing_started']=True;save(OUT/'result.json',result)
            command([str(app),'openroad','-exit',str(OUT/'work/repair.tcl')],'one-signal-routing-attempt')
            result['route_log']=s.route_log(c.regular(sup.TRACE/'one-signal-routing-attempt.stdout').read_bytes())
            phase('route-audit')
            command([str(app),'openroad','-exit',str(OUT/'work/unfix.tcl')],'paired-original-class-return')
            phase('unfix-audit')
            command([str(app),'openroad','-exit',str(OUT/'work/final-drc.tcl')],'full-original-class-read-only-DRT')
            phase('drc-audit')
        result['native_result']=json.loads(c.regular(OUT/'work/drc-audit-result.json').read_bytes())
        result['next_stage']=s.continuation_gate(result['native_result'])
        restored_inputs();assert c.file_sha(app)==APP_SHA;s.methods()
        result.update(status='COMPLETE_BOUNDED_SIGNAL_REPAIR_NOT_RC_STA_OR_PHY_ACCEPTANCE',
            original_inputs_unchanged=True,runtime_appimage_sha256=APP_SHA,
            published_package_source_is_not_rebuilt_ELF_attestation=True)
    except BaseException as e:
        result.update(status='FAIL_OR_INTERRUPTED_SIGNAL_REPAIR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        try:sup.stop_process(sup.ACTIVE)
        finally:
            sup.STOP.set();beat.join(timeout=2)
            for sig,handler in previous.items():signal.signal(sig,handler)
            sup.OUT,sup.TRACE=oldout,oldtrace
            result['outputs']={str(p.relative_to(OUT)):c.file_sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
            save(OUT/'result.json',result)
        s.methods()

def publish():
    s.methods()
    import publish_mainchip_saved_postroute as p
    previous=p.GROUP
    try:
        p.GROUP=GROUP;space('publish')
        return p.publish_evidence(OUT,ROOT/('publication-'+GROUP))
    finally:p.GROUP=previous

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group()
    g.add_argument('--restore-worker',action='store_true');g.add_argument('--publish',action='store_true')
    a=p.parse_args()
    if a.restore_worker:restore_worker()
    elif a.publish:print(json.dumps(publish(),indent=2),flush=True)
    else:run()
if __name__=='__main__':main()
