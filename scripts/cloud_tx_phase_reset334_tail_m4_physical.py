#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current AVSS18 restore and unchanged physical gates for exactly12 M4 branches."""
import argparse,ast,copy,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import cloud_tx_phase_reset244_physical as original
import tx_phase_reset334_avss18_rc_admission as admission
import ensure_cloud_tested_source_release as guard
import wait_cloud_tested_source_release as waiter
import cdr_v59_tail_access_runtime as runtime
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-tail-m4-physical-methods.json'
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset334-tail-m4-physical'
STAGE=OUT/'native'
GROUP='tx-phase-reset334-tail-m4-physical'
ORIGINAL='scripts/cloud_tx_phase_reset244_physical.py'
OLD_PREREQUISITE=original.prerequisite
STATUS='PASS_TAIL_M4_PHYSICAL_SOURCE_CONTROLS_NO_NATIVE'
PASS='PASS_BOTH_TAIL_M4_EXACT12_MATERIAL_334_PHYSICAL_1010_TERMINALS_REQUIRES_FRESH_MIM_RC_LOADED'
sha=admission.sha
EDITS=[('    host();m=pins();pre=prerequisite()\n', '    host();m=pins();_tail_m4_authorize(m);pre=prerequisite()\n'), ("        report['clock_contract']=clock_contract()\n", "        report['clock_contract']=clock_contract()\n        report['source_controls_prerequisite']=_tail_m4_save_prerequisite(pre)\n        report['baseline_restoration']=_tail_m4_restore(OUT);save()\n"), ("ROOT/'hw/soc/flow/make_pcie_tx_phase_reset244_v1.py','--pdk'", "ROOT/'scripts/generate_tx_phase_reset334_tail_m4_native.py','--pdk'"), ("                variant['generation']=generated;save()\n", "                variant['generation']=generated;save()\n                variant['native_material']=_tail_m4_material(app,execute,polarity,out,report['baseline_restoration']);save()\n"), ('PASS_FRESH334_DRC_DEEP_FLAT_LVS9_FAULTS_AND1010_NATIVE_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_AND_LOADED_RESET', 'PASS_TAIL_M4_MATERIAL40_FAULTS334_DRC_DEEP_FLAT_LVS9_FAULTS1010_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_LOADED'), ("        report.update(status='PASS_BOTH_FRESH334_PHYSICAL_AND1010_TERMINAL_GATES_REQUIRES_MIM_RC_AND_LOADED_RESET',sources_unchanged=True)", "        _tail_m4_finish(report)\n        report.update(status='PASS_BOTH_TAIL_M4_EXACT12_MATERIAL_334_PHYSICAL_1010_TERMINALS_REQUIRES_FRESH_MIM_RC_LOADED',sources_unchanged=True)"), ("    finally:\n        report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()", "    finally:\n        if 'baseline_restoration'in report:_tail_m4_finalize_baseline(report)\n        report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()\n        assert report.get('original_baseline_byte_unchanged',True),report.get('baseline_immutability_error')")]

def write(path,r):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');temporary.replace(path)

def methods():
    original.host();m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    for key in ('simulation_authorized','extraction_authorized','continuation_authorized'):
        assert m[key]is False,key
    for key in ('source_controls_authorized','native_generation_authorized','native_material_authorized'):
        assert type(m[key])is bool,key
    assert m['native_generation_authorized']is m['native_material_authorized']
    assert m['owned_process']==dict(seconds=18000,minimum_available_kib=2097152,maximum_group_rss_kib=10485760,output_limit_per_stream_bytes=16777216)
    return m

def completed_controls():
    m=methods();c=m['completed_source_controls'];assert isinstance(c,dict)
    tested_raw=(ROOT/c['tested_method_path']).read_bytes();tested=json.loads(tested_raw)
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    for p,h in c['proof_files'].items():assert m['protected'][p]==h==sha(ROOT/p)
    normalized=copy.deepcopy(m)
    normalized.update(native_generation_authorized=False,native_material_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    r=json.loads((ROOT/c['result_path']).read_bytes())
    assert r['status']==STATUS and r['native_executed']is False
    run=original.api('actions/runs/'+str(c['run']));job=original.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-physical-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'and job['name']=='source-controls'
    log=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+guard.REPO+'/actions/jobs/'+str(c['job'])+'/logs'])
    assert log==(ROOT/c['log_path']).read_bytes()
    for key in ('publication','imports','wait'):
        record=json.loads((ROOT/c[key+'_path']).read_bytes())
        assert record==r['completed_auxiliary_controls'][key]
    return dict(run=c['run'],job=c['job'],head=c['head'],log_sha256=hashlib.sha256(log).hexdigest(),
                tested_method_sha256=hashlib.sha256(tested_raw).hexdigest(),all_tested_pins_unchanged=True)

