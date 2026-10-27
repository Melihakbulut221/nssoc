#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/admission/main-entry and portable controls; never native qualification."""
import ast,copy,io,json,os,sys,tempfile,types
from pathlib import Path
from unittest import mock
import cloud_tx_phase_reset334_tail_m4_transient as controller
import tx_phase_reset334_tail_m4_transient_admission as a
import tx_phase_reset334_tail_m4_transient_adapter as d
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

def prepare_completion_fixture(missing_summary=False):
    """Run the actual derived prepare to return with synthetic IO/runtime collaborators."""
    module=d.session();seen=[]
    if missing_summary:
        text,_=d.derived_program()
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='prepare')
        function=ast.get_source_segment(text,node)
        assert function.count('    summary=json.loads(summary_raw)')==1
        function=function.replace('    summary=json.loads(summary_raw)\n','')
        exec(compile(function,'<actual-prepare-missing-summary-mutation>','exec'),module.__dict__)
    def forbidden(*args,**kwargs):raise AssertionError('No real transport or simulator permitted')
    module.methods=lambda:dict(native_transient_authorized=True,initial_case='p-initial-high')
    module.publication=types.SimpleNamespace(context=lambda *x:('fixture-tag','a'*40),api=lambda *x:{},validate_release=lambda *x:dict(fixture=True))
    module.preparation=types.SimpleNamespace(asset=forbidden,api=forbidden)
    with tempfile.TemporaryDirectory()as directory:
        root=Path(directory);prepared=root/'prepared';out=root/'out';out.mkdir()
        contract=dict(fixture='synthetic control-flow contract; not318 device acceptance')
        summary=dict(original_parent_TX_rejection=dict(electrical_screen_passed=False,fixture='unchanged rejection'))
        summary_raw=d.encode(summary);models={'p':'fixture-P','n':'fixture-N'}
        model_hashes={p:d.digest(b)for p,b in models.items()}
        original=['V'+str(i)+' n'+str(i)+' 0 0\n'for i in range(5)]
        original+=['.lib old-h hbt_typ\n','.lib old-r res_typ\n','.lib old-c cap_typ\n',
          '.include old-p\n','.include old-n\n','pre_osdi old-osdi\n',
          'save v(n)\n','.tran .3125p 34n\n','run wave.raw\n']
        base=''.join(original);changed=list(original)
        edits=[]
        for index in range(5,11):
            changed[index]=original[index].replace('old-','fixture-runtime-')
            edits.append(dict(line=index,old=original[index],new=changed[index]))
        runtime_base=''.join(changed);flag='* synthetic uniform OFF fixture\n';op_deck='synthetic OP-only fixture\n'
        def check_contract(label,deck,c,raw):
            assert label=='p-initial-high'and deck==base and c==contract and raw==summary_raw
            seen.append('contract')
        adapters=types.SimpleNamespace(op_only=lambda deck,c,active:op_deck,
          initialized_deck=lambda deck,c:deck+flag,flag_block=lambda c,active:flag)
        initialization=types.SimpleNamespace(digest=d.digest,prepared_contract=check_contract,adapters=lambda:adapters,
          PREPARATION=dict(run=a.SOURCE['run'],head=a.SOURCE['head'],summary_sha256=d.digest(summary_raw)))
        native=types.SimpleNamespace(ENGINE_SHA=d.digest(b'fixture ELF identity only'),OUT=None)
        manifest=dict(files={'models/fixture.lib':dict(bytes=len(b'fixture library'),sha256=d.digest(b'fixture library'))})
        engine_proof=dict(engine_sha256=native.ENGINE_SHA,model_manifest=manifest)
        def fake_runtime():
            assert native.OUT==prepared/'runtime'and native.OUT.is_dir()
            engine=native.OUT/'fixture-engine';engine.write_bytes(b'fixture ELF identity only')
            libs=native.OUT/'libs';(libs/'models').mkdir(parents=True)
            (libs/'models/fixture.lib').write_bytes(b'fixture library')
            seen.append('synthetic-runtime-files')
            return engine,libs,engine_proof
        native.restore=fake_runtime
        def fake_paths(label,deck,c,raw,model_values,model_paths,model_dir,osdi):
            assert label=='p-initial-high'and deck==base and c==contract and raw==summary_raw
            assert model_values==models and all(model_paths[p].read_text()==models[p]for p in models)
            assert str(model_dir).endswith('/runtime/libs/models')and str(osdi).endswith('/runtime/libs/r3_cmc.osdi')
            return op_deck,dict(six_path_cards=edits,runtime_base_sha256=d.digest(runtime_base))
        paths=types.SimpleNamespace(runtime_deck=fake_paths,bench=types.SimpleNamespace(binding=types.SimpleNamespace(MODELS=model_hashes)))
        module.initialization=initialization;module.paths=paths;module.native=native
        def restore(label,prep,destination):
            assert prep==prepared and destination==out;prep.mkdir()
            model_paths={p:prep/(p+'.spice')for p in models}
            for p,path in model_paths.items():path.write_text(models[p])
            op=dict(cases={label:dict(contract_sha256=d.digest(d.encode(contract)))},runtime_and_models=engine_proof)
            proof=dict(summary_sha256=initialization.PREPARATION['summary_sha256'],outer_zero_OP_summary_sha256=a.SOURCE['summary'])
            seen.append('synthetic-current-restoration')
            return b'fixture outer OP',op,summary_raw,base,contract,model_paths,models,proof,initialization.PREPARATION
        module._restore_current=restore
        try:answer=module.prepare('p-initial-high',prepared,out,'fixture')
        except NameError as error:
            assert missing_summary and error.name=='summary'
            assert seen==['synthetic-current-restoration','contract','synthetic-runtime-files']
            assert(prepared/'native/bench.cir').read_text()==runtime_base+flag
            return dict(actual_missing_summary_fault_rejected=True,failed_after_final_native_deck_write=True)
        assert not missing_summary
        prepared_report,proof,c,engine,spec=answer
        assert seen==['synthetic-current-restoration','contract','synthetic-runtime-files']
        assert proof['original_parent_TX_rejection']==summary['original_parent_TX_rejection']
        assert proof['summary_sha256']==spec['summary_sha256']==d.digest(summary_raw)
        assert proof['outer_zero_OP_summary_sha256']==a.SOURCE['summary']
        assert proof['zero_OP_run']==a.SOURCE['run']and proof['zero_OP_summary_sha256']==a.ASSETS['native']['sha256']
        assert c==contract and engine.read_bytes()==b'fixture ELF identity only'
        assert all(Path(p).is_file()and d.digest(Path(p).read_bytes())==h for p,h in prepared_report['protected_inputs'].items())
        assert(prepared/'native/bench.cir').read_text()==runtime_base+flag
    return dict(actual_derived_prepare_return_reached=True,final_original_parent_rejection_assignment_reached=True,
      complete_prepared_input_map_checked=True,synthetic_runtime_path_helpers_only=True,no_archive_or_native_engine=True)

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
    spec=dict(group='tx-phase-reset334-tail-m4-transient-native-initial-p-initial-high',run=123)
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


