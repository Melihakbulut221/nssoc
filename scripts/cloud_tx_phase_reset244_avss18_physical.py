#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact original physical pipeline plus immutable baseline/material admission."""
import argparse,ast,copy,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import cloud_tx_phase_reset244_physical as original
import tx_phase_reset244_avss18_baseline as baseline
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset244-avss18-native-methods.json'
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset244-avss18-physical'
GROUP='tx-phase-reset244-avss18-physical'
ORIGINAL='scripts/cloud_tx_phase_reset244_physical.py'
OLD_PREREQUISITE=original.prerequisite
SOURCE_RUN=40206328842
SOURCE_JOB=121207947350
SOURCE_HEAD='ec29fe6fe97c3f39a4b158892faf51ce1a710104'
SOURCE_RESULT='docs/evidence/tx-phase-reset244-avss18-source-controls-full-result-20261025.json'
SOURCE_LOG='docs/evidence/tx-phase-reset244-avss18-source-controls-job-20261025.log'
STATUS='PASS_AVSS18_NATIVE_WRAPPER_SOURCE_CONTROLS_NO_NATIVE'
EDITS=[('    host();m=pins();pre=prerequisite()\n', '    host();m=pins();_avss18_authorize(m);pre=prerequisite()\n'), ("        report['clock_contract']=clock_contract()\n", "        report['clock_contract']=clock_contract()\n        report['source_controls_prerequisite']=_avss18_save_prerequisite(pre)\n        report['baseline_restoration']=_avss18_restore(OUT);save()\n"), ("ROOT/'hw/soc/flow/make_pcie_tx_phase_reset244_v1.py','--pdk'", "ROOT/'scripts/generate_tx_phase_reset244_avss18_native.py','--pdk'"), ("                variant['generation']=generated;save()\n", "                variant['generation']=generated;save()\n                variant['native_material']=_avss18_material(app,execute,polarity,out,report['baseline_restoration']);save()\n"), ('PASS_FRESH334_DRC_DEEP_FLAT_LVS9_FAULTS_AND1010_NATIVE_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_AND_LOADED_RESET', 'PASS_AVSS18_MATERIAL20_FAULTS334_DRC_DEEP_FLAT_LVS9_FAULTS1010_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_LOADED'), ("        report.update(status='PASS_BOTH_FRESH334_PHYSICAL_AND1010_TERMINAL_GATES_REQUIRES_MIM_RC_AND_LOADED_RESET',sources_unchanged=True)", "        _avss18_finish(report)\n        report.update(status='PASS_BOTH_AVSS18_EXACT_MATERIAL_334_PHYSICAL_1010_TERMINALS_REQUIRES_FRESH_MIM_RC_LOADED',sources_unchanged=True)"), ("    finally:\n        report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()", "    finally:\n        if 'baseline_restoration'in report:_avss18_finalize_baseline(report)\n        report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()\n        assert report.get('original_baseline_byte_unchanged',True),report.get('baseline_immutability_error')")]
def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def methods():
    m=json.loads(METHOD.read_text())
    for path,h in m['protected'].items():assert sha(ROOT/path)==h,path
    assert m['simulation_authorized']is m['extraction_authorized']is False
    return m
def validate_source_proof(run,job,result,log):
    assert run['id']==SOURCE_RUN and run['head_sha']==SOURCE_HEAD and run['run_attempt']==1
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'
    assert run['path']=='.github/workflows/tx-phase-reset244-avss18-source-cloud.yml'
    assert run['status']=='completed'and run['conclusion']=='success'
    assert job['id']==SOURCE_JOB and job['run_id']==SOURCE_RUN and job['head_sha']==SOURCE_HEAD
    assert job['name']=='source-controls'and job['run_attempt']==1 and job['status']=='completed'and job['conclusion']=='success'
    assert len(log)==843683 and hashlib.sha256(log).hexdigest()=='508427f5f5cf25302785640e537c0329e5d103d59d966b306384307318ecd5ac'
    assert result['source_head']==SOURCE_HEAD and result['status']=='PASS_TWO_POLARITY_AVSS18_SOURCE_PLANS_54_FAULTS_NO_NATIVE_PROOF'
    assert len(result['faults'])==54 and all(r['rejected']for r in result['faults'])
    assert set(result['polarity'])=={'p','n'}
    assert result['native_execution']is result['native_geometry_proved']is result['electrical_accepted']is False
    assert result['original_electrical_rejection_preserved']is True
    assert result['source_method']['native_generation_authorized']is False
def prerequisite():
    methods();planning=OLD_PREREQUISITE()
    r=original.api('actions/runs/'+str(SOURCE_RUN));j=original.api('actions/jobs/'+str(SOURCE_JOB))
    log=subprocess.check_output(['gh','api','--allow-escape-sequences',
          'repos/Melihakbulut221/nssoc/actions/jobs/'+str(SOURCE_JOB)+'/logs'])
    assert log==(ROOT/SOURCE_LOG).read_bytes()
    result=json.loads((ROOT/SOURCE_RESULT).read_text());validate_source_proof(r,j,result,log)
    return dict(**planning,avss18_source_controls=dict(run=SOURCE_RUN,job=SOURCE_JOB,source=SOURCE_HEAD,
       result_sha256=sha(ROOT/SOURCE_RESULT),log_sha256=hashlib.sha256(log).hexdigest(),
       all54_source_faults_passed=True,native_geometry_proved=False))
