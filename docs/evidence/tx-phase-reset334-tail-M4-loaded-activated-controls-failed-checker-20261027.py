#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted full-main/context/transport/failure fixtures; no original electrical threshold changes."""
import ast,contextlib,copy,io,json,os,sys,tempfile,types
from pathlib import Path
from unittest import mock
import tx_phase_reset334_tail_m4_loaded_admission as a
import tx_phase_reset334_tail_m4_loaded_adapter as d
import cloud_tx_phase_reset334_tail_m4_loaded as controller
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

def inherited_controls():
    m=controller.methods();assert m['source_controls_authorized']is True
    for p in m['required_repository_modules']:assert p in m['protected']and(controller.ROOT/p).is_file()
    outer,metadata=a.prerequisite();_,r=a.native_snapshot();assert a.validate(r)and a.validate_outer(outer,r)
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
      refusal('changed-frozen-controller',mutated_derivation)]
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
    code,derivation=controller.derive()
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
    return dict(status=controller.STATUS,
      actual_controller_imported=True,prerequisite=metadata,RC_faults=faults,metadata_faults=metadata_faults,context_faults=context_faults,
      all_original_function_code_objects_identical=True,original_module_globals_unchanged=True,main_derivation=derivation,actual_main_entry_positives=entries,
      inherited_preparation=source,inherited_initialization=initialization,inherited_zero_OP=zero,archive_controls=archive,
      original_failed_HBT_count=17,actual_binding_or_preparation_executed=False,simulation_executed=False,extraction_executed=False)


def mutated_derivation():
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);m=controller.methods()
        for path in (controller.ORIGINAL,controller.CONTEXT):
            p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((controller.ROOT/path).read_bytes())
        changed=root/controller.ORIGINAL;changed.write_bytes(changed.read_bytes()+b'\n')
        with mock.patch.object(controller,'ROOT',root),mock.patch.object(controller,'methods',return_value=m):
            return controller.derive()


def outer_view_controls():
    _,outer=a.snapshot();_,native=a.native_snapshot();assert a.validate_outer(outer,native)
    rejected=[]
    changes=[
      ('outer-run',lambda x:x.update(run_id=1)),('outer-source',lambda x:x.update(source_head='0'*40)),
      ('outer-attempt',lambda x:x.update(run_attempt=2)),('outer-status',lambda x:x.update(status='PASS')),
      ('erased-native',lambda x:x.pop('native_result')),('raw-native-hash',lambda x:x.update(native_result_sha256='0'*64)),
      ('raw-native-size',lambda x:x.update(native_result_bytes=1)),('raw-native-path',lambda x:x.update(native_result_raw_path='result.json')),
      ('missing-outer-member',lambda x:x['outputs'].pop('native-RC-result.json')),
      ('native-view-result',lambda x:x['outputs'].update({'native/result.json':'0'*64})),
      ('native-view-model',lambda x:x['outputs'].update({'native/precision/p/composition/reset334-wire.spice':'0'*64})),
      ('full-physical-result',lambda x:x['outputs'].update({'native/intrinsic/physical/result.json':'0'*64})),
      ('consumed-physical-result',lambda x:x['outputs'].update({'native/intrinsic/physical/native/result.json':'0'*64})),
      ('same-count-native-alias',lambda x:x['outputs'].update({'native/aliased-result.json':x['outputs'].pop('native/result.json')})),
      ('supervisor-return',lambda x:x['supervisor'].update(returncode=1)),
      ('supervisor-memory-error',lambda x:x['supervisor'].update(memory_read_error='fixture')),
      ('supervisor-failure',lambda x:x['supervisor'].update(supervision_failure='fixture')),
      ('remaining-live',lambda x:x['supervisor']['process_group_cleanup'].update(remaining_live=[123])),
      ('changed-min-available',lambda x:x['supervisor'].update(minimum_available_kib=1)),
      ('changed-max-rss',lambda x:x['supervisor'].update(maximum_group_rss_kib=1)),
      ('erased-electrical-rejection',lambda x:x.update(original_electrical_rejection_preserved=False)),
      ('simulation-claim',lambda x:x.update(simulation_executed=True)),
      ('geometry-claim',lambda x:x.update(geometry_generation_executed=True)),
      ('source-integrity',lambda x:x.update(protected_sources_unchanged=False))]
    for name,edit in changes:
        bad=copy.deepcopy(outer);edit(bad);rejected.append(refusal(name,lambda:a.validate_outer(bad,native)))
    expected=a.expected_files(outer)
    assert len(expected)==3181 and expected['result.json']==a.SOURCE['summary']
    assert {p[7:]:h for p,h in expected.items()if p.startswith('native/')}==dict(native['outputs'],**{'result.json':a.ASSETS['native']['sha256']})
    assert len(rejected)==24
    return dict(complete_outer_members=3181,complete_consumed_native_members=3165,exact_full_set_equality=True,rejected=rejected)