def outer_admission_controls(outer,native):
    assert a.validate_outer(outer,native)
    changes=[
      ('run',lambda r:r.update(run_id=1)),
      ('head',lambda r:r.update(source_head='0'*40)),
      ('attempt',lambda r:r.update(run_attempt=2)),
      ('status',lambda r:r.update(status='RUNNING')),
      ('qualification',lambda r:r.update(zero_op_qualification_complete=False)),
      ('native-present',lambda r:r.update(native_result_present=False)),
      ('source-integrity',lambda r:r.update(protected_sources_unchanged=False)),
      ('native-hash',lambda r:r.update(native_result_sha256='0'*64)),
      ('native-size',lambda r:r.update(native_result_bytes=1)),
      ('native-path',lambda r:r.update(native_result_raw_path='other.json')),
      ('missing-native-member',lambda r:r['outputs'].pop('native/result.json')),
      ('native-view-substitution',lambda r:r['outputs'].update({'outer-result.json':r['outputs'].pop('native/result.json')})),
      ('binding',lambda r:r['outputs'].update({'fresh-binding.summary.json':'0'*64})),
      ('preparation',lambda r:r['outputs'].update({'fresh-preparation.summary.json':'0'*64})),
      ('electrical-claim',lambda r:r.update(electrical_accepted=True)),
      ('transient-claim',lambda r:r.update(transient_executed=True)),
      ('supervisor-return',lambda r:r['supervisor'].update(returncode=1)),
      ('supervisor-failure',lambda r:r['supervisor'].update(supervision_failure='synthetic failure')),
      ('live-child',lambda r:r['supervisor']['process_group_cleanup'].update(remaining_live=[123])),
      ('embedded-native-substitute',lambda r:r['native_result'].update(source_head='0'*40))]
    rejected=[]
    for name,change in changes:
        bad=copy.deepcopy(outer);change(bad)
        assert d.encode(bad)!=d.encode(outer),name
        rejected.append(reject(name,lambda:a.validate_outer(bad,native)))
    assert len(rejected)==20
    return dict(positive=1,rejected=rejected,complete_outer_files=3286,complete_native_files=3271,
        all_prepared_files=3201,actual_authenticated_JSONs_only=True,no_archive=True)

