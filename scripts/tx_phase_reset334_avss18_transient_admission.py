#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact current-model OP capsule admission; never regenerate inputs or run a DUT."""
import hashlib,json,subprocess
from pathlib import Path
import cloud_chunked_results as chunks
import tx_phase_reset244_avss18_baseline as frozen
import tx_phase_reset334_avss18_loaded_admission as current_RC
import tx_phase_reset334_zero_op_runtime as original_paths
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
SOURCE={'run': 40222180657, 'job': 121256065604, 'head': 'a218dd078115fbb65088de6e0129bb4e5f3100cd', 'release': 423587568, 'group': 'tx-phase-reset334-avss18-loaded', 'summary': 'af1babab272ca21fc332b79b3a8f3288f8c5e055cacfc0479d9d03686b575002'}
ASSETS={'summary': {'id': 675815955, 'name': 'tx-phase-reset334-avss18-loaded-40222180657-1.summary.json', 'size': 2216507, 'sha256': 'af1babab272ca21fc332b79b3a8f3288f8c5e055cacfc0479d9d03686b575002'}, 'parts': {'id': 675816000, 'name': 'tx-phase-reset334-avss18-loaded-40222180657-1.parts.json', 'size': 883, 'sha256': '60df9e841e6a6ee254b115dbdba1c2b47cebeb778bfe3e3fc22b53d804b44614'}, 'archive': {'id': 675816052, 'name': 'tx-phase-reset334-avss18-loaded-40222180657-1.tar.gz.part0000', 'size': 150927784, 'sha256': 'f674a1c6d6b3b979fdd692f1ce4ffdd1ed40b18d69e41439afde23da1b04211e'}}
SUMMARY='docs/evidence/tx-phase-reset334-avss18-loaded-zero-OP-full-result-20261025.json'
ROOT_NAME='cloud-tx-phase-reset334-avss18-loaded'
TAG='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
MODELS={'p': 'bfe98e32e29aacd8defbb46eed28a62286bcc1513db0af1b6f8e1d514e1c8aa4', 'n': '1e5a2f72577c1923d06afa4e74f879ca2f8bd086581c1400188ff5ac7d95c975'}
PREPARATION_SHA='b9dfd2e1edcda8c30f6e4e81c622249fc4ed21e1818cad254a2002e49a8ad4b0'
BINDING_SHA='0bac53cd5b69341e36fc88dd2a4c9cd273dc445dc00c4620abe203edd80116b2'
LABELS=('p-initial-high','p-initial-low','n-initial-high','n-initial-low')
sha=frozen.sha
def digest(b):return hashlib.sha256(b).hexdigest()

def snapshot():
    raw=(ROOT/SUMMARY).read_bytes()
    assert len(raw)==ASSETS['summary']['size']and digest(raw)==SOURCE['summary']
    result=json.loads(raw);validate(result);return raw,result

def validate(r):
    assert r['source_head']==SOURCE['head']and r['run_id']==SOURCE['run']
    assert r['status']=='PASS_FOUR_FRESH318_ZERO_OPS_NOT_TRANSIENT_OR_PHASE_ACCEPTANCE'
    assert r['validation_errors']==[]and r['sources_unchanged']and r['all_four_expanded_zero_OPs_passed']
    assert r['native_simulator_invoked']and r['runtime_installed']and len(r['outputs'])==2805
    assert set(r['cases'])==set(LABELS)
    for key in ('transient_executed','electrical_phase_accepted','all31_clock_tree_accepted','PLL_connected','full_PHY_accepted','old_R_rescaled','geometry_generation_executed','new_extraction_performed'):assert r[key]is False
    cp=r['current_AVSS18_preparation'];assert cp['current_models']==r['current_RC_model_hashes']==MODELS==current_RC.MODELS
    assert cp['binding_summary_sha256']==BINDING_SHA and cp['preparation_summary_sha256']==PREPARATION_SHA
    assert cp['binding_faults_per_polarity']==20 and cp['preparation_faults']==8 and cp['path_faults']==32
    assert len(cp['path_controls']['negative_controls'])==32 and cp['unchanged_original_function_code_objects']
    assert cp['simulator_invoked']is cp['extraction_invoked']is cp['electrical_accepted']is False
    transport=cp['current_RC'];assert transport['all2717_files_authenticated']and len(transport['inventory']['files'])==2717
    rc_raw,rc=current_RC.snapshot()
    assert transport['metadata']['run']['id']==current_RC.SOURCE['run']and transport['metadata']['run']['head_sha']==current_RC.SOURCE['head']
    for path,h in rc['outputs'].items():assert r['outputs']['fresh-preparation/authenticated-RC/'+path]==h
    assert r['outputs']['fresh-preparation/authenticated-RC/result.json']==digest(rc_raw)
    assert len(cp['all_prepared_files'])==2736
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
    assert r['original_parent_TX_rejection']==cp['original_parent_TX_rejection']and r['original_parent_TX_rejection']['electrical_screen_passed']is False
    return True

def validate_metadata(run,job,info,ref):
    assert run['id']==SOURCE['run']and run['head_sha']==SOURCE['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-avss18-loaded-cloud.yml'
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
    validate(r);expected=dict(r['outputs']);assert 'result.json'not in expected
    expected['result.json']=SOURCE['summary'];assert len(expected)==2806
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
    return raw,r,dict(metadata=metadata,transport=parts,inventory=inventory,all2806_files_authenticated=True,
      original_electrical_rejection_preserved=True,outer_zero_OP_summary_sha256=SOURCE['summary'],summary_sha256=PREPARATION_SHA)