def prepare_completion_fixture(wrong_consumption_root=False):
    """Execute the complete actual prepare body with explicit synthetic collaborators, never an archive."""
    seen=[];models={pol:'.subckt fixture_'+pol+' a b\n.ends\n'for pol in ('p','n')}
    hashes={pol:d.digest(text)for pol,text in models.items()}
    composition={pol:dict(fixture=pol)for pol in ('p','n')}
    source_netlist=(d.ROOT/d.SOURCE).read_text()
    originals=d.original_rejections();four=d.prior_four_tail_rejection()
    source=ast.get_source_segment((controller.ROOT/'scripts/tx_phase_reset334_tail_m4_loaded_adapter.py').read_text(),
      next(n for n in ast.parse((controller.ROOT/'scripts/tx_phase_reset334_tail_m4_loaded_adapter.py').read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='prepare'))
    if wrong_consumption_root:
        old="base=destination/'authenticated-RC/native'";new="base=destination/'authenticated-RC'"
        assert source.count(old)==1;source=source.replace(old,new)
    def restore(destination):
        seen.append('restore-stub')
        for pol in ('p','n'):
            base=destination/'native/precision'/pol
            (base/'source').mkdir(parents=True);(base/'composition').mkdir()
            d.write(base/'source/native.json',dict(fixture_native=pol))
            d.write(base/'composition/composition.json',composition[pol])
            (base/'composition/reset334-wire.spice').write_text(models[pol])
        return dict(polarities={p:dict(composition=composition[p])for p in ('p','n')}),dict(variants={p:dict(generation={'fixture_geometry':p},wires={'anchors':{'fixture_planes':p}})for p in ('p','n')}),dict(fixture_transport=True)
    def binding_controls(case):
        pol=case['sign'];assert case['text']==source_netlist and case['composition']==composition[pol]
        assert case['native']==dict(fixture_native=pol)and case['model_text']==models[pol]
        assert case['geometry']=={'fixture_geometry':pol}and case['planes']=={'fixture_planes':pol}
        seen.append('binding:'+pol)
        return dict(negative_controls=['synthetic_'+str(i)for i in range(20)],controls_passed=True,positive=dict(fixed_internal_probes={'fixture':pol}))
    binding=types.SimpleNamespace(controls=binding_controls,MODELS=hashes)
    def bench_context(raw,payload,b):
        summary=json.loads(raw);assert b is binding and summary['current_RC_run']==a.SOURCE['run']
        assert set(payload)=={'p','n'};return types.SimpleNamespace(SUMMARY_SHA=d.digest(raw))
    def positive_prepare(raw,payload,mm,observer,netlist,paths,libs,osdi,destination):
        assert mm==models and observer==b'fixture-observer'and netlist==source_netlist
        result={};destination.mkdir()
        for label in d.LABELS:
            folder=destination/label;folder.mkdir();pol=label[0]
            contract=dict(vectors=['v'+str(i)for i in range(4726)],hbt=['h'+str(i)for i in range(318)],
              thermal_nodes=['t'+str(i)for i in range(390)],binding_summary_sha256=d.digest(raw),instances=[dict(variant=pol,model_sha256=hashes[pol])])
            deck='* synthetic full preparation orchestration fixture\n.tran .3125p 34n\n'
            (folder/'bench.cir').write_text(deck);d.write(folder/'contract.json',contract);result[label]={'fixture':True}
            assert paths[pol].as_posix().endswith('/qualified-binding/qualified-rc/'+pol+'/composition/reset334-wire.spice')
        seen.append('four-preparations')
        return dict(actual_input_faults=['synthetic_'+str(i)for i in range(8)],cases=result)
    def prepared_contract(label,deck,c,raw):
        assert label in d.LABELS and '.tran .3125p 34n'in deck and len(c['vectors'])==4726
        assert json.loads(raw)['prior_four_tail_rejection']==four;seen.append('prepared-contract:'+label)
    init=types.SimpleNamespace(prepared_contract=prepared_contract)
    paths=types.SimpleNamespace(fixture=True);screen=types.SimpleNamespace(fixture=True)
    def runtime_context(bench,raw):
        assert json.loads(raw)['binding_summary_sha256']==bench.SUMMARY_SHA
        seen.append('nested-preparation-context');return init,paths,screen
    def positive_paths(cases,raw,mm):
        assert set(cases)==set(d.LABELS)and mm==models and json.loads(raw)['prior_four_tail_rejection']==four
        seen.append('path-check');return dict(negative_controls=['synthetic_'+str(i)for i in range(32)])
    def isolated(module,overrides):
        if module is d.old_prepare_check:return types.SimpleNamespace(positive_prepare=positive_prepare)
        assert module is d.old_path_check and overrides=={'runtime':paths}
        return types.SimpleNamespace(positive_paths=positive_paths)
    ns=dict(vars(d));ns.update(admission=types.SimpleNamespace(restore=restore,MODELS=hashes,SOURCE=a.SOURCE,physical=a.physical),
      binding_context=lambda:binding,bench_context=bench_context,runtime_context=runtime_context,isolated=isolated,
      frozen_observer=lambda:b'fixture-observer',original_rejections=lambda:originals,prior_four_tail_rejection=lambda:four)
    exec(compile(source,'actual-prepare-completion-fixture','exec'),ns)
    with tempfile.TemporaryDirectory()as td:
        destination=Path(td)/'fresh-preparation'
        try:returned=ns['prepare'](destination)
        except FileNotFoundError:
            assert wrong_consumption_root and seen==['restore-stub']
            return dict(name='old_outer_root_rejected_at_actual_native_read',rejected=True,actual_prepare_body=True)
        assert not wrong_consumption_root
        cases,raw,mm,model_paths,actual_init,actual_paths,actual_screen,proof=returned
        assert set(cases)==set(d.LABELS)and mm==models and actual_init is init and actual_paths is paths and actual_screen is screen
        assert proof['prior_four_tail_rejection']==four and proof['original17_HBT_rejection']==originals[0]
        assert json.loads((destination/'current-preparation-proof.json').read_bytes())==proof
        assert all(d.digest((destination/p).read_bytes())==h for p,h in proof['all_prepared_files'].items())
        assert seen==['restore-stub','binding:p','binding:n','four-preparations','nested-preparation-context']+['prepared-contract:'+x for x in d.LABELS]+['path-check']
        return dict(name='complete_actual_prepare_return_and_manifest',actual_prepare_body=True,actual_return_reached=True,
          synthetic_binding_and_deck_helpers=True,real_RC_archive_or_simulation=False,complete_manifest_files=len(proof['all_prepared_files']),
          original17_and_later4_rejections_preserved=True,sequence=seen)


def native_fixture():
    original,parent=d.original_rejections();four=d.prior_four_tail_rejection()
    return dict(source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),status=controller.PASS,all_four_expanded_zero_OPs_passed=True,sources_unchanged=True,
      native_simulator_invoked=True,runtime_installed=True,current_RC_model_hashes=dict(a.MODELS),original_electrical_rejection_preserved=True,
      transient_executed=False,electrical_phase_accepted=False,all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False,
      old_R_rescaled=False,geometry_generation_executed=False,new_extraction_performed=False,
      original17_HBT_rejection=original,prior_four_tail_rejection=four,
      current_TAIL_M4_preparation=dict(current_models=dict(a.MODELS),current_RC=dict(all3181_files_authenticated=True,native_view_files=3165,consumed_native_view='native',
          outer_summary_sha256=a.SOURCE['summary'],native_summary_sha256=a.ASSETS['native']['sha256'],complete_files=3181,full_current_physical_files=631),physical_source=copy.deepcopy(a.physical.SOURCE),
        binding_faults_per_polarity=20,preparation_faults=8,path_faults=32,unchanged_original_function_code_objects=True),
      cases={label:dict(complete=True,passed=True,errors=[],returncode=0,source_and_runtime_unchanged=True,wave_raw_exists=False,
        expected_HBT_count=318,expected_saved_vectors=4726,zero_OP_gate=dict(passed=True))for label in d.LABELS})