def authorization_controls(method):
    positives=[];rejected=[]
    flags=('source_controls_authorized','native_transient_authorized','simulation_authorized',
        'native_continuation_authorized','geometry_generation_authorized','extraction_authorized','other_cases_authorized')
    with tempfile.TemporaryDirectory()as temporary:
        root=Path(temporary);path=root/'method.json';pinned=root/'protected.py';pinned.write_bytes(b'fixture pinned bytes\n')
        def load(value):
            path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
            return controller.methods()
        with mock.patch.multiple(controller,ROOT=root,METHOD=path):
            for enabled in (False,True):
                base=copy.deepcopy(method);base.update(source_unit_complete=True,source_controls_authorized=True,
                    native_transient_authorized=enabled,simulation_authorized=enabled,
                    native_continuation_authorized=False,geometry_generation_authorized=False,
                    extraction_authorized=False,other_cases_authorized=False)
                base['protected']={'protected.py':controller.sha(pinned)}
                assert load(base)==base;positives.append('native-'+str(enabled))
                edits=[
                    ('incomplete-unit',lambda r:r.update(source_unit_complete=False)),
                    ('split-native-pair',lambda r:r.update(native_transient_authorized=not r['native_transient_authorized'])),
                    *[(key+'-not-bool',lambda r,key=key:r.__setitem__(key,int(r[key])))for key in flags],
                    *[(key,lambda r,key=key:r.__setitem__(key,True))for key in
                      ('geometry_generation_authorized','extraction_authorized','other_cases_authorized')],
                    ('budget',lambda r:r.update(segment_seconds=13201)),
                    ('other-case',lambda r:r.update(initial_case='n-initial-low')),
                    ('VCE',lambda r:r.update(original_minimum_VCE_v=.39)),
                    ('step',lambda r:r.update(original_step_s=.625e-12)),
                    ('stop',lambda r:r.update(original_stop_s=33e-9)),
                    ('UI',lambda r:r.update(original_UI_samples=[.5])),
                    ('first-fall',lambda r:r.update(original_first_fall_limit_s=63e-12)),
                    ('margin',lambda r:r.update(minimum_signed_margin_v=.09)),
                    ('protected-source',lambda r:r['protected'].update({'protected.py':'0'*64}))]
                assert len(edits)==21
                for label,change in edits:
                    bad=copy.deepcopy(base);change(bad)
                    assert d.encode(bad)!=d.encode(base),(enabled,label)
                    rejected.append(reject(str(enabled)+':'+label,lambda:load(bad)))
                if enabled:
                    old=copy.deepcopy(base);old['native_transient_authorized']=True
                    assert d.encode(old)==d.encode(base)and load(old)==base
                    try:reject('activated-no-op',lambda:load(old))
                    except AssertionError as error:assert str(error)=='Accepted activated-no-op'
                    else:raise AssertionError('The exact activated no-op was misreported as a rejection')
    assert len(positives)==2 and len(rejected)==42
    return dict(positive=positives,rejected=rejected,both_actual_methods_modes_exercised=True,
        every_mutation_type_sensitive_and_applicable=True,activated_no_op_regression_reproduced=True)