def authorize(m):
    assert m['native_generation_authorized']is m['native_material_authorized']is True
    assert m['simulation_authorized']is m['extraction_authorized']is m['continuation_authorized']is False
    release={}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '='in line:
            k,v=line.split('=',1);release[k]=v.strip('"')
    assert release['ID']=='ubuntu'and release['VERSION_ID']=='22.04'
    assert os.environ['ImageOS']=='ubuntu22'

def prerequisite():
    planning=OLD_PREREQUISITE()
    return dict(original_planning=planning,current_tail_source_controls=completed_controls())

def derive():
    m=methods();raw=(ROOT/ORIGINAL).read_text()
    node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='main')
    before=ast.get_source_segment(raw,node);after=before
    for old,new in EDITS:
        assert old!=new and after.count(old)==1;after=after.replace(old,new,1)
    reverse=after
    for old,new in reversed(EDITS):
        assert reverse.count(new)==1;reverse=reverse.replace(new,old,1)
    assert reverse==before;ast.parse(after)
    proof=dict(original_main_sha256=hashlib.sha256(before.encode()).hexdigest(),
               generated_main_sha256=hashlib.sha256(after.encode()).hexdigest(),edit_count=len(EDITS))
    assert proof==m['controller_derivation']
    return after,dict(**proof,reversed_byte_exact=True,edits=EDITS)

def save_prerequisite(pre):
    path=STAGE/'source-controls-prerequisite.json';write(path,pre)
    return dict(path=path.name,sha256=sha(path),proof=pre)

def restore(out):
    _,physical=admission.physical()
    proof=admission.restore(physical,out/'baseline')
    assert proof['all407_files_authenticated']and admission.frozen.unchanged(proof)
    path=out/'baseline-restoration.json';write(path,proof)
    return proof

def material(app,execute,pol,out,restored):
    destination=out/'native-material.json'
    execution=execute([app,'python',ROOT/'scripts/generate_tx_phase_reset334_tail_m4_native.py','--material',
       '--baseline',Path(restored['directory'])/pol/'layout','--candidate',out/'layout',
       '--preset',pol,'--pdk',ROOT/'pdk','--output',destination],out,'native-material',allow_failure=True)
    if destination.exists():(STAGE/('physical-'+pol+'-native-material.json')).write_bytes(destination.read_bytes())
    assert execution['returncode']==0 and destination.is_file()
    proof=json.loads(destination.read_text())
    assert proof['status']=='PASS_EXACT12_TAIL_M4_NATIVE_MATERIAL_AND40_ACTUAL_FAULTS_REQUIRES_DRC_LVS_RC_LOADED'
    assert proof['native_geometry_delta_proved']and proof['all_inputs_byte_unchanged']and proof['no_GDS_written']
    assert len(proof['actual_native_faults'])==40 and all(r['rejected']for r in proof['actual_native_faults'])
    assert len(proof['actual_text_serialization_positives'])==2 and all(r['json_roundtrip']for r in proof['actual_text_serialization_positives'])
    assert proof['native_comparison']==proof['post_fault_positive']
    assert proof['DRC_LVS_proved']is proof['RC_or_electrical_accepted']is False
    return proof

def finish(report):
    assert set(report['variants'])=={'p','n'}and admission.frozen.unchanged(report['baseline_restoration'])
    for pol,v in report['variants'].items():
        assert v['native_material']['native_geometry_delta_proved']and v['native_material']['polarity']==pol
        assert v['steps']['drc']['measurement']['category_count']==560
        assert v['wires']['graph']['native_device_count']==334 and v['wires']['graph']['native_terminal_count']==1010
        assert v['wires']['anchors']['counts']['body_terminals']==326
        assert len(v['generation']['tail_m4_plan'])==12
    report.update(exact12_native_M4_rectangles_per_polarity_proved=True,
                  original_electrical_rejection_preserved=True,old_R_rescaled=False,
                  fresh_RC_required=True,fresh_loaded_waveforms_required=True)

def finalize_baseline(report):
    try:
        assert admission.frozen.unchanged(report['baseline_restoration'])
        report['original_baseline_byte_unchanged']=True
    except BaseException as e:
        report.update(status='FAIL_OR_ERROR',original_baseline_byte_unchanged=False,
                      baseline_immutability_error=repr(e),baseline_immutability_traceback=traceback.format_exc())

