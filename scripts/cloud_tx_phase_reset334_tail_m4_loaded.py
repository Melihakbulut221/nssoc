#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Owned fresh four-case zero-OP on current M4 RC; no transient, extraction or geometry."""
import argparse,ast,copy,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import tx_phase_reset334_tail_m4_loaded_admission as admission
import tx_phase_reset334_tail_m4_loaded_adapter as adapter
import ensure_cloud_tested_source_release as guard
import wait_cloud_tested_source_release as waiter
import cdr_v59_tail_access_runtime as runtime
ROOT=admission.ROOT
METHOD=ROOT/'scripts/tx-phase-reset334-tail-m4-loaded-methods.json'
GROUP='tx-phase-reset334-tail-m4-loaded'
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset334-tail-m4-loaded'
STAGE=OUT/'native'
ORIGINAL='scripts/cloud_tx_phase_reset334_zero_op.py'
ORIGINAL_SHA='096f78daa2eca069eda8fb96624dac2cb7abf16f554dfa7459c680b2d6bb757e'
CONTEXT='scripts/cloud_tx_phase_reset334_avss18_loaded.py'
CONTEXT_SHA='a910d4a068e6a936034ec62b2ddec84d1c78ca7a686503c31592efa91368f62b'
GENERATED_SHA='804b944769b6ff44c2913a311e9de6f8dfe5dd4a633ea2d2eed9189784f6071b'
STATUS='PASS_TAIL_M4_FRESH_FOUR_OP_SOURCE_CONTROLS_NO_NATIVE'
PASS='PASS_FOUR_FRESH318_ZERO_OPS_NOT_TRANSIENT_OR_PHASE_ACCEPTANCE'
sha=admission.sha