def preflight_controls(method):
    positives=[];rejected=[]
    with tempfile.TemporaryDirectory()as temporary:
        root=Path(temporary);path=root/'method.json'
        base=copy.deepcopy(method);base.update(source_unit_complete=True,protected={},
            source_controls_authorized=True,native_transient_authorized=True,simulation_authorized=True,
            native_continuation_authorized=False,geometry_generation_authorized=False,
            extraction_authorized=False,other_cases_authorized=False)
        calls=[]
        def completed(m):assert m['native_transient_authorized']is True;calls.append('controls');return {'fixture':True}
        def wait(group,env):assert group.startswith('tx-phase-reset334-tail-m4-transient-native-');calls.append('wait')
        def context(group,env):calls.append('context');return 'fixture-tag','a'*40
        def api(path):calls.append(path);return {'fixture':path}
        def validation(*args):calls.append('validate');return dict(existing_assets=[])
        def invoke(value,stage='initial',case='p-initial-high'):
            path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
            return controller.preflight(stage,case)
        with mock.patch.multiple(controller,ROOT=root,METHOD=path,completed_controls=completed),             mock.patch.object(controller.waiter,'wait',wait),             mock.patch.multiple(controller.release,context=context,api=api,validate_release=validation),             mock.patch.dict(os.environ,{'ImageOS':'ubuntu24'}):
            for stage in ('initial','cross'):
                value=copy.deepcopy(base);value['native_continuation_authorized']=stage=='cross';calls.clear()
                result=invoke(value,stage)
                assert result['completed_controls']=={'fixture':True}
                assert calls==['controls','wait','context','releases/tags/fixture-tag','git/ref/tags/fixture-tag','validate']
                positives.append(stage)
            disabled=copy.deepcopy(base);disabled.update(native_transient_authorized=False,simulation_authorized=False)
            rejected.append(reject('disabled-native',lambda:invoke(disabled)))
            rejected.append(reject('unauthorized-continuation',lambda:invoke(base,'cross')))
            rejected.append(reject('other-case',lambda:invoke(base,case='n-initial-low')))
            rejected.append(reject('unknown-stage',lambda:invoke(base,'unknown')))
            with mock.patch.dict(os.environ,{'ImageOS':'ubuntu22'}):
                rejected.append(reject('wrong-runner-image',lambda:invoke(base)))
            with mock.patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'2'}):
                rejected.append(reject('repeated-attempt',lambda:invoke(base)))
            with mock.patch.object(controller.release,'validate_release',lambda *args:dict(existing_assets=[{'id':1}])):
                rejected.append(reject('nonempty-reservation',lambda:invoke(base)))
    assert len(positives)==2 and len(rejected)==7
    return dict(positive=positives,rejected=rejected,actual_preflight_and_methods=True,
        only_release_transport_and_completed_proof_collaborators_synthetic=True,no_network=True)


