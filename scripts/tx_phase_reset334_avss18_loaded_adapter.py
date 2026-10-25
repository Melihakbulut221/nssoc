#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind fresh RC evidence to isolated copies of the unchanged loaded numerical functions."""
import copy,hashlib,json,os,types
from pathlib import Path
import tx_phase_reset334_avss18_loaded_admission as admission
import tx_phase_reset334_loaded_binding as old_binding
import tx_phase_reset334_loaded_contract as old_bench
import tx_phase_reset334_loaded_native_adapter as old_initialization
import tx_phase_reset334_zero_op_runtime as old_paths
import tx_phase_reset334_transient_support as old_screen
import check_tx_phase_reset334_loaded_preparation as old_prepare_check
import check_tx_phase_reset334_zero_op_runtime as old_path_check
ROOT=Path(__file__).resolve().parents[1]
SOURCE='hw/soc/analog/pcie/clock_div2_assert_offset_v4.spice'
ORIGINAL_REJECTION='docs/evidence/tx-phase-reset334-first-loaded-rejected-result-20261025.json'
PARENT_REJECTION='docs/evidence/tx-phase334-parent-TX-rejection-boundary-20261025.json'
LABELS=tuple(s+'-initial-'+h for s in ('p','n')for h in ('high','low'))
ALLOWED={
 'tx_phase_reset334_loaded_binding':{'MODELS'},
 'tx_phase_reset334_loaded_contract':{'binding','SUMMARY_SHA','SOURCE','RUN','PAYLOAD_SHA'},
 'tx_phase_reset334_loaded_native_adapter':{'PREPARATION'},
 'tx_phase_reset334_zero_op_runtime':{'initialization','bench'},
 'tx_phase_reset334_transient_support':{'initialization','paths'},
 'check_tx_phase_reset334_loaded_preparation':{'bench'},
 'check_tx_phase_reset334_zero_op_runtime':{'runtime'}}

def encode(x):return(json.dumps(x,indent=2,allow_nan=False)+'\n').encode()

def digest(x):return hashlib.sha256(x.encode()if isinstance(x,str)else x).hexdigest()

def write(p,x):Path(p).write_bytes(encode(x))

def isolated(module,overrides):
    """New globals only: original code objects, defaults and modules remain untouched."""
    assert module.__name__ in ALLOWED and set(overrides)==ALLOWED[module.__name__]
    ns=dict(vars(module));ns.update(overrides)
    result=types.ModuleType(module.__name__+'_current_AVSS18')
    result.__dict__.update(ns);ns=result.__dict__
    ns['__name__']=module.__name__+'_current_AVSS18'
    for name,fn in vars(module).items():
        if isinstance(fn,types.FunctionType)and fn.__module__==module.__name__:
            assert fn.__closure__ is None and name not in overrides
            new=types.FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__)
            new.__kwdefaults__=fn.__kwdefaults__;new.__annotations__=fn.__annotations__.copy()
            ns[name]=new;assert new.__code__ is fn.__code__ and new.__globals__ is ns
    assert all(vars(module)[k]is not overrides[k]for k in overrides if isinstance(overrides[k],types.ModuleType))
    return result

def original_rejections():
    raw=(ROOT/ORIGINAL_REJECTION).read_bytes();r=json.loads(raw)
    assert r['run_id']==40178775666 and r['status']=='REJECTED_PHYSICAL334_THREE_MODEL_ORIGINAL_LOADED_GATES'
    assert r['full_capture']and not r['native_process_saved']and not r['electrical_screen_passed']
    h=r['review']['measurement']['hbt_safety'];failed={k:v for k,v in h.items()if not v['passed']}
    assert len(h)==318 and len(failed)==17 and not r['review']['passed']
    parent=json.loads((ROOT/PARENT_REJECTION).read_bytes());assert parent['electrical_screen_passed']is False
    return dict(original_result_sha256=digest(raw),run=40178775666,status=r['status'],failed_HBT_count=17,
      all17_original_failed_HBT_records=failed,original_complete_review=r['review'],original_electrical_rejection_unchanged=True),parent

def binding_context():return isolated(old_binding,dict(MODELS=dict(admission.MODELS)))

def bench_context(summary_raw,payload_raw,binding):
    d=json.loads(summary_raw)
    assert binding.MODELS==admission.MODELS
    assert d['current_RC_summary_sha256']==admission.SOURCE['summary']and d['current_RC_run']==admission.SOURCE['run']
    assert d['run_id']==int(os.environ['GITHUB_RUN_ID'])and d['source_head']==os.environ['GITHUB_SHA']
    return isolated(old_bench,dict(binding=binding,SUMMARY_SHA=digest(summary_raw),SOURCE=d['source_head'],RUN=d['run_id'],
      PAYLOAD_SHA={p:digest(payload_raw[p])for p in ('p','n')}))

def runtime_context(bench,summary_raw):
    d=json.loads(summary_raw)
    assert d['current_RC_summary_sha256']==admission.SOURCE['summary']and d['current_RC_run']==admission.SOURCE['run']
    assert d['binding_summary_sha256']==bench.SUMMARY_SHA
    assert d['source_head']==bench.SOURCE and d['run_id']==bench.RUN
    init=isolated(old_initialization,dict(PREPARATION=dict(run=d['run_id'],head=d['source_head'],summary_sha256=digest(summary_raw))))
    paths=isolated(old_paths,dict(initialization=init,bench=bench))
    screen=isolated(old_screen,dict(initialization=init,paths=paths))
    return init,paths,screen

