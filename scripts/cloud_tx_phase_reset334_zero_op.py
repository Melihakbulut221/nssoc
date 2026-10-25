#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh318-HBT zero-source OP only; no DUT transient or old waveform reuse."""
import argparse,json,os,subprocess,time,traceback
from pathlib import Path
import tx_phase_reset334_zero_op_runtime as path_binding
import check_tx_phase_reset334_zero_op_runtime as checker
import tx_phase_reset334_loaded_native_adapter as initialization
import cloud_tx_phase_reset334_loaded_preparation as preparation
import cloud_tx_phase_async_preset_intrinsic as native
import compare_cloud_routed_endpoints as reports
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-phase-reset334-zero-op'
METHOD='scripts/tx-phase-reset334-zero-op-methods.json'
GROUP='tx-phase-reset334-zero-op'
def sha(p):return initialization.digest(Path(p).read_bytes())
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def methods():
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert m['native_transient_authorized']is False
    return m
def source_controls():
    import check_tx_phase_reset334_loaded_native_adapter as old_checker
    m=methods();a=old_checker.controls();b=checker.controls();p=publication.controls();q=prerequisite_controls(m['qualified_adapter'])
    assert len(a['negative_controls'])==30 and len(b['negative_controls'])==12 and len(p['rejected'])==17
    return dict(status='PASS_FROZEN318_AND_NEW_ZERO_OP_SOURCE_CONTROLS_ONLY',
      protected_files=len(m['protected']),initialization_controls=a,zero_OP_gate_controls=b,
      publication_controls=p,prerequisite_controls=q,native_simulator_invoked=False,transient_executed=False)