def finalization_fixtures():
    rows=[]
    for mode in ('preflight-refusal','supervisor-refusal','native-rejection','complete-four-OP','truncated-native-result','source-integrity-failure'):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'out';stage=out/'native'
            def flight():
                if mode=='preflight-refusal':raise RuntimeError('EXACT_PREFLIGHT_REFUSAL')
                return {'fixture':True}
            def run():
                stage.mkdir();native=native_fixture()
                if mode not in ('complete-four-OP','source-integrity-failure','truncated-native-result'):native['status']='FAIL_OR_ERROR'
                controller.write(stage/'result.json',native);(stage/'partial.bin').write_bytes(b'complete saved partial evidence')
                if mode=='truncated-native-result':(stage/'result.json').write_bytes(b'{"status":"RUNNING","cases":')
                if mode=='supervisor-refusal':raise RuntimeError('EXACT_SUPERVISOR_REFUSAL')
                return dict(returncode=0 if mode in ('complete-four-OP','source-integrity-failure','truncated-native-result')else 7)
            with mock.patch.object(controller,'OUT',out),mock.patch.object(controller,'STAGE',stage),mock.patch.object(controller,'preflight',flight),\
              mock.patch.object(controller,'run_owned_child',run),mock.patch.object(controller,'derive',return_value=('',{'fixture':True})),\
              mock.patch.object(controller,'methods',side_effect=AssertionError('EXACT_SOURCE_INTEGRITY_FAILURE')if mode=='source-integrity-failure'else None,return_value={}):
                try:controller.main()
                except(RuntimeError,AssertionError,json.JSONDecodeError):assert mode!='complete-four-OP'
                else:assert mode=='complete-four-OP'
                raw=(out/'result.json').read_bytes();r=json.loads(raw)
                assert(r['status']==controller.PASS)==(mode=='complete-four-OP')
                assert r['zero_op_qualification_complete']is(mode=='complete-four-OP')
                for key in ('electrical_accepted','transient_executed','geometry_generation_executed','extraction_executed'):assert r[key]is False
                if mode!='preflight-refusal':
                    assert(out/'native-four-OP-result.json').read_bytes()==(stage/'result.json').read_bytes()
                    assert r['outputs']['native/partial.bin']==controller.sha(stage/'partial.bin')
                    assert r['native_result_sha256']==controller.sha(stage/'result.json')
                if mode=='truncated-native-result':
                    assert'native_result'not in r and r['native_result_present']is True
                    assert'JSONDecodeError'in r['error']and'JSONDecodeError'in r['native_result_parse_error']and r['native_result_parse_traceback']
                if mode=='source-integrity-failure':
                    assert r['protected_sources_unchanged']is False and'EXACT_SOURCE_INTEGRITY_FAILURE'in r['source_error']
                    assert r['native_result']['status']==controller.PASS and r['status']=='FAIL_OR_ERROR'
                rows.append(dict(mode=mode,status=r['status'],result_sha256=d.digest(raw),raw_native_sha256=r.get('native_result_sha256'),
                  original_error=r.get('error'),parse_error=r.get('native_result_parse_error'),source_error=r.get('source_error'),
                  complete_output_inventory=r['outputs'],synthetic_supervisor_only=True))
    return dict(actual_controller_main_finally=rows)


