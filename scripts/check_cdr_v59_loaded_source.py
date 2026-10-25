#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual source/report admission controls; no model restore or simulator execution."""
import ast,copy,hashlib,json
import cdr_v59_loaded_admission as a
BLOCKS=[{"name":"native_binding","start_line":31,"end_line":127,"bytes":7507,"sha256":"a7067fdb80569bbabc2d70193e2bf4e28865a0647a1c0789ca0995aeb37deafb"},{"name":"binding_faults","start_line":128,"end_line":180,"bytes":3639,"sha256":"20f3e8acdf034b458eb8c9bc7e3dde43af0a0f5cdf0c863d47f27fe66e4c0222"},{"name":"case_corner_oracles","start_line":188,"end_line":191,"bytes":424,"sha256":"7bb0b9fbd02029addf8024787d91591eb9a4f73869134cffe806828c3e5da6ab"},{"name":"model_runtime_and_bench","start_line":225,"end_line":260,"bytes":4136,"sha256":"37df0c59a36aa6fb9f465ff9f543dfdf8fd428fcc4ae9ee14505298fdc53dd3b"},{"name":"OFF_OP_stream_admission","start_line":267,"end_line":275,"bytes":1271,"sha256":"1a05d71d6f12258dc23fa7437f44574674b4d616df9d4cb18c0132961a1f9717"},{"name":"frozen_measurement","start_line":276,"end_line":337,"bytes":7156,"sha256":"25d8ab3689494cd55f7173b56d25914bb5b41f8bc3fa6f7d38ac20cf430bebfb"}]
def digest(b):return hashlib.sha256(b).hexdigest()
def derivation(old,new,d):
    assert digest(old)==d['baseline_sha256']=='12fffebb23c7478d0994c00bc0e6fc53e4842b09bfca496db59316c923e86ab2'
    assert len(d['edits'])==6 and len({x['label']for x in d['edits']})==6
    text=old.decode()
    for row in d['edits']:
        assert text.count(row['before'])==1;text=text.replace(row['before'],row['after'])
    assert text.encode()==new and digest(new)==d['generated_sha256']
    reverse=text
    for row in reversed(d['edits']):
        assert reverse.count(row['after'])==1;reverse=reverse.replace(row['after'],row['before'])
    assert reverse.encode()==old
    funcs=lambda raw:{n.name:ast.dump(n)for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
    x,y=funcs(old),funcs(new);assert x.keys()==y.keys()and [k for k in x if x[k]!=y[k]]==['main']
    oldlines=old.splitlines(keepends=True)
    for row in BLOCKS:
        block=b''.join(oldlines[row['start_line']-1:row['end_line']])
        assert len(block)==row['bytes']and digest(block)==row['sha256']
        assert new.count(block)==1,row['name']
    literals=lambda raw:{n.targets[0].id:ast.literal_eval(n.value)for n in ast.parse(raw).body
        if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id in ('MODEL','CASES')}
    before,after=literals(old),literals(new)
    assert before['CASES']==after['CASES']==a.descriptor()['cases']and len(after['CASES'])==10
    assert after['MODEL']==a.MODEL
    return dict(reversible_edits=6,unchanged_blocks=BLOCKS,all_ten_cases_preserved=True,non_main_functions_AST_identical=True)

def main_entry_controls(new):
    """Execute the exact complete main with explicit entry stubs, stopping before restore."""
    import argparse,contextlib,io,os,sys,tempfile,traceback,types
    from pathlib import Path
    from unittest import mock
    failed=new.decode()
    substitutions=[
      ('import cdr_v59_loaded_admission as current_inputs\n','import cdr_v59_loaded_admission as current\n'),
      ('ROOT/current_inputs.SUMMARY','ROOT/current.SUMMARY'),
      ('ROOT/current_inputs.STAGE','ROOT/current.STAGE'),
      ('current_inputs.restore(out,args.prepare_only)','current.restore(out,args.prepare_only)'),
      ('current_inputs.verify_restored(out)','current.verify_restored(out)')]
    for before,after in substitutions:
        assert failed.count(before)==1;failed=failed.replace(before,after)
    assert digest(failed.encode())=='b489dd21d11c1d49fb6fc2347f4c5faa2f445b8b298fb0e6c7536394e22b2f9f'
    class RestorationBoundaryStop(RuntimeError):pass
    def exercise(source,old):
        tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main']
        assert len(nodes)==1
        # Full original function retains its later numeric current assignment.
        program=compile(ast.Module(body=nodes,type_ignores=[]),'actual-loaded-main-entry-fixture','exec')
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'scripts').mkdir();(root/'docs/evidence').mkdir(parents=True)
            names=['scripts/cloud_cdr_pd_vi.py','scripts/cloud_tx_stream.py','scripts/cloud_cdr_xor.py',
              'scripts/run_cloud_tx_mux4.py','docs/evidence/cdr-via-rich-stream-transport-pass-20261019.json']
            pins={}
            actual_method=a.methods()
            for name in names:
                data=(a.ROOT/name).read_bytes();assert digest(data)==actual_method['protected'][name]
                (root/name).write_bytes(data);pins[name]=digest(data)
            # This limited methods fixture only enables the entry seam, never qualifies a capsule.
            (root/'scripts/cdr-v59-loaded-methods.json').write_text(json.dumps(dict(protected=pins))+'\n')
            calls=[];out=root/'cloud-cdr-v59-loaded-nominal_early'
            def restore(path,prepare):
                assert path==out and prepare is True
                calls.append('restore_boundary');(path/'current-mim-bundle').mkdir()
                raise RestorationBoundaryStop('EXPLICIT_STOP_BEFORE_NETWORK_OR_CAPSULE_RESTORE')
            def verify(path):
                assert path==out and calls==['restore_boundary']
                calls.append('finally_verification_boundary')
                return dict(synthetic_entry_fixture_only=True)
            admission=types.SimpleNamespace(SUMMARY=a.SUMMARY,STAGE=a.STAGE,restore=restore,verify_restored=verify)
            def prbs(seed):
                assert seed==0x7f
                return [0,1]*128
            ns=dict(argparse=argparse,json=json,os=os,Path=Path,traceback=traceback,ROOT=root,
              UI=125e-12,START=2e-9,STOP=2e-9+258*125e-12,STEP=.3125e-12,
              CASES=a.descriptor()['cases'],sha=lambda p:digest(Path(p).read_bytes()),
              reports=types.SimpleNamespace(),pump=types.SimpleNamespace(CORNERS={'nominal':{'scale':1.0}}),
              primitive=types.SimpleNamespace(prbs=prbs),
              legacy=types.SimpleNamespace(__file__=str(root/'scripts/cloud_cdr_pd_vi.py')),
              stream=types.SimpleNamespace(__file__=str(root/'scripts/cloud_tx_stream.py')),
              readback_controls=lambda:dict(synthetic_entry_fixture_only=True),
              current=admission,current_inputs=admission)
            exec(program,ns)
            assert 'current'in ns['main'].__code__.co_varnames
            assert 'current_inputs'not in ns['main'].__code__.co_varnames
            failure=None
            with mock.patch.object(sys,'argv',['loaded-entry','--case','nominal_early','--prepare-only']),contextlib.redirect_stdout(io.StringIO())as output:
                try:ns['main']()
                except BaseException as error:failure=error
            assert failure is not None
            saved=json.loads((out/'result.json').read_bytes())
            assert saved['status']=='FAIL_OR_ERROR'and saved['accepted']is saved['full_phy_accepted']is False
            if old:
                assert type(failure)is UnboundLocalError and "'current'"in str(failure)
                assert calls==[]and not(out/'current-mim-bundle').exists()
                assert 'current.SUMMARY'in saved['traceback']or 'UnboundLocalError'in saved['traceback']
            else:
                assert type(failure)is RestorationBoundaryStop and str(failure)=='EXPLICIT_STOP_BEFORE_NETWORK_OR_CAPSULE_RESTORE'
                assert calls==['restore_boundary','finally_verification_boundary']
                assert saved['current_saved_input_integrity']==dict(synthetic_entry_fixture_only=True)
            assert not(out/'native').exists()
            return dict(exception_type=type(failure).__name__,exception=str(failure),calls=calls,
              saved_status=saved['status'],stdout=output.getvalue(),exact_complete_main_compiled=True,
              copied_protected_entry_files=pins)
    original=exercise(failed,True);corrected=exercise(new.decode(),False)
    return dict(positive_cases=['corrected_complete_main_reaches_mocked_restore_and_finally'],
      rejected=['original_current_module_alias_shadow'],original=original,corrected=corrected,
      actual_full_main_entry_executed=True,explicit_entry_stubs=True,
      stopped_before_real_restore=True,prior_archive_accessed=False,simulator_executed=False,
      native_binding_or_measurement_executed=False)

