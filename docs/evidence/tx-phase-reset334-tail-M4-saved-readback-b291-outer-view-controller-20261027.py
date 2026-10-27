#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the completed tail-M4 capture with unchanged original timing gates; never run an engine."""
import argparse,copy,hashlib,json,os,shutil,subprocess,traceback
from pathlib import Path
import tx_phase_reset334_tail_m4_saved_diagnosis as observer
import tx_phase_reset334_tail_m4_transient_adapter as current
import cloud_tx_phase_reset334_saved_capture as prior
import cloud_tx_normal_saved_capture as transport
import ensure_cloud_tested_source_release as release
import tx_phase_reset334_tail_m4_saved_resources as resources
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/tx-phase-reset334-tail-m4-saved-capture-methods.json'
GROUP='tx-phase-reset334-tail-m4-saved-capture'
OUT=ROOT/('cloud-'+GROUP)
PREFIX='docs/evidence/tx-phase-reset334-tail-M4-transient-native-initial-terminal-20261027'
SOURCE=dict(run=40567765771,job=122414584974,source='2071d818cce135a16f378ba22af0186df8ce80a7',
 branch='codex/phase318-saved-capture-diagnosis',conclusion='failure',
 workflow='.github/workflows/tx-phase-reset334-tail-m4-transient-cloud.yml',
 release_id=425882934,tag='cloud-results-40567765771-1-tx-phase-reset334-tail-m4-transient-native-initial-p-initial-high',
 part_asset_ids=[682722333,682723770,682725442,682727490])
SUMMARY_SHA='d0ebfc842547a9439f6f1c5125bb34436613d2aed384abe5fe0c23ff4fe2cc0c'
PARTS_SHA='7ac3fd71ebb91e21a1b08d39b874ec5c6e72052d353f376f37e23bf0e7196f3e'
RAW_SHA='c96c2f3255ebf01f8faa387c339edcce4769f2bb170886ea06320bf3986d52bc'
NATIVE_SHA='7fa2fc332ab24b990d013f27d34f28cf04e0390e45a2c14bf41448a718426b96'
CONTROLLER_SHA='bdcb6cf1269683926c85fbf90a23cee27beb10355e54ab69dd50281322ef4224'
write=resources.write
sha=transport.sha
encode=current.encode
digest=current.digest

def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    for k in ('native_simulation_authorized','native_extraction_authorized','geometry_generation_authorized','continuation_authorized'):
        assert m[k]is False
    assert m['original_first_fall_limit_s']==62.5e-12 and m['minimum_signed_margin_v']==.1
    authorization(m)
    return m


def authorization(m):
    flags=('source_controls_authorized','readback_authorized','native_simulation_authorized',
      'native_extraction_authorized','geometry_generation_authorized','continuation_authorized')
    assert all(type(m[k])is bool for k in flags)
    assert all(m[k]is False for k in flags[2:])
    assert not m['readback_authorized']or m['source_controls_authorized']
    assert (m['completed_source_controls']is not None)==m['readback_authorized']
    return True


def completed_controls(m):
    c=m['completed_source_controls'];assert isinstance(c,dict)
    for p,h in c['proof_files'].items():assert m['protected'][p]==h and sha(ROOT/p)==h
    tested=json.loads((ROOT/c['tested_method_path']).read_bytes())
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    normalized=copy.deepcopy(m);normalized.update(readback_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    record=json.loads((ROOT/c['result_path']).read_bytes())
    assert record['status']=='PASS_CURRENT_TAIL_M4_SAVED_CAPTURE_SOURCE_CONTROLS_ONLY'
    run=release.api('actions/runs/'+str(c['run']));job=release.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-saved-capture-cloud.yml'
    assert run['head_branch']==SOURCE['branch']and job['name']=='source-controls'
    log=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+release.REPO+'/actions/jobs/'+str(c['job'])+'/logs'])
    assert log==(ROOT/c['log_path']).read_bytes()
    return dict(run=c['run'],job=c['job'],head=c['head'],exact_tested_metadata_normalization=True)