def runtime_controls():
    m=controller.methods()
    with tempfile.TemporaryDirectory(prefix='tail-m4-OP-runtime-')as folder:
        root=Path(folder)
        owned=controller.runtime.supervisor(controller.ROOT,root/'out',root/'supervision',controller.methods,m['protected'][controller.runtime.SAMPLER])
        with contextlib.redirect_stdout(io.StringIO()):owned.controls()
        result=json.loads((owned.TRACE/'controls.json').read_text());assert len(result['controls'])==13
    return dict(supervisor=result,actual_generic_process_controls=True,ngspice_or_CAD_executed=False)


def derived_preparation_boundary(prepare_only,omit_digest=False):
    ns,proof=controller.program_namespace();seen=[]
    original,parent=d.original_rejections();four=d.prior_four_tail_rejection()
    original_digest=ns['initialization'].digest
    init=types.SimpleNamespace(adapters=lambda:types.SimpleNamespace(),digest=original_digest)
    assert init.digest is original_digest
    if omit_digest:
        assert prepare_only is True
        del init.digest
    path_binding=types.SimpleNamespace(bench=types.SimpleNamespace(binding=types.SimpleNamespace(MODELS=dict(a.MODELS))))
    class StopBeforeEngine(RuntimeError):pass
    def prepare(destination):
        assert destination==ns['OUT']/'fresh-preparation';destination.mkdir()
        raw=d.encode(dict(original_parent_TX_rejection=parent))
        (destination/'preparation.summary.json').write_bytes(raw);seen.append('fresh-prepare-complete')
        actual=dict(path_controls={'negative_controls':['synthetic_'+str(i)for i in range(32)]},
          original17_HBT_rejection=original,prior_four_tail_rejection=four)
        return {label:('synthetic-full34ns',{})for label in d.LABELS},raw,{}, {},init,path_binding,None,actual
    def stop():
        assert ns['initialization']is init and ns['path_binding']is path_binding
        seen.append('original-engine-restore-boundary');raise StopBeforeEngine('explicit stop before runtime fetch or engine')
    with tempfile.TemporaryDirectory()as td, mock.patch.object(d,'prepare',prepare):
        ns['OUT']=Path(td)/'actual-main';m=dict(prepared_path_controls_authorized=True,native_zero_op_authorized=True)
        ns['methods']=lambda:m
        ns['publication']=types.SimpleNamespace(context=lambda *args:('fixture-tag','a'*40),api=lambda p:{'fixture':p},validate_release=lambda *args:{'fixture':True})
        ns['native']=types.SimpleNamespace(restore=stop)
        try:ns['main'](prepare_only=prepare_only)
        except AttributeError as error:
            assert omit_digest and prepare_only and error.name=='digest'and error.obj is init
            frames=[];tb=error.__traceback__
            while tb:
                frames.append(tb);tb=tb.tb_next
            assert frames[-1].tb_frame.f_code is ns['sha'].__code__
            assert frames[-2].tb_frame.f_code is ns['main'].__code__
            assert seen==['fresh-prepare-complete']
            assert(ns['OUT']/'fresh-preparation/preparation.summary.json').is_file()
            prior=json.loads((ns['OUT']/'result.json').read_bytes())
            assert prior['status']=='PASS_FOUR_EXACT_RUNTIME_PATH_BINDINGS_NO_NATIVE_ZERO_OP'
            assert prior['native_simulator_invoked']is prior['runtime_installed']is False
            return dict(prepare_only=True,rejected=True,exact_old_missing_digest_reproduced=True,
              error=repr(error),unchanged_original_main_finally_and_sha=True,
              preparation_file_written_before_finally=True,earlier_result_is_not_a_completed_fixture=True,
              native_or_archive_executed=False)
        except StopBeforeEngine:assert not prepare_only and not omit_digest
        else:assert prepare_only and not omit_digest
        result=json.loads((ns['OUT']/'result.json').read_bytes())
        assert result['current_RC_model_hashes']==a.MODELS and result['original17_HBT_rejection']==original and result['prior_four_tail_rejection']==four
        assert ns['initialization']is init and ns['path_binding']is path_binding
        assert init.digest is original_digest
        if prepare_only:
            assert seen==['fresh-prepare-complete']and result['status']=='PASS_FOUR_EXACT_RUNTIME_PATH_BINDINGS_NO_NATIVE_ZERO_OP'
            assert result['zero_source_OP_executed']is False
        else:
            assert seen==['fresh-prepare-complete','original-engine-restore-boundary']and result['status']=='FAIL_FRESH318_ZERO_OP'
            assert'StopBeforeEngine'in result['validation_errors'][0]['error']
        assert result['native_simulator_invoked']is False and result['runtime_installed']is False
        assert result['outputs']['fresh-preparation/preparation.summary.json']==controller.sha(ns['OUT']/'fresh-preparation/preparation.summary.json')
    return dict(prepare_only=prepare_only,actual_full_main_and_current_inputs=True,correct_isolated_context_installed=True,
      explicit_original_runtime_boundary=True,synthetic_preparation_only=True,
      exact_original_digest_callable=True,native_or_archive_executed=False)


