#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require the actual unchanged static32 equivalence proof before full synthesis."""
import copy,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BIND=ROOT/'scripts/pcie-gen12-training-records-static-equivalence-prerequisite.json'
RUN=40124904042
SOURCE='12eab91fbf81ede012b12220ef82c6fd881714e9'
WORKFLOW='.github/workflows/pcie-gen12-training-records-static-equivalence-cloud.yml'
REBOUND={'scripts/pcie-gen12-training-records-static-methods.json',
         'scripts/pcie-gen12-training-records-static-prerequisites.json'}
FAULTS={'truncate_to16','discard_count23_byte','shift_K_destination','discard_high_count_DE',
        'discard_count15_COM','wrong_source_slot','reverse_overlapping_write_order','discard_byte'}
def digest(b):return hashlib.sha256(b).hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def validate(d,r,m,actual,run,jobs):
    assert d['state']=='BOUND_ACTUAL_STATIC32_EQUIVALENCE'
    assert d['run']==RUN and d['source']==SOURCE and d['attempt']==1 and d['workflow']==WORKFLOW
    assert set(d['rebound_metadata_paths'])==REBOUND
    assert int(r['run'])==RUN and r['source']==SOURCE
    assert r['status']=='PASS_STATIC32_WRITE_EQUIVALENCE_AND8_COMPILED_FAULTS'
    assert r['original_full_record_proof_completed']is False
    assert r['synthesis_improvement_measured']is False and r['full_PHY_accepted']is False
    assert r['derivation_sha256']==d['derivation_sha256']
    assert r['protected_source_hashes']==m['protected']
    assert len(m['protected'])==61
    assert set(actual)==set(m['protected'])-REBOUND
    assert all(actual[p]==h for p,h in m['protected'].items()if p not in REBOUND)
    assert r['coverage']['all_counts']==list(range(32))
    assert r['coverage']['all_batch_slots']==list(range(4))
    assert r['coverage']['slot_cases']==62720 and r['coverage']['full_serial_block_cases']==15360
    assert r['slot_positive']['returncode']==0 and r['four_stage_positive']['returncode']==0
    assert len(r['negative_controls'])==8
    assert {x['label']for x in r['negative_controls']}==FAULTS
    assert all(x['returncode']!=0 for x in r['negative_controls'])
    assert run['id']==RUN and run['head_sha']==SOURCE and run['run_attempt']==1
    assert run['path']==WORKFLOW and run['status']=='completed'and run['conclusion']=='success'
    assert run['event']=='workflow_dispatch'and run['head_branch']=='codex/pcie-gen12-rx-integration'
    assert len(jobs)==2 and {j['name']for j in jobs}=={'controls','equivalence'}
    for j in jobs:
        assert j['status']=='completed'and j['conclusion']=='success'
        assert j['id']==d['job_ids'][j['name']]
    return {'run':RUN,'source':SOURCE,'result_sha256':d['result_sha256'],
            'original61_source_hashes_bound':True,'rebound_metadata_paths':sorted(REBOUND),
            'complete_record_proof_inferred':False}
def load():
    d=json.loads(BIND.read_text())
    assert d['state']=='BOUND_ACTUAL_STATIC32_EQUIVALENCE',d['state']
    rb=(ROOT/d['result_path']).read_bytes();mb=(ROOT/d['derivation_path']).read_bytes()
    assert digest(rb)==d['result_sha256']and len(rb)==d['result_bytes']
    assert digest(mb)==d['derivation_sha256']
    r=json.loads(rb);m=json.loads(mb)
    actual={p:digest((ROOT/p).read_bytes())for p in m['protected']if p not in REBOUND}
    run=api('actions/runs/'+str(RUN))
    jobs=api('actions/runs/'+str(RUN)+'/jobs?filter=latest&per_page=100')['jobs']
    return d,r,m,actual,run,jobs
def require():return validate(*load())
def controls():
    args=load();positive=validate(*args);faults={}
    changes={
      'unbound':lambda a:a[0].update(state='UNBOUND'),
      'wrong_run':lambda a:a[0].update(run=RUN+1),
      'wrong_source':lambda a:a[1].update(source='0'*40),
      'wrong_result_status':lambda a:a[1].update(status='FAIL_OR_ERROR'),
      'invent_complete_acceptance':lambda a:a[1].update(original_full_record_proof_completed=True),
      'invent_synthesis_acceptance':lambda a:a[1].update(synthesis_improvement_measured=True),
      'omit_count31':lambda a:a[1]['coverage'].update(all_counts=list(range(31))),
      'omit_slot3':lambda a:a[1]['coverage'].update(all_batch_slots=[0,1,2]),
      'truncate_slot_vectors':lambda a:a[1]['coverage'].update(slot_cases=62719),
      'truncate_full_vectors':lambda a:a[1]['coverage'].update(full_serial_block_cases=15359),
      'accept_wrong_mutant':lambda a:a[1]['negative_controls'][0].update(returncode=0),
      'wrong_mutant_identity':lambda a:a[1]['negative_controls'][0].update(label='unrelated'),
      'change_engineering_source':lambda a:a[3].update({next(iter(a[3])):'0'*64}),
      'waive_additional_source':lambda a:a[0]['rebound_metadata_paths'].append('hw/soc/rtl/pcie/soc_pcie_gen12_training_records_static.v'),
      'nonterminal_run':lambda a:a[4].update(status='in_progress'),
      'wrong_run_attempt':lambda a:a[4].update(run_attempt=2),
      'failed_equivalence_job':lambda a:a[5][0].update(conclusion='failure'),
      'wrong_job_identity':lambda a:a[5][0].update(id=-1),
      'failed_positive_block':lambda a:a[1]['four_stage_positive'].update(returncode=1),
      'wrong_derivation':lambda a:a[1].update(derivation_sha256='0'*64)}
    for name,change in changes.items():
        a=copy.deepcopy(args);change(a)
        try:validate(*a)
        except (AssertionError,KeyError,ValueError,TypeError):faults[name]=True
        else:raise AssertionError('Accepted prerequisite corruption '+name)
    assert len(faults)==20 and all(faults.values())
    return {'status':'PASS_STATIC32_NATIVE_PREREQUISITE_AND20_FAULTS',
            'prerequisite':positive,'negative_controls':faults,'new_RTL_execution':False}
if __name__=='__main__':print(json.dumps(controls(),indent=2))
