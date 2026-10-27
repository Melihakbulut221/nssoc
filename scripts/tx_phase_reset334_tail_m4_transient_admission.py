#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact current-model OP capsule admission; never regenerate inputs or run a DUT."""
import hashlib,json,subprocess
from pathlib import Path
import cloud_chunked_results as chunks
import tx_phase_reset244_avss18_baseline as frozen
import tx_phase_reset334_tail_m4_loaded_admission as current_RC
import tx_phase_reset334_tail_m4_loaded_adapter as prior_loaded
import tx_phase_reset334_zero_op_runtime as original_paths
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
SOURCE={'run': 40549236303, 'job': 122348788796, 'head': '7d654637774b04fcbea63a0d880a2de7daae83e7', 'release': 425766455, 'group': 'tx-phase-reset334-tail-m4-loaded', 'summary': '2cafe4a2c38555ec96beb3d29e87ddf8cf8011a9f0a84c6bf7172ac220d30261'}
ASSETS={'summary': {'id': 682312012, 'name': 'tx-phase-reset334-tail-m4-loaded-40549236303-1.summary.json', 'size': 3832886, 'sha256': '2cafe4a2c38555ec96beb3d29e87ddf8cf8011a9f0a84c6bf7172ac220d30261'}, 'parts': {'id': 682312101, 'name': 'tx-phase-reset334-tail-m4-loaded-40549236303-1.parts.json', 'size': 886, 'sha256': 'bde24052012a5e72092a6e9d8eed7f83ee4909f3b50f2ebd1aa9ca507730863c'}, 'archive': {'id': 682312951, 'name': 'tx-phase-reset334-tail-m4-loaded-40549236303-1.tar.gz.part0000', 'size': 262840889, 'sha256': '1083608b98c18cb98cbed5330b895fdb3a8f3fee5c7370ea044dc7f937044e8b'}, 'native': {'id': 682312767, 'name': 'native-four-OP-result.json', 'size': 3114446, 'sha256': 'f1e921615c66430a0b28bfc5f5d3434872c78c83a4a4ed2495789e8348bcd280'}}
SUMMARY='docs/evidence/tx-phase-reset334-tail-M4-four-OP-native-pass-20261027-summary.json'
ROOT_NAME='cloud-tx-phase-reset334-tail-m4-loaded'
NATIVE='docs/evidence/tx-phase-reset334-tail-M4-four-OP-native-pass-20261027-native-four-OP-result.json'
OUTER_FILES=3286
NATIVE_FILES=3271
PREPARED_FILES=3201
TAG='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
MODELS={'p': '474987ee48116c9ca825f526fa6eb36c66244307994c414c3dac7854afb63306', 'n': '75f73b6868707cdcc4386e7a41d2ee877344af7702cf412aa5e5d04edb5dda09'}
PREPARATION_SHA='a09ef332cf35bafd71d4b94b94e715c85dee2f40593e4bec6749a9af0db07b5e'
BINDING_SHA='e4e5b3c976596b5f3fb2472f41b8200325827b5211243d29307569ce626aef38'
LABELS=('p-initial-high','p-initial-low','n-initial-high','n-initial-low')
sha=frozen.sha
def digest(b):return hashlib.sha256(b).hexdigest()

def snapshot():
    raw=(ROOT/SUMMARY).read_bytes()
    assert len(raw)==ASSETS['summary']['size']and digest(raw)==SOURCE['summary']
    result=json.loads(raw);_,native=native_snapshot();validate_outer(result,native);return raw,result

def native_snapshot():
    raw=(ROOT/NATIVE).read_bytes()
    assert len(raw)==ASSETS['native']['size']and digest(raw)==ASSETS['native']['sha256']
    result=json.loads(raw);validate(result);return raw,result

def validate_outer(r,native):
    assert r['source_head']==SOURCE['head']and r['run_id']==SOURCE['run']and r['run_attempt']==1
    assert r['status']==native['status']=='PASS_FOUR_FRESH318_ZERO_OPS_NOT_TRANSIENT_OR_PHASE_ACCEPTANCE'
    assert r['zero_op_qualification_complete']is r['native_result_present']is r['protected_sources_unchanged']is True
    assert r['native_result']==native and r['native_result_sha256']==ASSETS['native']['sha256']
    assert r['native_result_bytes']==ASSETS['native']['size']and r['native_result_raw_path']=='native-four-OP-result.json'
    assert r['original_electrical_rejection_preserved']is r['fresh_current_original_34ns_waveforms_required']is True
    for key in ('electrical_accepted','full_phy_accepted','transient_executed','geometry_generation_executed','extraction_executed','continuation_executed','old_R_rescaled'):assert r[key]is False
    assert len(r['outputs'])==OUTER_FILES-1 and len(native['outputs'])==NATIVE_FILES-1
    expected={'native/'+p:h for p,h in native['outputs'].items()}
    expected['native/result.json']=ASSETS['native']['sha256']
    assert {p:h for p,h in r['outputs'].items()if p.startswith('native/')}==expected
    assert r['outputs']['native-four-OP-result.json']==ASSETS['native']['sha256']
    for name,h in (('fresh-binding.summary.json',BINDING_SHA),('fresh-preparation.summary.json',PREPARATION_SHA)):
        assert r['outputs'][name]==h
    assert r['supervisor']['returncode']==0 and r['supervisor']['supervision_failure']is None
    assert not r['supervisor']['process_group_cleanup']['remaining_live']
    return True