def native_result_controls():
    native=native_fixture();assert controller.validate_native(native)
    changes=[
      ('current-run',lambda x:x.update(run_id=1)),('current-source',lambda x:x.update(source_head='0'*40)),
      ('stale-RC-summary',lambda x:x['current_TAIL_M4_preparation']['current_RC'].update(outer_summary_sha256='0'*64)),
      ('stale-inner-summary',lambda x:x['current_TAIL_M4_preparation']['current_RC'].update(native_summary_sha256='0'*64)),
      ('partial-whole-capsule',lambda x:x['current_TAIL_M4_preparation']['current_RC'].update(complete_files=3180)),
      ('old-physical-source',lambda x:x['current_TAIL_M4_preparation']['physical_source'].update(run=1)),
      ('original-rejection-status',lambda x:x.update(status='REJECTED')),
      ('not-all-four',lambda x:x.update(all_four_expanded_zero_OPs_passed=False)),
      ('old-model-P',lambda x:x['current_RC_model_hashes'].update(p=d.old_binding.MODELS['p'])),
      ('missing-N',lambda x:x['current_RC_model_hashes'].pop('n')),
      ('changed-source',lambda x:x.update(sources_unchanged=False)),
      ('missing-case',lambda x:x['cases'].pop('n-initial-low')),
      ('native-return',lambda x:x['cases']['p-initial-high'].update(returncode=1)),
      ('original-gate-rejection',lambda x:x['cases']['p-initial-high']['zero_OP_gate'].update(passed=False)),
      ('hidden-native-error',lambda x:x['cases']['p-initial-high'].update(errors=['preserved failure'])),
      ('unexpected-wave',lambda x:x['cases']['p-initial-high'].update(wave_raw_exists=True)),
      ('stale-106-HBT',lambda x:x['cases']['p-initial-high'].update(expected_HBT_count=106)),
      ('stale-vectors',lambda x:x['cases']['p-initial-high'].update(expected_saved_vectors=1)),
      ('erased-17-rejection',lambda x:x.pop('original17_HBT_rejection')),
      ('erased-4-rejection',lambda x:x.pop('prior_four_tail_rejection')),
      ('wrong-RC-root',lambda x:x['current_TAIL_M4_preparation']['current_RC'].update(consumed_native_view='.')),
      ('partial-native-view',lambda x:x['current_TAIL_M4_preparation']['current_RC'].update(native_view_files=3164)),
      ('missing-binding-fault',lambda x:x['current_TAIL_M4_preparation'].update(binding_faults_per_polarity=19)),
      ('transient-claim',lambda x:x.update(transient_executed=True))]
    rejected=[]
    for name,edit in changes:
        bad=copy.deepcopy(native);edit(bad);rejected.append(refusal(name,lambda:controller.validate_native(bad)))
    assert len(rejected)==24
    return dict(positive_synthetic_native_report=True,rejected=rejected,no_simulator=True)



def reject(bucket,name,fn,types=(AssertionError,KeyError,ValueError,FileNotFoundError,FileExistsError)):
    try:fn()
    except types:bucket.append(name)
    else:raise AssertionError('Accepted '+name)

def permissions(text):
    assert text.count('permissions:\n  contents: read\n  actions: read\n')==1
    controls=text.split('  source-controls:\n',1)[1].split('  fresh-four-original-zero-OPs:\n',1)[0]
    native=text.split('  fresh-four-original-zero-OPs:\n',1)[1]
    assert 'contents: write'not in controls
    assert native.count('    permissions:\n      contents: write\n      actions: read\n')==1
    assert native.index('Wait read-only')<native.index('Install exact Python runtime dependencies')
    assert 'if: always()'in native and 'inputs.native'in native
    return True

