#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/admission/main-entry and portable controls; never native qualification."""
import ast,copy,json,os,sys,tempfile,types
from pathlib import Path
from unittest import mock
import cloud_tx_phase_reset334_avss18_transient as controller
import tx_phase_reset334_avss18_transient_admission as a
import tx_phase_reset334_avss18_transient_adapter as d
import check_tx_phase_reset334_avss18_loaded as inherited_imports
import check_tx_phase_reset334_transient as original_check

def reject(name,fn):
    try:fn()
    except(AssertionError,KeyError,TypeError,ValueError,FileNotFoundError):return name
    raise AssertionError('Accepted '+name)

def main_entry_fixture(stage):
    ns,proof=controller.program_namespace();seen=[]
    class StopBeforeCurrentRestore(RuntimeError):pass
    def stop(label,prepared,out,group):
        assert label=='p-initial-high'and group==controller.group(stage,label)
        seen.append(dict(label=label,prepared=str(prepared),out=str(out)))
        raise StopBeforeCurrentRestore('explicit stop before archive/network/Docker/native')
    def forbidden(*args,**kwargs):raise AssertionError('Unexpected native/network operation')
    with tempfile.TemporaryDirectory()as tmp:
        base=Path(tmp)
        class RootProxy:
            def __str__(self):return '/home/runner/work/nssoc/nssoc'
            def __truediv__(self,name):return base/name
        ns.update(ROOT=RootProxy(),reports=types.SimpleNamespace(OUT=None),
          subprocess=types.SimpleNamespace(run=forbidden,check_output=forbidden))
        original=ns['review']
        ns['review']=types.SimpleNamespace(methods=lambda:dict(protected={},native_transient_authorized=True,segment_seconds=13200),
          prepare=stop,FLAGS=original.FLAGS)
        with mock.patch.object(sys,'argv',['fixture','--stage',stage,'--case','p-initial-high']):
            try:ns['main']()
            except StopBeforeCurrentRestore:pass
            else:raise AssertionError('Full native main swallowed preparation stop')
        result=json.loads((base/('cloud-'+controller.group(stage,'p-initial-high'))/'result.json').read_bytes())
        assert len(seen)==1 and result['status']=='FAIL_OR_ERROR'and 'StopBeforeCurrentRestore'in result['error']
        assert result['outputs']=={}and not result['native_process_saved']and not result['full_capture']and not result['electrical_screen_passed']
        assert result['controller_sha256']==controller.sha(Path(controller.__file__))
    return dict(stage=stage,actual_main_entered=True,actual_finally_failure_preserved=True,
      explicit_stop_before_restore_and_DUT=True,native_or_archive_executed=False)

def preparation_entry_fixture(use_old=False):
    module=d.session();seen=[]
    class StopAtCurrentRestore(RuntimeError):pass
    def stop(label,prepared,out):
        seen.append('current-OP-capsule')
        raise StopAtCurrentRestore('explicit stop before any archive/engine')
    def forbidden(*args,**kwargs):raise AssertionError('Legacy or native path reached')
    module.methods=lambda:dict(native_transient_authorized=True,initial_case='p-initial-high')
    module._restore_current=stop
    module.publication=types.SimpleNamespace(context=lambda *x:('fixture-tag','a'*40),api=lambda *x:{},validate_release=lambda *x:{})
    module.preparation=types.SimpleNamespace(asset=forbidden,api=forbidden)
    module.native=types.SimpleNamespace(restore=forbidden)
    fn=module.prepare
    if use_old:fn=types.FunctionType(d.frozen.prepare.__code__,module.__dict__)
    with tempfile.TemporaryDirectory()as tmp:
        try:fn('p-initial-high',Path(tmp)/'prepared',Path(tmp),'fixture')
        except StopAtCurrentRestore:
            assert not use_old and seen==['current-OP-capsule']
            return dict(actual_derived_prepare_entered=True,current_capsule_boundary_reached=True,no_archive_or_engine=True)
        except AssertionError as error:
            assert use_old and str(error)=='Legacy or native path reached'and seen==[]
            return dict(original_legacy_prepare_rejected_before_restore=True)
        raise AssertionError('Preparation entry fixture did not stop explicitly')