def validate(r):
    assert r['source_head']==SOURCE['head']and r['run_id']==SOURCE['run']
    assert r['status']=='PASS_FOUR_FRESH318_ZERO_OPS_NOT_TRANSIENT_OR_PHASE_ACCEPTANCE'
    assert r['validation_errors']==[]and r['sources_unchanged']and r['all_four_expanded_zero_OPs_passed']
    assert r['native_simulator_invoked']and r['runtime_installed']and len(r['outputs'])==NATIVE_FILES-1
    assert set(r['cases'])==set(LABELS)
    for key in ('transient_executed','electrical_phase_accepted','all31_clock_tree_accepted','PLL_connected','full_PHY_accepted','old_R_rescaled','geometry_generation_executed','new_extraction_performed'):assert r[key]is False
    cp=r['current_TAIL_M4_preparation'];assert cp['current_models']==r['current_RC_model_hashes']==MODELS==current_RC.MODELS
    assert cp['binding_summary_sha256']==BINDING_SHA and cp['preparation_summary_sha256']==PREPARATION_SHA
    assert cp['binding_faults_per_polarity']==20 and cp['preparation_faults']==8 and cp['path_faults']==32
    assert len(cp['path_controls']['negative_controls'])==32 and cp['unchanged_original_function_code_objects']
    assert cp['simulator_invoked']is cp['extraction_invoked']is cp['electrical_accepted']is False
    transport=cp['current_RC'];assert transport['all3181_files_authenticated']and len(transport['inventory']['files'])==3181
    rc_raw,rc=current_RC.snapshot()
    assert transport['metadata']['run']['id']==current_RC.SOURCE['run']and transport['metadata']['run']['head_sha']==current_RC.SOURCE['head']
    for path,h in rc['outputs'].items():assert r['outputs']['fresh-preparation/authenticated-RC/'+path]==h
    assert r['outputs']['fresh-preparation/authenticated-RC/result.json']==digest(rc_raw)
    assert len(cp['all_prepared_files'])==PREPARED_FILES
    assert all(r['outputs']['fresh-preparation/'+p]==h for p,h in cp['all_prepared_files'].items())
    assert r['outputs']['fresh-preparation/binding.summary.json']==BINDING_SHA
    assert r['outputs']['fresh-preparation/preparation.summary.json']==PREPARATION_SHA
    for pol,h in MODELS.items():assert r['outputs']['fresh-preparation/qualified-binding/qualified-rc/'+pol+'/composition/reset334-wire.spice']==h
    for label,row in r['cases'].items():
        assert row['complete']and row['passed']and row['errors']==[]and row['returncode']==0
        assert row['expected_HBT_count']==318 and row['expected_saved_vectors']==4726
        assert row['zero_OP_gate']==original_paths.gate(row)and row['zero_OP_gate']['passed']
        assert row['solver']['profile']=='breakpoint_tight_trap'and row['solver']['method']=='TRAPEZOIDAL'
        assert row['solver']['numeric_options']==dict(maxord=2,reltol=1e-6,abstol=1e-13,vntol=1e-8,trtol=1,itl4=100)
        assert row['solver']['native_minbreak_variable_s']==1e-18
        assert row['path_binding']['byte_exact_reversal']and len(row['path_binding']['six_path_cards'])==6
        assert row['path_binding']['original_source_and_save_cards_unchanged']and row['path_binding']['uniform_all318_OFF']
        assert row['deck_sha256']==r['outputs'][label+'/bench.cir']==row['path_binding']['OP_deck_sha256']
        assert row['contract_sha256']==r['outputs'][label+'/contract.json']==r['outputs']['fresh-preparation/cases/'+label+'/contract.json']
        assert row['path_binding']['prepared_deck_sha256']==r['outputs']['fresh-preparation/cases/'+label+'/bench.cir']
        assert row['native_log_sha256']==r['outputs'][label+'/native.log']and row['zero_source_op']['sha256']==r['outputs'][label+'/op.raw']
    old_raw=(ROOT/'docs/evidence/tx-phase-reset334-first-loaded-rejected-result-20261025.json').read_bytes()
    assert digest(old_raw)=='815b8422d6d8ba88f9f8596d3c417591a90f86a593e37d841332cbe006b1f402'
    old=json.loads(old_raw);rejection=r['original17_HBT_rejection']
    assert rejection==cp['original17_HBT_rejection']and rejection['original_complete_review']==old['review']
    assert rejection['all17_original_failed_HBT_records']=={k:v for k,v in old['review']['measurement']['hbt_safety'].items()if not v['passed']}
    assert rejection['failed_HBT_count']==len(rejection['all17_original_failed_HBT_records'])==17
    assert r['original17_HBT_rejection']==prior_loaded.original_rejections()[0]
    assert r['prior_four_tail_rejection']==cp['prior_four_tail_rejection']==prior_loaded.prior_four_tail_rejection()
    assert len(r['prior_four_tail_rejection']['all_four_failed_HBT_records'])==4
    assert r['original_electrical_rejection_preserved']is True
    assert transport['native_view_files']==3165 and transport['complete_files']==3181
    assert transport['full_current_physical_files']==631 and transport['consumed_native_view']=='native'
    assert r['original_parent_TX_rejection']==cp['original_parent_TX_rejection']and r['original_parent_TX_rejection']['electrical_screen_passed']is False
    return True

