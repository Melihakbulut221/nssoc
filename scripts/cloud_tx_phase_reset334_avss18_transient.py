#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh current-model portable34ns source wrapper; no transient until exact reviewed activation."""
import argparse,copy,hashlib,json,os,subprocess,sys
from pathlib import Path
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-avss18-transient-methods.json'
ORIGINAL='scripts/cloud_tx_phase_reset334_transient.py'
ORIGINAL_SHA='db0108b0b553d24d1ce8d4813806f41821bbf607053538a2ebe59127629eb0f0'
WORKFLOW='.github/workflows/tx-phase-reset334-avss18-transient-cloud.yml'
EDITS=[{'before': 'import tx_phase_reset334_transient_support as review', 'after': 'from tx_phase_reset334_avss18_transient_adapter import session\nreview=session()', 'count': 1}, {'before': 'tx-phase-reset334-transient-native-', 'after': 'tx-phase-reset334-avss18-transient-native-', 'count': 4}, {'before': 'codex/tx-clock-phase-parent', 'after': 'codex/phase318-saved-capture-diagnosis', 'count': 2}, {'before': 'tx-phase-reset334-transient-cloud.yml', 'after': 'tx-phase-reset334-avss18-transient-cloud.yml', 'count': 2}, {'before': '.reset334-portable-stage-', 'after': '.reset334-avss18-portable-stage-', 'count': 1}, {'before': 'cloud-tx-phase-reset334-prepared-', 'after': 'cloud-tx-phase-reset334-avss18-prepared-', 'count': 1}, {'before': "        r['original_parent_TX_rejection']=proof['original_parent_TX_rejection']", 'after': "        r['original_parent_TX_rejection']=proof['original_parent_TX_rejection']\n        r.update(original17_HBT_rejection=proof['original17_HBT_rejection'],current_RC_model_hashes=proof['current_models'],old_R_rescaled=False,geometry_generation_executed=False,new_extraction_performed=False)", 'count': 1}, {'before': "                a=next(a for a in rel['assets']if a['name'].endswith(suffix))", 'after': "                expected=spec['group']+'-'+str(spec['run'])+'-1'+suffix\n                matches=[a for a in rel['assets']if a['name']==expected];assert len(matches)==1\n                a=matches[0]", 'count': 1}]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def group(stage,case):
    assert stage in ('initial','cross')and case=='p-initial-high'
    return 'tx-phase-reset334-avss18-transient-native-'+stage+'-'+case

def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert m['segment_seconds']==13200 and m['initial_case']=='p-initial-high'
    assert m['original_first_fall_limit_s']==62.5e-12 and m['minimum_signed_margin_v']==.1
    assert m['native_transient_authorized']is m['simulation_authorized']
    for key in ('geometry_generation_authorized','extraction_authorized','other_cases_authorized'):assert m[key]is False
    return m

def completed_controls(m):
    c=m['completed_source_controls'];assert isinstance(c,dict)
    for p,h in c['proof_files'].items():assert m['protected'][p]==h and sha(ROOT/p)==h
    tested=json.loads((ROOT/c['tested_method_path']).read_bytes())
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    normalized=copy.deepcopy(m)
    normalized.update(native_transient_authorized=False,simulation_authorized=False,native_continuation_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    r=json.loads((ROOT/c['result_path']).read_bytes());assert r['status']=='PASS_CURRENT_AVSS18_PORTABLE_SOURCE_CONTROLS_ONLY'
    run=release.api('actions/runs/'+str(c['run']));job=release.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']==WORKFLOW and run['head_branch']=='codex/phase318-saved-capture-diagnosis'and job['name']=='source-controls'
    log=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/Melihakbulut221/nssoc/actions/jobs/'+str(c['job'])+'/logs'])
    assert log==(ROOT/c['log_path']).read_bytes()
    return dict(run=c['run'],job=c['job'],head=c['head'],all_tested_source_pins_preserved=True,log_sha256=hashlib.sha256(log).hexdigest())

def preflight(stage,case):
    m=methods();assert m['native_transient_authorized']is True
    assert os.environ.get('ImageOS')=='ubuntu24'
    if stage=='cross':assert m['native_continuation_authorized']is True
    name=group(stage,case);proof=completed_controls(m);waiter.wait(name,os.environ)
    tag,head=release.context(name,os.environ)
    result=release.validate_release(release.api('releases/tags/'+tag),release.api('git/ref/tags/'+tag),tag,head)
    assert not result['existing_assets'];result['completed_controls']=proof
    return result

def derived_program(text=None):
    if text is None:text=(ROOT/ORIGINAL).read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==ORIGINAL_SHA
    changed=text
    for e in EDITS:
        assert changed.count(e['before'])==e['count'];changed=changed.replace(e['before'],e['after'])
    reversed_text=changed
    for e in reversed(EDITS):
        assert reversed_text.count(e['after'])==e['count'];reversed_text=reversed_text.replace(e['after'],e['before'])
    assert reversed_text==text
    return changed,dict(original_sha256=ORIGINAL_SHA,generated_sha256=hashlib.sha256(changed.encode()).hexdigest(),
      literal_edits=EDITS,reversed_byte_exact=True,original_Docker_CRIU_13200s_lifecycle_preserved=True)

def program_namespace():
    text,proof=derived_program()
    ns=dict(__name__='current_AVSS18_portable_lifecycle',__file__=str(Path(__file__)))
    exec(compile(text,'<current-AVSS18-portable-lifecycle>','exec'),ns)
    return ns,proof

def main(stage,case):
    pre=preflight(stage,case);ns,derivation=program_namespace();old=sys.argv
    try:
        sys.argv=[str(Path(__file__)),'--stage',stage,'--case',case]
        ns['main']()
    finally:
        sys.argv=old
        result=ROOT/('cloud-'+group(stage,case))/'result.json'
        if result.is_file():
            r=json.loads(result.read_bytes())
            r.update(current_source_release_prerequisite=pre,current_lifecycle_derivation=derivation,
              scope='Only three current AVSS18 RC macros under unchanged external fixture; old failed17 HBT screen retained; no all31/PLL/fullPHY acceptance.')
            result.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--preflight',action='store_true')
    p.add_argument('--stage',choices=('initial','cross'),default='initial');p.add_argument('--case',default='p-initial-high')
    args=p.parse_args()
    assert not(args.controls and args.preflight)
    if args.controls:
        assert methods()['source_controls_authorized']is True
        from check_tx_phase_reset334_avss18_transient import controls
        print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    elif args.preflight:print(json.dumps(preflight(args.stage,args.case),indent=2,allow_nan=False))
    else:main(args.stage,args.case)