def validate_result(r):
    assert r['run_id']==SOURCE['run']and r['source_head']==SOURCE['source']and r['controller_sha256']==CONTROLLER_SHA
    assert r['status']=='REJECTED_PHYSICAL334_THREE_MODEL_ORIGINAL_LOADED_GATES'
    assert r['stage']=='initial'and r['case']=='p-initial-high'and r['full_capture']is True
    assert r['native_process_saved']is False and r['native_exit_code']==0 and r['sources_unchanged']is True
    assert r['electrical_screen_passed']is False and r['full_PHY_accepted']is False
    assert r['continuation']==dict(run=SOURCE['run'],attempt=1,
      group='tx-phase-reset334-tail-m4-transient-native-initial-p-initial-high',source_head=SOURCE['source'],
      controller_sha256=CONTROLLER_SHA,case='p-initial-high',native_process_saved=False,next_phase='review_complete_capture')
    q=r['review'];assert q['passed']is False and q['errors']==q['diagnostics']==[]
    h=q['measurement']['hbt_safety'];assert len(h)==318 and {n for n,v in h.items()if not v['passed']}==set()
    cap=q['capture'];assert cap['raw_sha256']==r['outputs']['work/wave.raw']==RAW_SHA
    assert cap['header_rows']==114525 and cap['columns']==4727 and cap['start_s']==0 and cap['end_s']==34e-9
    assert len(r['outputs'])==30
    assert r['current_RC_model_hashes']==current.admission.MODELS
    assert r['original17_HBT_rejection']==current.admission.snapshot()[1]['original17_HBT_rejection']
    assert r['preparation_source']['outer_zero_OP_summary_sha256']==current.admission.SOURCE['summary']
    assert r['preparation_source']['summary_sha256']==current.admission.PREPARATION_SHA
    for k in ('old_R_rescaled','geometry_generation_executed','new_extraction_performed'):assert r[k]is False
    assert r['run_attempt']==1 and r['wrapper_terminal_complete']is True
    assert r['wrapper_finalization_errors']==r['inner_terminal_inventory_errors']==[]
    assert r['inner_terminal_actions_complete']is True
    assert r['native_lifecycle_result_sha256']==NATIVE_SHA and r['native_lifecycle_result_bytes']==2315269
    assert r['native_lifecycle_result_raw_path']=='native-lifecycle-result.json'
    assert r['outputs']['native-lifecycle-result.json']==NATIVE_SHA
    assert q['measurement']['all318_HBT_safety_passed']is True
    assert q['measurement']['all_three_fixed_phase_screens_passed']is False
    assert q['gate']['checks']['all318_numeric_safety']is True and q['gate']['passed']is False
    for row in h.values():
        assert row['passed']is True
        assert row['min_post_vce_v']>=.4 and row['max_whole_abs_vce_v']<=1.6
        assert row['max_whole_abs_vbe_v']<=1. and row['max_whole_abs_ic_per_emitter_a']<=.003
    original_OP=current.admission.snapshot()[1]
    assert r['prior_four_tail_rejection']==original_OP['prior_four_tail_rejection']
    assert r['original_parent_TX_rejection']==original_OP['original_parent_TX_rejection']
    assert r['preparation_source']['native_zero_OP_summary_sha256']==current.admission.ASSETS['native']['sha256']
    assert r['preparation_source']['all3286_files_authenticated']is True
    assert r['preparation_source']['complete_outer_files']==3286
    assert r['preparation_source']['complete_consumed_native_files']==3271
    assert r['preparation_source']['OP_only_deck_used_as_transient']is False
    return True