def validate_metadata(run,job,info,ref):
    assert run['id']==SOURCE['run']and run['head_sha']==SOURCE['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-loaded-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'
    assert job['id']==SOURCE['job']and job['run_id']==SOURCE['run']and job['head_sha']==SOURCE['head']
    assert job['run_attempt']==1 and job['status']=='completed'and job['conclusion']=='success'
    assert info['id']==SOURCE['release'];publication.validate_release(info,ref,TAG,SOURCE['head'])
    for a in ASSETS.values():
        matches=[x for x in info['assets']if x['name']==a['name']];assert len(matches)==1
        x=matches[0];assert x['id']==a['id']and x['size']==a['size']and x['state']=='uploaded'and x['digest']=='sha256:'+a['sha256']
    return True

def prerequisite():
    raw,r=snapshot()
    run=frozen.api('actions/runs/'+str(SOURCE['run']));job=frozen.api('actions/jobs/'+str(SOURCE['job']))
    info=frozen.api('releases/'+str(SOURCE['release']));ref=frozen.api('git/ref/tags/'+TAG)
    validate_metadata(run,job,info,ref)
    assert frozen.raw_asset(ASSETS['summary'])==raw
    return r,dict(run=run,job=job,release=info,tag=ref)

def expected_files(r):
    _,native=native_snapshot();validate_outer(r,native);expected=dict(r['outputs']);assert 'result.json'not in expected
    expected['result.json']=SOURCE['summary'];assert len(expected)==OUTER_FILES
    return expected

def restore(destination):
    raw,r=snapshot();_,metadata=prerequisite()
    transport=destination.parent/'current-OP-transport';transport.mkdir(exist_ok=False)
    (transport/'summary.json').write_bytes(raw)
    b=frozen.raw_asset(ASSETS['parts']);(transport/'parts.json').write_bytes(b);m=json.loads(b);a=ASSETS['archive']
    assert m['format']=='ordered-tar-gzip-parts-v1'and m['source_directory']==ROOT_NAME
    assert m['stem']==SOURCE['group']+'-'+str(SOURCE['run'])+'-1'
    assert m['bytes']==a['size']and m['sha256']==a['sha256']
    assert m['parts']==[dict(index=0,name=a['name'],bytes=a['size'],sha256=a['sha256'])]
    part=transport/a['name']
    with part.open('xb')as output:
        subprocess.run(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream','repos/'+frozen.REPO+'/releases/assets/'+str(a['id'])],stdout=output,check=True)
    parts=chunks.verify_parts(m,transport)
    inventory=frozen.audit_archive(part,expected_files(r),destination,ROOT_NAME)
    assert(destination/'result.json').read_bytes()==raw
    native_raw,native=native_snapshot()
    assert(destination/'native/result.json').read_bytes()==native_raw
    expected_native={str(p.relative_to(destination/'native')):sha(p)for p in(destination/'native').rglob('*')if p.is_file()}
    assert expected_native==dict(native['outputs'],**{'result.json':ASSETS['native']['sha256']})
    assert len(expected_native)==NATIVE_FILES
    return native_raw,native,dict(metadata=metadata,transport=parts,inventory=inventory,all3286_files_authenticated=True,
      complete_outer_files=OUTER_FILES,complete_consumed_native_files=NATIVE_FILES,consumed_native_view='native',
      native_zero_OP_summary_sha256=ASSETS['native']['sha256'],
      original_electrical_rejection_preserved=True,outer_zero_OP_summary_sha256=SOURCE['summary'],summary_sha256=PREPARATION_SHA)
