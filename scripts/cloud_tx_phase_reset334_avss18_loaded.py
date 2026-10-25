#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current AVSS18 binding/preparation and fresh OFF zero-OP; transient remains disabled."""
import argparse,copy,hashlib,json,os,subprocess
from pathlib import Path
import ensure_cloud_tested_source_release as release
import wait_cloud_tested_source_release as waiter
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-avss18-loaded-methods.json'
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset334-avss18-loaded'
GROUP='tx-phase-reset334-avss18-loaded'
ORIGINAL='scripts/cloud_tx_phase_reset334_zero_op.py'
ORIGINAL_SHA='096f78daa2eca069eda8fb96624dac2cb7abf16f554dfa7459c680b2d6bb757e'
OLD="        prior_raw,prior=prerequisite(m['qualified_adapter'])\n        (OUT/'qualified-adapter.summary.json').write_bytes(prior_raw)\n        spec=initialization.PREPARATION\n        old=preparation.api('actions/runs/'+str(spec['run']))\n        assert old['head_sha']==spec['head']and old['run_attempt']==1 and old['status']=='completed'and old['conclusion']=='success'\n        summary_raw=preparation.asset(spec['summary_asset'],spec['summary_sha256'])\n        summary=json.loads(summary_raw);(OUT/'preparation.summary.json').write_bytes(summary_raw)\n        labels=[s+'-initial-'+h for s in ('p','n')for h in ('high','low')]\n        selected=['cases/'+label+'/'+name for label in labels for name in ('bench.cir','contract.json')]\n        selected+=['qualified-binding/qualified-rc/'+s+'/composition/reset334-wire.spice'for s in ('p','n')]\n        restored,restore_proof=reports.restore_report('tx-phase-reset334-loaded-preparation',spec['run'],\n          spec['summary_sha256'],spec['parts_sha256'],OUT/'prepared',selected)\n        assert restored==summary;r['prepared_archive']=restore_proof\n        cases={label:((OUT/'prepared/cases'/label/'bench.cir').read_text(),\n          json.loads((OUT/'prepared/cases'/label/'contract.json').read_bytes()))for label in labels}\n        model_paths={s:OUT/'prepared/qualified-binding/qualified-rc'/s/'composition/reset334-wire.spice'for s in ('p','n')}\n        models={s:p.read_text()for s,p in model_paths.items()}\n        r['path_controls']=checker.positive_paths(cases,summary_raw,models)\n        assert len(r['path_controls']['negative_controls'])==32\n        a=initialization.adapters()\n        for label,(deck,contract)in cases.items():\n            assert prior['cases'][label]['actual_HBT_names']==a.targets(contract)\n            assert prior['cases'][label]['base_deck_sha256']==initialization.digest(deck)\n            assert prior['cases'][label]['initialized_deck_sha256']==initialization.digest(a.initialized_deck(deck,contract))\n        r['original_parent_TX_rejection']=summary['original_parent_TX_rejection']\n        assert not r['original_parent_TX_rejection']['electrical_screen_passed']\n"
NEW="        cases,summary_raw,models,model_paths,current_proof=_current_inputs(OUT,r)\n        summary=json.loads(summary_raw)\n        r['path_controls']=current_proof['path_controls']\n        assert len(r['path_controls']['negative_controls'])==32\n        a=initialization.adapters()\n        r['original_parent_TX_rejection']=summary['original_parent_TX_rejection']\n        assert not r['original_parent_TX_rejection']['electrical_screen_passed']\n"

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    for k in ('native_transient_authorized','extraction_authorized','geometry_generation_authorized'):assert m[k]is False
    assert m['native_zero_op_authorized']is m['simulation_authorized']
    return m

