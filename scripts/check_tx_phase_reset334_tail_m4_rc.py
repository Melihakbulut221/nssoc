#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/admission and real temporary-file handoff controls; never run native."""
import ast,copy,importlib.metadata,json,os,sys,tempfile,contextlib,io,hashlib,types
from unittest import mock
from pathlib import Path
import tx_phase_reset334_tail_m4_rc_admission as a
import tx_phase_reset334_tail_m4_rc_adapter as d
import cloud_tx_phase_reset334_tail_m4_rc as controller
import cloud_tx_phase_reset334_intrinsic_mim as old_intrinsic
import cloud_tx_phase_reset334_mim_precision as old_precision

def immediate_imports(node):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):return
    if isinstance(node,(ast.Import,ast.ImportFrom)):yield node
    for child in ast.iter_child_nodes(node):yield from immediate_imports(child)

def import_closure(root,pins,roots):
    queue=list(roots);seen={};edges=[];standard=set(sys.stdlib_module_names)|set(sys.builtin_module_names)
    external={'numpy':'2.1.3','networkx':'3.4.2'}
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

def inherited_and_admission_controls():
    m=a.methods();assert m['source_controls_authorized']is True
    # Actual imports above and this explicit inventory prevent an absent repo helper
    # being silently categorized as an external Python dependency.
    for p in m['required_repository_modules']:
        assert p in m['protected']and(a.ROOT/p).is_file()
        assert a.sha(a.ROOT/p)==m['protected'][p]
    imports=import_closure(a.ROOT,m['protected'],m['import_roots'])
    assert Path(controller.__file__).resolve()==a.ROOT/'scripts/cloud_tx_phase_reset334_tail_m4_rc.py'
    old_i=old_intrinsic.controls();old_r=old_precision.source_controls()
    assert len(old_i['physical_faults'])==16 and len(old_i['derivations']['rejected'])==9
    assert len(old_r['rejected'])==19 and len(old_r['source_derivations'])==13
    assert len(old_r['cap_order_controls'])==4 and len(old_r['publication_controls']['rejected'])==17
    prior,pre=a.prerequisite();assert a.validate(prior)
    results=[];derivation_faults=[];faults=[];metadata_faults=[];handoff_faults=[];relocation_faults=[]
    def refuse(bucket,name,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,FileNotFoundError,FileExistsError):bucket.append(name)
        else:raise AssertionError('Accepted '+name)
    for kind in d.FROZEN:
        text,proof=d.sources(kind);assert proof['reversed_byte_exact'];results.append(dict(kind=kind,**proof))
        original=(a.ROOT/d.FROZEN[kind][0]).read_text()
        refuse(derivation_faults,kind+'-changed-original',lambda kind=kind,original=original:d.sources(kind,(original+'\n').encode()))
        before=ast.parse(original);after=ast.parse(text)
        unchanged={n.name:ast.dump(n,include_attributes=False)for n in before.body if isinstance(n,ast.FunctionDef)}
        changed={n.name:ast.dump(n,include_attributes=False)for n in after.body if isinstance(n,ast.FunctionDef)}
        allowed=set()if kind=='source'else{'main'}if kind=='intrinsic'else{'main','validate'}
        assert set(unchanged)==set(changed)
        assert all(changed[k]==v for k,v in unchanged.items()if k not in allowed)
    refuse(derivation_faults,'missing-edit',lambda:d.derive('x=1',[('missing','x=2',1)]))
    refuse(derivation_faults,'ambiguous-edit',lambda:d.derive('x=1\nx=1',[('x=1','x=2',1)]))
    refuse(derivation_faults,'identity-edit',lambda:d.derive('x=1',[('x=1','x=1',1)]))
    changes=[
      ('source',lambda x:x.update(source_head='0'*40)),
      ('status',lambda x:x.update(status='PASS')),
      ('sources',lambda x:x.update(sources_unchanged=False)),
      ('errors',lambda x:x.update(validation_errors=['bad'])),
      ('missing-polarity',lambda x:x['variants'].pop('n')),
      ('missing-output',lambda x:x['outputs'].pop(next(iter(x['outputs'])))),
      ('GDS',lambda x:x['variants']['p']['generation']['output_sha256'].update({'nssoc_tx_phase_reset244_p_v1.gds':'0'*64})),
      ('DRC-markers',lambda x:x['variants']['p']['steps']['drc']['measurement'].update(markers=1)),
      ('DRC-census',lambda x:x['variants']['n']['steps']['drc']['measurement'].update(category_count=559)),
      ('LVS-census',lambda x:x['variants']['p']['steps']['flat_lvs']['audit']['circuits'][0].update(layout_devices_recursive=333)),
      ('LVS-ports',lambda x:x['variants']['n']['steps']['deep_lvs']['ports'].update(actual_count=10)),
      ('terminal-census',lambda x:x['variants']['p']['wires']['graph'].update(native_terminal_count=1009)),
      ('component-census',lambda x:x['variants']['n']['wires']['graph'].update(wire_component_count=118)),
      ('body-census',lambda x:x['variants']['p']['wires']['anchors']['counts'].update(body_terminals=325)),
      ('original-physical-fault',lambda x:x['variants']['p']['steps']['wrong_offset_length'].update(expected_verdict_observed=False)),
      ('original-anchor-fault',lambda x:x['variants']['n']['wires']['anchors']['negative_controls'][0].update(rejected=False)),
      ('old-offset',lambda x:x['variants']['p']['generation']['sole_device_dimension_delta'].update(new_L_um=32)),
      ('false-electrical',lambda x:x.update(electrical_accepted=True)),
      ('baseline-change',lambda x:x.update(original_baseline_byte_unchanged=False)),
      ('rescaled-R',lambda x:x.update(old_R_rescaled=True)),
      ('material-fault',lambda x:x['variants']['n']['native_material']['actual_native_faults'][0].update(rejected=False)),
      ('material-extra-shape',lambda x:x['variants']['p']['native_material']['native_comparison'].update(changed_shape_records=2)),
      ('old-M4-box',lambda x:x['variants']['p']['native_material']['native_comparison']['exact_target_plan'][0].update(old_native_box_dbu=[0,0,1,1])),
      ('false-pristine-material',lambda x:x['variants']['n']['native_material'].update(all_inputs_byte_unchanged=False))]
    for name,mutate in changes:
        x=copy.deepcopy(prior);mutate(x);refuse(faults,name,lambda x=x:a.validate(x))
    fields=[('run','id',1),('run','head_sha','0'*40),('run','run_attempt',2),('run','status','in_progress'),
      ('run','conclusion','failure'),('run','path','wrong'),('run','head_branch','wrong'),
      ('job','id',1),('job','run_id',1),('job','head_sha','0'*40),('job','run_attempt',2),
      ('job','status','in_progress'),('job','conclusion','failure'),('release','id',1),
      ('release','tag_name','wrong'),('release','target_commitish','0'*40),('release','draft',True),('release','prerelease',False)]
    for slot,key,value in fields:
        x=copy.deepcopy(pre);x[slot][key]=value
        refuse(metadata_faults,slot+'-'+key,lambda x=x:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    for field,value in [('sha','0'*40),('type','tag')]:
        x=copy.deepcopy(pre);x['tag']['object'][field]=value
        refuse(metadata_faults,'tag-'+field,lambda x=x:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    for key,value in [('size',1),('digest','sha256:'+'0'*64),('id',1),('state','new')]:
        x=copy.deepcopy(pre);asset=next(v for v in x['release']['assets']if v['id']==a.ASSETS['archive']['id']);asset[key]=value
        refuse(metadata_faults,'archive-'+key,lambda x=x:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    x=copy.deepcopy(pre);x['release']['assets'].append(copy.deepcopy(next(v for v in x['release']['assets']if v['id']==a.ASSETS['summary']['id'])))
    refuse(metadata_faults,'duplicate-summary-asset',lambda:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);(root/'nested').mkdir();(root/'nested/a').write_bytes(b'fresh native fixture');(root/'empty').write_bytes(b'')
        expected={'nested/a':a.sha(root/'nested/a'),'empty':a.sha(root/'empty')};positive=d.inventory(root,expected)
        assert positive['files']==2
        (root/'nested/a').write_bytes(b'changed');refuse(handoff_faults,'changed-byte',lambda:d.inventory(root,expected));(root/'nested/a').write_bytes(b'fresh native fixture')
        (root/'extra').write_bytes(b'x');refuse(handoff_faults,'extra-file',lambda:d.inventory(root,expected));(root/'extra').unlink()
        (root/'empty').unlink();refuse(handoff_faults,'missing-file',lambda:d.inventory(root,expected));(root/'empty').write_bytes(b'')
        (root/'link').symlink_to(root/'nested/a');refuse(handoff_faults,'symlink',lambda:d.inventory(root,expected));(root/'link').unlink()
        (root/'dirlink').symlink_to(root/'nested',target_is_directory=True);refuse(handoff_faults,'directory-symlink',lambda:d.inventory(root,expected));(root/'dirlink').unlink()
        assert d.inventory(root,expected)==positive
    # Relational fixture uses actual admitted rows but deliberately synthetic displaced
    # points. It proves the guard, not a fresh native geometric access or ownership.
    original=copy.deepcopy(prior['variants']['p']['wires']['anchors']);current=copy.deepcopy(original)
    labels={x['label']:x for x in current['anchors']};moves=[]
    for row in current['rows']:
        if row['model']!='cap_cmim'or row['terminal']!='mim_btm':continue
        old=copy.deepcopy(row);new=[row['point_dbu'][0]+11,row['point_dbu'][1]+17]
        row.update(point_dbu=new,original_native_terminal_selection=dict(selection=old['selection'],point_dbu=old['point_dbu'],candidate_contacts=old['candidate_contacts']),selection='actual_placed_mim_bottom_Metal5_access_outside_intrinsic_mask')
        row['candidate_contacts']=[dict(metal=67,point_dbu=new,kind=row['selection'])];labels[row['reference_label']]['point_dbu']=new
        moves.append(dict(native_id=row['device'],reference_label=row['reference_label'],old_point_dbu=old['point_dbu'],new_point_dbu=new,native_cluster=row['native_cluster'],wire_component=row['wire_component']))
    relocation_positive=d.validate_relocations(original,current,moves)
    relchanges=[
      ('missing-move',lambda o,c,x:x.pop()),('wrong-original-point',lambda o,c,x:x[0].update(old_point_dbu=[0,0])),
      ('wrong-current-point',lambda o,c,x:x[0].update(new_point_dbu=[0,0])),('wrong-cluster',lambda o,c,x:x[0].update(native_cluster=-1)),
      ('wrong-component',lambda o,c,x:x[0].update(wire_component=-1)),('wrong-reference',lambda o,c,x:x[0].update(reference_label='wrong')),
      ('unlisted-terminal',lambda o,c,x:c['rows'][0].update(point_dbu=[0,0])),
      ('reordered-rows',lambda o,c,x:c['rows'].reverse()),
      ('lost-original',lambda o,c,x:next(r for r in c['rows']if 'original_native_terminal_selection'in r).pop('original_native_terminal_selection')),
      ('unlisted-anchor',lambda o,c,x:c['anchors'][0].update(point_dbu=[0,0])),
      ('anchor-property',lambda o,c,x:next(r for r in c['anchors']if r['label']==x[0]['reference_label']).update(metal=8)),
      ('anchor-label',lambda o,c,x:c['anchors'][0].update(label='wrong'))]
    for name,mutate in relchanges:
        o,c,x=copy.deepcopy((original,current,moves));mutate(o,c,x)
        refuse(relocation_faults,name,lambda:d.validate_relocations(o,c,x))
    assert len(results)==3 and len(derivation_faults)==6 and len(faults)==24
    assert len(metadata_faults)==25 and len(handoff_faults)==5 and len(relocation_faults)==12
    archive=a.frozen.archive_controls();assert len(archive['rejected'])==13 and archive['inherited_parts_controls']['negative_controls']==6
    assert sorted(d.intrinsic_output_names())==m['expected_intrinsic_output_names']
    a.methods()
    return dict(status='PASS_TAIL_M4_FRESH_RC_SOURCE_CONTROLS_NO_NATIVE',
      prerequisite=pre,actual_controller_imported=True,import_closure=imports,inherited_intrinsic=old_i,inherited_precision=old_r,
      source_derivations=results,derivation_faults=derivation_faults,physical_faults=faults,
      metadata_faults=metadata_faults,handoff_faults=handoff_faults,relocation_faults=relocation_faults,
      actual_file_handoff_positive=positive,relocation_guard_positive=relocation_positive,
      relocation_fixture_is_synthetic_not_native=True,archive_controls=archive,
      native_execution=False,extraction_executed=False,simulation_executed=False)


c=controller

def reject(bucket,name,fn,types=(AssertionError,KeyError,ValueError,FileNotFoundError,FileExistsError)):
    try:fn()
    except types:bucket.append(name)
    else:raise AssertionError('Accepted '+name)


def outer_view_controls():
    _,outer=a.physical();_,native=a.native_physical()
    assert a.validate_outer(outer,native)
    names=d.intrinsic_output_names()
    assert {'physical/'+x for x in a.expected_files(outer)}<=names
    assert 'physical/result.json'in names and 'physical/native/result.json'in names
    assert 'physical/native/p/layout/nssoc_tx_phase_reset244_p_v1.gds'in names
    assert 'physical/p/layout/nssoc_tx_phase_reset244_p_v1.gds'not in names
    faults=[]
    mutations=[
      ('outer-source',lambda x:x.update(source_head='0'*40)),
      ('outer-run',lambda x:x.update(run_id=1)),
      ('outer-attempt',lambda x:x.update(run_attempt=2)),
      ('outer-status',lambda x:x.update(status='PASS')),
      ('outer-native-alias',lambda x:x.update(native_result={})),
      ('outer-native-digest',lambda x:x.update(native_result_sha256=a.SOURCE['summary'])),
      ('outer-native-bytes',lambda x:x.update(native_result_bytes=1)),
      ('outer-native-path',lambda x:x.update(native_result_raw_path='result.json')),
      ('outer-output-omission',lambda x:x['outputs'].pop(next(iter(x['outputs'])))),
      ('inner-output-hash',lambda x:x['outputs'].update({'native/result.json':a.SOURCE['summary']})),
      ('inner-member-hash',lambda x:x['outputs'].update({'native/'+next(iter(native['outputs'])):'0'*64})),
      ('supervision-return',lambda x:x['supervisor'].update(returncode=1)),
      ('supervision-limit',lambda x:x['supervisor'].update(maximum_group_rss_kib=1)),
      ('supervision-memory',lambda x:x['supervisor'].update(memory_read_error='bad')),
      ('supervision-failure',lambda x:x['supervisor'].update(supervision_failure='bad')),
      ('supervision-live',lambda x:x['supervisor']['process_group_cleanup'].update(remaining_live=[123])),
      ('physical-gate',lambda x:x.update(physical_gates_passed=False)),
      ('false-electrical',lambda x:x.update(electrical_accepted=True)),
      ('false-rescaled-R',lambda x:x.update(old_R_rescaled=True)),
      ('direct-material-hash',lambda x:x['outputs'].update({'physical-p-native-material.json':'0'*64}))]
    for name,mutation in mutations:
        changed=copy.deepcopy(outer);mutation(changed)
        reject(faults,name,lambda changed=changed:a.validate_outer(changed,native))
    assert len(faults)==20
    return dict(complete_capsule_files=len(a.expected_files(outer)),native_view_files=len(native['outputs'])+1,
                explicitly_enumerated_intrinsic_outputs=len(names),enumerated_names_sha256=a.methods()['expected_intrinsic_output_names_sha256'],
                no_native_or_archive_executed=True,refused=faults)

def consumed_view_fixtures():
    text,_=d.sources('intrinsic');tree=ast.parse(text)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main')
    work=next(n for n in main.body if isinstance(n,ast.Try))
    # Actual contiguous restore block, including both native result validation and SHA.
    assert ast.unparse(work.body[0])=="physical = OUT / 'physical'"
    assert isinstance(work.body[1],ast.Assign)and isinstance(work.body[2],ast.Assign)and isinstance(work.body[3],ast.Assign)
    assert ast.unparse(work.body[3])=="physical = physical / 'native'"
    prefix=work.body[:7]
    assert ast.unparse(prefix[-1]).startswith("assert sha(physical / 'result.json') == SOURCE['summary']")
    commands=[]
    for n in ast.walk(main):
        if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='execute':
            if any(isinstance(x,ast.Constant)and x.value in ('native-export','native-mim-geometry')for x in n.value.args):
                commands.append(n)
    assert len(commands)==2
    positive=[];refused=[]
    outer_raw,outer=a.physical();native_raw,native=a.native_physical()
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);out=root/'intrinsic';out.mkdir()
        def restore(prior,destination):
            assert prior==native
            destination.mkdir();(destination/'result.json').write_bytes(outer_raw)
            (destination/'native').mkdir();(destination/'native/result.json').write_bytes(native_raw)
            return dict(synthetic_file_fixture=True,full_archive_not_read=True)
        scope=dict(OUT=out,SOURCE=a.NATIVE_SOURCE,prior=native,_actual_physical_restore=restore,sha=a.sha,validate=a.validate)
        exec(compile(ast.Module(body=prefix,type_ignores=[]),'actual-derived-restore-prefix','exec'),scope)
        assert scope['physical']==out/'physical/native'
        captured=[]
        scope.update(app='app',paths=dict(native='native.py',mim='mim.py'),out=root/'pol-output',
                     execute=lambda command,label,destination:captured.append(dict(command=command,label=label,destination=destination)))
        for pol in ('p','n'):
            scope['pol']=pol
            for node in commands:exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-native-consumer-argv','exec'),scope)
        assert len(captured)==4
        for row in captured:
            assert row['command'][3]in (out/'physical/native/p',out/'physical/native/n')
        positive.append(dict(name='actual_restore_and_all_four_native_argv',paths=[str(x['command'][3].relative_to(root))for x in captured]))
        # Actual old outer-as-native identity must fail at the preserved hash assertion.
        tail=prefix[-1]
        wrong=dict(scope,SOURCE=a.SOURCE)
        reject(refused,'outer-summary-used-as-native',lambda:exec(compile(ast.Module(body=[tail],type_ignores=[]),'actual-native-summary-assert','exec'),wrong))
        wrong=dict(scope,physical=out/'physical')
        reject(refused,'outer-root-used-as-native',lambda:exec(compile(ast.Module(body=[tail],type_ignores=[]),'actual-native-view-assert','exec'),wrong))
    return dict(positive=positive,refused=refused,actual_selected_AST_statements=True,archive_or_engine_executed=False)

def derived_main_fixtures():
    body,proof=c.derive();positive=[];refused=[]
    for mode in ('intrinsic-refusal','precision-refusal','complete-two-stage'):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder)/'native';intrinsic=root/'intrinsic';precision=root/'precision'
            fake=types.SimpleNamespace(OUT=root,INTRINSIC=intrinsic,PRECISION=precision)
            def run_intrinsic():
                intrinsic.mkdir();c.write(intrinsic/'result.json',dict(status='fixture_intrinsic',failure=mode=='intrinsic-refusal'))
                if mode=='intrinsic-refusal':raise RuntimeError('EXACT_INTRINSIC_STOP')
                return dict(status='fixture_intrinsic',physical_prerequisite={'fixture':True}),{'fixture':True}
            def run_precision(prior):
                precision.mkdir();c.write(precision/'result.json',dict(status='fixture_precision',failure=mode=='precision-refusal'))
                if mode=='precision-refusal':raise RuntimeError('EXACT_PRECISION_STOP')
                return dict(status='fixture_precision',polarities={'p':{},'n':{}},
                    **{k:False for k in ('accepted','qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted')}),{'fixture':True}
            fake.run_intrinsic=run_intrinsic;fake.run_precision=run_precision
            scope=dict(adapter=fake,admission=types.SimpleNamespace(SOURCE=a.SOURCE,sha=a.sha,methods=lambda:None),
                       preflight=lambda:dict(completed_source_controls={'fixture':True}),write=c.write,os=os,json=json,traceback=__import__('traceback'))
            exec(compile(body,'actual-qualified-derived-main-fixture','exec'),scope)
            try:scope['main']()
            except RuntimeError as error:
                assert mode!='complete-two-stage';refused.append(dict(name=mode,error=str(error)))
            else:assert mode=='complete-two-stage';positive.append(mode)
            result=json.loads((root/'result.json').read_bytes())
            assert (result['status']==c.PASS)==(mode=='complete-two-stage')
            assert (root/'fresh-intrinsic-result.json').read_bytes()==(intrinsic/'result.json').read_bytes()
            if precision.exists():assert (root/'fresh-two-order-result.json').read_bytes()==(precision/'result.json').read_bytes()
            assert all(result[k]is False for k in ('electrical_accepted','simulation_executed','geometry_generation_executed','old_R_rescaled'))
    return dict(derivation=proof,positive=positive,refused=refused,actual_complete_derived_main=True,synthetic_stage_collaborators=True)

def finalization_fixtures():
    rows=[];mutations=[]
    for mode in ('preflight-refusal','supervisor-refusal','native-rejection','complete-RC','truncated-native-result','source-integrity-failure'):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'out';stage=out/'native'
            def flight():
                if mode=='preflight-refusal':raise RuntimeError('EXACT_PREFLIGHT_REFUSAL')
                return {'fixture':True}
            def run():
                stage.mkdir()
                native=dict(status=c.PASS if mode in ('complete-RC','source-integrity-failure')else'FAIL_OR_ERROR',
                            protected_sources_unchanged=True,fresh_native_RC_extracted=True,both_polarities_and_orders_verified=True,
                            original_13_wire_9_MIM_faults_each_order_and19_composition_faults_preserved=True,
                            electrical_accepted=False,full_phy_accepted=False,simulation_executed=False,geometry_generation_executed=False,old_R_rescaled=False)
                c.write(stage/'result.json',native);(stage/'partial.bin').write_bytes(b'complete saved partial evidence')
                if mode=='truncated-native-result':(stage/'result.json').write_bytes(b'{"status":"RUNNING","variants":')
                if mode=='supervisor-refusal':raise RuntimeError('EXACT_SUPERVISOR_REFUSAL')
                return dict(returncode=0 if mode in ('complete-RC','source-integrity-failure','truncated-native-result')else 7)
            with mock.patch.object(c,'OUT',out),mock.patch.object(c,'STAGE',stage),mock.patch.object(d,'INTRINSIC',stage/'intrinsic'),mock.patch.object(d,'PRECISION',stage/'precision'),                 mock.patch.object(c,'preflight',flight),mock.patch.object(c,'run_owned_child',run),                 mock.patch.object(c,'methods',side_effect=AssertionError('EXACT_SOURCE_INTEGRITY_FAILURE')if mode=='source-integrity-failure'else None,return_value={}),mock.patch.object(c,'derive',return_value=('',{'fixture':True})):
                try:c.main()
                except (RuntimeError,AssertionError,json.JSONDecodeError):assert mode!='complete-RC'
                else:assert mode=='complete-RC'
                r=json.loads((out/'result.json').read_bytes())
                assert (r['status']==c.PASS)==(mode=='complete-RC')
                assert r['electrical_accepted']is r['simulation_executed']is r['geometry_generation_executed']is False
                if mode!='preflight-refusal':
                    assert (out/'native-RC-result.json').read_bytes()==(stage/'result.json').read_bytes()
                    assert r['outputs']['native/partial.bin']==c.sha(stage/'partial.bin')
                if mode=='truncated-native-result':
                    assert 'native_result'not in r and r['native_result_present']is True
                    assert r['native_result_parse_error']and r['native_result_parse_traceback']
                    assert 'JSONDecodeError'in r['error']and 'JSONDecodeError'in r['native_result_parse_error']
                    assert r['native_result_bytes']==len((stage/'result.json').read_bytes())
                    assert r['native_result_sha256']==c.sha(stage/'result.json')
                if mode=='source-integrity-failure':
                    assert r['protected_sources_unchanged']is False
                    assert 'EXACT_SOURCE_INTEGRITY_FAILURE'in r['source_error']and r['source_traceback']
                    assert r['native_result']['status']==c.PASS and r['status']=='FAIL_OR_ERROR'
                rows.append(dict(mode=mode,result=r,synthetic_supervisor_only=True))
    return dict(actual_controller_main_finally=rows)


def runtime_controls():
    m=c.methods()
    with tempfile.TemporaryDirectory(prefix='tail-m4-runtime-')as folder:
        root=Path(folder)
        owned=c.runtime.supervisor(c.ROOT,root/'out',root/'supervision',c.methods,m['protected'][c.runtime.SAMPLER])
        with contextlib.redirect_stdout(io.StringIO()):owned.controls()
        supervisor=json.loads((owned.TRACE/'controls.json').read_text())
        assert len(supervisor['controls'])==13
        probe=c.runtime.launcher(c.ROOT,c.methods,m['protected'][c.runtime.PROBE])
        launcher=probe.controls()
        assert len(launcher['positive'])==2 and len(launcher['rejected'])==9
    return dict(supervisor=supervisor,launcher=launcher,actual_appimage_executed=False,native_executed=False)


def permissions(text):
    assert text.count('permissions:\n  contents: read\n  actions: read\n')==1
    controls=text.split('  source-controls:\n',1)[1].split('  fresh-two-polarity-both-order-RC:\n',1)[0]
    native=text.split('  fresh-two-polarity-both-order-RC:\n',1)[1]
    assert 'contents: write'not in controls
    assert native.count('    permissions:\n      contents: write\n      actions: read\n')==1
    assert native.index('Wait read-only')<native.index('Restore the exact qualified')
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
    raw=(c.ROOT/source_path).read_bytes()
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
                    name=row['name'][:-5];marker='TAIL_M4_RC_CONTROL_'+name.upper().replace('-','_')
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
    m=c.methods();template=c.ROOT/m['template']
    text=template.read_text();assert permissions(text)
    active=c.ROOT/m['active_workflow']
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


def authorization_controls():
    m=c.methods();positive=[];refused=[]
    with tempfile.TemporaryDirectory()as folder:
        path=Path(folder)/'method.json'
        for mode in (False,True):
            candidate=copy.deepcopy(m);candidate.update(native_execution_authorized=mode,extraction_authorized=mode)
            path.write_text(json.dumps(candidate))
            with mock.patch.object(a,'METHOD',path):
                assert c.methods()==candidate
                if mode:c.authorize(candidate)
            positive.append(dict(native=mode,extraction=mode))
        mutations=[('simulation',lambda x:x.update(simulation_authorized=True)),
                   ('geometry',lambda x:x.update(geometry_generation_authorized=True)),
                   ('continuation',lambda x:x.update(continuation_authorized=True)),
                   ('zero-op',lambda x:x.update(zero_op_authorized=True)),
                   ('split-authorization',lambda x:x.update(native_execution_authorized=True,extraction_authorized=False)),
                   ('nonboolean-native',lambda x:x.update(native_execution_authorized=1,extraction_authorized=1)),
                   ('resource-limit',lambda x:x['owned_process'].update(seconds=1))]
        for name,mutate in mutations:
            candidate=copy.deepcopy(m);mutate(candidate);path.write_text(json.dumps(candidate))
            with mock.patch.object(a,'METHOD',path):reject(refused,name,c.methods)
    return dict(positive=positive,refused=refused)

def child_preflight_controls():
    positive=[];refused=[]
    identity=dict(source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1)
    controls=dict(fixture='exact passed controls')
    reservation=dict(existing_assets=[],tag='fixture',source='fixture')
    proof=dict(**identity,completed_controls=controls,reservation=reservation)
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);path=root/'authorized-preflight.json'
        path.write_text(json.dumps(proof))
        with mock.patch.object(c,'OUT',root),mock.patch.object(c,'methods',return_value={}),mock.patch.object(c,'authorize'),\
             mock.patch.object(c,'completed_controls',return_value=controls),mock.patch.object(c.guard,'context',return_value=('tag','head')),\
             mock.patch.object(c.guard,'api',return_value={}),mock.patch.object(c.guard,'validate_release',return_value=reservation):
            result=c.child_preflight()
            assert result==dict(reservation,completed_source_controls=controls);positive.append('exact_parent_preflight')
            for name,key,value in [('source','source_head','0'*40),('run','run_id',-1),('attempt','run_attempt',2),
                                   ('control-proof','completed_controls',{}),('reservation','reservation',{})]:
                changed=copy.deepcopy(proof);changed[key]=value;path.write_text(json.dumps(changed))
                reject(refused,name,c.child_preflight)
            path.write_text(json.dumps(proof))
            with mock.patch.object(c.guard,'validate_release',return_value=dict(reservation,existing_assets=['already-published'])):
                reject(refused,'nonempty-release',c.child_preflight)
    return dict(positive=positive,refused=refused,actual_child_preflight=True,no_remote_call=True)

def controls():
    inherited=inherited_and_admission_controls()
    result=dict(status=c.STATUS,native_executed=False,extraction_executed=False,simulation_executed=False,
                inherited=inherited,outer_view=outer_view_controls(),consumed_view=consumed_view_fixtures(),
                derived_main=derived_main_fixtures(),finalization=finalization_fixtures(),
                runtime=runtime_controls(),workflow=workflow_controls(),
                authorization=authorization_controls(),child_preflight=child_preflight_controls())
    c.methods()
    return result

if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