def control_emit_program(text):
    header="      - name: Emit exact complete or partial control bytes\n        if: always()\n        run: |\n          python3 - <<'PYCONTROL'\n"
    assert text.count(header)==1
    body=text.split(header,1)[1].split('          PYCONTROL\n',1)[0]
    assert all(line.startswith('          ')for line in body.splitlines())
    code='\n'.join(line[10:]for line in body.splitlines())+'\n'
    tree=ast.parse(code)
    assignments={n.targets[0].id:n.value for n in tree.body if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
    assert ast.literal_eval(assignments['names'])==('wrapper-controls','import-controls','publication-controls','wait-controls','source-controls')
    assert "647af19c78158045739b2589d61a2962bbff69e230b593ccb33019550edbd709"in code
    assert "scope['emit']"in code and "missing_files_created=False"in code
    imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
    assert len(imports)==2 and isinstance(imports[0],ast.Import)
    assert [x.name for x in imports[0].names]==['ast','base64','hashlib','json']
    assert isinstance(imports[1],ast.ImportFrom)and imports[1].module=='pathlib'
    return code

def control_emit_fixtures(text):
    import base64,hashlib
    code=control_emit_program(text);positive=[];refused=[]
    names=('wrapper-controls','import-controls','publication-controls','wait-controls','source-controls')
    source_path=Path('scripts/cloud_cdr_v59_binding_rc.py')
    raw=(controller.ROOT/source_path).read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='647af19c78158045739b2589d61a2962bbff69e230b593ccb33019550edbd709'
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);(root/'scripts').mkdir();(root/source_path).write_bytes(raw)
        payload={name:(b'{"fixture":"' + name.encode()+b'"}\n')for name in names}
        payload['wrapper-controls']=b'x'*7000
        payload['publication-controls']=bytes([255,0])
        payload['import-controls']=b''
        for name,b in payload.items():(root/(name+'.json')).write_bytes(b)
        def exercise():
            previous=Path.cwd()
            try:
                os.chdir(root)
                with contextlib.redirect_stdout(io.StringIO())as output:exec(compile(code,'actual-control-emission-template','exec'),{})
                lines=output.getvalue().splitlines();census=json.loads(lines[-1].split(' ',1)[1])
                assert census['missing_files_created']is False and not census['failures']
                for row in census['emitted']:
                    name=row['name'][:-5];marker='TAIL_M4_LOADED_CONTROL_'+name.upper().replace('-','_')
                    begin=[x for x in lines if x.startswith(marker+'_BEGIN ')];assert len(begin)==1
                    header=json.loads(begin[0].split(' ',1)[1])
                    pieces=[x.split(' ',2)for x in lines if x.startswith(marker+'_CHUNK ')]
                    assert [int(x[1])for x in pieces]==list(range(header['chunks']))
                    assert lines.count(marker+'_END')==1
                    got=base64.b64decode(''.join(x[2]for x in pieces))
                    assert got==payload[name]==(root/row['name']).read_bytes()
                    assert header['bytes']==row['bytes']==len(got)
                    assert header['sha256']==row['sha256']==hashlib.sha256(got).hexdigest()
                return census
            finally:os.chdir(previous)
        full=exercise();assert len(full['emitted'])==5 and full['missing']==[]
        positive.append(dict(name='five_actual_files_complete_indexed_bytes',proof=full))
        for name in ('wrapper-controls','source-controls'):(root/(name+'.json')).unlink()
        partial=exercise();assert len(partial['emitted'])==3
        assert partial['missing']==['wrapper-controls.json','source-controls.json']
        assert not(root/'wrapper-controls.json').exists()and not(root/'source-controls.json').exists()
        positive.append(dict(name='earlier_failure_missing_records_never_created',proof=partial))
        (root/source_path).write_bytes(raw+b' ')
        reject(refused,'mutated_frozen_emitter_source',exercise)
        (root/source_path).write_bytes(raw)
    reject(refused,'absent_always_scope',lambda:control_emit_program(text.replace(
        '      - name: Emit exact complete or partial control bytes\n        if: always()',
        '      - name: Emit exact complete or partial control bytes\n        if: success()')))
    assert len(positive)==2 and len(refused)==2
    return dict(positive=positive,refused=refused,actual_template_program_executed=True,
                original_records_modified=False,missing_records_created=False)

def workflow_controls():
    m=controller.methods();template=controller.ROOT/m['template']
    text=template.read_text();assert permissions(text)
    active=controller.ROOT/m['active_workflow']
    if active.exists():assert active.read_bytes()==template.read_bytes()
    rejected=[]
    for name,bad in (
        ('absent-native-write',text.replace('    permissions:\n      contents: write\n      actions: read\n','')),
        ('native-read-only',text.replace('      contents: write','      contents: read')),
        ('global-write',text.replace('permissions:\n  contents: read','permissions:\n  contents: write')),
        ('controls-write',text.replace('  source-controls:\n','  source-controls:\n    permissions:\n      contents: write\n'))):
        reject(rejected,name,lambda bad=bad:permissions(bad))
    return dict(actual_template_path=m['template'],active_byte_equal_if_registered=True,rejected=rejected,
                control_evidence=control_emit_fixtures(text))