def completed_controls(m):
    c=m['completed_source_controls'];assert isinstance(c,dict)
    for p,h in c['proof_files'].items():assert m['protected'][p]==h and sha(ROOT/p)==h
    tested=json.loads((ROOT/c['tested_method_path']).read_bytes())
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    normalized=copy.deepcopy(m)
    normalized.update(prepared_path_controls_authorized=False,native_zero_op_authorized=False,simulation_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    r=json.loads((ROOT/c['result_path']).read_bytes());assert r['status']=='PASS_CURRENT_AVSS18_LOADED_SOURCE_CONTROLS_ONLY'
    run=release.api('actions/runs/'+str(c['run']));job=release.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-avss18-loaded-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'and job['name']=='source-controls'
    log=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/Melihakbulut221/nssoc/actions/jobs/'+str(c['job'])+'/logs'])
    assert log==(ROOT/c['log_path']).read_bytes()
    return dict(run=c['run'],job=c['job'],head=c['head'],all_tested_source_pins_preserved=True,log_sha256=hashlib.sha256(log).hexdigest())

def preflight(mode):
    m=methods();assert mode in ('prepare','zero-op')
    assert m['prepared_path_controls_authorized'if mode=='prepare'else'native_zero_op_authorized']is True
    assert os.environ.get('ImageOS')=='ubuntu24'
    proof=completed_controls(m);waiter.wait(GROUP,os.environ)
    tag,head=release.context(GROUP,os.environ)
    result=release.validate_release(release.api('releases/tags/'+tag),release.api('git/ref/tags/'+tag),tag,head)
    assert not result['existing_assets'];result['completed_controls']=proof
    return result

def derived_program(text=None):
    if text is None:text=(ROOT/ORIGINAL).read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==ORIGINAL_SHA
    assert text.count(OLD)==1
    changed=text.replace(OLD,NEW);assert changed.count(NEW)==1 and changed.replace(NEW,OLD)==text
    return changed,dict(original_sha256=ORIGINAL_SHA,generated_sha256=hashlib.sha256(changed.encode()).hexdigest(),
      literal_edits=[dict(before=OLD,after=NEW,count=1)],reversed_byte_exact=True,
      original_runtime_restore_native_loop_solver_flags_zero_OP_and_gate_unchanged=True)

def program_namespace():
    # Import of the actual controller is exercised in hosted controls; no __main__ execution.
    from tx_phase_reset334_avss18_loaded_adapter import prepare
    text,proof=derived_program();ns=dict(__name__='current_AVSS18_zero_OP',__file__=str(ROOT/ORIGINAL))
    exec(compile(text,'<current-AVSS18-zero-OP>','exec'),ns)
    ns.update(OUT=OUT,GROUP=GROUP,METHOD=str(METHOD.relative_to(ROOT)),methods=methods)
    def current_inputs(out,result):
        cases,raw,models,paths,initialization,path_binding,screen,actual=prepare(out/'fresh-preparation')
        ns.update(initialization=initialization,path_binding=path_binding)
        result.update(current_AVSS18_preparation=actual,current_RC_model_hashes=dict(path_binding.bench.binding.MODELS),
          original17_HBT_rejection=actual['original17_HBT_rejection'],controller_derivation=proof,
          original_electrical_rejection_preserved=True,old_R_rescaled=False,geometry_generation_executed=False,new_extraction_performed=False)
        return cases,raw,models,paths,actual
    ns['_current_inputs']=current_inputs
    return ns,proof

def main(mode):
    pre=preflight(mode);OUT.parent.mkdir(parents=True,exist_ok=True)
    ns,proof=program_namespace()
    try:ns['main'](prepare_only=mode=='prepare')
    finally:
        if (OUT/'result.json').is_file():
            r=json.loads((OUT/'result.json').read_bytes());r['release_prerequisite_current_source']=pre
            r['current_controller_derivation']=proof
            (OUT/'result.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--controls',action='store_true');parser.add_argument('--preflight',choices=('prepare','zero-op'));parser.add_argument('--mode',choices=('prepare','zero-op'))
    args=parser.parse_args();assert sum((args.controls,bool(args.preflight),bool(args.mode)))==1
    if args.controls:
        from check_tx_phase_reset334_avss18_loaded import controls
        assert methods()['source_controls_authorized']is True
        print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    elif args.preflight:print(json.dumps(preflight(args.preflight),indent=2,allow_nan=False))
    else:main(args.mode)
