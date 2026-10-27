#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded cloud restoration, exact original-clock transfer and read-only DRT measurement."""
import argparse,contextlib,hashlib,importlib,json,os,shutil,signal,sys,threading,traceback
from pathlib import Path
import mainchip_original_clock_restoration as c
ROOT=c.ROOT
OUT=ROOT/'cloud-mainchip-original-clock-restoration'
METHOD=ROOT/'scripts/mainchip-original-clock-restoration-cloud-methods.json'
GROUP='mainchip-original-clock-restoration'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
ARCHIVE=ROOT/'hw/soc/pcie-evidence/20261025-gen12-record-qualified-source'
SUPERVISOR_SHA='e326e548ebe11550d18a049d639bdf063f03602d4ba08299b00a5747d3281c0b'
SELECTED=['geometry/routed/work/before-guide-read.odb','geometry/routed/work/detailed-route.odb',
 'geometry/result.json','geometry/topology.json','geometry/fixed-clock.json',
 'geometry/all-source-clocks.log','geometry/all-clocks/before.def','geometry/all-clocks/after.def']
SUP=None

def methods():
    m=json.loads(c.regular(METHOD).read_bytes());c.source_gate()
    for p,h in m['protected'].items():assert c.file_sha(ROOT/p)==h,('source',p)
    assert m['native_routing_authorized']is False and m['simulation_authorized']is False
    assert m['full_phy_accepted']is False
    return m