def snapshot():
    raw=(ROOT/(PREFIX+'.summary.json')).read_bytes();assert len(raw)==2321446 and digest(raw)==SUMMARY_SHA
    part=(ROOT/(PREFIX+'.parts.json')).read_bytes();assert digest(part)==PARTS_SHA
    r=json.loads(raw);validate_result(r);m=json.loads(part)
    assert m['bytes']==4051609570 and m['sha256']=='faa2bfe168249d6ca1b2b8ff0f70030925f5699b5983078a0f68519b15b35372'
    assert m['source_directory']=='cloud-tx-phase-reset334-tail-m4-transient-native-initial-p-initial-high'
    assert len(m['parts'])==4
    native=(ROOT/(PREFIX+'.native-lifecycle-result.json')).read_bytes()
    assert len(native)==2315269 and digest(native)==NATIVE_SHA
    n=json.loads(native);assert len(n['outputs'])==28
    assert all(r['outputs'][p]==h for p,h in n['outputs'].items())
    assert all(r[k]==n[k]for k in n if k!='outputs')
    return raw,r,m

def metadata(run,job,info,ref,manifest):
    identity=transport.source_identity(run,info,ref,SOURCE)
    parts=transport.asset_plan(info,SOURCE,manifest)
    assert job['id']==SOURCE['job']and job['run_id']==SOURCE['run']and job['head_sha']==SOURCE['source']
    assert job['run_attempt']==1 and job['status']=='completed'and job['conclusion']=='failure'
    assets={a['name']:a for a in info['assets']};assert len(assets)==len(info['assets'])
    for asset_id,suffix,h,size in [(682721590,'summary.json',SUMMARY_SHA,2321446),(682721712,'parts.json',PARTS_SHA,1749)]:
        name='tx-phase-reset334-tail-m4-transient-native-initial-p-initial-high-40567765771-1.'+suffix
        a=assets[name];assert a['id']==asset_id and a['size']==size and a['digest']=='sha256:'+h and a['state']=='uploaded'
    return dict(identity=identity,job=job,parts=parts)

def restore_capture(work,r,manifest):
    run=transport.api('actions/runs/'+str(SOURCE['run']));job=transport.api('actions/jobs/'+str(SOURCE['job']))
    info=transport.api('releases/'+str(SOURCE['release_id']));ref=transport.api('git/ref/tags/'+SOURCE['tag'])
    proof=metadata(run,job,info,ref,manifest)
    for asset_id,suffix in [(682721590,'summary.json'),(682721712,'parts.json')]:
        b=subprocess.check_output(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream',
          transport.REPO+'releases/assets/'+str(asset_id)])
        assert b==(ROOT/(PREFIX+'.'+suffix)).read_bytes()
    parts=work/'native-parts';parts.mkdir()
    for row in proof['parts']:transport.fetch_asset(row,parts/row['name'])
    expected=dict(r['outputs']);expected['result.json']=SUMMARY_SHA
    selected={'work/'+n for n in ('wave.raw','bench.cir','contract.json','native.log','op.raw')}
    audit=transport.audit_complete(manifest,parts,work/'native',expected,selected)
    assert audit['publication_addons']=={} and len(audit['all_original_files'])==31
    return work/'native/work',dict(metadata=proof,full_archive=audit,all31_files_authenticated=True)