def prepare(destination):
    """Fresh source/native binding and four original cases; never calls a simulator."""
    destination=Path(destination);destination.mkdir(exist_ok=False)
    rc,physical,transport=admission.restore(destination/'authenticated-RC')
    base=destination/'authenticated-RC';binding=binding_context();payload_raw={};models={};model_paths={}
    summary=dict(status='PASS_TWO_PHYSICAL334_ROLE_BINDINGS_NOT_LOADED_ELECTRICAL_ACCEPTANCE',
      run_id=int(os.environ['GITHUB_RUN_ID']),source_head=os.environ['GITHUB_SHA'],validation_errors=[],
      sources_unchanged=True,actual_native_binding_executed=True,simulator_invoked=False,new_extraction_performed=False,
      current_RC_summary_sha256=admission.SOURCE['summary'],current_RC_run=admission.SOURCE['run'],variants={})
    for pol in ('p','n'):
        native=json.loads((base/'precision'/pol/'source/native.json').read_bytes())
        comp=json.loads((base/'precision'/pol/'composition/composition.json').read_bytes())
        model_path=base/'precision'/pol/'composition/reset334-wire.spice';model=model_path.read_text()
        assert comp==rc['polarities'][pol]['composition']and digest(model_path.read_bytes())==admission.MODELS[pol]
        v=physical['variants'][pol]
        case=dict(text=(ROOT/SOURCE).read_text(),sign=pol,geometry=v['generation'],planes=v['wires']['anchors'],native=native,composition=comp,model_text=model)
        proof=binding.controls(case);assert len(proof['negative_controls'])==20 and proof['controls_passed']
        payload_raw[pol]=encode(proof);(destination/(pol+'-bindings-and-controls.json')).write_bytes(payload_raw[pol])
        path=destination/'qualified-binding/qualified-rc'/pol/'composition/reset334-wire.spice';path.parent.mkdir(parents=True)
        path.write_bytes(model_path.read_bytes());assert digest(path.read_bytes())==admission.MODELS[pol]
        models[pol]=model;model_paths[pol]=path
        summary['variants'][pol]=dict(binding_result_sha256=digest(payload_raw[pol]),model_sha256=admission.MODELS[pol],
          actual_internal_probe_pairs=proof['positive']['fixed_internal_probes'],negative_controls=proof['negative_controls'])
    summary_raw=encode(summary);(destination/'binding.summary.json').write_bytes(summary_raw)
    bench=bench_context(summary_raw,payload_raw,binding);check=isolated(old_prepare_check,dict(bench=bench))
    # Existing immutable scalar observer is still the stimulus source; no measured waveform/phase fit.
    observer=frozen_observer();(destination/'original-PLL-observer.summary.json').write_bytes(observer)
    preparation=check.positive_prepare(summary_raw,payload_raw,models,observer,(ROOT/SOURCE).read_text(),
      model_paths,'/fixture/sg13g2-ngspice-models','/fixture/r3_cmc.osdi',destination/'cases')
    assert len(preparation['actual_input_faults'])==8 and set(preparation['cases'])==set(LABELS)
    original,parent=original_rejections();write(destination/'original-loaded-rejection.json',original)
    prep=dict(status='PASS_FOUR_REAL_THREE_MODEL_PREPARATIONS_NOT_ELECTRICAL_ACCEPTANCE',run_id=summary['run_id'],source_head=summary['source_head'],
      validation_errors=[],sources_unchanged=True,preparation=preparation,original_parent_TX_rejection=parent,
      current_RC_summary_sha256=admission.SOURCE['summary'],current_RC_run=admission.SOURCE['run'],binding_summary_sha256=digest(summary_raw),
      original17_HBT_rejection=original,simulator_invoked=False,new_extraction=False)
    prep_raw=encode(prep);(destination/'preparation.summary.json').write_bytes(prep_raw)
    init,paths,screen=runtime_context(bench,prep_raw)
    cases={label:((destination/'cases'/label/'bench.cir').read_text(),json.loads((destination/'cases'/label/'contract.json').read_bytes()))for label in LABELS}
    for label,(deck,c)in cases.items():
        init.prepared_contract(label,deck,c,prep_raw)
        assert len(c['vectors'])==len(set(c['vectors']))==4726 and len(c['hbt'])==318 and len(c['thermal_nodes'])==390
        assert c['binding_summary_sha256']==digest(summary_raw)and all(x['model_sha256']==admission.MODELS[x['variant']]for x in c['instances'])
    path_check=isolated(old_path_check,dict(runtime=paths));path_proof=path_check.positive_paths(cases,prep_raw,models)
    assert len(path_proof['negative_controls'])==32
    manifest={str(p.relative_to(destination)):digest(p.read_bytes())for p in destination.rglob('*')if p.is_file()}
    proof=dict(status='PASS_CURRENT_AVSS18_BINDING_PREPARATION_AND_RUNTIME_PATHS_NOT_ELECTRICAL',current_RC=transport,
      physical_source=admission.physical.SOURCE,current_models=dict(admission.MODELS),binding_summary_sha256=digest(summary_raw),
      preparation_summary_sha256=digest(prep_raw),binding_faults_per_polarity=20,preparation_faults=8,path_faults=32,
      path_controls=path_proof,original17_HBT_rejection=original,original_parent_TX_rejection=parent,all_prepared_files=manifest,
      unchanged_original_function_code_objects=True,simulator_invoked=False,extraction_invoked=False,electrical_accepted=False)
    write(destination/'current-preparation-proof.json',proof)
    return cases,prep_raw,models,model_paths,init,paths,screen,proof

def frozen_observer():
    import cloud_tx_phase_reset334_loaded_preparation as original
    o=old_bench.original
    run=original.api('actions/runs/'+str(o.OBSERVER_RUN))
    assert run['head_sha']==o.OBSERVER_HEAD and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='success'
    return original.asset(o.OBSERVER_ASSET,o.OBSERVER_SHA)
