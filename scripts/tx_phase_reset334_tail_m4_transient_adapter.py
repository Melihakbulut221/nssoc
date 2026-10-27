#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current OP/preparation admission for the preserved portable transient numerical functions."""
import ast,copy,hashlib,json,types
from pathlib import Path
import tx_phase_reset334_tail_m4_transient_admission as admission
import tx_phase_reset334_tail_m4_loaded_adapter as loaded
import tx_phase_reset334_transient_support as frozen
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/tx-phase-reset334-tail-m4-transient-methods.json'
ORIGINAL='scripts/tx_phase_reset334_transient_support.py'
ORIGINAL_SHA='6e13a8fb79af6cffb3f65c0085ba15ca5e2d565508f7154ffc94c2469383a7df'
OLD="    op_raw=preparation.asset(OP['summary_asset'],OP['summary_sha256'])\n    op=json.loads(op_raw);validate_OP(op,preparation.api('actions/runs/'+str(OP['run'])))\n    (out/'qualified-zero-OP.summary.json').write_bytes(op_raw)\n    spec=initialization.PREPARATION\n    old=preparation.api('actions/runs/'+str(spec['run']))\n    assert old['head_sha']==spec['head']and old['run_attempt']==1 and old['status']=='completed'and old['conclusion']=='success'\n    summary_raw=preparation.asset(spec['summary_asset'],spec['summary_sha256']);summary=json.loads(summary_raw)\n    (out/'qualified-preparation.summary.json').write_bytes(summary_raw)\n    prepared_root.mkdir(exist_ok=False)\n    selected=['cases/'+label+'/'+n for n in ('bench.cir','contract.json')]\n    selected+=['qualified-binding/qualified-rc/'+s+'/composition/reset334-wire.spice'for s in ('p','n')]\n    restored,proof=reports.restore_report('tx-phase-reset334-loaded-preparation',spec['run'],\n      spec['summary_sha256'],spec['parts_sha256'],prepared_root/'prepared',selected)\n    assert restored==summary\n    base=(prepared_root/'prepared/cases'/label/'bench.cir').read_text()\n    c=json.loads((prepared_root/'prepared/cases'/label/'contract.json').read_bytes())\n    initialization.prepared_contract(label,base,c,summary_raw)\n    assert op['cases'][label]['contract_sha256']==digest(json.dumps(c,indent=2,allow_nan=False)+'\\n')\n    models_at={s:prepared_root/'prepared/qualified-binding/qualified-rc'/s/'composition/reset334-wire.spice'for s in ('p','n')}\n    models={s:p.read_text()for s,p in models_at.items()}\n"
NEW="    op_raw,op,summary_raw,base,c,models_at,models,proof,spec=_restore_current(label,prepared_root,out)\n    summary=json.loads(summary_raw)\n    initialization.prepared_contract(label,base,c,summary_raw)\n    assert op['cases'][label]['contract_sha256']==digest(json.dumps(c,indent=2,allow_nan=False)+'\\n')\n"
PRESERVED=('digest','write','methods','runtime_identity','compatible','measurement_checks','gate','review_capture')
digest=loaded.digest
encode=loaded.encode