def child_preflight_controls():
    positive=[];refused=[]
    identity=dict(source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1)
    controls=dict(fixture='exact passed controls')
    reservation=dict(existing_assets=[],tag='fixture',source='fixture')
    proof=dict(**identity,completed_controls=controls,reservation=reservation)
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);path=root/'authorized-preflight.json'
        path.write_text(json.dumps(proof))
        with mock.patch.object(controller,'OUT',root),mock.patch.object(controller,'methods',return_value={}),mock.patch.object(controller,'authorize'),\
             mock.patch.object(controller,'completed_controls',return_value=controls),mock.patch.object(controller.guard,'context',return_value=('tag','head')),\
             mock.patch.object(controller.guard,'api',return_value={}),mock.patch.object(controller.guard,'validate_release',return_value=reservation):
            result=controller.child_preflight()
            assert result==dict(reservation,completed_source_controls=controls);positive.append('exact_parent_preflight')
            for name,key,value in [('source','source_head','0'*40),('run','run_id',-1),('attempt','run_attempt',2),
                                   ('control-proof','completed_controls',{}),('reservation','reservation',{})]:
                changed=copy.deepcopy(proof);changed[key]=value;path.write_text(json.dumps(changed))
                reject(refused,name,controller.child_preflight)
            path.write_text(json.dumps(proof))
            with mock.patch.object(controller.guard,'validate_release',return_value=dict(reservation,existing_assets=['already-published'])):
                reject(refused,'nonempty-release',controller.child_preflight)
    return dict(positive=positive,refused=refused,actual_child_preflight=True,no_remote_call=True)

def authorization_controls():
    m=controller.methods();positive=[];rejected=[]
    keys=('native_execution_authorized','native_zero_op_authorized','simulation_authorized','prepared_path_controls_authorized')
    with tempfile.TemporaryDirectory()as folder:
        path=Path(folder)/'method.json'
        for mode in (False,True):
            candidate=copy.deepcopy(m);candidate.update({k:mode for k in keys});path.write_text(json.dumps(candidate))
            with mock.patch.object(controller,'METHOD',path):
                assert controller.methods()==candidate
                if mode:controller.authorize(candidate)
            positive.append(dict(four_OP_authorizations=mode))
        mutations=[('transient',lambda x:x.update(native_transient_authorized=True)),
          ('geometry',lambda x:x.update(geometry_generation_authorized=True)),
          ('continuation',lambda x:x.update(continuation_authorized=True)),
          ('extraction',lambda x:x.update(extraction_authorized=True)),
          ('split-authorization',lambda x:x.update(native_zero_op_authorized=True)),
          ('nonboolean-native',lambda x:x.update({k:1 for k in keys})),
          ('resource-limit',lambda x:x['owned_process'].update(seconds=1))]
        for name,mutate in mutations:
            candidate=copy.deepcopy(m);mutate(candidate);path.write_text(json.dumps(candidate))
            with mock.patch.object(controller,'METHOD',path):reject(rejected,name,controller.methods)
    return dict(positive=positive,rejected=rejected)