def derive():
    m=methods();raw=(ROOT/ORIGINAL).read_text()
    node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='main')
    before=ast.get_source_segment(raw,node);after=before;records=[]
    for old,new in EDITS:
        assert after.count(old)==1
        after=after.replace(old,new);records.append(dict(old=old,new=new,count=1))
    reverse=after
    for old,new in reversed(EDITS):
        assert reverse.count(new)==1;reverse=reverse.replace(new,old)
    assert reverse==before;ast.parse(after)
    proof=dict(original_main_sha256=hashlib.sha256(before.encode()).hexdigest(),
               generated_main_sha256=hashlib.sha256(after.encode()).hexdigest(),
               edit_count=len(records),edits=records,reversed_byte_exact=True)
    assert {k:proof[k]for k in ('original_main_sha256','generated_main_sha256','edit_count')}==m['controller_derivation']
    # The two baseline admission functions are copied byte-exact, not reinterpreted.
    frozen=(ROOT/'scripts/cloud_tx_phase_reset334_intrinsic_mim.py').read_text()
    current=(ROOT/'scripts/tx_phase_reset244_avss18_baseline.py').read_text()
    for name in ('validate_run','validate'):
        a=next(n for n in ast.parse(frozen).body if isinstance(n,ast.FunctionDef)and n.name==name)
        b=next(n for n in ast.parse(current).body if isinstance(n,ast.FunctionDef)and n.name==name)
        assert ast.get_source_segment(frozen,a)==ast.get_source_segment(current,b)
    return after,proof
def authorize(m):
    assert m['native_generation_authorized']is True
    assert m['simulation_authorized']is m['extraction_authorized']is False
    release={}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '='in line:
            k,v=line.split('=',1);release[k]=v.strip('"')
    assert release['ID']=='ubuntu'and release['VERSION_ID']=='22.04'
    assert os.environ['ImageOS']=='ubuntu22'
def save_prerequisite(pre):
    path=OUT/'source-controls-prerequisite.json'
    path.write_text(json.dumps(pre,indent=2,allow_nan=False)+'\n');return dict(path=path.name,sha256=sha(path),proof=pre)
def restore(out):
    proof=baseline.restore(out)
    path=out/'baseline-restoration.json';path.write_text(json.dumps(proof,indent=2,allow_nan=False)+'\n')
    return proof
def material(app,execute,pol,out,restored):
    destination=out/'native-material.json'
    execution=execute([app,'python',ROOT/'scripts/tx_phase_reset244_avss18_native_material.py',
       '--baseline',Path(restored['directory'])/pol/'layout','--candidate',out/'layout',
       '--preset',pol,'--pdk',ROOT/'pdk','--output',destination],out,'native-material',allow_failure=True)
    if destination.exists():
        (OUT/('physical-'+pol+'-native-material.json')).write_bytes(destination.read_bytes())
    assert execution['returncode']==0 and destination.is_file()
    proof=json.loads(destination.read_text())
    assert proof['status']=='PASS_EXACT_AVSS18_NATIVE_MATERIAL_AND20_ACTUAL_FAULTS_REQUIRES_DRC_LVS_RC_LOADED'
    assert proof['native_geometry_delta_proved']and proof['all_inputs_byte_unchanged']and proof['no_GDS_written']
    assert len(proof['actual_native_faults'])==20 and all(r['rejected']for r in proof['actual_native_faults'])
    assert len(proof['actual_text_serialization_positives'])==2 and all(r['json_roundtrip']for r in proof['actual_text_serialization_positives'])
    assert proof['native_comparison']==proof['post_fault_positive']
    assert proof['DRC_LVS_proved']is proof['RC_or_electrical_accepted']is False
    return proof
def finish(report):
    assert set(report['variants'])=={'p','n'}and baseline.unchanged(report['baseline_restoration'])
    for pol,v in report['variants'].items():
        assert v['native_material']['native_geometry_delta_proved']and v['native_material']['polarity']==pol
        assert v['steps']['drc']['measurement']['category_count']==560
        assert v['wires']['graph']['native_device_count']==334 and v['wires']['graph']['native_terminal_count']==1010
        assert v['wires']['anchors']['counts']['body_terminals']==326
    report.update(exact_one_native_rectangle_per_polarity_proved=True,
                  original_electrical_rejection_preserved=True,old_R_rescaled=False,
                  fresh_RC_required=True,fresh_loaded_waveforms_required=True)
def finalize_baseline(report):
    try:
        assert baseline.unchanged(report['baseline_restoration'])
        report['original_baseline_byte_unchanged']=True
    except BaseException as e:
        report.update(status='FAIL_OR_ERROR',original_baseline_byte_unchanged=False,
                      baseline_immutability_error=repr(e),baseline_immutability_traceback=traceback.format_exc())
def install():
    body,proof=derive()
    original.OUT=OUT;original.METHOD=METHOD;original.GROUP=GROUP;original.prerequisite=prerequisite
    original.__dict__.update(_avss18_authorize=authorize,_avss18_save_prerequisite=save_prerequisite,
       _avss18_restore=restore,_avss18_material=material,_avss18_finish=finish,
       _avss18_finalize_baseline=finalize_baseline)
    exec(compile(body,'derived-avss18-original-physical-main','exec'),original.__dict__)
    return proof
def controls():
    original.host();m=methods();assert m['source_controls_authorized']is True
    proof=install();inherited=original.controls()
    assert len(inherited['schematic_fault_controls'])==10 and len(inherited['publication_controls']['rejected'])==17
    import check_tx_phase_reset244_avss18_native as check
    result=check.controls()
    methods()
    return dict(status=STATUS,derivation=proof,inherited=inherited,controls=result,
       native_execution=False,native_geometry_proved=False,electrical_accepted=False,
       original_electrical_rejection_preserved=True)
def main():
    original.host();methods();install();original.main()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args()
    if a.controls:print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    else:main()