def metadata_fixture():
    p=a.descriptor();run=copy.deepcopy(p['run'])
    jobs=dict(total_count=len(p['jobs']),jobs=[dict(**x,run_id=run['id'],head_sha=run['head_sha'])for x in p['jobs']])
    info=copy.deepcopy(p['release']);info['assets']=copy.deepcopy(p['assets'])
    ref=dict(ref='refs/tags/'+info['tag_name'],object=dict(type='commit',sha=run['head_sha']))
    return run,jobs,info,ref
def controls():
    m=a.methods();s=a.snapshots();a.validate_reports(s['summary'],s['stage'])
    old=(a.ROOT/'scripts/cloud_cdr500_v58_loaded.py').read_bytes()
    new=(a.ROOT/'scripts/cloud_cdr_v59_loaded.py').read_bytes()
    d=json.loads((a.ROOT/'scripts/cdr-v59-loaded-source-derivation.json').read_bytes())
    source_proof=derivation(old,new,d)
    entry_proof=main_entry_controls(new)
    rejected=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,ValueError,TypeError,IndexError):rejected.append(name)
        else:raise AssertionError('Accepted changed current loaded input: '+name)
    changes=[
      ('wrong_outer_source',lambda r,q:r.update(source_head='a'*40)),
      ('wrong_stage_source',lambda r,q:q.update(source_head='a'*40)),
      ('outer_failure',lambda r,q:r.update(status='FAIL')),
      ('stage_not_passed',lambda r,q:r.update(native_stage_passed=False)),
      ('stage_return_nonzero',lambda r,q:r['command'].update(returncode=1)),
      ('stage_result_hash',lambda r,q:r.update(stage_result_sha256='0'*64)),
      ('stage_output_hash',lambda r,q:r['outputs'].update({'stage/result.json':'0'*64})),
      ('acceptance_changed',lambda r,q:r.update(accepted=True)),
      ('electrical_reused',lambda r,q:r.update(electrical_accepted=True)),
      ('simulation_reused',lambda r,q:r.update(simulation_executed=True)),
      ('geometry_regenerated',lambda r,q:r.update(geometry_regenerated=True)),
      ('publication_failure_erased',lambda r,q:r.update(original_publication_failure_preserved=False)),
      ('stage_sources_changed',lambda r,q:q.update(sources_unchanged=False)),
      ('second_order_absent',lambda r,q:q.update(both_native_orders_verified=False)),
      ('order_records_changed',lambda r,q:q.update(native_rc_and_device_records_equal_in_both_orders=False)),
      ('PEX_claim',lambda r,q:q.update(qualified_pex=True)),
      ('old_device_census',lambda r,q:q['composition']['contract']['counts'].update(devices=394)),
      ('old_R_census',lambda r,q:q['composition']['contract']['counts'].update(R=24573)),
      ('old_C_census',lambda r,q:q['composition']['contract']['counts'].update(C=15693)),
      ('missing_MIM',lambda r,q:q['composition']['contract'].update(intrinsic_mim_models_in_final_netlist=6)),
      ('double_count_retained',lambda r,q:q['composition']['contract'].update(explicit_mim_device_estimate_double_count_removed=False)),
      ('wire_token_removed',lambda r,q:q['composition']['contract'].update(all_raw_wire_tokens_preserved=False)),
      ('target_length_restored',lambda r,q:next(x for x in q['composition']['contract']['device_records']if x['native_id']==184)['parameters'].update(l='7.4u')),
      ('target_width_changed',lambda r,q:next(x for x in q['composition']['contract']['device_records']if x['native_id']==185)['parameters'].update(w='8u')),
      ('originals_changed',lambda r,q:q['current_input_integrity'].update(original706_unchanged=False)),
      ('canonical_file_missing',lambda r,q:r['canonical_capsule_copy'].pop(next(iter(r['canonical_capsule_copy'])))),
      ('stage_member_missing',lambda r,q:r['stage_copy'].pop(next(iter(r['stage_copy'])))),
      ('model_publication_hash',lambda r,q:r['outputs'].update({'stage/composition/pd500-mim-wire.spice':'0'*64})),
    ]
    for name,change in changes:
        r,q=copy.deepcopy(s['summary']),copy.deepcopy(s['stage']);change(r,q)
        reject(name,lambda r=r,q=q:a.validate_reports(r,q))
    a.validate_remote(*metadata_fixture())
    remote=[
      ('wrong_run',lambda r,j,i,t:r.update(id=1)),
      ('unfinished_run',lambda r,j,i,t:r.update(status='in_progress')),
      ('failed_run',lambda r,j,i,t:r.update(conclusion='failure')),
      ('wrong_attempt',lambda r,j,i,t:r.update(run_attempt=2)),
      ('missing_native_job',lambda r,j,i,t:j['jobs'].pop()),
      ('failed_native_job',lambda r,j,i,t:j['jobs'][-1].update(conclusion='failure')),
      ('wrong_release',lambda r,j,i,t:i.update(id=1)),
      ('release_not_prerelease',lambda r,j,i,t:i.update(prerelease=False)),
      ('tag_source_changed',lambda r,j,i,t:t['object'].update(sha='a'*40)),
      ('archive_digest_changed',lambda r,j,i,t:i['assets'][-1].update(digest='sha256:'+'0'*64)),
    ]
    for name,change in remote:
        args=metadata_fixture();change(*args);reject(name,lambda args=args:a.validate_remote(*args))
    for name,badold,badnew in [('changed_old_source',old+b'\n',new),
       ('changed_threshold',old,new.replace(b'min(signed)>=.1',b'min(signed)>=.05')),
       ('changed_OFF_flag',old,new.replace(b'[off] = 1',b'[off] = 0')),
       ('changed_stop',old,new.replace(b'STOP==START+258*UI',b'STOP==START+128*UI')),
       ('changed_loaded_margin',old,new.replace(b'150f',b'100f'))]:
        reject(name,lambda badold=badold,badnew=badnew:derivation(badold,badnew,d))
    assert len(rejected)==43 and len(set(rejected))==43
    a.methods()
    return dict(status='PASS_CURRENT_V59_LOADED_SOURCE_ADMISSION_NOT_PREPARATION_OR_SIMULATION',
      protected_files=len(m['protected']),source_proof=source_proof,rejected=rejected,main_entry_controls=entry_proof,
      full_actual_report_positive=True,remote_envelope_positive_is_schema_fixture=True,
      archive_restore_executed=False,preparation_executed=False,simulation_executed=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