def install():
    body,proof=derive()
    original.OUT=STAGE;original.METHOD=METHOD;original.GROUP=GROUP;original.prerequisite=prerequisite
    original.__dict__.update(_tail_m4_authorize=authorize,_tail_m4_save_prerequisite=save_prerequisite,
       _tail_m4_restore=restore,_tail_m4_material=material,_tail_m4_finish=finish,
       _tail_m4_finalize_baseline=finalize_baseline)
    exec(compile(body,'derived-tail-M4-original-physical-main','exec'),original.__dict__)
    return proof

def child():
    methods();install();original.main()

def preflight():
    m=methods();authorize(m);controls=completed_controls()
    waiter.wait(GROUP,os.environ)
    tag,head=guard.context(GROUP,os.environ)
    reservation=guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    assert not reservation['existing_assets']
    return dict(reservation=reservation,completed_controls=controls)

def finalize(report):
    native=STAGE/'result.json'
    if native.is_file():
        raw=native.read_bytes();(OUT/'native-physical-result.json').write_bytes(raw)
        report['native_result_sha256']=hashlib.sha256(raw).hexdigest()
        report['native_result']=json.loads(raw)
    if 'baseline_restoration'in report.get('native_result',{}):
        finalize_baseline(report['native_result'])
        if not report['native_result']['original_baseline_byte_unchanged']:report['status']='FAIL_OR_ERROR'
    for pol in ('p','n'):
        p=STAGE/('physical-'+pol+'-native-material.json')
        if p.is_file():(OUT/p.name).write_bytes(p.read_bytes())
    try:methods();report['protected_sources_unchanged']=True
    except BaseException as e:report.update(status='FAIL_OR_ERROR',protected_sources_unchanged=False,source_error=repr(e))
    report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
    write(OUT/'result.json',report)
    return report

def run_owned_child():
    import signal,threading
    m=methods();trace=OUT/'supervision';trace.mkdir(exist_ok=False)
    owned=runtime.supervisor(ROOT,OUT,trace,methods,m['protected'][runtime.SAMPLER])
    old_signals={s:signal.signal(s,owned.interrupted)for s in (signal.SIGTERM,signal.SIGINT)}
    worker=threading.Thread(target=owned.heartbeat,daemon=True);worker.start()
    try:
        probe=runtime.launcher(ROOT,methods,m['protected'][runtime.PROBE])
        observed=probe.probe(Path(os.environ['CLOUD_APPIMAGE']),original.APP_SHA,OUT/'runtime-preflight')
        write(OUT/'runtime-preflight.json',observed)
        assert observed['accepted']and observed['interpreter']['pya_version']=='0.30.7'
        result=owned.supervised([sys.executable,'-B',ROOT/'scripts/cloud_tx_phase_reset334_tail_m4_physical.py','--child'],
            'complete-two-polarity-physical',False,seconds=m['owned_process']['seconds'],cwd=OUT)
        record=json.loads((trace/'complete-two-polarity-physical.command.json').read_text())
        assert record['returncode']==result.returncode and not record['supervision_failure']
        assert not record['process_group_cleanup']['remaining_live']
        return record
    finally:
        owned.stop_process(owned.ACTIVE);owned.STOP.set();worker.join(timeout=2)
        for sig,handler in old_signals.items():signal.signal(sig,handler)
        owned.sample('final_resource_sample')

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),electrical_accepted=False,full_phy_accepted=False,
      simulation_executed=False,extraction_executed=False,continuation_executed=False,
      original_electrical_rejection_preserved=True,old_R_rescaled=False)
    write(OUT/'result.json',report);error=None
    try:
        report['preflight']=preflight();report['derivation']=derive()[1];write(OUT/'result.json',report)
        report['supervisor']=run_owned_child()
        native=json.loads((STAGE/'result.json').read_bytes())
        assert report['supervisor']['returncode']==0 and native['status']==PASS
        assert native['original_baseline_byte_unchanged']and native['sources_unchanged']and not native['validation_errors']
        report.update(status=PASS,native_generation_completed=True,physical_gates_passed=True,
                      fresh_RC_required=True,fresh_loaded_waveforms_required=True)
    except BaseException as e:
        error=e;report.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc())
    finally:finalize(report)
    if error is not None:raise error
    assert report['status']==PASS
    return report

def controls():
    methods()
    from check_tx_phase_reset334_tail_m4_physical import controls as check
    return check()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--child',action='store_true');a=p.parse_args()
    if a.controls:print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    elif a.child:child()
    else:main()
