#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/closure/admission and real main-entry controls; no native execution."""
import ast,copy,importlib.metadata,json,os,sys,tempfile,types
from pathlib import Path
import tx_phase_reset334_avss18_loaded_admission as a
import tx_phase_reset334_avss18_loaded_adapter as d
import cloud_tx_phase_reset334_avss18_loaded as controller
def immediate_imports(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    if isinstance(node,(ast.Import,ast.ImportFrom)):yield node
    for child in ast.iter_child_nodes(node):yield from immediate_imports(child)

def import_closure(root,pins,roots):
    queue=list(roots);seen={};edges=[];standard=set(sys.stdlib_module_names)|set(sys.builtin_module_names)
    external={'numpy':'2.3.3','networkx':'3.4.2'}
    while queue:
        name=queue.pop()
        if name in seen:continue
        path=root/name;assert path.is_file()and not path.is_symlink()and name in pins
        assert a.sha(path)==pins[name];seen[name]=pins[name]
        for node in immediate_imports(ast.parse(path.read_bytes())):
            if isinstance(node,ast.ImportFrom):assert node.level==0
            for module in ([x.name for x in node.names]if isinstance(node,ast.Import)else[node.module]):
                assert module
                target='scripts/'+module.replace('.','/')+'.py';top=module.split('.')[0]
                if(root/target).exists()or(root/target).is_symlink():
                    assert target in pins and(root/target).is_file()and not(root/target).is_symlink();queue.append(target)
                elif top in standard:pass
                else:assert top in external and importlib.metadata.version(top)==external[top],module
                edges.append(dict(source=name,module=module))
    return dict(files=seen,edges=edges,explicit_external_versions=external,
      scope='Module-initialization imports; generated native imports are bound separately by immutable source derivations')

import check_tx_phase_reset334_loaded_native_adapter as old_init_check

def refusal(name,fn):
    try:fn()
    except(AssertionError,KeyError,ValueError,TypeError,FileNotFoundError):return name
    raise AssertionError('Accepted '+name)

def entry_fixture(prepare_only):
    ns,proof=controller.program_namespace();seen=[]
    class StopAtCurrentPreparation(RuntimeError):pass
    def stop(out,result):
        assert out==ns['OUT']and result['run_id']==int(os.environ['GITHUB_RUN_ID'])
        seen.append('current-preparation');raise StopAtCurrentPreparation('explicit stop before restore/network/native')
    def forbidden(*args,**kwargs):raise AssertionError('Unexpected network or simulator call')
    with tempfile.TemporaryDirectory()as tmp:
        ns['OUT']=Path(tmp)/'actual-main'
        m=dict(prepared_path_controls_authorized=True,native_zero_op_authorized=True)
        ns['methods']=lambda:m
        ns['_current_inputs']=stop
        ns['publication']=types.SimpleNamespace(context=lambda *args:('fixture-tag','a'*40),api=lambda path:dict(fixture=path),validate_release=lambda *args:dict(fixture=True))
        ns['native']=types.SimpleNamespace(restore=forbidden)
        try:ns['main'](prepare_only=prepare_only)
        except StopAtCurrentPreparation:pass
        else:raise AssertionError('Main did not preserve explicit stop')
        result=json.loads((ns['OUT']/'result.json').read_bytes())
        assert seen==['current-preparation']and result['status']=='FAIL_FRESH318_ZERO_OP'
        assert len(result['validation_errors'])==1 and 'StopAtCurrentPreparation'in result['validation_errors'][0]['error']
        assert result['outputs']=={}and not result['native_simulator_invoked']and not result['runtime_installed']
    return dict(prepare_only=prepare_only,actual_main_reached_current_preparation=True,explicit_pre_native_stop_preserved=True,
      actual_finally_result_written=True,simulator_or_archive_executed=False)

def controls():
    m=controller.methods();assert m['source_controls_authorized']is True
    for p in m['required_repository_modules']:assert p in m['protected']and(controller.ROOT/p).is_file()
    imports=import_closure(controller.ROOT,m['protected'],m['import_roots'])
    r,metadata=a.prerequisite();assert a.validate(r)
    faults=[]
    changes=[
      ('run',lambda x:x.update(run_id=1)),('head',lambda x:x.update(source_head='0'*40)),
      ('attempt',lambda x:x.update(run_attempt=2)),('status',lambda x:x.update(status='PASS')),
      ('missing-output',lambda x:x['outputs'].pop(next(iter(x['outputs'])))),('missing-N',lambda x:x['polarities'].pop('n')),
      ('changed-source',lambda x:x.update(protected_sources_unchanged=False)),('erased-rejection',lambda x:x.update(original_electrical_rejection_preserved=False)),
      ('old-R-scaled',lambda x:x.update(old_R_rescaled=True)),('electrical-claim',lambda x:x.update(electrical_accepted=True)),
      ('old-P-model',lambda x:x['polarities']['p']['composition'].update(model_sha256=d.old_binding.MODELS['p'])),
      ('wrong-census',lambda x:x['polarities']['p']['composition']['positive'].update(wire_resistors=1)),
      ('missing-composition-fault',lambda x:x['polarities']['p']['composition']['controls'].pop()),
      ('accepted-composition-fault',lambda x:x['polarities']['p']['composition']['controls'][0].update(rejected=False)),
      ('missing-native-binding',lambda x:x['polarities']['p']['composition']['bindings'].pop()),
      ('unpreserved-wire-tokens',lambda x:x['polarities']['p']['composition'].update(all_raw_wire_tokens_preserved=False)),
      ('missing-native-order',lambda x:x['polarities']['n']['orders'].pop('precise_reversed')),
      ('order-inequality',lambda x:x['polarities']['p']['native_order_equivalence'].update(symmetric_endpoint_value_multiset_exact=False)),
      ('native-return',lambda x:x['polarities']['p']['orders']['precise']['native'].update(returncode=1)),
      ('disconnected-probe',lambda x:x['polarities']['p']['orders']['precise']['audit'].update(disconnected_probes=['A0000'])),
      ('wrong-R-value-proof',lambda x:x['polarities']['p']['orders']['precise']['audit'].update(native_export_r_edge_value_multiset_exact=False)),
      ('changed-C-proof',lambda x:x['polarities']['p']['orders']['precise']['audit'].update(complete_collapsed_capacitance_conserved=False)),
      ('missing-wire-fault',lambda x:x['polarities']['p']['orders']['precise']['wire_controls']['cases'].pop()),
      ('missing-MIM-fault',lambda x:x['polarities']['p']['orders']['precise']['mim_controls'].pop())]
    for name,edit in changes:
        x=copy.deepcopy(r);edit(x);faults.append(refusal(name,lambda:a.validate(x)))
    metadata_faults=[]
    originals=(metadata['run'],metadata['job'],metadata['release'],metadata['tag'])
    edits=[(0,'id',1),(0,'head_sha','0'*40),(0,'status','in_progress'),(0,'conclusion','failure'),(0,'run_attempt',2),
      (0,'path','other.yml'),(0,'head_branch','other'),(1,'id',1),(1,'head_sha','0'*40),(1,'conclusion','failure'),
      (2,'id',1),(2,'draft',True),(2,'prerelease',False),(2,'target_commitish','0'*40)]
    for i,key,value in edits:
        x=copy.deepcopy(originals);x[i][key]=value
        metadata_faults.append(refusal(str(i)+':'+key,lambda:a.validate_metadata(*x)))
    for key,value in [('sha','0'*40),('type','tag')]:
        x=copy.deepcopy(originals);x[3]['object'][key]=value
        metadata_faults.append(refusal('tag:'+key,lambda:a.validate_metadata(*x)))
    for key,value in [('id',1),('size',1),('digest','sha256:'+'0'*64),('state','new')]:
        x=copy.deepcopy(originals);asset=next(v for v in x[2]['assets']if v['id']==a.ASSETS['archive']['id']);asset[key]=value
        metadata_faults.append(refusal('asset:'+key,lambda:a.validate_metadata(*x)))
    original_globals={module.__name__:dict(vars(module))for module in (d.old_binding,d.old_bench,d.old_initialization,d.old_paths,d.old_screen)}
    binding=d.binding_context();assert binding.MODELS==a.MODELS and binding.MODELS!=d.old_binding.MODELS
    context_faults=[refusal('function-override',lambda:d.isolated(d.old_binding,dict(MODELS=a.MODELS,bind=lambda:None))),
      refusal('missing-model-override',lambda:d.isolated(d.old_binding,{})),
      refusal('changed-frozen-controller',lambda:controller.derived_program((controller.ROOT/controller.ORIGINAL).read_text()+'\n'))]
    raw=d.encode(dict(current_RC_summary_sha256=a.SOURCE['summary'],current_RC_run=a.SOURCE['run'],source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID'])))
    payload={'p':b'fixture-P','n':b'fixture-N'};bench=d.bench_context(raw,payload,binding)
    context_faults.append(refusal('stale-model-context',lambda:d.bench_context(raw,payload,d.old_binding)))
    for key,value in [('current_RC_summary_sha256','0'*64),('current_RC_run',1),('source_head','0'*40),('run_id',1)]:
        bad=json.loads(raw);bad[key]=value;context_faults.append(refusal('binding:'+key,lambda:d.bench_context(d.encode(bad),payload,binding)))
    preparation=json.loads(raw);preparation['binding_summary_sha256']=bench.SUMMARY_SHA
    init,paths,screen=d.runtime_context(bench,d.encode(preparation))
    assert paths.bench is bench and paths.initialization is init and screen.paths is paths and screen.initialization is init
    for module,new in [(d.old_binding,binding),(d.old_bench,bench),(d.old_initialization,init),(d.old_paths,paths),(d.old_screen,screen)]:
        for name,fn in vars(module).items():
            if isinstance(fn,types.FunctionType)and fn.__module__==module.__name__:
                assert getattr(new,name).__code__ is fn.__code__ and getattr(new,name).__globals__ is new.__dict__
        assert all(vars(module)[key]is value for key,value in original_globals[module.__name__].items())
    for key,value in [('current_RC_summary_sha256','0'*64),('current_RC_run',1),('binding_summary_sha256','0'*64),('source_head','0'*40),('run_id',1)]:
        bad=copy.deepcopy(preparation);bad[key]=value
        context_faults.append(refusal('prepared:'+key,lambda:d.runtime_context(bench,d.encode(bad))))
    source=d.old_prepare_check.controls();initialization=old_init_check.controls();zero=d.old_path_check.controls()
    original,parent=d.original_rejections();assert len(original['all17_original_failed_HBT_records'])==17
    code,derivation=controller.derived_program()
    old=ast.parse((controller.ROOT/controller.ORIGINAL).read_text());new=ast.parse(code)
    before={n.name:ast.dump(n,include_attributes=False)for n in old.body if isinstance(n,ast.FunctionDef)}
    after={n.name:ast.dump(n,include_attributes=False)for n in new.body if isinstance(n,ast.FunctionDef)}
    assert set(before)==set(after)and all(after[k]==v for k,v in before.items()if k!='main')
    entries=[entry_fixture(x)for x in (True,False)]
    archive=a.frozen.archive_controls()
    assert len(faults)==24 and len(metadata_faults)==20 and len(context_faults)==13
    assert len(source['rejected'])==15 and len(initialization['negative_controls'])==30 and len(zero['negative_controls'])==12
    assert len(archive['rejected'])==13 and archive['inherited_parts_controls']['negative_controls']==6
    controller.methods()
    return dict(status='PASS_CURRENT_AVSS18_LOADED_SOURCE_CONTROLS_ONLY',import_closure=imports,
      actual_controller_imported=True,prerequisite=metadata,RC_faults=faults,metadata_faults=metadata_faults,context_faults=context_faults,
      all_original_function_code_objects_identical=True,original_module_globals_unchanged=True,main_derivation=derivation,actual_main_entry_positives=entries,
      inherited_preparation=source,inherited_initialization=initialization,inherited_zero_OP=zero,archive_controls=archive,
      original_failed_HBT_count=17,actual_binding_or_preparation_executed=False,simulation_executed=False,extraction_executed=False)

if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