def save(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.tmp')
    assert not path.is_symlink()and not temporary.exists()
    with temporary.open('x')as f:
        f.write(json.dumps(value,indent=2,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)

def terminal_stream(record,trace,label):
    assert record['label']==label and record['supervision_failure']is None
    assert record['returncode']==0
    assert record['process_group_cleanup']['remaining_live']==[]
    for key in ('stdout','stderr'):
        p=trace/(label+'.'+key)
        assert p.stat().st_size==record[key+'_bytes']and c.file_sha(p)==record[key+'_sha256']
    return record

def supervisor():
    global SUP
    if SUP is None:
        old=list(sys.path);sys.path.insert(0,str(ARCHIVE/'scripts'))
        try:SUP=importlib.import_module('cloud_pcie_gen12_training_records_telemetry')
        finally:sys.path[:]=old
        assert Path(SUP.__file__).resolve()==ARCHIVE/'scripts/cloud_pcie_gen12_training_records_telemetry.py'
        assert c.file_sha(Path(SUP.__file__).resolve())==SUPERVISOR_SHA
        for name in ('check_pcie_gen12_training_records','check_pcie_gen12_raw32_rx','check_pcie_gen12_tx_raw32'):
            assert Path(sys.modules[name].__file__).resolve()==ARCHIVE/'scripts'/(name+'.py')
        from pcie_live_memory_sampler import install
        install(SUP)
        SUP.OUT=OUT;SUP.TRACE=OUT/'supervision'
        assert SUP.SECONDS==1200 and SUP.MIN_AVAILABLE_KIB==2097152 and SUP.MAX_GROUP_RSS_KIB==10485760
    return SUP

@contextlib.contextmanager
def native_environment(donor,recipient):
    values=dict(NSSOC_CLOCK_RESTORE_DONOR=str(donor),NSSOC_CLOCK_RESTORE_RECIPIENT=str(recipient),
        NSSOC_CLOCK_RESTORE_OUT=str(OUT/'work'),PYTHONPATH=str(ROOT/'scripts'))
    keys=set(values)|{'GH_TOKEN','GITHUB_TOKEN'}
    previous={k:os.environ.get(k)for k in keys}
    try:
        os.environ.update(values)
        for k in ('GH_TOKEN','GITHUB_TOKEN'):os.environ.pop(k,None)
        yield
    finally:
        for k,v in previous.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v

def admit_restore_proof(proof):
    expected=c.diagnosis(c.regular(ROOT/c.DIAG).read_bytes())['restore']
    assert proof==expected,'Exact original ODB archive/selected-file restoration proof differs'
    assert proof['run']==40209284989
    assert proof['restore']['archive']['bytes']==629603913
    assert proof['restore']['archive']['sha256']=='df1269d646d03ff4a03203c1347d0a22a78a1e3fd81ca00e43bd4266cbd91ace'
    return proof

def required_space(stage,unpacked_bytes=0):
    assert type(unpacked_bytes)is int and unpacked_bytes>=0
    if stage=='initial':return 16*1024**3
    if stage=='restore':return 12*1024**3
    if stage=='phase':return 4*1024**3
    assert stage=='publish','Unknown storage stage'
    return max(4*1024**3,unpacked_bytes+1024**3)

def disk_admission(free,stage,unpacked_bytes=0):
    assert type(free)is int and free>=0
    needed=required_space(stage,unpacked_bytes)
    assert free>=needed,('Insufficient disk headroom',stage,free,needed)
    return dict(stage=stage,free_bytes=free,required_bytes=needed,unpacked_bytes=unpacked_bytes)

def storage(stage):
    unpacked=0
    if stage=='publish'and OUT.exists():
        assert not OUT.is_symlink()and OUT.is_dir()
        for p in OUT.rglob('*'):
            assert not p.is_symlink()and (p.is_file()or p.is_dir())
            if p.is_file():unpacked+=p.stat().st_size
    return disk_admission(shutil.disk_usage(ROOT).free,stage,unpacked)

def restore_worker():
    m=methods();assert m['cloud_restore_authorized']is True
    assert not(OUT/'source').exists()
    import cloud_mainchip_clock_diagnostic as old
    old.methods() # All original source/timing/physical input pins remain mandatory.
    source=old.live_source()
    old.reports.OUT=OUT
    storage('restore')
    result,proof=old.reports.restore_report(old.SOURCE_GROUP,old.SOURCE_RUN,old.SUMMARY,old.PARTS,OUT/'source',SELECTED)
    admit_restore_proof(proof)
    expected=json.loads(c.regular(ROOT/'docs/evidence/mainchip-saved-postroute-first-native-full-summary-20261025.json').read_bytes())
    assert result==expected
    assert result['status']=='FAIL_OR_ERROR'and result['error']=="AssertionError(('all-source-clocks', 1))"
    assert result['source_head']==old.SOURCE_HEAD and result['final_timing_complete']is False
    assert proof['restore']['full_archive_verified_before_extraction']is True
    inventory={p:result['outputs'][p]for p in SELECTED}
    inventory['result.json']=old.SUMMARY
    assert set(inventory)==set(proof['restore']['selected_files'])
    for p,h in inventory.items():assert c.file_sha(OUT/'source'/p)==h,p
    assert inventory[old.BEFORE]==c.DONOR_SHA and inventory[old.AFTER]==c.RECIPIENT_SHA
    save(OUT/'source-admission.json',dict(source=source,restore=proof,inputs=inventory,
        complete_archive_authenticated=True,original_failed_gate_preserved=True,
        exact_selected_native_files=9,cold_restart=False,native_routing_started=False))

def verify_inputs():
    r=json.loads(c.regular(OUT/'source-admission.json').read_bytes())
    assert r['original_failed_gate_preserved']is True and r['complete_archive_authenticated']is True
    assert set(r['inputs'])==set(SELECTED)|{'result.json'}
    for p,h in r['inputs'].items():assert c.file_sha(OUT/'source'/p)==h,p
    return r

def publish():
    methods()
    import publish_mainchip_saved_postroute as p
    previous=p.GROUP
    try:
        p.GROUP=GROUP
        storage('publish')
        return p.publish_evidence(OUT,ROOT/('publication-'+GROUP))
    finally:p.GROUP=previous

def native_run():
    m=methods()
    assert m['cloud_restore_authorized']is True and m['native_execution_authorized']is True
    assert c.source_gate()['native_prepare_audit_authorized']is True
    # Same strict reserved-only lookup; it never creates or repairs a release.
    import ensure_cloud_tested_source_release as guard
    tag,source=guard.context(GROUP,os.environ)
    guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,source)
    initial_space=storage('initial')
    OUT.mkdir(exist_ok=False);(OUT/'supervision').mkdir()
    result=dict(status='RUNNING_CLOCK_RESTORATION_DIAGNOSTIC',source_head=os.environ['GITHUB_SHA'],
        accepted=False,full_phy_accepted=False,final_timing_complete=False,
        native_routing_started=False,phase_results=[],zero_DRT_markers=None,storage=[initial_space])
    save(OUT/'result.json',result)
    sup=supervisor();previous={s:signal.signal(s,sup.interrupted)for s in (signal.SIGINT,signal.SIGTERM)}
    worker=threading.Thread(target=sup.heartbeat,daemon=True);worker.start()
    def run(args,label):
        result['storage'].append(storage('phase'));save(OUT/'result.json',result)
        sup.supervised(args,label,seconds=1200,cwd=ROOT)
        record=json.loads(c.regular(sup.TRACE/(label+'.command.json')).read_bytes())
        terminal_stream(record,sup.TRACE,label);result['phase_results'].append(record);save(OUT/'result.json',result)
    def phase(name,drc=False):
        key='NSSOC_CLOCK_DRC_PHASE'if drc else'NSSOC_CLOCK_RESTORE_PHASE'
        old=os.environ.get(key);os.environ[key]=name
        try:
            script='mainchip_original_clock_drc.py'if drc else'mainchip_original_clock_restoration_native.py'
            run([str(app),'openroad','-exit','-python',str(ROOT/'scripts'/script)],('drc-'if drc else'')+name)
        finally:
            if old is None:os.environ.pop(key,None)
            else:os.environ[key]=old
    try:
        run([sys.executable,str(ROOT/'scripts/bootstrap_flow.py')],'bootstrap-exact-runtime')
        app=c.regular(Path(os.environ['CLOUD_APPIMAGE']).resolve());assert c.file_sha(app)==APP_SHA
        run([sys.executable,str(Path(__file__).resolve()),'--restore-worker'],'restore-authenticated-original-ODB')
        result['source_admission']=verify_inputs();save(OUT/'result.json',result)
        app=c.regular(Path(os.environ['CLOUD_APPIMAGE']).resolve());assert c.file_sha(app)==APP_SHA
        result['runtime']=dict(appimage_sha256=APP_SHA,published_recipe_not_rebuilt_ELF_attestation=True)
        with native_environment(OUT/'source'/SELECTED[0],OUT/'source'/SELECTED[1]):
            run([str(app),'openroad','-version'],'actual-runtime-version')
            phase('prepare')
            run([str(app),'openroad','-exit',str(OUT/'work/restore.tcl')],'paired-original-clock-import')
            phase('audit-restored')
            phase('prepare',True)
            run([str(app),'openroad','-exit',str(OUT/'work/initial-drc.tcl')],'read-only-initial-DRT')
            phase('audit',True)
            drc=json.loads(c.regular(OUT/'work/drc-audit-result.json').read_bytes())
            assert drc['status']=='COMPLETE_INITIAL_DRT_MEASUREMENT_NOT_SIGNOFF'
            result['initial_DRT']=drc;result['zero_DRT_markers']=drc['measurement']['zero_reported_DRT_markers']
            save(OUT/'result.json',result)
            phase('prepare-fixed')
            run([str(app),'openroad','-exit',str(OUT/'work/fixed.tcl')],'paired-fixed-control-import')
            phase('audit-fixed')
            run([str(app),'openroad','-exit',str(OUT/'work/unfixed.tcl')],'paired-original-class-return')
            phase('audit-unfixed')
        verify_inputs();assert c.file_sha(app)==APP_SHA
        result.update(status='COMPLETE_CLOCK_RESTORATION_INITIAL_DRT_AND_FIXED_ROUNDTRIP_NOT_SIGNOFF',
            original1691_clock_gate_passed=True,actual218_clock_records_restored=True,
            original_inputs_unchanged=True,full_FIXED_roundtrip_verified=True)
    except BaseException as e:
        result.update(status='FAIL_OR_INTERRUPTED_CLOCK_RESTORATION',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        try:sup.stop_process(sup.ACTIVE)
        finally:
            sup.STOP.set();worker.join(timeout=2)
            for s,fn in previous.items():signal.signal(s,fn)
            result['outputs']={str(p.relative_to(OUT)):c.file_sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
            save(OUT/'result.json',result)
        methods()

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--restore-worker',action='store_true');g.add_argument('--publish',action='store_true')
    args=p.parse_args()
    if args.restore_worker:restore_worker()
    elif args.publish:print(json.dumps(publish(),indent=2),flush=True)
    else:native_run()
if __name__=='__main__':main()
