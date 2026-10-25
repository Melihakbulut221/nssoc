#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/admission and real temporary-file handoff controls; never run native."""
import ast,copy,importlib.metadata,json,os,sys,tempfile
from pathlib import Path
import tx_phase_reset334_avss18_rc_admission as a
import tx_phase_reset334_avss18_rc_adapter as d
import cloud_tx_phase_reset334_avss18_rc as controller
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

def controls():
    m=a.methods();assert m['source_controls_authorized']is True
    # Actual imports above and this explicit inventory prevent an absent repo helper
    # being silently categorized as an external Python dependency.
    for p in m['required_repository_modules']:
        assert p in m['protected']and(a.ROOT/p).is_file()
        assert a.sha(a.ROOT/p)==m['protected'][p]
    imports=import_closure(a.ROOT,m['protected'],m['import_roots'])
    assert Path(controller.__file__).resolve()==a.ROOT/'scripts/cloud_tx_phase_reset334_avss18_rc.py'
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
      ('old-rectangle',lambda x:x['variants']['p']['native_material']['generation_comparison'].update(source_new_rect_um=[109.,89.,115.,2371.])),
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
    assert len(d.intrinsic_output_names())==459
    a.methods()
    return dict(status='PASS_AVSS18_FRESH_RC_SOURCE_CONTROLS_NO_NATIVE',
      prerequisite=pre,actual_controller_imported=True,import_closure=imports,inherited_intrinsic=old_i,inherited_precision=old_r,
      source_derivations=results,derivation_faults=derivation_faults,physical_faults=faults,
      metadata_faults=metadata_faults,handoff_faults=handoff_faults,relocation_faults=relocation_faults,
      actual_file_handoff_positive=positive,relocation_guard_positive=relocation_positive,
      relocation_fixture_is_synthetic_not_native=True,archive_controls=archive,
      native_execution=False,extraction_executed=False,simulation_executed=False)

if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
