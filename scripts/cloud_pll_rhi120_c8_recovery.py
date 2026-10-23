#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Whole845+4-contact all-terminal 1us native trajectory across hosted process checkpoints.

Checkpointing changes elapsed host execution only. Never restart, interpolate,
concatenate captures, change TSTOP, or infer full PHY acceptance from these probes.
"""
import argparse,copy,hashlib,json,os,re,shutil,subprocess,tarfile,time
from pathlib import Path
import numpy as np
import cloud_native_checkpoint_probe as native
import cloud_native_portable_checkpoint as portable
import cloud_pll_vbic_acquisition as acquisition
import cloud_pll_filter_physical_acquisition as physical_pll
import cloud_tx_input_driver_localpins as restoration
import run_cloud_pll865_snapshot as pll
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from cloud_chunked_results import verify_parts
from route_cloud_newer_postcts import fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-rhi120-c8-native'
LIB=ROOT/'cloud-pll-snapshot'
CASE=OUT/'case'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
BOUNDED=dict(run=38904997140,group='native-portable-checkpoint',root='cloud-native-portable-checkpoint',bytes=59772311,sha='30bad1656b8c6f291d805b3161b8336825d7608c3a04355c57e10a6f8c0f7331',summary='5f261d535f386661979ef9854e26dead27b6ba1d4d681eed931d5c300faed176')
CROSS_SHA='fccc1d9f00d142f43013ac7900f80fb3daa26c9821d025b14cea6f9f43f343a0'
CHECKPOINT_STATUS='SAVED_ACTUAL_PHYSICAL845_ONE_US_PROCESS_NOT_FULL_CAPTURE_OR_ACCEPTANCE'
COMPLETE_STATUS='COMPLETE_ACTUAL_PHYSICAL845_ONE_US_NATIVE_CONTINUATION_NOT_PHY_ACCEPTANCE'
MARKER=b'Binary:\n'
import read_pll845_full_native_op as full_op
import read_pll845_full_native_transient as full_wave
import cloud_pll845_disk_budget as host_disk
import pll_rhi120_c8_native_columns as columns
sha=full_wave.sha
def method_hashes():
    paths=[Path(__file__),Path(native.__file__),Path(portable.__file__),Path(acquisition.__file__),
        Path(physical_pll.__file__),Path(pll.__file__),ROOT/'scripts/cloud_vbic_tree32_backend.py',
        ROOT/'scripts/review_pcie_pll_acquisition_v1.py',
        ROOT/'scripts/cloud_pll_divider_load3p2v2_diagnostic.py',ROOT/'scripts/compare_cloud_routed_endpoints.py',
        Path(full_op.__file__),Path(full_wave.__file__),Path(host_disk.__file__),ROOT/'scripts/read_pll845_all_native_transient.py']
    paths.extend(ROOT/p for p in EXTRA_METHODS)
    return {str(p.relative_to(ROOT)):sha(p)for p in paths}

def payload_info(path):
    with path.open('rb')as f:
        header=f.read(full_wave.MAX_HEADER);assert MARKER in header,'Missing native binary header'
        offset=header.index(MARKER)+len(MARKER)
        f.seek(offset);digest=hashlib.sha256();count=0
        while b:=f.read(4*1024**2):digest.update(b);count+=len(b)
    return dict(header_bytes=offset,payload_bytes=count,payload_sha256=digest.hexdigest(),bytes=path.stat().st_size,sha256=sha(path))

def prefix_preserved(path,prior):
    with path.open('rb')as f:
        h=f.read(full_wave.MAX_HEADER);assert MARKER in h
        f.seek(h.index(MARKER)+len(MARKER));left=prior['payload_bytes'];d=hashlib.sha256()
        while left:
            b=f.read(min(left,4*1024**2));assert b,'Truncated checkpoint prefix'
            d.update(b);left-=len(b)
    assert d.hexdigest()==prior['payload_sha256'],'Native checkpoint payload changed'
    return True

def original_process_contract(case,protected,boots):
    assert boots==['native-entrypoint'],'Cold restart detected'
    assert all(sha(Path(p))==v for p,v in protected.items()),'Protected native input changed'
    body=(case/'circuit.cir').read_text()
    assert body.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1,'Original full analysis changed'
    assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',body))==102
    assert '.options reltol=1e-4 abstol=1e-12 klu'in body
    assert sha(case/'parent865.spice')==physical_pll.MODEL_SHA
    vectors=next(s[5:].split()for s in body.splitlines()if s.startswith('save '))
    assert len(vectors)==34
    return vectors

def controls():
    import tempfile
    with tempfile.TemporaryDirectory()as tmp:
        p=Path(tmp)/'raw';p.write_bytes(b'old header\n'+MARKER+b'0123456789')
        info=payload_info(p)
        p.write_bytes(b'backpatched native header\n'+MARKER+b'0123456789more')
        assert prefix_preserved(p,info)
        rejected=[]
        for name,data in [('truncation',b'0123'),('corruption',b'012345678xmore')]:
            p.write_bytes(b'header\n'+MARKER+data)
            try:prefix_preserved(p,info)
            except AssertionError:rejected.append(name)
            else:raise AssertionError('Bad native prefix accepted')
        assert rejected==['truncation','corruption']
    return dict(prefix_header_backpatch_allowed=True,payload_faults_rejected=rejected,
                reader=pll.self_test(),full_terminal_reader=full_wave.controls(),acquisition=pll.acquisition_controls(),
                cycles=pll.acquisition_cycle_controls(),readback=readback_controls())

def restore_models(wanted):
    assert not LIB.exists();LIB.mkdir()
    packed=OUT/'models-source.tar.gz';fetch(acquisition.URL+'.tar.gz',acquisition.ARCHIVE_SHA,packed)
    assert packed.stat().st_size==1318040150
    found=set()
    with tarfile.open(packed)as tar:
        for m in tar:
            p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==LIB.name
            rel=str(Path(*p.parts[1:]))
            if rel not in wanted:continue
            assert m.isfile()and rel not in found;found.add(rel)
            data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==wanted[rel]
            target=LIB/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert found==set(wanted);packed.unlink()

def prepare_original():
    OUT.mkdir(exist_ok=False)
    fetch(BASE+'cloud-results-38906315749-1-native-portable-cross-job/native-portable-cross-job-38906315749-1.summary.json',CROSS_SHA,OUT/'cross-job-proof.json')
    cross=json.loads((OUT/'cross-job-proof.json').read_text())
    assert cross['cross_job_native_restore_proven'] and cross['source']==BOUNDED
    assert cross['positive']['rows']==12818 and all(c['rejected']for c in cross['controls'])
    assert cross['source_has_avx512f']and not cross['destination_has_avx512f']
    assert cross['glibc_tunables']==portable.TUNABLES and cross['unchanged_native_inputs']
    restoration.OUT=OUT;old,proof=restoration.restore(BOUNDED)
    assert proof['native_checkpoint_proven']and proof['original_bounded_trajectory_unchanged']
    wanted={str(Path(p).relative_to(LIB)):d for p,d in proof['preparation']['protected'].items()if Path(p).is_relative_to(LIB)}
    assert len(wanted)>=37;restore_models(wanted)
    shutil.copytree(LIB,OUT/'model-sources')
    CASE.mkdir();(OUT/'runtime').mkdir()
    engine=OUT/'runtime/patched-ngspice';shutil.copy2(old/'runtime/patched-ngspice',engine);assert sha(engine)==native.ENGINE_SHA
    for filename in ['native-image.tar','source-summary.json']:
        shutil.copy2(old/filename,OUT/filename)
    assert sha(OUT/'native-image.tar')==proof['native_image_sha256']
    shutil.copytree(old/'physical-parent-proof',OUT/'physical-parent-proof')
    full=(LIB/'circuit.cir').read_text();bounded=(old/'resumed/circuit.cir').read_text()
    assert bounded.replace('.tran 3.125e-13 4e-09 0 3.125e-13','.tran 3.125e-13 1e-06 0 3.125e-13')==full
    (CASE/'circuit.cir').write_text(full)
    shutil.copy2(old/'resumed/parent865.spice',CASE/'parent865.spice')
    expected='NSSOC actual845 original1us continuous capture\n.include "circuit.cir"\n.control\nop\nwrite op.raw all\nrun actual-acquisition.raw\nquit\n.endc\n.end\n'
    readback='echo NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\n'
    (CASE/'actual-acquisition.cir').write_text(expected.replace('quit\n.endc',readback+'quit\n.endc'))
    (CASE/'spinit').write_text('set num_threads=1\n')
    protected={str(p):sha(p)for p in [engine,*LIB.rglob('*'),*CASE.iterdir()]if p.is_file()}
    physical_pll.verify_prepared(OUT,proof['preparation']['physical_parent'],(CASE/'parent865.spice').read_text())
    receipt=dict(image_id=proof['image_id'],native_image_sha256=proof['native_image_sha256'],
        protected=protected,model_sources=wanted,physical_parent=proof['preparation']['physical_parent'],
        expected_options=proof['restored']['native_options'],bounded_source=BOUNDED,
        cross_job_summary_sha256=CROSS_SHA,runtime_libraries=proof['runtime_libraries'],
        glibc_tunables=portable.TUNABLES,vectors=original_process_contract(CASE,protected,['native-entrypoint']))
    # Only the small immutable source proof is retained; no bounded capture is a
    # full-run input. New full trajectory starts at time zero exactly once.
    (OUT/'bounded-source-summary.json').write_text(json.dumps(proof,indent=2)+'\n')
    shutil.rmtree(OUT/'inputs')
    return receipt



PREP_RUN=39920519407
PREP_SUMMARY='63c6b8d34ecf277dce223427c72bdb943ed0dc010c80f496d8feb33f268f94dd'
PREP_PARTS='92a85edae348ad4e3ebfb62b372f627dde16ef9aadb4fcb55cedc1422a9d4657'
PREP_HEAD='efe9885e87bce9eb82a1c6decc4ed85ab2d65160'
def verify_new_physical(case):
    report_path=OUT/'prepared/result.json'
    assert sha(report_path)==PREP_SUMMARY
    prepared=json.loads(report_path.read_text())
    assert prepared['source_head']==PREP_HEAD and prepared['sources_unchanged']
    assert prepared['status']=='PASS_WHOLE_PLL_LOADED_DECK_AND2737_TERMINAL_INSTRUMENTATION_REQUIRES_NATIVE_EXECUTION'
    assert prepared['all_original_stimuli_loads_solver_duration_unchanged']and prepared['terminal_probes']==2737
    for n in ['candidate-circuit.cir','terminal-instrumentation.json','composition/pll845-mim-wire.spice','composition/composition.json']:
        assert sha(OUT/'prepared'/n)==prepared['outputs'][n]
    assert sha(case/'parent865.spice')==prepared['outputs']['composition/pll845-mim-wire.spice']
    contract=json.loads((OUT/'prepared/composition/composition.json').read_text())
    coverage=json.loads((OUT/'prepared/terminal-instrumentation.json').read_text())
    assert contract['counts']==dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
    assert not contract['uncontacted_body_groups']and len(contract['device_records'])==845
    assert len(coverage['native_terminal_probes'])==2737 and coverage['full_native_terminal_coverage']
    assert len(coverage['auxiliary_contact_probes'])==4 and len(coverage['vectors'])==1694
    assert len(coverage['vectors'])==len(set(coverage['vectors']))
    assert all(t['explicit_zero_reference']or t['vector']in coverage['vectors']for t in coverage['native_terminal_probes'])
    return coverage
def validate_bound_deck(body):
    coverage=verify_new_physical(CASE)
    assert body==(OUT/'prepared/candidate-circuit.cir').read_text(),'Prepared full deck changed'
    assert body.count('.tran 3.125e-13 1e-06 0 3.125e-13')==1
    assert '.options reltol=1e-4 abstol=1e-12 klu'in body
    assert [s[5:].split()for s in body.splitlines()if s.startswith('save ')]==[coverage['vectors']]
    assert re.findall(r'(?m)^alter .*\[off\] = 1$',body)==coverage['native_hbt_off_targets']
    return coverage['vectors']
def process_contract(case,protected,boots):
    assert boots==['native-entrypoint'],'Cold restart detected'
    assert all(sha(Path(p))==v for p,v in protected.items()),'Protected native input changed'
    return validate_bound_deck((case/'circuit.cir').read_text())
def verify_native_flags(log):
    coverage=verify_new_physical(CASE)
    wanted={l.split()[1].split('[off]')[0].removeprefix('@')for l in coverage['native_hbt_off_targets']}
    flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
    assert len(flags)==len(wanted)==102 and {n for n,b in flags}==wanted
    assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1']for _,body in flags)
    return dict(actual_native_devices=102,all_off_readbacks_one=True)
def prepare():
    import compare_cloud_routed_endpoints as reports
    # Reuse only the proven immutable engine/image/runtime preparation.
    # Its old bounded simulation never runs or supplies a full-run waveform.
    receipt=prepare_original()
    reports.OUT=OUT
    base=BASE+f'cloud-results-{PREP_RUN}-1-pll-rhi120-c8-preparation/'
    fetch(base+f'pll-rhi120-c8-preparation-{PREP_RUN}-1.summary.json',PREP_SUMMARY,OUT/'preparation-summary.json')
    prepared=json.loads((OUT/'preparation-summary.json').read_text())
    files=['candidate-circuit.cir','terminal-instrumentation.json','composition/pll845-mim-wire.spice','composition/composition.json']
    files+=['model-sources/'+n for n in prepared['source_inputs']]
    actual,proof=reports.restore_report('pll-rhi120-c8-preparation',PREP_RUN,PREP_SUMMARY,PREP_PARTS,OUT/'prepared',files)
    assert actual==prepared
    for n,digest in prepared['source_inputs'].items():
        source=OUT/'prepared/model-sources'/n
        assert sha(source)==digest
        # The loaded-deck proof also retains its source bench, which was not
        # a runtime dependency of the older portable engine capsule.
        for dest in (LIB/n,OUT/'model-sources'/n):
            if dest.exists():assert sha(dest)==digest
            else:
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
            assert sha(dest)==digest
        receipt['model_sources'][n]=digest
    shutil.copy2(OUT/'prepared/candidate-circuit.cir',CASE/'circuit.cir')
    shutil.copy2(OUT/'prepared/composition/pll845-mim-wire.spice',CASE/'parent865.spice')
    vectors=validate_bound_deck((CASE/'circuit.cir').read_text())
    body=(CASE/'circuit.cir').read_text();rejected=[]
    for name,bad in [('removed_OFF',re.sub(r'^alter .*\[off\] = 1\n','',body,count=1,flags=re.M)),
                     ('wrong_OFF',body.replace('[off] = 1','[off] = 0',1)),
                     ('missing_terminal',body.replace(' '+vectors[-1], '',1)),
                     ('shortened_transient',body.replace('1e-06 0 3.125e-13','5e-08 0 3.125e-13',1))]:
        assert bad!=body
        try:validate_bound_deck(bad)
        except AssertionError as e:rejected.append(dict(fault=name,rejected=True,reason=str(e)))
        else:raise AssertionError('Changed full capture contract accepted')
    assert len(rejected)==4
    inputs=[OUT/'runtime/patched-ngspice',*LIB.rglob('*'),*CASE.iterdir(),*(OUT/'prepared').rglob('*')]
    receipt.update(original_runtime_physical_parent=receipt['physical_parent'],physical_parent=proof,
        prepared_source=proof,full_native_terminal_count=2737,auxiliary_contacts=4,
        binding_faults=rejected,vectors=vectors,
        protected={str(p):sha(p)for p in inputs if p.is_file()})
    process_contract(CASE,receipt['protected'],['native-entrypoint'])
    (OUT/'new-preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


INITIAL_SPEC=dict(run=39925042125,attempt=1,stage='initial',
 summary_sha256='74033b131a40f5009565b1dd6e219f1b6748f555f750b1c715ebbc77ad93be8d',
 parts_sha256='bf1b8dcc19d1b8b31eb6934537f0efe728e7f8a6fd5060d1e1334d22627d436d')
EXTRA_METHODS=['scripts/pll_rhi120_c8_native_columns.py','scripts/read_pll_rhi120_c8_all_native.py',
 'docs/evidence/pll-rhi120-c8-column-qualification-pass-20261023.json']
def verify_resume_methods(report,current):
    initial='scripts/cloud_pll_rhi120_c8_initial.py'
    current_path='scripts/cloud_pll_rhi120_c8_recovery.py'
    assert current[current_path]==sha(Path(__file__))
    expected_initial={k:v for k,v in current.items()if k not in [current_path,*EXTRA_METHODS]}
    expected_initial[initial]=sha(ROOT/initial)
    assert expected_initial[initial]=='08028af99b7d139175d61b0ef2712e57df69b8b59d675653bfa775e1ff06b5c9'
    if report['controller_sha256']==current[current_path]:
        assert report['method_hashes']==current,'Changed recovery source methods'
        mode='exact-current-RHI120-recovery-continuation'
    else:
        assert report['controller_sha256']==expected_initial[initial],'Unrecognized initial or old physical candidate'
        assert report['method_hashes']==expected_initial,'Changed initial runtime/physical/parser methods'
        mode='exact-failed-RHI120-initial-with-qualified-table-reader'
    return dict(mode=mode,native_solver_physical_runtime_and_original_parser_methods_unchanged=True,
      qualified_exact_table_methods_added=EXTRA_METHODS)
def source_gate(run,spec,report):
    assert run['id']==spec['run']
    assert run['status']=='completed','Do not fork a live native process'
    if spec['stage']=='initial':
        assert spec==INITIAL_SPEC,'Only the audited exact failed initial capsule is eligible'
        assert run['id']==39925042125 and run['conclusion']=='failure'
        assert run['head_sha']=='ece94d479509de8fda3ac37ef4f0a4d9856aef85'
        assert report['status']=='FAIL_OR_ERROR'and report['error']=='AssertionError()'
        assert report['checkpoint_saved']and not report['full_capture']
        assert report['checkpoint_prefix']['sha256']=='2dd133ea5eb78a7a7d87a5836612bd135f20fa1da32fb7a2a6331d71ce89f166'
        return dict(original_run=39925042125,original_failure_preserved=True,
          original_summary_sha256=INITIAL_SPEC['summary_sha256'],
          exact_post_checkpoint_table_failure_only=True)
    assert spec['stage']=='recovery'and run['conclusion']=='success'
    assert report['status']==CHECKPOINT_STATUS and report['checkpoint_saved']
    return dict(original_run=39925042125,original_failure_preserved=True,
      previous_successful_recovery_run=spec['run'])
def verify_column_qualification():
    repo='repos/Melihakbulut221/nssoc/'
    api=lambda p:json.loads(subprocess.check_output(['gh','api',repo+p]))
    run=api('actions/runs/39940337710')
    assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='6be6d42e995f521c7119a3f6aca3c4a3783ae87d'
    assert run['path']=='.github/workflows/pll-rhi120-c8-column-qualification-cloud.yml'
    data=subprocess.check_output(['gh','api',repo+'releases/assets/668796731','-H','Accept: application/octet-stream'])
    assert hashlib.sha256(data).hexdigest()=='98fe00cf33c4ea04126990558e85abd48ea1fe6f6c5b47f89adb441f21681e03'
    report=json.loads(data)
    assert report['status']=='PASS_EXACT_ACTUAL_TABLES_ALL_COLUMNS_AND35_CONTROLS_NOT_CAPTURE_OR_RECOVERY'
    assert len(report['table_controls']['rejected'])==7 and len(report['reader_controls']['controls'])==16 and len(report['op_controls'])==12
    assert report['source_audit']['summary_sha256']==columns.AUDIT_SUMMARY
    assert report['native_position']['raw_sha256']=='2dd133ea5eb78a7a7d87a5836612bd135f20fa1da32fb7a2a6331d71ce89f166'
    return dict(run=39940337710,summary_sha256=hashlib.sha256(data).hexdigest(),all35_controls_passed=True)
def resume_controls():
    current=method_hashes();key='scripts/cloud_pll_rhi120_c8_recovery.py'
    good=dict(controller_sha256=current[key],method_hashes=current)
    assert verify_resume_methods(good,current)
    original={k:v for k,v in current.items()if k not in [key,*EXTRA_METHODS]}
    initial='scripts/cloud_pll_rhi120_c8_initial.py';original[initial]=sha(ROOT/initial)
    assert verify_resume_methods(dict(controller_sha256=original[initial],method_hashes=original),current)
    rejected=[]
    for label in ('old-physical-controller','changed-runtime','missing-method','extra-method','changed-initial-controller'):
        bad=copy.deepcopy(good)
        if label=='old-physical-controller':bad['controller_sha256']='0'*64
        elif label=='changed-runtime':bad['method_hashes']['scripts/cloud_native_checkpoint_probe.py']='0'*64
        elif label=='missing-method':del bad['method_hashes']['scripts/read_pll845_full_native_op.py']
        elif label=='extra-method':bad['method_hashes']['unexpected']='0'*64
        else:bad=dict(controller_sha256=original[initial],method_hashes=dict(original));bad['method_hashes'][initial]='0'*64
        try:verify_resume_methods(bad,current)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    rr=dict(id=39925042125,status='completed',conclusion='failure',head_sha='ece94d479509de8fda3ac37ef4f0a4d9856aef85')
    pr=dict(status='FAIL_OR_ERROR',error='AssertionError()',checkpoint_saved=True,full_capture=False,
      checkpoint_prefix=dict(sha256='2dd133ea5eb78a7a7d87a5836612bd135f20fa1da32fb7a2a6331d71ce89f166'))
    assert source_gate(rr,INITIAL_SPEC,pr)
    for label in ('live-source','different-failed-run','changed-summary','missing-checkpoint','different-error','changed-payload','unexpected-source-success'):
        r,s,p=copy.deepcopy((rr,INITIAL_SPEC,pr))
        if label=='live-source':r['status']='in_progress'
        elif label=='different-failed-run':s['run']+=1
        elif label=='changed-summary':s['summary_sha256']='0'*64
        elif label=='missing-checkpoint':p['checkpoint_saved']=False
        elif label=='different-error':p['error']='native_failure'
        elif label=='changed-payload':p['checkpoint_prefix']['sha256']='0'*64
        else:r['conclusion']='success'
        try:source_gate(r,s,p)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    r=dict(id=39950000000,status='completed',conclusion='success')
    sp=dict(run=r['id'],stage='recovery')
    pr=dict(status=CHECKPOINT_STATUS,checkpoint_saved=True)
    assert source_gate(r,sp,pr)
    for label in ('failed-recovery-source','live-recovery-source','missing-recovery-checkpoint','wrong-recovery-status'):
        rr,ss,pp=copy.deepcopy((r,sp,pr))
        if label=='failed-recovery-source':rr['conclusion']='failure'
        elif label=='live-recovery-source':rr['status']='in_progress'
        elif label=='missing-recovery-checkpoint':pp['checkpoint_saved']=False
        else:pp['status']='FAIL_OR_ERROR'
        try:source_gate(rr,ss,pp)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(rejected)==16
    return dict(rejected=rejected,physical_candidate_replay_not_executed=True)

def restore_source(spec):
    assert set(spec)=={'run','attempt','stage','summary_sha256','parts_sha256'}
    assert str(spec['run']).isdigit()and str(spec['attempt']).isdigit()and spec['stage']in ('initial','recovery')
    assert all(re.fullmatch('[0-9a-f]{64}',spec[k])for k in ('summary_sha256','parts_sha256'))
    assert not OUT.exists()
    repository='repos/Melihakbulut221/nssoc/'
    run=json.loads(subprocess.check_output(['gh','api',repository+'actions/runs/'+str(spec['run'])]))
    assert run['status']=='completed','Do not fork a live native process'
    assert run['run_attempt']==int(spec['attempt'])==1 and str(run['id'])!=os.environ['GITHUB_RUN_ID']
    assert run['path']in('.github/workflows/pll-rhi120-c8-native-initial-cloud.yml','.github/workflows/pll-rhi120-c8-native-recovery-cloud.yml')
    assert run['head_branch']=='codex/complete-open-work'
    staging=ROOT/'cloud-pll-native-restore';staging.mkdir(exist_ok=False)
    group='pll-rhi120-c8-native-'+spec['stage'];stem=f"{group}-{spec['run']}-{spec['attempt']}"
    url=BASE+f"cloud-results-{spec['run']}-{spec['attempt']}-{group}/"
    fetch(url+stem+'.summary.json',spec['summary_sha256'],staging/'source-summary.json')
    fetch(url+stem+'.parts.json',spec['parts_sha256'],staging/(stem+'.parts.json'))
    report=json.loads((staging/'source-summary.json').read_text())
    source_gate(run,spec,report)
    assert report['source_head']==run['head_sha']
    resume_methods=verify_resume_methods(report,method_hashes())
    assert report['run_id']==str(spec['run'])and report['run_attempt']==str(spec['attempt'])and report['stage']==spec['stage']
    manifest=json.loads((staging/(stem+'.parts.json')).read_text());assert manifest['source_directory']==OUT.name and manifest['stem']==stem
    for i,part in enumerate(manifest['parts']):
        assert part['index']==i and part['name']==stem+'.tar.gz.part'+str(i).zfill(4)
        fetch(url+part['name'],part['sha256'],staging/part['name'])
    verify_parts(manifest,staging)
    # Consume the verified ordered bytes without a second compressed disk copy.
    with host_disk.joined_parts(manifest,staging)as packed,tarfile.open(fileobj=packed,mode='r|gz')as tar:
        seen=set()
        for m in tar:
            p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==OUT.name
            assert m.name not in seen and(m.isfile()or m.isdir());seen.add(m.name)
            tar.extract(m,ROOT,filter='data')
    assert sha(OUT/'result.json')==spec['summary_sha256']
    assert all(sha(OUT/p)==d for p,d in report['outputs'].items())
    assert not LIB.exists();shutil.copytree(OUT/'model-sources',LIB)
    assert all(sha(LIB/p)==d for p,d in report['preparation']['model_sources'].items())
    assert sha(CASE/'actual-acquisition.raw')==report['checkpoint_prefix']['sha256']
    assert payload_info(CASE/'actual-acquisition.raw')==report['checkpoint_prefix']
    history=OUT/'history';history.mkdir(exist_ok=True)
    shutil.copyfile(OUT/'result.json',history/(stem+'.json'))
    shutil.rmtree(staging)
    report['_source_failure_recovery']=source_gate(run,spec,report)
    report['_resume_methods']=resume_methods
    return report

def command(name,image,cpu,create):
    engine=OUT/'runtime/patched-ngspice'
    code='printf "native-entrypoint\\n" >> boots.log; exec "'+str(engine)+'" -n -b actual-acquisition.cir'
    return ['docker','create'if create else'run',*([]if create else['-d']),'--name',name,
        '--network','host','--security-opt','seccomp=unconfined','--cpuset-cpus',cpu,
        '--mount','type=bind,src='+str(ROOT)+',dst='+str(ROOT)+',readonly',
        '--mount','type=bind,src='+str(CASE)+',dst='+str(CASE),'-w',str(CASE),
        '-e','SPICE_SCRIPTS='+str(CASE),'-e','OMP_NUM_THREADS=1','-e','RAYON_NUM_THREADS=1',
        '-e','GLIBC_TUNABLES='+portable.TUNABLES,'--entrypoint','/bin/dash',image,'-c',code]

def execute(stage,seconds,spec=None):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert stage=='recovery' and spec is not None,'Recovery cannot cold-start'
    assert os.environ['GITHUB_RUN_ATTEMPT']=='1','Inspect preserved state instead of rerunning'
    assert 60<=seconds<=7200
    column_qualification=verify_column_qualification()
    reference_root=ROOT/'cloud-pll-rhi120-column-reference';reference_root.mkdir(exist_ok=False)
    column_reference=columns.load_reference(reference_root)
    prior=restore_source(spec)
    preparation=prior['preparation']if prior else prepare()
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(__file__),
        method_hashes=method_hashes(),run_id=os.environ['GITHUB_RUN_ID'],run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],stage=stage,
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),preparation=preparation,
        source_checkpoint=spec,resume_methods=prior.get('_resume_methods')if prior else None,
        source_failure_recovery=prior['_source_failure_recovery'],column_qualification=column_qualification,
        checkpoint_saved=False,full_capture=False,acquisition_accepted=False,
        full_device_safety_accepted=False,full_phy_accepted=False,qualified_pex=False,
        scope='Whole845+4-contact physical RC model, all1694 terminal vectors, original1us/.3125ps/KLU/zeroOP/102OFF and original stimuli/loads. Native process continuation only. Frozen both final100ns acquisition windows. Full-terminal capture alone does not prove device safety/PVT/qualifiedPEX/CDR/x4/mainchip or PHY.',
        controls=prior['controls']if prior else controls())
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(label,args,required=True,timeout=900):
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        dest=OUT/(stage+'-'+label+'.log');dest.write_text(p.stdout+p.stderr)
        result.setdefault('commands',[]).append(dict(label=label,args=args,returncode=p.returncode,sha256=sha(dest)));save()
        if required and p.returncode:raise RuntimeError(label+': '+(p.stdout+p.stderr)[-6000:])
        return p
    container=None;save()
    try:
        assert sha(native.__file__)=='28e3ca20e1d7cce96ac68f4ec19e510326d8e96ed0da77ddc16ab5b3c5e86231'
        assert not run('empty-runner',['docker','ps','-aq']).stdout.strip()
        result['cpu']=json.loads(run('lscpu',['lscpu','--json']).stdout)
        run('kernel',['uname','-a'])
        result['criu_build']=json.loads((Path(os.environ['RUNNER_TEMP'])/'criu-build.json').read_text())
        assert sha('/usr/sbin/criu')==result['criu_build']['binary_sha256']
        assert result['criu_build']['source_commit']=='9539417f3e3cfa4eb84c319cd71f4d52f1f08645'
        config="import json,pathlib;p=pathlib.Path('/etc/docker/daemon.json');d=json.loads(p.read_text())if p.exists()else{};d['experimental']=True;p.write_text(json.dumps(d))"
        run('docker-experimental',['sudo','python3','-c',config]);run('docker-restart',['sudo','systemctl','restart','docker'])
        assert sha(OUT/'native-image.tar')==preparation['native_image_sha256']
        run('load-image',['docker','load','-i',str(OUT/'native-image.tar')])
        info=json.loads(run('image',['docker','image','inspect',preparation['image_id']]).stdout)[0]
        assert info['Id']==preparation['image_id']
        cpu=prior['cpu_affinity']if prior else str(min(os.sched_getaffinity(0)))
        assert int(cpu)in os.sched_getaffinity(0);result['cpu_affinity']=cpu
        boots=(CASE/'boots.log').read_text().splitlines()if prior else['native-entrypoint']
        vectors=process_contract(CASE,preparation['protected'],boots);assert vectors==preparation['vectors']
        container='nssoc-pll-full-'+stage
        cmd=command(container,preparation['image_id'],cpu,bool(prior));result['native_command']=cmd;save()
        cid=run('create-or-start',cmd).stdout.strip();assert re.fullmatch('[0-9a-f]{64}',cid)
        if prior:
            assert result['boot_id']!=prior['boot_id'],'A separate cloud host is required'
            assert cmd[cmd.index('--network'):]==prior['native_command'][prior['native_command'].index('--network'):]
            checkpoints=OUT/'checkpoints/state'
            assert {str(p.relative_to(checkpoints)):sha(p)for p in checkpoints.rglob('*')if p.is_file()}==prior['checkpoint_images']
            root=Path(run('docker-root',['docker','info','--format','{{.DockerRootDir}}']).stdout.strip())
            dest=root/'containers'/cid/'checkpoints/state'
            run('checkpoint-dir',['sudo','mkdir','-p',str(dest.parent)])
            run('copy-checkpoint',['sudo','cp','-a',str(checkpoints),str(dest)])
            check="import pathlib,hashlib,json,sys;r=pathlib.Path(sys.argv[1]);print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in r.rglob('*')if p.is_file()}))"
            actual=json.loads(run('copy-proof',['sudo','python3','-c',check,str(dest)]).stdout);assert actual==prior['checkpoint_images']
            started=run('restore',['docker','start','--checkpoint','state',container],False)
            if started.returncode:
                run('restore-detail',['sudo','cat','/run/containerd/io.containerd.runtime.v2.task/moby/'+cid+'/work/restore.log'],False)
                raise RuntimeError('Native continuation restore failed')
            result['native_resume_started']=True;save()
        state=json.loads(run('runtime-environment',['docker','inspect',container]).stdout)[0]
        assert 'GLIBC_TUNABLES='+portable.TUNABLES in state['Config']['Env']
        result['actual_native_environment']=state['Config']['Env'];result['native_started_epoch']=time.time();save()
        start=time.monotonic();raw=CASE/'actual-acquisition.raw'
        while True:
            state=json.loads(subprocess.check_output(['docker','inspect',container]))[0]['State']
            elapsed=time.monotonic()-start
            result['elapsed_this_stage_s']=elapsed
            progress=dict(elapsed_s=elapsed,raw_bytes=raw.stat().st_size if raw.exists()else 0,native_running=state['Running'])
            print(json.dumps(progress),flush=True);result['last_progress']=progress;save()
            if not state['Running']:break
            free=shutil.disk_usage(OUT).free
            storage=host_disk.disk_plan(OUT);reserve=storage['archive_reserve_bytes']
            result['disk_budget']=dict(free_bytes=free,**storage)
            if elapsed>=seconds or free<reserve:
                result['checkpoint_reason']='host_budget'if elapsed>=seconds else'preserve_before_disk_exhaustion'
                checkpoints=OUT/'checkpoints'
                if checkpoints.exists():shutil.rmtree(checkpoints)
                checkpoints.mkdir()
                run('save-checkpoint',['docker','checkpoint','create','--checkpoint-dir',str(checkpoints),container,'state'])
                state=json.loads(run('checkpoint-stopped',['docker','inspect',container]).stdout)[0]['State']
                assert not state['Running']
                run('readable-checkpoint',['sudo','chown','-R',str(os.getuid())+':'+str(os.getgid()),str(checkpoints)])
                result['checkpoint_images']={str(p.relative_to(checkpoints/'state')):sha(p)for p in(checkpoints/'state').rglob('*')if p.is_file()}
                assert result['checkpoint_images']and'pages-1.img'in result['checkpoint_images']
                result['checkpoint_prefix']=payload_info(raw);assert result['checkpoint_prefix']['payload_bytes']>(len(vectors)+1)*8*1000
                result.update(status=CHECKPOINT_STATUS,checkpoint_saved=True);break
            time.sleep(min(60,max(1,seconds-elapsed)))
        run('native-log',['docker','logs',container],False)
        log=(OUT/(stage+'-native-log.log')).read_text()
        cumulative=OUT/'cumulative-native.log'
        oldlog=cumulative.read_text()if cumulative.exists()else''
        cumulative.write_text(oldlog+log)
        result['native_startup_readback']=verify_native_flags(cumulative.read_text())
        assert (CASE/'boots.log').read_text().splitlines()==['native-entrypoint']
        if prior:
            prefix_preserved(raw,prior['checkpoint_prefix']);result['prior_payload_unchanged']=True
            assert raw.stat().st_size>prior['checkpoint_prefix']['bytes'],'Native continuation made no progress'
        process_contract(CASE,preparation['protected'],['native-entrypoint'])
        verify_new_physical(CASE)
        result['zero_source_operating_point']=full_op.read((CASE/'op.raw').read_bytes(),vectors)
        if not result['checkpoint_saved']:
            result['native_exitcode']=state['ExitCode'];save();assert state['ExitCode']==0,(state,log[-6000:])
            options,diagnostics,_=backend_readback(cumulative.read_text(),'klu')
            result.update(native_options=options,diagnostics=diagnostics);save();assert not diagnostics
            assert all(options[k]==preparation['expected_options'][k]for k in ('backend','numeric','method'))
            result.update(status='COMPLETE_RHI120_NATIVE_REQUIRES_ALL_COLUMN_FULL_CAPTURE_REVIEW',
              native_complete=True,full_capture=False,full_capture_reader_pending=True,original_gate_passed=None)
        # Bind actual new-candidate table, not the old RHI140 native identities.
        import read_pll845_all_native_transient as table_reader
        with raw.open('rb')as stream:prefix=stream.read(table_reader.MAX_HEADER)
        table,metadata=table_reader.parse(prefix)
        op_raw=(CASE/'op.raw').read_bytes()
        op_head=op_raw[:op_raw.index(MARKER)].decode('ascii')
        op_table=[line.split() for line in op_head.split('Variables:\n',1)[1].splitlines()]
        assert len(table)==len(op_table)+1==5106
        result['exact_native_tables']=columns.check_tables(table,op_table,column_reference)
        assert all([v,'voltage'] in [row[1:]for row in table]for v in vectors)
        (OUT/'native-header-prefix.bin').write_bytes(prefix)
        (OUT/'native-column-contract.json').write_text(json.dumps(dict(
          source_preparation_run=PREP_RUN,source_preparation_sha256=PREP_SUMMARY,
          raw_table=table,raw_table_sha256=table_reader.digest(table),
          required_vectors=vectors,required_vectors_sha256=table_reader.digest(vectors),
          required_vector_indices={v:next(int(row[0])for row in table if row[1]==v)for v in vectors},
          native_terminal_probes=2737,all_native_terminal_probes_covered=True,
          source_raw_sha256=sha(raw),source_op_sha256=sha(CASE/'op.raw'),
          full_capture_accepted=False),indent=2)+'\n')
        result['all_native_op_controls']=full_op.controls(op_raw,vectors)
        assert len(result['all_native_op_controls'])==12
        stride=8*len(table);rows,partial=divmod(raw.stat().st_size-metadata['header_bytes'],stride)
        assert rows>1000
        with raw.open('rb')as stream:
            stream.seek(metadata['header_bytes']+(rows-1)*stride)
            last=float(np.frombuffer(stream.read(8),dtype='<f8')[0])
        assert np.isfinite(last)and 0<last<=1e-6
        result['native_position']=dict(last_time_s=last,complete_rows=rows,partial_row_bytes=partial,columns=len(table))
        result['protected_inputs_unchanged']=True;save()
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e));save();raise
    finally:
        if container:
            run('final-log',['docker','logs',container],False)
            run('cleanup',['docker','rm','-f',container],False)
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save();print(json.dumps({k:result[k]for k in ('status','error','checkpoint_saved','full_capture','original_gate_passed')if k in result}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--stage',choices=['initial','recovery']);p.add_argument('--seconds',type=int,default=14400);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.controls:print(json.dumps(dict(original=controls(),resume=resume_controls())))
    else:
        text=os.environ.get('SOURCE_CHECKPOINT','').strip()
        execute(a.stage,a.seconds,json.loads(text)if text else None)