def write(path,r):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=json.loads(METHOD.read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    for key in ('native_transient_authorized','extraction_authorized','geometry_generation_authorized','continuation_authorized'):
        assert m[key]is False,key
    for key in ('native_zero_op_authorized','simulation_authorized','native_execution_authorized','prepared_path_controls_authorized'):
        assert type(m[key])is bool,key
    assert m['native_zero_op_authorized']is m['simulation_authorized']is m['native_execution_authorized']
    assert m['prepared_path_controls_authorized']is m['native_zero_op_authorized']
    assert m['owned_process']==dict(seconds=18000,minimum_available_kib=2097152,maximum_group_rss_kib=10485760,output_limit_per_stream_bytes=16777216)
    return m


def completed_controls():
    m=methods();c=m['completed_source_controls'];assert isinstance(c,dict)
    tested_raw=(ROOT/c['tested_method_path']).read_bytes();tested=json.loads(tested_raw)
    assert set(m['protected'])==set(tested['protected'])|set(c['proof_files'])
    assert all(m['protected'][p]==h for p,h in tested['protected'].items())
    for p,h in c['proof_files'].items():assert m['protected'][p]==h==sha(ROOT/p)
    normalized=copy.deepcopy(m)
    normalized.update(prepared_path_controls_authorized=False,native_zero_op_authorized=False,
      native_execution_authorized=False,simulation_authorized=False,completed_source_controls=None)
    normalized['protected']=tested['protected'];assert normalized==tested
    r=json.loads((ROOT/c['result_path']).read_bytes());assert r['status']==STATUS and r['native_executed']is False
    run=admission.frozen.api('actions/runs/'+str(c['run']));job=admission.frozen.api('actions/jobs/'+str(c['job']))
    assert run['id']==job['run_id']==c['run']and job['id']==c['job']
    assert run['head_sha']==job['head_sha']==c['head']and run['run_attempt']==job['run_attempt']==1
    assert run['status']==job['status']=='completed'and run['conclusion']==job['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-loaded-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'and job['name']=='source-controls'
    log=subprocess.check_output(['gh','api','--allow-escape-sequences','repos/'+guard.REPO+'/actions/jobs/'+str(c['job'])+'/logs'])
    assert log==(ROOT/c['log_path']).read_bytes()
    for key in ('publication','imports','wait'):
        assert json.loads((ROOT/c[key+'_path']).read_bytes())==r['completed_auxiliary_controls'][key]
    return dict(run=c['run'],job=c['job'],head=c['head'],log_sha256=hashlib.sha256(log).hexdigest(),
      tested_method_sha256=hashlib.sha256(tested_raw).hexdigest(),all_tested_pins_unchanged=True)


def authorize(m):
    assert m['native_execution_authorized']is m['native_zero_op_authorized']is m['simulation_authorized']is True
    assert m['prepared_path_controls_authorized']is True
    for key in ('native_transient_authorized','extraction_authorized','geometry_generation_authorized','continuation_authorized'):
        assert m[key]is False,key
    release={}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '='in line:
            k,v=line.split('=',1);release[k]=v.strip('"')
    assert release['ID']=='ubuntu'and release['VERSION_ID']=='24.04'
    assert os.environ['ImageOS']=='ubuntu24'


def derive():
    m=methods();raw=(ROOT/ORIGINAL).read_bytes();context=(ROOT/CONTEXT).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA and hashlib.sha256(context).hexdigest()==CONTEXT_SHA
    selected={}
    for n in ast.parse(context).body:
        if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in ('OLD','NEW'):
            assert n.targets[0].id not in selected;selected[n.targets[0].id]=ast.literal_eval(n.value)
    assert set(selected)=={'OLD','NEW'}and all(isinstance(s,str)for s in selected.values())
    text=raw.decode();old,new=selected['OLD'],selected['NEW'];assert text.count(old)==1 and new not in text
    changed=text.replace(old,new);assert changed.count(new)==1 and changed.replace(new,old)==text
    assert hashlib.sha256(changed.encode()).hexdigest()==GENERATED_SHA
    ast.parse(changed)
    proof=dict(original_sha256=ORIGINAL_SHA,context_sha256=CONTEXT_SHA,generated_sha256=GENERATED_SHA,literal_edit_count=1)
    assert proof==m['controller_derivation']
    return changed,dict(**proof,edits=[dict(before=old,after=new,count=1)],reversed_byte_exact=True,
      original_four_case_native_loop_and_all_numerical_functions_unchanged=True)


def preflight():
    m=methods();authorize(m);controls=completed_controls();waiter.wait(GROUP,os.environ)
    tag,head=guard.context(GROUP,os.environ)
    reservation=guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    assert not reservation['existing_assets']
    return dict(reservation=reservation,completed_controls=controls,source_head=os.environ['GITHUB_SHA'],
      run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']))


def child_preflight():
    m=methods();authorize(m);proof=json.loads((OUT/'authorized-preflight.json').read_bytes())
    assert (proof['source_head'],proof['run_id'],proof['run_attempt'])==(os.environ['GITHUB_SHA'],int(os.environ['GITHUB_RUN_ID']),1)
    assert proof['completed_controls']==completed_controls()
    tag,head=guard.context(GROUP,os.environ)
    current=guard.validate_release(guard.api('releases/tags/'+tag),guard.api('git/ref/tags/'+tag),tag,head)
    assert current==proof['reservation']and not current['existing_assets']
    return dict(current,completed_source_controls=proof['completed_controls'])


def program_namespace():
    text,proof=derive();ns=dict(__name__='current_tail_M4_zero_OP',__file__=str(ROOT/ORIGINAL))
    exec(compile(text,'<current-tail-M4-zero-OP>','exec'),ns)
    ns.update(OUT=STAGE,GROUP=GROUP,METHOD=str(METHOD.relative_to(ROOT)),methods=methods,write=write)
    def current_inputs(out,result):
        cases,raw,models,paths,initialization,path_binding,screen,actual=adapter.prepare(out/'fresh-preparation')
        ns.update(initialization=initialization,path_binding=path_binding)
        result.update(current_TAIL_M4_preparation=actual,current_RC_model_hashes=dict(path_binding.bench.binding.MODELS),
          original17_HBT_rejection=actual['original17_HBT_rejection'],prior_four_tail_rejection=actual['prior_four_tail_rejection'],
          controller_derivation=proof,original_electrical_rejection_preserved=True,old_R_rescaled=False,
          geometry_generation_executed=False,new_extraction_performed=False)
        return cases,raw,models,paths,actual
    ns['_current_inputs']=current_inputs
    return ns,proof


def child():
    child_preflight();ns,_=program_namespace();ns['main'](prepare_only=False)


def finalize(report):
    native=STAGE/'result.json';report['native_result_present']=native.is_file()
    if native.is_file():
        raw=native.read_bytes();copied=OUT/'native-four-OP-result.json';copied.write_bytes(raw)
        report.update(native_result_sha256=hashlib.sha256(raw).hexdigest(),native_result_bytes=len(raw),native_result_raw_path=copied.name)
        assert sha(copied)==report['native_result_sha256']
        try:
            parsed=json.loads(raw);assert isinstance(parsed,dict),'Native result must be an object'
        except Exception as error:
            report.update(status='FAIL_OR_ERROR',native_result_parse_error=repr(error),native_result_parse_traceback=traceback.format_exc())
        else:report['native_result']=parsed
    for name in ('binding.summary.json','preparation.summary.json','current-preparation-proof.json',
                 'original-loaded-rejection.json','prior-four-tail-rejection.json'):
        original=STAGE/'fresh-preparation'/name
        if original.is_file():
            copied=OUT/('fresh-'+name);copied.write_bytes(original.read_bytes());assert sha(copied)==sha(original)
    try:methods();report['protected_sources_unchanged']=True
    except BaseException as error:
        report.update(status='FAIL_OR_ERROR',protected_sources_unchanged=False,source_error=repr(error),source_traceback=traceback.format_exc())
    report['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
    write(OUT/'result.json',report);return report


def run_owned_child():
    import signal,threading
    m=methods();trace=OUT/'supervision';trace.mkdir(exist_ok=False)
    owned=runtime.supervisor(ROOT,OUT,trace,methods,m['protected'][runtime.SAMPLER])
    old_signals={s:signal.signal(s,owned.interrupted)for s in (signal.SIGTERM,signal.SIGINT)}
    worker=threading.Thread(target=owned.heartbeat,daemon=True);worker.start()
    try:
        result=owned.supervised([sys.executable,'-B',ROOT/'scripts/cloud_tx_phase_reset334_tail_m4_loaded.py','--child'],
          'fresh-current-four-original-zero-OPs',False,seconds=m['owned_process']['seconds'],cwd=OUT)
        record=json.loads((trace/'fresh-current-four-original-zero-OPs.command.json').read_text())
        assert record['returncode']==result.returncode and not record['supervision_failure']
        assert not record['process_group_cleanup']['remaining_live']
        return record
    finally:
        owned.stop_process(owned.ACTIVE);owned.STOP.set();worker.join(timeout=2)
        for sig,handler in old_signals.items():signal.signal(sig,handler)
        owned.sample('final_resource_sample')


def validate_native(native):
    assert native['source_head']==os.environ['GITHUB_SHA']and native['run_id']==int(os.environ['GITHUB_RUN_ID'])
    assert native['status']==PASS and native['all_four_expanded_zero_OPs_passed']is True
    assert native['sources_unchanged']and native['native_simulator_invoked']and native['runtime_installed']
    assert native['current_RC_model_hashes']==admission.MODELS
    assert native['original_electrical_rejection_preserved']is True
    for key in ('transient_executed','electrical_phase_accepted','all31_clock_tree_accepted','PLL_connected','full_PHY_accepted','old_R_rescaled','geometry_generation_executed','new_extraction_performed'):
        assert native[key]is False,key
    assert native['original17_HBT_rejection']==adapter.original_rejections()[0]
    assert native['prior_four_tail_rejection']==adapter.prior_four_tail_rejection()
    proof=native['current_TAIL_M4_preparation']
    assert proof['current_models']==admission.MODELS and proof['current_RC']['all3181_files_authenticated']is True
    assert proof['current_RC']['native_view_files']==3165 and proof['current_RC']['consumed_native_view']=='native'
    assert proof['current_RC']['outer_summary_sha256']==admission.SOURCE['summary']
    assert proof['current_RC']['native_summary_sha256']==admission.ASSETS['native']['sha256']
    assert proof['current_RC']['complete_files']==3181 and proof['current_RC']['full_current_physical_files']==631
    assert proof['physical_source']==admission.physical.SOURCE
    assert proof['binding_faults_per_polarity']==20 and proof['preparation_faults']==8 and proof['path_faults']==32
    assert proof['unchanged_original_function_code_objects']is True
    assert set(native['cases'])==set(adapter.LABELS)
    for row in native['cases'].values():
        assert row['complete']is True and row['passed']is True and row['errors']==[]
        assert row['returncode']==0 and row['source_and_runtime_unchanged']is True and row['wave_raw_exists']is False
        assert row['expected_HBT_count']==318 and row['expected_saved_vectors']==4726 and row['zero_OP_gate']['passed']is True
    return True


def main():
    OUT.mkdir(parents=True,exist_ok=False)
    report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),
      run_attempt=int(os.environ['GITHUB_RUN_ATTEMPT']),electrical_accepted=False,full_phy_accepted=False,
      transient_executed=False,geometry_generation_executed=False,extraction_executed=False,continuation_executed=False,
      original_electrical_rejection_preserved=True,old_R_rescaled=False,zero_op_qualification_complete=False)
    write(OUT/'result.json',report);error=None
    try:
        report['preflight']=preflight();write(OUT/'authorized-preflight.json',report['preflight'])
        report['derivation']=derive()[1];write(OUT/'result.json',report)
        report['supervisor']=run_owned_child();native=json.loads((STAGE/'result.json').read_bytes())
        assert report['supervisor']['returncode']==0;validate_native(native)
        report.update(status=PASS,zero_op_qualification_complete=True,fresh_current_original_34ns_waveforms_required=True)
    except BaseException as e:
        error=e;report.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc())
    finally:finalize(report)
    if error is not None:raise error
    assert report['status']==PASS
    return report


def controls():
    assert methods()['source_controls_authorized']is True
    from check_tx_phase_reset334_tail_m4_loaded import controls as check
    return check()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--child',action='store_true');a=p.parse_args()
    if a.controls:print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
    elif a.child:child()
    else:main()