def owned_child_terminal_fixtures():
    import signal,threading
    results=[]
    for mode in ('success','body-only','body-and-stop-failure','cleanup-only-stop-failure','body-and-all-cleanup-failures','cleanup-only-final-sample-failure'):
        with tempfile.TemporaryDirectory()as folder:
            out=Path(folder)/'out';out.mkdir();calls=[]
            primary=RuntimeError('EXACT_PRIMARY_BODY_'+mode)
            body_failure=mode.startswith('body-')
            all_failures=mode=='body-and-all-cleanup-failures'
            class StopEvent:
                def set(self):
                    calls.append('set-stop')
                    if all_failures:raise RuntimeError('EXACT_STOP_EVENT_FAILURE')
            class Worker:
                def __init__(self,*,target,daemon):assert target is owned.heartbeat and daemon is True
                def start(self):calls.append('start-heartbeat')
                def join(self,timeout):
                    assert timeout==2;calls.append('join-heartbeat')
                    if all_failures:raise RuntimeError('EXACT_JOIN_FAILURE')
                def is_alive(self):calls.append('heartbeat-is-alive');return False
            handlers={signal.SIGTERM:'original-TERM',signal.SIGINT:'original-INT'}
            def signal_call(sig,handler):
                label=signal.Signals(sig).name
                if handler is owned.interrupted:
                    calls.append('install-'+label);return handlers[sig]
                assert handler==handlers[sig];calls.append('restore-'+label)
                if all_failures and sig==signal.SIGTERM:raise RuntimeError('EXACT_SIGNAL_RESTORE_FAILURE')
                return owned.interrupted
            def stop(active):
                assert active is owned.ACTIVE;calls.append('stop-process')
                if mode in ('body-and-stop-failure','cleanup-only-stop-failure')or all_failures:
                    raise RuntimeError('EXACT_STOP_PROCESS_FAILURE')
                return dict(signals=[],remaining_live=[],remaining_nonrunning=[])
            def sample(kind):
                assert kind=='final_resource_sample';calls.append('final-sample')
                if mode=='cleanup-only-final-sample-failure'or all_failures:raise RuntimeError('EXACT_FINAL_SAMPLE_FAILURE')
            def supervised(argv,label,native,*,seconds,cwd):
                assert argv==[sys.executable,'-B',controller.ROOT/'scripts/cloud_tx_phase_reset334_tail_m4_loaded.py','--child']
                assert label=='fresh-current-four-original-zero-OPs'and native is False and seconds==18000 and cwd==out
                calls.append('supervised-body')
                if body_failure:raise primary
                record=dict(returncode=0,supervision_failure=None,process_group_cleanup={'remaining_live':[]})
                controller.write(out/'supervision'/('fresh-current-four-original-zero-OPs.command.json'),record)
                return types.SimpleNamespace(returncode=0)
            owned=types.SimpleNamespace(ACTIVE=object(),STOP=StopEvent(),heartbeat=lambda:None,interrupted=lambda *_:None,
              stop_process=stop,sample=sample,supervised=supervised)
            m=dict(protected={controller.runtime.SAMPLER:'fixture-sampler'},owned_process={'seconds':18000})
            caught=None
            with mock.patch.object(controller,'OUT',out),mock.patch.object(controller,'methods',return_value=m),\
                 mock.patch.object(controller.runtime,'supervisor',return_value=owned),\
                 mock.patch.object(signal,'signal',side_effect=signal_call),mock.patch.object(threading,'Thread',Worker):
                try:record=controller.run_owned_child()
                except BaseException as error:caught=error
            if mode=='success':assert caught is None and record['returncode']==0
            elif body_failure:assert caught is primary,'Original exception object replaced by cleanup error'
            else:assert isinstance(caught,RuntimeError)and'Owned terminal cleanup failed'in str(caught)
            expected=['install-SIGTERM','install-SIGINT','start-heartbeat','supervised-body','stop-process','set-stop','join-heartbeat']
            if not all_failures:expected.append('heartbeat-is-alive')
            expected+=['restore-SIGTERM','restore-SIGINT','final-sample'];assert calls==expected
            path=out/'supervision-finalization.json';raw=path.read_bytes();evidence=json.loads(raw)
            assert evidence['all_terminal_actions_attempted']is True and len(evidence['terminal_actions'])==6
            assert [r['action']for r in evidence['terminal_actions']]==['stop_owned_process','set_stop_event','join_heartbeat','restore_signal_SIGTERM','restore_signal_SIGINT','final_resource_sample']
            if body_failure:
                assert evidence['status']=='FAIL_PRIMARY_BODY'and evidence['primary_error']==repr(primary)
                assert evidence['primary_traceback']and'EXACT_PRIMARY_BODY_'in evidence['primary_traceback']
            elif mode=='success':assert evidence['status']=='PASS_OWNED_TERMINAL_CLEANUP'
            else:assert evidence['status']=='FAIL_TERMINAL_CLEANUP'and evidence['primary_error']is None
            errors=[r for r in evidence['terminal_actions']if not r['completed']]
            assert len(errors)==(5 if all_failures else(0 if mode in ('success','body-only')else 1))
            if body_failure and errors:assert any('Owned terminal cleanup failures:'in note for note in primary.__notes__)
            results.append(dict(mode=mode,actual_run_owned_child=True,primary_exception_identity_preserved=body_failure,
              terminal_receipt_sha256=d.digest(raw),evidence=evidence,calls=calls,
              synthetic_process_and_signal_API_only=True,engine_or_archive_executed=False))
    return dict(cases=results,all_terminal_actions_attempted_after_earlier_failure=True)

def controls():
    base=inherited_controls()
    base.update(outer_native_view=outer_view_controls(),
      actual_prepare_completion=[prepare_completion_fixture(False),prepare_completion_fixture(True)],
      actual_post_preparation_main=[derived_preparation_boundary(x)for x in (True,False)],
      actual_old_missing_digest_regression=derived_preparation_boundary(True,omit_digest=True),
      native_result_controls=native_result_controls(),finalization=finalization_fixtures(),owned_child_terminal=owned_child_terminal_fixtures(),runtime=runtime_controls(),
      authorization=authorization_controls(),child_preflight=child_preflight_controls(),workflow=workflow_controls(),
      prior_four_failed_HBT_count=len(d.prior_four_tail_rejection()['all_four_failed_HBT_records']),
      native_executed=False,actual_fresh_model_binding_executed=False)
    controller.methods();return base


if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False),flush=True)