def terminal_controls():
    cases=[];saved='SAVED_PHYSICAL334_THREE_MODEL_NATIVE_PROCESS_REQUIRES_CONTINUATION_AND_FULL_REVIEW'
    complete='COMPLETE_PHYSICAL334_THREE_MODEL_FULL_NATIVE_CAPTURE_REQUIRES_REVIEW_AND_FULL_PHY'
    rejected='REJECTED_PHYSICAL334_THREE_MODEL_ORIGINAL_LOADED_GATES'
    labels=('saved','complete','electrical-rejected','body-failure','missing','truncated',
        'source-integrity','previous-fragment','previous-native-copy','encoding-failure','inventory-symlink','body-and-write-failure')
    for label in labels:
        with tempfile.TemporaryDirectory()as temporary:
            root=Path(temporary);out=root/('cloud-'+controller.group('initial','p-initial-high'))
            primary=RuntimeError('synthetic original body failure: '+label);seen=[];raw=None;stderr=io.StringIO()
            def body():
                nonlocal raw
                assert not out.exists(),'Wrapper created lifecycle output before original main'
                out.mkdir();(out/'partial-evidence.log').write_bytes(b'complete synthetic evidence\n')
                native=dict(status=saved if label=='saved'else complete,electrical_screen_passed=label=='complete',
                    native_process_saved=label=='saved',full_capture=label!='saved',
                    original17_HBT_rejection={'fixture':17},prior_four_tail_rejection={'fixture':4})
                if label=='electrical-rejected'or label=='body-and-write-failure':
                    native.update(status=rejected,electrical_screen_passed=False)
                if label=='body-failure':native.update(status='RUNNING',electrical_screen_passed=False)
                if label=='encoding-failure':native['synthetic_nonfinite']=float('nan')
                if label!='missing':
                    raw=b'{"status":'if label=='truncated'else(json.dumps(native,indent=2)+'\n').encode()
                    (out/'result.json').write_bytes(raw)
                if label=='previous-fragment':(out/'result.json.writing').write_bytes(b'original partial write\n')
                if label=='previous-native-copy':(out/'native-lifecycle-result.json').write_bytes(b'prior native copy\n')
                if label=='inventory-symlink':(out/'linked-evidence').symlink_to(out/'partial-evidence.log')
                seen.append('body')
                if label in ('electrical-rejected','body-failure','body-and-write-failure'):raise primary
            def final_methods():
                seen.append('terminal-integrity')
                if label=='source-integrity':raise AssertionError('synthetic protected source changed')
                return {}
            def hard_write(*args):raise OSError('synthetic terminal write failure')
            old_argv=sys.argv
            with mock.patch.multiple(controller,ROOT=root,preflight=lambda *args:dict(synthetic_release=True),
                program_namespace=lambda:({'main':body},dict(synthetic_namespace=True)),methods=final_methods),                mock.patch.object(sys,'stderr',stderr):
                with mock.patch.object(controller,'write_terminal',hard_write)if label=='body-and-write-failure'else mock.patch.dict({},{}):
                    error=None
                    try:controller.main('initial','p-initial-high')
                    except BaseException as caught:error=caught
            assert sys.argv is old_argv and seen==['body','terminal-integrity']
            if label in ('saved','complete'):assert error is None
            elif label in ('electrical-rejected','body-failure','body-and-write-failure'):assert error is primary
            else:assert isinstance(error,RuntimeError),(label,error)
            if raw is not None:
                assert(out/'native-lifecycle-result.json').read_bytes()==raw
            if label=='body-and-write-failure':
                assert(out/'result.json').read_bytes()==raw
                diagnostic=json.loads(stderr.getvalue());assert diagnostic['terminal_result_write_failed']is True
                assert diagnostic['primary_error']==repr(primary)and'OSError'in diagnostic['terminal_error']
            else:
                result=json.loads((out/'result.json').read_bytes())
                if label in ('saved','complete'):assert result['status']in (saved,complete)and result['wrapper_terminal_complete']
                elif label=='electrical-rejected':assert result['status']==rejected and not result['electrical_screen_passed']
                else:assert result['status']=='FAIL_OR_ERROR'and result['electrical_screen_passed']is False
                if raw is not None:
                    assert result['native_lifecycle_result_sha256']==d.digest(raw)
                    assert result['native_lifecycle_result_bytes']==len(raw)
                assert result['outputs']['partial-evidence.log']==d.digest(b'complete synthetic evidence\n')
                for name,h in result['outputs'].items():
                    assert not(out/name).is_symlink()and controller.sha(out/name)==h
                if label=='previous-fragment':
                    assert(out/'result.json.writing.preserved-0').read_bytes()==b'original partial write\n'
                if label=='previous-native-copy':
                    assert(out/'native-lifecycle-result.json.preserved-0').read_bytes()==b'prior native copy\n'
                if label=='encoding-failure':
                    fragments=[p for p in out.glob('result.json.writing.preserved-*')]
                    assert len(fragments)==1 and fragments[0].stat().st_size>0
                    assert result['outputs'][fragments[0].name]==controller.sha(fragments[0])
                    assert result['full_native_observations_preserved_by_raw_result']is True
                if label=='source-integrity':
                    assert json.loads(raw)['status']==complete and result['status']=='FAIL_OR_ERROR'
            cases.append(dict(name=label,actual_outer_main_and_finally=True,
                original_primary_exception_preserved=label in ('electrical-rejected','body-failure','body-and-write-failure'),
                no_archive_or_native=True))
    assert len(cases)==12
    return dict(cases=cases,positive=2,refusal=10,synthetic_native_body_only=True)