def reconstruct(oproot,op,result):
    inputs=current.read_inputs(oproot,op)
    binding_raw,prep_raw,payloads,models,model_paths,init,runtime,cases=inputs
    controls=current.actual_input_controls(oproot,op,inputs)
    assert len(controls['actual_source_refusals'])==18 and len(controls['original_path_controls']['negative_controls'])==32
    scalar=(oproot/'fresh-preparation/original-PLL-observer.summary.json').read_bytes()
    original_model_paths={p:Path('/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-phase-reset334-tail-m4-loaded/native/fresh-preparation/qualified-binding/qualified-rc')/p/'composition/reset334-wire.spice'for p in ('p','n')}
    deck,c=runtime.bench.prepare(binding_raw,payloads,models,scalar,'p',True,original_model_paths,
      '/fixture/sg13g2-ngspice-models','/fixture/r3_cmc.osdi')
    assert deck==cases['p-initial-high'][0]and c==cases['p-initial-high'][1]
    path=result['preparation_source']['path_binding'];rows=deck.splitlines(keepends=True)
    assert len(path['six_path_cards'])==6 and path['byte_exact_reversal']is True
    for e in path['six_path_cards']:
        assert rows[e['line']]==e['old'];rows[e['line']]=e['new']
    rewritten=''.join(rows);assert digest(rewritten)==path['runtime_base_sha256']
    a=init.adapters();full=a.initialized_deck(rewritten,c)
    assert full.replace(a.flag_block(c,True),'')==rewritten
    assert digest(full)==result['outputs']['work/bench.cir']and digest(encode(c))==result['outputs']['work/contract.json']
    screen=current.loaded.isolated(current.loaded.old_screen,dict(initialization=init,paths=runtime))
    assert screen.review_capture.__code__ is current.frozen.review_capture.__code__
    # Reuse the actual 24 contract/deck/input mutations with only its bench globals rebound.
    import types
    ns=dict(vars(prior),bench=runtime.bench)
    ns['validate_actual']=prior.validate_actual
    actual=types.FunctionType(prior.actual_controls.__code__,ns)(c,full,c,full,
      dict(binding_summary=binding_raw,payloads=payloads,models=models,scalar=scalar))
    assert len(actual['rejected'])==24
    _,positive=runtime.bench.qualified_inputs(binding_raw,payloads,models)
    return c,full,screen,positive,dict(current18_and32=controls,original24=actual,
      binding_summary_sha256=digest(binding_raw),preparation_sha256=digest(prep_raw),
      scalar_sha256=digest(scalar),model_hashes={p:digest(x)for p,x in models.items()},
      all_original_numerical_functions_unchanged=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--readback',action='store_true');a=p.parse_args()
    assert a.controls!=a.readback;m=methods()
    if a.controls:
        assert m['source_controls_authorized']is True
        from check_tx_phase_reset334_tail_m4_saved_capture import controls
        print(json.dumps(controls(),indent=2,allow_nan=False));return
    assert m['readback_authorized']is True
    control_proof=completed_controls(m)
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',run_id=int(os.environ['GITHUB_RUN_ID']),source_head=os.environ['GITHUB_SHA'],
      original_electrical_rejection_preserved=True,accepted=False,new_simulation=False,native_process_resumed=False,
      full_PHY_accepted=False,completed_source_controls=control_proof)
    def save():write(OUT/'result.json',result)
    work=Path(os.environ['RUNNER_TEMP'])/'tx-current-tail-m4-saved-capture'
    try:
        save()
        result['publication_preflight']=transport.precreated(GROUP);save()
        assert shutil.disk_usage(work.parent).free>=16*1024**3
        work.mkdir(exist_ok=False)
        raw,original,manifest=snapshot()
        case,proof=restore_capture(work,original,manifest);result['native_archive']=proof;save()
        opraw,op,opproof=current.admission.restore(work/'qualified-current-OP')
        write(OUT/'current-OP-restoration.json',opproof)
        input_resources=resources.input_budget({name:(case/name).stat().st_size for name in ('wave.raw','contract.json','bench.cir','native.log','op.raw')},
          sum(row['bytes']for row in opproof['inventory']['files'].values()),opproof['transport']['bytes'])
        write(OUT/'restored-input-resource-bounds.json',input_resources);result['input_resource_bounds']=input_resources;save()
        expected,deck,screen,bindings,controls=reconstruct(work/'qualified-current-OP'/'native',op,original)
        actual=json.loads((case/'contract.json').read_bytes());actual_deck=(case/'bench.cir').read_text()
        controls['native_match']=prior.validate_actual(actual,actual_deck,expected,deck)
        controls['source_topology']=observer.actual_topology_controls(actual,bindings)
        write(OUT/'current-restored-input-controls.json',controls);result['actual_input_controls']=controls;save()
        write(OUT/'consumed-input-binding.json',dict(contract_sha256=sha(case/'contract.json'),
          native_deck_sha256=sha(case/'bench.cir'),current_models=current.admission.MODELS,
          current_native_OP_summary_sha256=digest(opraw),current_outer_OP_summary_sha256=current.admission.SOURCE['summary'],
          current_preparation_sha256=current.admission.PREPARATION_SHA,
          original_source_and_runtime_cards_equal=True,no_simulation=True,no_continuation=True))
        # Capture bytes stay under RUNNER_TEMP; only bounded derived JSON enters OUT.
        diagnosis=observer.observe(case,original,screen,bindings,lambda n,v:write(OUT/n,v))
        full=write(OUT/'complete-native-row-diagnosis.json',diagnosis)
        compact=dict(status=diagnosis['status'],full_witness=full,frames=len(diagnosis['frames']),
          failed_hbt_count=diagnosis['original_failed_HBT_count'],current_capture_sha256=RAW_SHA,
          failed_hbt_same_row_extrema=diagnosis['failed_hbt_same_row_extrema'],
          original17_current_minimum_frames=diagnosis['original17_current_minimum_frames'],
          first_fall_windows=diagnosis['first_fall_windows'],source_bound_tail_topology=diagnosis['source_bound_tail_topology'],
          native_pair_nodes=diagnosis['native_pair_nodes'],native_pair_crossings=diagnosis['native_pair_crossings'],
          pair_extrema_both_signs=diagnosis['pair_extrema_both_signs'],requested_fixed_samples=diagnosis['requested_fixed_samples'],
          frame_content_pointer='/frames',native_crossings_are_brackets_not_fitted_times=True,
          all_global_crossings_have_complete_state_frames=False,
          full_observations_published_as_direct_JSON_asset=True,full_original_review_replays=1,
          original_rejection_reproduced=True,causal_conclusion=False,circuit_edit_justified=False)
        index_asset=write(OUT/'diagnostic-index.json',compact)
        result.update(status='PASS_CURRENT_TAIL_M4_SAVED_DIAGNOSIS_ORIGINAL_ELECTRICAL_REJECTION_REMAINS',
          diagnostic_index_asset=index_asset,full_original_review_replays=1,source_capture_sha256=RAW_SHA)
    except BaseException as error:
        result.update(status='FAIL_CURRENT_TAIL_M4_SAVED_CAPTURE_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc())
        if isinstance(error,resources.ResourceLimit):result['resource_refusal']=error.record
        raise
    finally:
        errors=[];files={}
        for path in sorted(OUT.rglob('*')):
            if path.name=='result.json':continue
            try:
                assert not path.is_symlink(),str(path)
                if path.is_file():files[str(path.relative_to(OUT))]=sha(path)
            except BaseException as failure:
                errors.append(dict(action='inventory',path=str(path.relative_to(OUT)),error=repr(failure)))
        try:methods()
        except BaseException as failure:errors.append(dict(action='protected_sources',error=repr(failure)))
        result['outputs']=files;result['terminal_errors']=errors
        if errors:
            result['status']='FAIL_CURRENT_TAIL_M4_SAVED_CAPTURE_DIAGNOSIS'
            result['complete_diagnosis']=False
        final=resources.final_result(OUT/'result.json',result);raw=(OUT/'result.json').read_bytes()
        print('RESULT_SHA256',digest(raw));print('RESULT_BYTES',len(raw))
        if len(raw)<=8*1024**2:print(raw.decode())
        else:print('FULL_RESULT_PRESERVED_FOR_DIRECT_PUBLICATION')
        if final['terminal_failure_envelope']:raise RuntimeError('Complete terminal failure envelope preserved; diagnosis incomplete')
        if errors:raise RuntimeError('Terminal source or inventory validation failed; diagnosis incomplete')
if __name__=='__main__':main()