def context_controls(op):
    source=dict(run_id=a.SOURCE['run'],source_head=a.SOURCE['head'],current_RC_run=a.current_RC.SOURCE['run'],
      current_RC_summary_sha256=a.current_RC.SOURCE['summary'])
    payload={p:op['outputs']['fresh-preparation/'+p+'-bindings-and-controls.json']for p in ('p','n')}
    binding=dict(**source,variants={p:dict(model_sha256=a.MODELS[p],binding_result_sha256=payload[p])for p in ('p','n')})
    prep=dict(**source,binding_summary_sha256=a.BINDING_SHA)
    assert d.context_identity(binding,prep,payload)
    changes=[]
    for target in ('binding','preparation'):
        for key,value in [('run_id',int(os.environ['GITHUB_RUN_ID'])),('source_head',os.environ['GITHUB_SHA']),
          ('current_RC_run',1),('current_RC_summary_sha256','0'*64)]:
            assert source[key]!=value
            b,p,h=copy.deepcopy((binding,prep,payload));(b if target=='binding'else p)[key]=value
            changes.append(reject(target+':'+key,lambda:d.context_identity(b,p,h)))
    b,p,h=copy.deepcopy((binding,prep,payload));p['binding_summary_sha256']='0'*64
    changes.append(reject('wrong-binding-summary',lambda:d.context_identity(b,p,h)))
    for pol in ('p','n'):
        b,p,h=copy.deepcopy((binding,prep,payload));b['variants'][pol]['model_sha256']=d.loaded.old_binding.MODELS[pol]
        changes.append(reject('old-model-'+pol,lambda:d.context_identity(b,p,h)))
        b,p,h=copy.deepcopy((binding,prep,payload));h[pol]='0'*64
        changes.append(reject('wrong-payload-'+pol,lambda:d.context_identity(b,p,h)))
    b,p,h=copy.deepcopy((binding,prep,payload));del h['n']
    changes.append(reject('missing-polarity',lambda:d.context_identity(b,p,h)))
    assert len(changes)==14
    return dict(positive_prior_run_identity=True,fixture_uses_actual_OP_metadata_but_not_restored_binding_bytes=True,rejected=changes)

def continuation_asset_controls(source):
    main=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='main')
    loops=[n for n in ast.walk(main)if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='suffix']
    assert len(loops)==1
    selected=loops[0].body[:4]
    assert all(isinstance(n,(ast.Assign,ast.Assert))for n in selected)
    program=compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),'<actual-continuation-asset-seam>','exec')
    spec=dict(group='tx-phase-reset334-avss18-transient-native-initial-p-initial-high',run=123)
    name=spec['group']+'-123-1.summary.json'
    exact=dict(id=2,name=name);decoy=dict(id=1,name='qualified-zero-OP.summary.json')
    for assets in ([decoy,exact],[exact,decoy]):
        ns=dict(spec=spec,suffix='.summary.json',rel=dict(assets=assets))
        exec(program,ns);assert ns['a']is exact
    faults=[]
    for label,assets in [('missing-exact',[decoy]),('duplicate-exact',[exact,copy.deepcopy(exact)])]:
        ns=dict(spec=spec,suffix='.summary.json',rel=dict(assets=assets))
        faults.append(reject(label,lambda:exec(program,ns)))
    return dict(two_summary_orderings_preserve_exact_source_asset=True,rejected=faults)