def validate_prerequisite(d,run,spec):
    assert set(spec)=={'run','head','summary_asset','summary_sha256'}
    assert type(spec['run'])is int and spec['run']>0 and len(spec['head'])==40
    assert run['id']==spec['run']and run['head_sha']==spec['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert d['source_head']==spec['head']and d['run_id']==spec['run']
    assert d['status']=='PASS_FOUR_EXACT318_DECK_ADAPTERS_NO_NATIVE_OR_ELECTRICAL_ACCEPTANCE'
    assert d['validation_errors']==[]and d['sources_unchanged']
    assert all(d[k]is False for k in ('native_simulator_executed','runtime_installed','zero_source_OP_executed','transient_executed','electrical_accepted','all31_clock_tree_accepted','PLL_connected','full_PHY_accepted'))
    assert set(d['cases'])=={s+'-initial-'+h for s in ('p','n')for h in ('high','low')}
    for c in d['cases'].values():
        assert c['uniform_native_targets']==318 and c['all318_target_markers_exercised']
        assert len(c['actual_HBT_names'])==len(set(c['actual_HBT_names']))==318
        assert c['marker_log_is_synthetic_not_native_readback']
        assert len(c['negative_controls'])==3 and not c['native_executed']and not c['electrical_accepted']
    return True
def prerequisite(spec):
    run=preparation.api('actions/runs/'+str(spec['run']))
    raw=preparation.asset(spec['summary_asset'],spec['summary_sha256']);d=json.loads(raw)
    validate_prerequisite(d,run,spec)
    return raw,d
def prerequisite_controls(spec):
    import copy
    raw=(ROOT/'docs/evidence/tx-phase-reset334-loaded-native-adapter-full-result-20261025.json').read_bytes()
    assert initialization.digest(raw)==spec['summary_sha256']
    d=json.loads(raw)
    receipt=json.loads((ROOT/'docs/evidence/tx-phase-reset334-loaded-native-adapter-pass-20261025.json').read_text())
    run=receipt['run'];assert validate_prerequisite(d,run,spec)
    first=lambda x:next(iter(x['cases'].values()))
    mutations=[
      ('run-id',lambda x,r:r.update(id=1)),('run-source',lambda x,r:r.update(head_sha='0'*40)),
      ('run-failure',lambda x,r:r.update(conclusion='failure')),('summary-run',lambda x,r:x.update(run_id=1)),
      ('summary-source',lambda x,r:x.update(source_head='0'*40)),('wrong-status',lambda x,r:x.update(status='PASS')),
      ('prior-validation-error',lambda x,r:x.update(validation_errors=['retained'])),
      ('changed-sources',lambda x,r:x.update(sources_unchanged=False)),
      ('missing-case',lambda x,r:x['cases'].pop(next(iter(x['cases'])))),
      ('old106-target-count',lambda x,r:first(x).update(uniform_native_targets=106)),
      ('missing-actual-name',lambda x,r:first(x)['actual_HBT_names'].pop()),
      ('marker-not-synthetic',lambda x,r:first(x).update(marker_log_is_synthetic_not_native_readback=False)),
      ('missing-target-fault',lambda x,r:first(x)['negative_controls'].pop()),
      ('native-executed-claim',lambda x,r:x.update(native_simulator_executed=True)),
      ('electrical-acceptance-claim',lambda x,r:x.update(electrical_accepted=True))]
    bad=[]
    for name,edit in mutations:
        x=copy.deepcopy(d);r=copy.deepcopy(run);edit(x,r)
        bad.append(checker.reject(name,lambda:validate_prerequisite(x,r,spec)))
    assert len(bad)==15
    return dict(status='PASS_EXACT_COMPLETED318_PREPARATION_PREREQUISITE_CONTROLS',negative_controls=bad,
      actual_summary_sha256=spec['summary_sha256'],run=spec['run'],native_executed=False)

def main(prepare_only=False):
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    m=methods()
    assert m['prepared_path_controls_authorized'if prepare_only else'native_zero_op_authorized']is True
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING_PREPARED_PATHS_ONLY'if prepare_only else'RUNNING_FRESH318_ZERO_SOURCE_OP_ONLY',source_head=os.environ['GITHUB_SHA'],
      run_id=int(os.environ['GITHUB_RUN_ID']),validation_errors=[],cases={},
      native_simulator_invoked=False,runtime_installed=False,transient_executed=False,electrical_phase_accepted=False,all31_clock_tree_accepted=False,
      PLL_connected=False,full_PHY_accepted=False)
    def save():write(OUT/'result.json',r)
    try:
        tag,head=publication.context(GROUP,os.environ)
        r['release_prerequisite']=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
        prior_raw,prior=prerequisite(m['qualified_adapter'])
        (OUT/'qualified-adapter.summary.json').write_bytes(prior_raw)
        spec=initialization.PREPARATION
        old=preparation.api('actions/runs/'+str(spec['run']))
        assert old['head_sha']==spec['head']and old['run_attempt']==1 and old['status']=='completed'and old['conclusion']=='success'
        summary_raw=preparation.asset(spec['summary_asset'],spec['summary_sha256'])
        summary=json.loads(summary_raw);(OUT/'preparation.summary.json').write_bytes(summary_raw)
        labels=[s+'-initial-'+h for s in ('p','n')for h in ('high','low')]
        selected=['cases/'+label+'/'+name for label in labels for name in ('bench.cir','contract.json')]
        selected+=['qualified-binding/qualified-rc/'+s+'/composition/reset334-wire.spice'for s in ('p','n')]
        restored,restore_proof=reports.restore_report('tx-phase-reset334-loaded-preparation',spec['run'],
          spec['summary_sha256'],spec['parts_sha256'],OUT/'prepared',selected)
        assert restored==summary;r['prepared_archive']=restore_proof
        cases={label:((OUT/'prepared/cases'/label/'bench.cir').read_text(),
          json.loads((OUT/'prepared/cases'/label/'contract.json').read_bytes()))for label in labels}
        model_paths={s:OUT/'prepared/qualified-binding/qualified-rc'/s/'composition/reset334-wire.spice'for s in ('p','n')}
        models={s:p.read_text()for s,p in model_paths.items()}
        r['path_controls']=checker.positive_paths(cases,summary_raw,models)
        assert len(r['path_controls']['negative_controls'])==32
        a=initialization.adapters()
        for label,(deck,contract)in cases.items():
            assert prior['cases'][label]['actual_HBT_names']==a.targets(contract)
            assert prior['cases'][label]['base_deck_sha256']==initialization.digest(deck)
            assert prior['cases'][label]['initialized_deck_sha256']==initialization.digest(a.initialized_deck(deck,contract))
        r['original_parent_TX_rejection']=summary['original_parent_TX_rejection']
        assert not r['original_parent_TX_rejection']['electrical_screen_passed']
        if prepare_only:
            assert methods()==m;r['sources_unchanged']=True
            r['status']='PASS_FOUR_EXACT_RUNTIME_PATH_BINDINGS_NO_NATIVE_ZERO_OP'
            r['zero_source_OP_executed']=False;save();return
        native.OUT=OUT;engine,libraries,engine_proof=native.restore();r['runtime_and_models']=engine_proof
        r['runtime_installed']=True
        r['native_simulator_invoked']=False;save()
        for label,(prepared_deck,c)in cases.items():
            case=OUT/label;case.mkdir()
            row=dict(complete=False,errors=[]);r['cases'][label]=row
            try:
                deck,proof=path_binding.runtime_deck(label,prepared_deck,c,summary_raw,models,model_paths,
                  libraries/'models',libraries/'r3_cmc.osdi')
                (case/'bench.cir').write_text(deck);(case/'contract.json').write_text(json.dumps(c,indent=2,allow_nan=False)+'\n')
                (case/'spinit').write_text('set num_threads=1\n')
                row.update(path_binding=proof,deck_sha256=sha(case/'bench.cir'),
                  contract_sha256=sha(case/'contract.json'),expected_HBT_count=318,expected_saved_vectors=4726)
                env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')}
                env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',GLIBC_TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM')
                start=time.monotonic();save()
                try:
                    with (case/'native.log').open('w')as log:
                        proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
                    row['returncode']=proc.returncode;r['native_simulator_invoked']=True
                except subprocess.TimeoutExpired as error:
                    r['native_simulator_invoked']=True;row['returncode']=None;row['errors'].append(dict(stage='native_OP_timeout',error=repr(error)))
                row['elapsed_s']=time.monotonic()-start
                log=(case/'native.log').read_text(errors='replace')
                row.update(native_log_sha256=sha(case/'native.log'),native_log_tail=log[-16384:])
                for key,fn in [
                  ('solver',lambda:native.verify_solver_options(log,path_binding.bench.original.PROFILE)),
                  ('diagnostics',lambda:native.native_diagnostics(log,path_binding.bench.original.PROFILE)),
                  ('flags',lambda:a.flags(log,c,True)),
                  ('zero_source_op',lambda:native.zero_op(case/'op.raw',c['vectors']))]:
                    try:row[key]=fn()
                    except BaseException as error:row['errors'].append(dict(stage=key,error=repr(error)))
                row['wave_raw_exists']=(case/'wave.raw').exists()
                assert sha(case/'bench.cir')==row['deck_sha256']and sha(case/'contract.json')==row['contract_sha256']
                assert native.sha(engine)==native.ENGINE_SHA
                for sign,p in model_paths.items():assert sha(p)==path_binding.bench.binding.MODELS[sign]
                for name,meta in engine_proof['model_manifest']['files'].items():
                    p=libraries/name;assert p.is_file()and p.stat().st_size==meta['bytes']and sha(p)==meta['sha256']
                row.update(source_and_runtime_unchanged=True,complete=True)
            except BaseException as error:row['errors'].append(dict(stage='native_or_source',error=repr(error),traceback=traceback.format_exc()))
            row['zero_OP_gate']=path_binding.gate(row);row['passed']=row['complete']and row['zero_OP_gate']['passed']
            save();print(json.dumps(dict(case=label,passed=row['passed'],gate=row['zero_OP_gate'],errors=row['errors'])),flush=True)
        assert methods()==m;r['sources_unchanged']=True
        r['all_four_expanded_zero_OPs_passed']=len(r['cases'])==4 and all(c['passed']for c in r['cases'].values())
        r['original_parent_TX_rejection']=summary['original_parent_TX_rejection']
        assert not r['original_parent_TX_rejection']['electrical_screen_passed']
        r['status']='PASS_FOUR_FRESH318_ZERO_OPS_NOT_TRANSIENT_OR_PHASE_ACCEPTANCE'if r['all_four_expanded_zero_OPs_passed']else'REJECTED_FRESH318_ZERO_OP_PRESERVE_COMPLETE_EVIDENCE'
    except BaseException as error:
        r['status']='FAIL_FRESH318_ZERO_OP';r['validation_errors'].append(dict(error=repr(error),traceback=traceback.format_exc()));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
    assert r['all_four_expanded_zero_OPs_passed'],'Expanded zero-source OP rejected; original complete logs/states retained'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native-op',action='store_true');parser.add_argument('--source-controls',action='store_true');parser.add_argument('--prepared-controls',action='store_true')
    args=parser.parse_args();assert sum((args.native_op,args.source_controls,args.prepared_controls))==1
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.source_controls:print(json.dumps(source_controls(),indent=2,allow_nan=False))
    else:main(prepare_only=args.prepared_controls)