def derived_program(text=None):
    if text is None:text=(ROOT/ORIGINAL).read_text()
    assert digest(text)==ORIGINAL_SHA
    edits=[dict(before=OLD,after=NEW,count=1),
      dict(before="assert run['path']=='.github/workflows/tx-phase-reset334-zero-op-cloud.yml'",
           after="assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-loaded-cloud.yml'",count=1)]
    changed=text
    for e in edits:
        assert changed.count(e['before'])==e['count'];changed=changed.replace(e['before'],e['after'])
    reverse=changed
    for e in reversed(edits):
        assert reverse.count(e['after'])==e['count'];reverse=reverse.replace(e['after'],e['before'])
    assert reverse==text
    before={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    after={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(changed).body if isinstance(n,ast.FunctionDef)}
    assert set(before)==set(after)and all(before[n]==after[n]for n in PRESERVED)
    return changed,dict(original_sha256=ORIGINAL_SHA,generated_sha256=digest(changed),literal_edits=edits,
      reversed_byte_exact=True,preserved_functions=list(PRESERVED),scope='Only current preparation restore and OP workflow identity; original numerical functions unchanged')

def context_identity(binding,preparation,payload_hashes):
    assert binding['run_id']==preparation['run_id']==admission.SOURCE['run']
    assert binding['source_head']==preparation['source_head']==admission.SOURCE['head']
    for r in (binding,preparation):
        assert r['current_RC_run']==admission.current_RC.SOURCE['run']
        assert r['current_RC_summary_sha256']==admission.current_RC.SOURCE['summary']
    assert preparation['binding_summary_sha256']==admission.BINDING_SHA
    assert set(payload_hashes)==set(binding['variants'])=={'p','n'}
    for p in ('p','n'):
        assert payload_hashes[p]==binding['variants'][p]['binding_result_sha256']
        assert binding['variants'][p]['model_sha256']==admission.MODELS[p]
    return True

def context(binding_raw,preparation_raw,payloads,models):
    assert digest(binding_raw)==admission.BINDING_SHA and digest(preparation_raw)==admission.PREPARATION_SHA
    binding=json.loads(binding_raw);preparation=json.loads(preparation_raw)
    context_identity(binding,preparation,{p:digest(b)for p,b in payloads.items()})
    current_binding=loaded.binding_context()
    bench=loaded.isolated(loaded.old_bench,dict(binding=current_binding,SUMMARY_SHA=admission.BINDING_SHA,
      SOURCE=admission.SOURCE['head'],RUN=admission.SOURCE['run'],PAYLOAD_SHA={p:digest(b)for p,b in payloads.items()}))
    bench.qualified_inputs(binding_raw,payloads,models)
    init,paths,unused_historical_screen=loaded.runtime_context(bench,preparation_raw)
    assert init.PREPARATION==dict(run=admission.SOURCE['run'],head=admission.SOURCE['head'],summary_sha256=admission.PREPARATION_SHA)
    assert paths.bench is bench and paths.initialization is init
    assert unused_historical_screen.prepare.__code__ is frozen.prepare.__code__
    return init,paths

def read_inputs(root,op):
    """Read only authenticated original34ns cases; top-level OP-only decks are never inputs."""
    prep=root/'fresh-preparation'
    paths=[prep/'binding.summary.json',prep/'preparation.summary.json',
      *[prep/(p+'-bindings-and-controls.json')for p in ('p','n')],
      *[prep/'qualified-binding/qualified-rc'/p/'composition/reset334-wire.spice'for p in ('p','n')],
      *[prep/'cases'/label/name for label in admission.LABELS for name in ('bench.cir','contract.json')]]
    assert len(paths)==14 and len(set(paths))==14
    for p in paths:
        assert p.is_file()and not p.is_symlink()
        assert admission.sha(p)==op['outputs'][str(p.relative_to(root))]
    binding_raw=(prep/'binding.summary.json').read_bytes();raw=(prep/'preparation.summary.json').read_bytes()
    payloads={p:(prep/(p+'-bindings-and-controls.json')).read_bytes()for p in ('p','n')}
    model_paths={p:prep/'qualified-binding/qualified-rc'/p/'composition/reset334-wire.spice'for p in ('p','n')}
    models={p:q.read_text()for p,q in model_paths.items()}
    init,runtime=context(binding_raw,raw,payloads,models)
    cases={label:((prep/'cases'/label/'bench.cir').read_text(),json.loads((prep/'cases'/label/'contract.json').read_bytes()))for label in admission.LABELS}
    for label,(base,c)in cases.items():
        init.prepared_contract(label,base,c,raw)
        assert digest(base)==op['cases'][label]['path_binding']['prepared_deck_sha256']
        assert digest(base)!=op['cases'][label]['deck_sha256'],'An OP-only deck cannot initialize the original transient'
        assert digest(encode(c))==op['cases'][label]['contract_sha256']
        assert len(c['vectors'])==len(set(c['vectors']))==4726 and len(c['hbt'])==318 and len(c['thermal_nodes'])==390
        assert c['binding_summary_sha256']==admission.BINDING_SHA
        assert all(x['model_sha256']==admission.MODELS[x['variant']]for x in c['instances'])
    return binding_raw,raw,payloads,models,model_paths,init,runtime,cases

def actual_input_controls(root,op,inputs):
    binding_raw,raw,payloads,models,model_paths,init,runtime,cases=inputs
    checker=loaded.isolated(loaded.old_path_check,dict(runtime=runtime))
    paths=checker.positive_paths(cases,raw,models)
    assert len(paths['negative_controls'])==32
    rejected=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,TypeError):rejected.append(name)
        else:raise AssertionError('Accepted actual restored input '+name)
    reject('binding-byte',lambda:context(binding_raw+b' ',raw,payloads,models))
    reject('preparation-byte',lambda:context(binding_raw,raw+b' ',payloads,models))
    for p in ('p','n'):
        changed=dict(payloads);changed[p]+=b' '
        reject('payload-'+p,lambda:context(binding_raw,raw,changed,models))
        changed=dict(models);changed[p]+='\n'
        reject('model-'+p,lambda:context(binding_raw,raw,payloads,changed))
    for label,(base,c)in cases.items():
        op_deck=(root/label/'bench.cir').read_text()
        reject(label+'-OP-deck-as-transient',lambda:init.prepared_contract(label,op_deck,c,raw))
        bad=copy.deepcopy(c);bad['vectors'].pop()
        reject(label+'-vector-removed',lambda:init.prepared_contract(label,base,bad,raw))
        bad=copy.deepcopy(c);bad['instances'][0]['model_sha256']='0'*64
        reject(label+'-old-model-identity',lambda:init.prepared_contract(label,base,bad,raw))
    assert len(rejected)==18
    return dict(actual_source_refusals=rejected,original_path_controls=paths,
      all_four_original34ns_preparations_revalidated=True,current_pair_models_exact=True,
      same_row_or_electrical_acceptance=False,simulator_invoked=False)