def controls():
    m=controller.methods();assert m['source_controls_authorized']is True
    imports=inherited_imports.import_closure(controller.ROOT,m['protected'],m['import_roots'])
    for path in m['required_repository_modules']:assert path in m['protected']and(controller.ROOT/path).is_file()
    op,metadata=a.prerequisite();assert a.validate(op)and len(a.expected_files(op))==2806
    op_faults=[]
    edits=[
      ('old-run',lambda r:r.update(run_id=40175085823)),
      ('old-head',lambda r:r.update(source_head='63a4c761e08442f037027916233acb78f4dfd8c1')),
      ('native-return',lambda r:r['cases']['p-initial-high'].update(returncode=1)),
      ('nonzero-state',lambda r:r['cases']['p-initial-high']['zero_source_op'].update(all_saved_electrical_and_thermal_states_zero=False)),
      ('missing-HBT-flag',lambda r:r['cases']['p-initial-high']['flags'].update(actual_HBT_targets=317)),
      ('missing-native-vector',lambda r:r['cases']['p-initial-high']['zero_source_op'].update(columns=4725)),
      ('altered-OP-bytes',lambda r:r['outputs'].update({'p-initial-high/op.raw':'0'*64})),
      ('altered-prepared-deck',lambda r:r['outputs'].update({'fresh-preparation/cases/p-initial-high/bench.cir':'0'*64})),
      ('missing-case',lambda r:r['cases'].pop('n-initial-low')),
      ('old-current-model',lambda r:r['current_AVSS18_preparation']['current_models'].update(p=d.loaded.old_binding.MODELS['p'])),
      ('wrong-preparation-identity',lambda r:r['current_AVSS18_preparation'].update(preparation_summary_sha256='0'*64)),
      ('wrong-binding-identity',lambda r:r['current_AVSS18_preparation'].update(binding_summary_sha256='0'*64)),
      ('lost-previous-failure',lambda r:r['original17_HBT_rejection']['all17_original_failed_HBT_records'].pop(next(iter(r['original17_HBT_rejection']['all17_original_failed_HBT_records'])))),
      ('erased-previous-review',lambda r:r['original17_HBT_rejection']['original_complete_review'].update(passed=True)),
      ('missing-current-RC-file',lambda r:r['outputs'].pop('fresh-preparation/authenticated-RC/result.json')),
      ('missing-output',lambda r:r['outputs'].pop(next(iter(r['outputs'])))),
      ('claim-transient',lambda r:r.update(transient_executed=True)),
      ('claim-extraction',lambda r:r.update(new_extraction_performed=True)),
      ('claim-geometry',lambda r:r.update(geometry_generation_executed=True)),
      ('old-R-rescaled',lambda r:r.update(old_R_rescaled=True))]
    for name,change in edits:
        r=copy.deepcopy(op);change(r);op_faults.append(reject(name,lambda:a.validate(r)))
    original=(metadata['run'],metadata['job'],metadata['release'],metadata['tag']);meta=[]
    for index,key,value in [(0,'id',1),(0,'head_sha','0'*40),(0,'status','in_progress'),(0,'conclusion','failure'),
      (0,'run_attempt',2),(0,'path','other.yml'),(0,'head_branch','other'),(1,'id',1),(1,'head_sha','0'*40),(1,'conclusion','failure'),
      (2,'id',1),(2,'draft',True),(2,'prerelease',False),(2,'target_commitish','0'*40)]:
        rows=copy.deepcopy(original);rows[index][key]=value
        meta.append(reject(str(index)+':'+key,lambda:a.validate_metadata(*rows)))
    for key,value in [('sha','0'*40),('type','tag')]:
        rows=copy.deepcopy(original);rows[3]['object'][key]=value
        meta.append(reject('tag:'+key,lambda:a.validate_metadata(*rows)))
    for key,value in [('id',1),('size',1),('digest','sha256:'+'0'*64),('state','new')]:
        rows=copy.deepcopy(original);asset=next(x for x in rows[2]['assets']if x['id']==a.ASSETS['archive']['id']);asset[key]=value
        meta.append(reject('asset:'+key,lambda:a.validate_metadata(*rows)))
    source,derivation=controller.derived_program();support,source_proof=d.derived_program()
    ns,_=controller.program_namespace();current=ns['review']
    original_globals={module.__name__:dict(vars(module))for module in (d.frozen,d.loaded.old_initialization,d.loaded.old_paths,d.loaded.old_bench,d.loaded.old_binding)}
    for name in d.PRESERVED:
        assert getattr(current,name).__code__ is getattr(d.frozen,name).__code__
        assert getattr(current,name).__globals__ is current.__dict__
    assert current.METHOD==d.METHOD and current.OP['run']==a.SOURCE['run']and current.OP['summary_sha256']==a.SOURCE['summary']
    assert current.validate_OP(op,metadata['run'])
    original_regression=original_check.controls()
    portable=ns['controls']();assert portable['count']==22
    asset_controls=continuation_asset_controls(source)
    assert original_check.budget_seam(source)
    derivation_faults=[reject('changed-frozen-lifecycle',lambda:controller.derived_program((controller.ROOT/controller.ORIGINAL).read_text()+'\n')),
      reject('changed-frozen-support',lambda:d.derived_program((d.ROOT/d.ORIGINAL).read_text()+'\n')),
      reject('Docker-config-shadow',lambda:original_check.budget_seam(source.replace('docker_config_program','config'))),
      reject('budget-unbound',lambda:original_check.budget_seam(source.replace("seconds==config['segment_seconds']==13200","seconds==13200")))]
    current_row,contract=original_check.positive_fixture()
    assert current.gate(current_row,contract)==d.frozen.gate(current_row,contract)
    entries=[main_entry_fixture(stage)for stage in ('initial','cross')]
    prepare_entry=preparation_entry_fixture();old_entry=preparation_entry_fixture(True)
    for module in (d.frozen,d.loaded.old_initialization,d.loaded.old_paths,d.loaded.old_bench,d.loaded.old_binding):
        assert all(vars(module)[k]is value for k,value in original_globals[module.__name__].items())
    archive=a.frozen.archive_controls()
    contexts=context_controls(op)
    assert len(op_faults)==len(meta)==20 and len(derivation_faults)==4
    assert len(original_regression['negative_controls'])==52 and len(archive['rejected'])==13 and archive['inherited_parts_controls']['negative_controls']==6
    controller.methods()
    return dict(status='PASS_CURRENT_AVSS18_PORTABLE_SOURCE_CONTROLS_ONLY',import_closure=imports,
      prerequisite=metadata,OP_faults=op_faults,metadata_faults=meta,context_controls=contexts,
      lifecycle_derivation=derivation,support_derivation=source_proof,derivation_faults=derivation_faults,
      numerical_functions_use_exact_original_code_objects=True,original_module_globals_unchanged=True,
      actual_main_entry_positives=entries,actual_preparation_entry=prepare_entry,legacy_preparation_refusal=old_entry,
      inherited_original_numerical_controls=original_regression,current_portable_controls=portable,continuation_asset_controls=asset_controls,archive_controls=archive,
      actual_restored18_source_plus32_path_controls_required_before_engine=True,
      actual_restore_executed=False,native_simulator_invoked=False,transient_executed=False,
      all17_previous_HBT_failures_retained=True,full_PHY_accepted=False)

if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