def controls():
    m=controller.methods();assert m['source_controls_authorized']is True
    imports=inherited_imports.import_closure(controller.ROOT,m['protected'],m['import_roots'])
    for path in m['required_repository_modules']:assert path in m['protected']and(controller.ROOT/path).is_file()
    outer,metadata=a.prerequisite();native_raw,op=a.native_snapshot()
    assert a.validate(op)and a.validate_outer(outer,op)and len(a.expected_files(outer))==3286
    assert len(op['outputs'])+1==3271 and len(op['current_TAIL_M4_preparation']['all_prepared_files'])==3201
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
      ('old-current-model',lambda r:r['current_TAIL_M4_preparation']['current_models'].update(p=d.loaded.old_binding.MODELS['p'])),
      ('wrong-preparation-identity',lambda r:r['current_TAIL_M4_preparation'].update(preparation_summary_sha256='0'*64)),
      ('wrong-binding-identity',lambda r:r['current_TAIL_M4_preparation'].update(binding_summary_sha256='0'*64)),
      ('lost-previous-failure',lambda r:r['original17_HBT_rejection']['all17_original_failed_HBT_records'].pop(next(iter(r['original17_HBT_rejection']['all17_original_failed_HBT_records'])))),
      ('erased-previous-review',lambda r:r['original17_HBT_rejection']['original_complete_review'].update(passed=True)),
      ('missing-current-RC-file',lambda r:r['outputs'].pop('fresh-preparation/authenticated-RC/result.json')),
      ('missing-output',lambda r:r['outputs'].pop(next(iter(r['outputs'])))),
      ('claim-transient',lambda r:r.update(transient_executed=True)),
      ('claim-extraction',lambda r:r.update(new_extraction_performed=True)),
      ('claim-geometry',lambda r:r.update(geometry_generation_executed=True)),
      ('old-R-rescaled',lambda r:r.update(old_R_rescaled=True)),
      ('lost-prior-four-tail',lambda r:r['prior_four_tail_rejection']['all_four_failed_HBT_records'].pop(next(iter(r['prior_four_tail_rejection']['all_four_failed_HBT_records'])))),
      ('runtime-not-installed',lambda r:r.update(runtime_installed=False)),
      ('loosened-solver',lambda r:r['cases']['p-initial-high']['solver']['numeric_options'].update(reltol=1e-3)),
      ('wrong-native-view',lambda r:r['current_TAIL_M4_preparation']['current_RC'].update(consumed_native_view='outer'))]
    for name,change in edits:
        r=copy.deepcopy(op);change(r);assert d.encode(r)!=d.encode(op),name
        op_faults.append(reject(name,lambda:a.validate(r)))
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
    assert current.METHOD==d.METHOD and current.OP['run']==a.SOURCE['run']and current.OP['summary_sha256']==a.ASSETS['native']['sha256']
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
    completion=prepare_completion_fixture();missing_summary_fault=prepare_completion_fixture(True)
    for module in (d.frozen,d.loaded.old_initialization,d.loaded.old_paths,d.loaded.old_bench,d.loaded.old_binding):
        assert all(vars(module)[k]is value for k,value in original_globals[module.__name__].items())
    archive=a.frozen.archive_controls()
    contexts=context_controls(op)
    assert len(op_faults)==24 and len(meta)==20 and len(derivation_faults)==4
    assert len(original_regression['negative_controls'])==52 and len(archive['rejected'])==13 and archive['inherited_parts_controls']['negative_controls']==6
    outer_controls=outer_admission_controls(outer,op)
    authorization=authorization_controls(m)
    preflight=preflight_controls(m)
    terminal=terminal_controls()
    controller.methods()
    return dict(status='PASS_CURRENT_TAIL_M4_PORTABLE_SOURCE_CONTROLS_ONLY',import_closure=imports,
      prerequisite=metadata,OP_faults=op_faults,outer_admission=outer_controls,metadata_faults=meta,context_controls=contexts,
      authorization_controls=authorization,preflight_controls=preflight,actual_outer_terminal_controls=terminal,
      lifecycle_derivation=derivation,support_derivation=source_proof,derivation_faults=derivation_faults,
      numerical_functions_use_exact_original_code_objects=True,original_module_globals_unchanged=True,
      actual_main_entry_positives=entries,actual_preparation_entry=prepare_entry,legacy_preparation_refusal=old_entry,
      actual_prepare_completion=completion,missing_summary_refusal=missing_summary_fault,
      inherited_original_numerical_controls=original_regression,current_portable_controls=portable,continuation_asset_controls=asset_controls,archive_controls=archive,
      actual_restored18_source_plus32_path_controls_required_before_engine=True,
      actual_restore_executed=False,native_simulator_invoked=False,transient_executed=False,
      all17_previous_HBT_failures_retained=True,prior_four_tail_failures_retained=True,full_PHY_accepted=False)

if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