def session():
    text,derivation=derived_program();module=types.ModuleType('current_TAIL_M4_portable_numerics')
    ns=module.__dict__;ns.update(__file__=str(ROOT/ORIGINAL))
    exec(compile(text,'<current-TAIL-M4-portable-numerics>','exec'),ns)
    ns.update(METHOD=METHOD,OP=dict(run=admission.SOURCE['run'],head=admission.SOURCE['head'],
      summary_asset=admission.ASSETS['native']['id'],summary_sha256=admission.ASSETS['native']['sha256']))
    for name in PRESERVED:
        fn=getattr(frozen,name)
        replacement=types.FunctionType(fn.__code__,ns,fn.__name__,fn.__defaults__)
        replacement.__kwdefaults__=fn.__kwdefaults__;ns[name]=replacement
        assert replacement.__code__ is fn.__code__ and replacement.__globals__ is ns
    def restore_current(label,prepared_root,out):
        prepared_root.mkdir(exist_ok=False)
        root=prepared_root/'qualified-current-OP'
        op_raw,op,proof=admission.restore(root)
        ns['validate_OP'](op,proof['metadata']['run'])
        (out/'qualified-zero-OP.summary.json').write_bytes(op_raw)
        (out/'current-OP-restoration.json').write_bytes(encode(proof))
        try:
            inputs=read_inputs(root/'native',op)
            actual=actual_input_controls(root/'native',op,inputs)
        except BaseException as error:
            import traceback
            (out/'current-input-failure.json').write_bytes(encode(dict(error=repr(error),traceback=traceback.format_exc(),
              outer_OP_sha256=admission.SOURCE['summary'],preparation_sha256=admission.PREPARATION_SHA,
              no_simulator_started=True)))
            raise
        binding_raw,summary_raw,payloads,models,model_paths,init,runtime,cases=inputs
        ns.update(initialization=init,paths=runtime)
        assert ns['prepare'].__code__ is not frozen.prepare.__code__
        assert ns['measurement_checks'].__code__ is frozen.measurement_checks.__code__
        (out/'qualified-preparation.summary.json').write_bytes(summary_raw)
        (out/'current-restored-input-controls.json').write_bytes(encode(actual))
        assert label in cases;base,c=cases[label];spec=init.PREPARATION
        assert proof['summary_sha256']==spec['summary_sha256']==admission.PREPARATION_SHA
        assert proof['outer_zero_OP_summary_sha256']==admission.SOURCE['summary']
        proof.update(current_models=dict(admission.MODELS),current_RC=admission.current_RC.SOURCE,
          original17_HBT_rejection=op['original17_HBT_rejection'],prior_four_tail_rejection=op['prior_four_tail_rejection'],current_input_controls=actual,
          support_derivation=derivation,restored_original34ns_deck=True,OP_only_deck_used_as_transient=False,
          geometry_generation_executed=False,new_extraction_performed=False,old_R_rescaled=False)
        return op_raw,op,summary_raw,base,c,model_paths,models,proof,spec
    ns['_restore_current']=restore_current
    return module
