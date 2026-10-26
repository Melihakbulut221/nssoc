#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted real-program fixtures; no native Pya, geometry, archive download or simulator."""
import ast,contextlib,copy,io,json,os,tempfile
from pathlib import Path
from unittest import mock
import cloud_tx_phase_reset334_tail_m4_physical as c
import tx_phase_reset334_avss18_rc_admission as a

def reject(bucket,name,fn,types=(AssertionError,KeyError,ValueError,FileNotFoundError,FileExistsError)):
    try:fn()
    except types:bucket.append(name)
    else:raise AssertionError('Accepted '+name)

def admission_controls():
    prior,pre=a.prerequisite();assert a.validate(prior)
    assert len(a.expected_files(prior))==407
    faults=[];metadata_faults=[]
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
        x=copy.deepcopy(prior);mutate(x);reject(faults,name,lambda x=x:a.validate(x))
    fields=[('run','id',1),('run','head_sha','0'*40),('run','run_attempt',2),('run','status','in_progress'),
      ('run','conclusion','failure'),('run','path','wrong'),('run','head_branch','wrong'),
      ('job','id',1),('job','run_id',1),('job','head_sha','0'*40),('job','run_attempt',2),
      ('job','status','in_progress'),('job','conclusion','failure'),('release','id',1),
      ('release','tag_name','wrong'),('release','target_commitish','0'*40),('release','draft',True),('release','prerelease',False)]
    for slot,key,value in fields:
        x=copy.deepcopy(pre);x[slot][key]=value
        reject(metadata_faults,slot+'-'+key,lambda x=x:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    for field,value in [('sha','0'*40),('type','tag')]:
        x=copy.deepcopy(pre);x['tag']['object'][field]=value
        reject(metadata_faults,'tag-'+field,lambda x=x:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    for key,value in [('size',1),('digest','sha256:'+'0'*64),('id',1),('state','new')]:
        x=copy.deepcopy(pre);asset=next(v for v in x['release']['assets']if v['id']==a.ASSETS['archive']['id']);asset[key]=value
        reject(metadata_faults,'archive-'+key,lambda x=x:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    x=copy.deepcopy(pre);x['release']['assets'].append(copy.deepcopy(next(v for v in x['release']['assets']if v['id']==a.ASSETS['summary']['id'])))
    reject(metadata_faults,'duplicate-summary-asset',lambda:a.validate_metadata(x['run'],x['job'],x['release'],x['tag']))
    archive=a.frozen.archive_controls()
    assert len(faults)==24 and len(metadata_faults)==25
    assert len(archive['rejected'])==13 and archive['inherited_parts_controls']['negative_controls']==6
    return dict(current_physical=pre,complete_inventory_files=407,physical_faults=faults,
                metadata_faults=metadata_faults,archive=archive,actual_archive_downloaded=False)

def permissions(text):
    assert text.count('permissions:\n  contents: read\n  actions: read\n')==1
    controls=text.split('  source-controls:\n',1)[1].split('  fresh-two-polarity334-physical:\n',1)[0]
    native=text.split('  fresh-two-polarity334-physical:\n',1)[1]
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
                    name=row['name'][:-5];marker='TAIL_M4_CONTROL_'+name.upper().replace('-','_')
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

def derived_main_fixtures():
    body,proof=c.derive();results=[];faults=[]
    for mode in ('restore-refused','post-restore-stop'):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'native';baseline=Path(td)/'saved';baseline.mkdir()
            (baseline/'immutable').write_bytes(b'actual fixture bytes')
            baseline_proof=dict(directory=str(baseline),inventory=dict(files={'immutable':dict(bytes=20,sha256=c.sha(baseline/'immutable'))}))
            # size comes from the actual file, never a fixture assumption.
            baseline_proof['inventory']['files']['immutable']['bytes']=(baseline/'immutable').stat().st_size
            seen=[]
            def restored(path):
                seen.append('restore')
                if mode=='restore-refused':raise RuntimeError('EXACT_RESTORE_REFUSAL')
                return baseline_proof
            def fetch(*args,**kwargs):seen.append('fetch');raise RuntimeError('EXACT_POST_RESTORE_STOP')
            scope=dict(c.original.__dict__)
            scope.update(OUT=out,host=lambda:None,pins=lambda:{'protected':{}},prerequisite=lambda:{'fixture':True},
              clock_contract=lambda:{'fixture':True},fetch=fetch,
              _tail_m4_authorize=lambda m:None,_tail_m4_save_prerequisite=lambda p:p,
              _tail_m4_restore=restored,_tail_m4_material=c.material,_tail_m4_finish=c.finish,
              _tail_m4_finalize_baseline=c.finalize_baseline)
            spec=c.ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json'
            assert spec.is_file()
            with mock.patch.object(c.original.publication,'context',return_value=('fixture','a'*40)),                 mock.patch.object(c.original.publication,'api',return_value={}),                 mock.patch.object(c.original.publication,'validate_release',return_value={'fixture':True}):
                exec(compile(body,'actual-derived-tail-main-fixture','exec'),scope)
                try:scope['main']()
                except RuntimeError as e:assert str(e)==('EXACT_RESTORE_REFUSAL'if mode=='restore-refused'else'EXACT_POST_RESTORE_STOP')
                else:raise AssertionError('Missing explicit fixture stop')
            report=json.loads((out/'result.json').read_text())
            assert report['status']=='FAIL_OR_ERROR'and report['traceback']and report['outputs']=={}
            assert seen==(['restore']if mode=='restore-refused'else['restore','fetch'])
            if mode=='post-restore-stop':assert report['original_baseline_byte_unchanged']is True
            results.append(dict(name=mode,result=report,actual_full_main=True,no_native_or_download=True))
    for i in range(len(c.EDITS)):
        with mock.patch.object(c,'EDITS',c.EDITS[:i]+c.EDITS[i+1:]):reject(faults,'missing-seam-'+str(i),c.derive)
    return dict(positive=results,refused=faults,derivation=proof)

def finalization_fixtures():
    rows=[];mutations=[]
    for mode in ('preflight-refusal','supervisor-refusal','native-rejection','complete-physical','truncated-native-result','source-integrity-failure'):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'out';stage=out/'native'
            def flight():
                if mode=='preflight-refusal':raise RuntimeError('EXACT_PREFLIGHT_REFUSAL')
                return {'fixture':True}
            def run():
                stage.mkdir()
                native=dict(status=c.PASS if mode in ('complete-physical','source-integrity-failure')else'FAIL_OR_ERROR',
                            original_baseline_byte_unchanged=True,sources_unchanged=True,validation_errors=[])
                c.write(stage/'result.json',native);(stage/'partial.bin').write_bytes(b'complete saved partial evidence')
                if mode=='truncated-native-result':(stage/'result.json').write_bytes(b'{"status":"RUNNING","variants":')
                if mode=='supervisor-refusal':raise RuntimeError('EXACT_SUPERVISOR_REFUSAL')
                return dict(returncode=0 if mode in ('complete-physical','source-integrity-failure','truncated-native-result')else 7)
            with mock.patch.object(c,'OUT',out),mock.patch.object(c,'STAGE',stage),                 mock.patch.object(c,'preflight',flight),mock.patch.object(c,'run_owned_child',run),                 mock.patch.object(c,'methods',side_effect=AssertionError('EXACT_SOURCE_INTEGRITY_FAILURE')if mode=='source-integrity-failure'else None,return_value={}),mock.patch.object(c,'derive',return_value=('',{'fixture':True})):
                try:c.main()
                except (RuntimeError,AssertionError,json.JSONDecodeError):assert mode!='complete-physical'
                else:assert mode=='complete-physical'
                r=json.loads((out/'result.json').read_bytes())
                assert (r['status']==c.PASS)==(mode=='complete-physical')
                assert r['electrical_accepted']is r['simulation_executed']is r['extraction_executed']is False
                if mode!='preflight-refusal':
                    assert (out/'native-physical-result.json').read_bytes()==(stage/'result.json').read_bytes()
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
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);p=root/'original';p.write_bytes(b'original')
        proof=dict(directory=str(root),inventory=dict(files={'original':dict(bytes=8,sha256=c.sha(p))}))
        for mode in ('changed','missing','extra'):
            p.write_bytes(b'original')
            if mode=='changed':p.write_bytes(b'changed!')
            elif mode=='missing':p.unlink()
            else:(root/'extra').write_bytes(b'extra')
            report=dict(status=c.PASS,baseline_restoration=proof)
            c.finalize_baseline(report)
            assert report['status']=='FAIL_OR_ERROR'and not report['original_baseline_byte_unchanged']
            mutations.append(dict(name=mode,error=report['baseline_immutability_error']))
            if(root/'extra').exists():(root/'extra').unlink()
    return dict(actual_controller_main_finally=rows,baseline_immutability_faults=mutations)

def authorization_controls():
    rejected=[]
    positive=dict(native_generation_authorized=True,native_material_authorized=True,
                  simulation_authorized=False,extraction_authorized=False,continuation_authorized=False)
    with mock.patch.object(Path,'read_text',return_value='ID=ubuntu\nVERSION_ID="22.04"\n'),         mock.patch.dict(os.environ,{'ImageOS':'ubuntu22'}):
        c.authorize(positive)
        for key in positive:
            changed=dict(positive);changed[key]=not positive[key]
            reject(rejected,key,lambda changed=changed:c.authorize(changed))
    for name,text,image in [('OS','ID=ubuntu\nVERSION_ID="24.04"\n','ubuntu24'),
                            ('distribution','ID=debian\nVERSION_ID="22.04"\n','ubuntu22'),
                            ('image','ID=ubuntu\nVERSION_ID="22.04"\n','ubuntu24')]:
        with mock.patch.object(Path,'read_text',return_value=text),mock.patch.dict(os.environ,{'ImageOS':image}):
            reject(rejected,name,lambda:c.authorize(positive))
    assert len(rejected)==8
    return dict(positive_mock_only=True,rejected=rejected)

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

def controls():
    m=c.methods();assert m['source_controls_authorized']is True
    assert type(m['native_generation_authorized'])is bool and type(m['native_material_authorized'])is bool
    import check_tx_phase_reset334_tail_m4_source as source_check
    with tempfile.TemporaryDirectory()as td:
        path=Path(td)/'source'
        with mock.patch.object(source_check.g,'METHOD',str(c.METHOD)),mock.patch.object(source_check,'OUT',path),             contextlib.redirect_stdout(io.StringIO()):
            source_check.main()
        source=json.loads((path/'result.json').read_bytes())
    assert len(source['positives'])==6 and len(source['faults'])==25
    old=dict(c.original.__dict__)
    try:
        c.original.METHOD=c.METHOD;c.original.prerequisite=c.OLD_PREREQUISITE
        inherited=c.original.controls()
    finally:
        c.original.__dict__.clear();c.original.__dict__.update(old)
    assert len(inherited['schematic_fault_controls'])==10
    assert len(inherited['publication_controls']['rejected'])==17
    result=dict(status=c.STATUS,source=source,inherited=inherited,admission=admission_controls(),
       derived_main=derived_main_fixtures(),finalization=finalization_fixtures(),workflow=workflow_controls(),
       runtime=runtime_controls(),authorization=authorization_controls(),native_executed=False,electrical_accepted=False,
       original_electrical_rejection_preserved=True)
    c.methods();return result
