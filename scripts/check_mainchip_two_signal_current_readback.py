#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual hosted text boundaries, full synthetic net census and failure lifecycle."""
import copy,json,os,tempfile,threading,types
from pathlib import Path
from unittest.mock import patch
import mainchip_two_signal_current_readback as a
import cloud_mainchip_two_signal_current_readback as d
import check_mainchip_signal_repair_readback as old
from cloud_chunked_results import pack
OUT=a.c.ROOT/'cloud-mainchip-two-signal-current-readback-controls'
def encoded(x):return(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
def write(root,files):
    for name,raw in files.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
def reject(name,fn):
    try:fn()
    except (AssertionError,KeyError,ValueError,FileNotFoundError)as error:
        return dict(name=name,error=repr(error))
    raise AssertionError('Accepted current readback fault '+name)
def fixture():
    """Actual three saved marker bodies; explicitly synthetic 143820-net text/API reports."""
    r=a.expected_report(a.c.regular(a.c.ROOT/(a.PREFIX+'.summary.json')).read_bytes())
    r=copy.deepcopy(r)
    clock=r['ownership']['markers'][0]['source_names'][0]
    names=sorted([clock]+['fixture_clock_'+str(i)for i in range(1690)])
    signals=list(a.source.TARGETS)+['fixture_special_power','fixture_special_ground']
    signals+=['fixture_signal_'+str(i)for i in range(143820-len(names)-len(signals))]
    allnames=names+signals;assert len(allnames)==len(set(allnames))==143820
    selected=set(names)
    raw=b'VERSION 5.8 ;\nNETS 143820 ;\n'+b''.join(
      ('- '+n+' + USE '+('CLOCK'if n in selected else'SIGNAL')+' ;\n').encode()for n in allnames)+b'END NETS\nEND DESIGN\n'
    files={p:b'fixture text\n'for p in a.SELECTED}
    for p in a.SELECTED:
        if p.endswith('.json'):files[p]=encoded({})
    files['work/expected-original-class.def']=raw
    owners=dict(selected=names,mutable=list(a.source.TARGETS),frozen=sorted(set(allnames)-set(a.source.TARGETS)),net_count=143820)
    files['work/owners.json']=encoded(owners)
    classes={n:'ROUTED'for n in owners['frozen']}
    files['work/original-classes.json']=encoded(classes)
    rows={n:dict(wire_present=True,metadata='FIXED',paths=['FIXED'],guides=1,terminals=2,
      special=False,sigtype='CLOCK'if n in selected else'SIGNAL')for n in allnames}
    for n in a.source.TARGETS:rows[n].update(metadata='ROUTED',paths=['ROUTED'],guides=3)
    for n in signals[2:4]:rows[n].update(wire_present=False,paths=[],special=True,sigtype='POWER',terminals=300)
    observed=dict(status='COMPLETE_ROUTER_CENSUS_GATE_NOT_ROUTING_ACCEPTANCE',accepted=False,
      source_odb_sha256=r['outputs']['work/fixed.odb'],rows=rows,
      special_observations={n:dict(identity=dict(name=n),guides=[])for n in signals[2:4]},
      duplicate_names=[],current_net=None,enumerated_count=143820,enumeration_complete=True,
      immutable_special_material={'fixture_only':True})
    census=a.source.router_census_observation(rows,owners)
    assert census['class_counts']==dict(target=2,ordinary_fixed=143816,ordinary_unwired=0,special=2)
    census.update(native_observation_refusals=[],observation_status=observed['status'],
      enumeration_complete=True,current_net=None,enumerated_count=143820,accepted=False)
    files['work/router-census-observed.json']=encoded(observed)
    files['work/router-census-report.json']=encoded(census)
    wanted=a.source.router_census(rows,owners)
    wanted['saved_census']={n:a.c.digest(files['work/'+n])for n in ('router-census-observed.json','router-census-report.json')}
    files['work/repair.tcl']=b'# Explicit synthetic plan; never executed\nread_db fixture.odb\ndetailed_route -droute_end_iter 64\n'
    files['work/fixed-audit-result.json']=encoded(dict(status='PASS_ACTUAL_ALL_NONTARGET_FIXED_BEFORE_ONE_ATTEMPT',
      router_census=wanted,repair_tcl_sha256=a.c.digest(files['work/repair.tcl']),fixed_odb_sha256=r['outputs']['work/fixed.odb']))
    gates={g:copy.deepcopy(r['native_result']['original_gate']['result'])for g in a.GATES}
    for g,v in gates.items():files['work/original-gate-'+g+'/result.json']=encoded(v)
    def gate(g):return dict(result=gates[g],sha256=a.c.digest(files['work/original-gate-'+g+'/result.json']))
    files['work/ownership.json']=encoded(r['ownership'])
    files['work/ownership-result.json']=encoded(dict(native_ownership=r['ownership'],original_gate=gate(a.GATES[0])))
    final=copy.deepcopy(r['native_result']);final['original_gate']=gate(a.GATES[2])
    prior=dict(status='PASS_ORIGINAL_CLASS_TWO_SIGNAL_REPAIR_REQUIRES_DRC',candidate_sha256=r['outputs']['work/repaired.odb'],
      expected_def_sha256=a.c.digest(raw),routing_delta=final['routing_delta'],
      original1691_clock_gate_passed=True,native_invariants_passed=True,original_gate=gate(a.GATES[1]))
    files['work/unfix-audit-result.json']=encoded(prior)
    files['work/drc-audit-result.json']=encoded(final);r['native_result']=final
    files['work/route-audit-result.json']=encoded(dict(status='PASS_ONLY_TWO_SIGNAL_DELTA_ALL_OTHERS_FIXED',
      native_invariants_passed=True,routing_delta=final['routing_delta']))
    p='docs/evidence/mainchip-signal-repair-saved-readback-native-terminal-20261026.diagnostics/saved/work/'
    marker=a.c.regular(a.c.ROOT/(p+'initial-drc-markers.json')).read_bytes()
    tr=a.c.regular(a.c.ROOT/(p+'initial-drc.rpt')).read_bytes()
    assert a.c.digest(marker)==a.source.MARKER_SHA and a.c.digest(tr)==a.source.TR_SHA
    files['work/initial-drc-markers.json']=files['work/source-markers.json']=marker
    files['work/initial-drc.rpt']=files['work/initial-drc-reread.rpt']=files['work/source-markers.rpt']=tr
    files['work/fixed-routing.drc']=b''
    phases=[]
    for index,label in enumerate(a.PHASES):
        stdout=('synthetic exact stream '+label+'\n').encode();stderr=b''
        row=copy.deepcopy(r['phase_results'][index]);row.pop('requested_timeout_seconds')
        row.update(stdout_bytes=len(stdout),stdout_sha256=a.c.digest(stdout),stderr_bytes=0,stderr_sha256=a.c.digest(stderr))
        files['supervision/'+label+'.command.json']=encoded(row)
        files['supervision/'+label+'.stdout']=stdout;files['supervision/'+label+'.stderr']=stderr
        phases.append(dict(row,requested_timeout_seconds=14400 if label=='one-two-signal-routing-attempt'else 1200))
    r['phase_results']=phases
    stream=files['supervision/one-two-signal-routing-attempt.stdout']
    r['route_log'].update(bytes=len(stream),sha256=a.c.digest(stream))
    r['outputs'].update({n:a.c.digest(b)for n,b in files.items()})
    return files,r,names
def boundary_controls():
    positive=[];refused=[]
    run=a.value(a.c.regular(a.c.ROOT/(a.PREFIX+'.run.json')).read_bytes())
    jobs=a.value(a.c.regular(a.c.ROOT/(a.PREFIX+'.jobs.json')).read_bytes())
    release=a.value(a.c.regular(a.c.ROOT/(a.PREFIX+'.release.json')).read_bytes())
    tag=a.value(a.c.regular(a.c.ROOT/(a.PREFIX+'.tag.json')).read_bytes())
    values=[run,jobs,release,tag]
    assert a.live_envelope(*values)['repair_succeeded']is False
    r=a.expected_report(a.c.regular(a.c.ROOT/(a.PREFIX+'.summary.json')).read_bytes())
    assert a.manifest(a.c.regular(a.c.ROOT/(a.PREFIX+'.parts.json')).read_bytes())['sha256']==a.ARCHIVE
    positive.append('complete_actual_run_jobs_summary_parts_not_repair_acceptance')
    for label,fn in [
      ('wrong_source',lambda x:x[0].update(head_sha='0'*40)),
      ('wrong_attempt',lambda x:x[0].update(run_attempt=2)),
      ('not_terminal',lambda x:x[0].update(status='in_progress')),
      ('wrong_conclusion',lambda x:x[0].update(conclusion='failure')),
      ('missing_job',lambda x:x[1]['jobs'].pop()),
      ('wrong_job_source',lambda x:x[1]['jobs'][0].update(head_sha='0'*40)),
      ('wrong_asset',lambda x:x[2]['assets'][0].update(digest='sha256:'+'0'*64)),
      ('annotated_tag',lambda x:x[3]['object'].update(type='tag'))]:
        x=copy.deepcopy(values);fn(x);refused.append(reject(label,lambda x=x:a.live_envelope(*x)))
    files,r,names=fixture();selector=a.c.digest(a.c.canonical(names))
    with tempfile.TemporaryDirectory()as tmp,patch.object(a.repair,'SELECTED_SHA',selector):
        root=Path(tmp);write(root,files);got=a.inspect_saved(root,r)
        assert got['remaining_marker_count']==3 and got['changed_signal_count']==0
        assert got['classification']['exclusive_group_counts']=={'clock-signal':3}
        assert got['root_cause_established']is got['postroute_bridge_eligible']is got['repair_succeeded']is False
        assert set(got['exact_target_rows'])==set(a.source.TARGETS)and len(got['exact_special_rows'])==2
        positive.append('actual_full_saved_join_143820_synthetic_nets_actual_three_marker_bodies')
    def altered(name,fn,top=None):
        body=copy.deepcopy(files);report=copy.deepcopy(r)
        x=json.loads(body[name]);fn(x);body[name]=encoded(x)
        report['outputs'].update({n:a.c.digest(b)for n,b in body.items()})
        if top:top(report,x)
        with tempfile.TemporaryDirectory()as tmp,patch.object(a.repair,'SELECTED_SHA',selector):
            root=Path(tmp);write(root,body);a.inspect_saved(root,report)
    for label,name,fn,top in [
      ('saved_command_differs','supervision/ownership.command.json',lambda x:x.update(returncode=1),None),
      ('saved_stream_digest','supervision/one-two-signal-routing-attempt.command.json',lambda x:x.update(stdout_sha256='0'*64),None),
      ('live_descendant','supervision/drc-audit.command.json',lambda x:x['process_group_cleanup'].update(remaining_live=[7]),None),
      ('clock_gate_false','work/drc-audit-result.json',lambda x:x.update(original1691_clock_gate_passed=False),lambda r,x:r.update(native_result=x)),
      ('native_invariant_false','work/drc-audit-result.json',lambda x:x.update(native_invariants_passed=False),lambda r,x:r.update(native_result=x)),
      ('unfix_candidate','work/unfix-audit-result.json',lambda x:x.update(candidate_sha256='0'*64),None),
      ('restored_DEF','work/unfix-audit-result.json',lambda x:x.update(expected_def_sha256='0'*64),None),
      ('changed_signal_claim','work/drc-audit-result.json',lambda x:x['routing_delta'].update(changed_signal_count=1,changed_signal_names=['net459']),lambda r,x:r.update(native_result=x)),
      ('gate_census','work/original-gate-after-final-two-net-drc/result.json',lambda x:x.update(clock_or_fixed_nets=1690),None),
      ('ownership_body','work/ownership.json',lambda x:x.update(eligible_for_one_two_net_attempt=False),None),
      ('duplicate_selector','work/owners.json',lambda x:x['selected'].__setitem__(1,x['selected'][0]),None),
      ('incomplete_census','work/router-census-observed.json',lambda x:x.update(enumeration_complete=False),None),
      ('wrong_fixed_database','work/router-census-observed.json',lambda x:x.update(source_odb_sha256='0'*64),None),
      ('ordinary_power_not_special','work/router-census-observed.json',lambda x:x['rows']['fixture_special_power'].update(special=False),None),
      ('target_fixed','work/router-census-observed.json',lambda x:x['rows']['net459'].update(metadata='FIXED',paths=['FIXED']),None),
      ('saved_census_refusals','work/router-census-report.json',lambda x:x.update(refusals=[{'name':'net459','reason':'fixture'}]),None),
      ('saved_census_digest','work/router-census-report.json',lambda x:x.update(rows_sha256='0'*64),None),
      ('plan_digest','work/fixed-audit-result.json',lambda x:x.update(repair_tcl_sha256='0'*64),None),
      ('class_missing','work/original-classes.json',lambda x:x.pop(next(iter(x))),None),
      ('class_unknown','work/original-classes.json',lambda x:x.update({next(iter(x)):'COVER'}),None)]:
        refused.append(reject(label,lambda name=name,fn=fn,top=top:altered(name,fn,top)))
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp)/'capsule';root.mkdir();transport=Path(tmp)/'parts';transport.mkdir()
        tiny={'result.json':b'{}','selected.txt':b'exact selected','unselected.odb':b'explicit synthetic ODB bytes'}
        write(root,tiny);m=pack(root,'fixture',transport,127);expected={p:a.c.digest(b)for p,b in tiny.items()}
        p=a.audit_extract(m,transport,Path(tmp)/'selected',expected,['selected.txt'])
        assert len(p['all_original_files'])==3 and not(Path(tmp)/'selected/unselected.odb').exists()
        positive.append('real_streamed_archive_complete_member_authentication_selected_text_only')
        expected['unselected.odb']='0'*64
        refused.append(reject('unselected_member_hash',lambda:a.audit_extract(m,transport,Path(tmp)/'bad',expected,['selected.txt'])))
    assert len(positive)==3 and len(refused)==29
    return dict(positive=positive,rejected=refused,full_native_input_or_archive_accessed=False,
      synthetic_ODB_bytes_only=True,actual_three_marker_bodies=True)
def lifecycle_controls():
    import io
    import ensure_cloud_tested_source_release as guard
    cases=[]
    modes=('complete','body_failure','malformed_command','cleanup_failure','source_failure',
      'body_and_cleanup','inventory_failure','command_read_failure','heartbeat_stop_failure',
      'terminal_save_failure','body_and_terminal_save')
    for mode in modes:
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);out=root/'out';transport=root/'transport';after=[False]
            primary=RuntimeError('EXACT_READBACK_BODY_FAILURE');cleanup=RuntimeError('EXACT_READBACK_CLEANUP_FAILURE')
            source=AssertionError('EXACT_READBACK_FINAL_SOURCE_FAILURE');inv=ValueError('EXACT_READBACK_INVENTORY_FAILURE')
            command_read=OSError('EXACT_READBACK_TERMINAL_COMMAND_READ_FAILURE')
            heartbeat_stop=RuntimeError('EXACT_READBACK_HEARTBEAT_STOP_FAILURE')
            terminal_save=OSError('EXACT_READBACK_TERMINAL_SAVE_FAILURE')
            calls=dict(method=0,command_read=0,result_save=0,thread_start=0,thread_join=0)
            captured=io.StringIO();event=threading.Event()
            original_regular=d.c.regular;original_save=d.save;original_inventory=d.inventory
            def method():
                calls['method']+=1
                if mode=='source_failure'and after[0]:raise source
                return dict(cloud_readback_authorized=True,protected={d.runtime.SAMPLER:'f'*64})
            def supervised(argv,label,**kw):
                assert argv[-1]=='--worker'and label==d.LABEL and kw==dict(seconds=1200,cwd=d.ROOT)
                (out/'saved').mkdir();(out/'saved/retained.json').write_bytes(b'{"retained":true}')
                stdout=b'complete synthetic stream';row=dict(label=label,returncode=0,supervision_failure=None,
                  process_group_cleanup=dict(remaining_live=[]),stdout_bytes=len(stdout),stdout_sha256=a.c.digest(stdout),
                  stderr_bytes=0,stderr_sha256=a.c.digest(b''))
                trace=out/'supervision'
                for suffix,raw in [('stdout',stdout),('stderr',b''),('command.json',encoded(row))]:(trace/(label+'.'+suffix)).write_bytes(raw)
                d.save(out/'classification-index.json',dict(marker_count=3,repair_succeeded=False))
                d.save(out/'source-admission.json',dict(synthetic=True))
                if mode=='malformed_command':(trace/(label+'.command.json')).write_bytes(b'{"label":')
                after[0]=True
                if mode in ('body_failure','body_and_cleanup','malformed_command','body_and_terminal_save'):raise primary
            def stop(p):
                if mode in ('cleanup_failure','body_and_cleanup'):raise cleanup
                return dict(remaining_live=[])
            def event_stop():
                if mode=='heartbeat_stop_failure':raise heartbeat_stop
                event.set()
            def thread_start():calls['thread_start']+=1
            def thread_join(timeout):
                assert timeout==2;calls['thread_join']+=1
            thread=types.SimpleNamespace(start=thread_start,join=thread_join)
            sup=types.SimpleNamespace(ACTIVE=None,STOP=types.SimpleNamespace(set=event_stop),TRACE=out/'supervision',
              interrupted=lambda *x:None,heartbeat=lambda:None,stop_process=stop,supervised=supervised)
            def inventory(path):
                if mode=='inventory_failure':raise inv
                return original_inventory(path)
            def regular(path):
                if path==out/'supervision'/(d.LABEL+'.command.json'):
                    calls['command_read']+=1
                    if mode=='command_read_failure'and calls['command_read']==2:raise command_read
                return original_regular(path)
            def save(path,value):
                if path==out/'result.json':
                    calls['result_save']+=1
                    if mode in ('terminal_save_failure','body_and_terminal_save')and calls['result_save']==2:raise terminal_save
                return original_save(path,value)
            with patch.object(d,'OUT',out),patch.object(d,'TRANSPORT',transport),patch.object(d,'methods',method),\
              patch.object(d.runtime,'supervisor',return_value=sup),patch.object(d,'inventory',side_effect=inventory),\
              patch.object(d.c,'regular',side_effect=regular),patch.object(d,'save',side_effect=save),\
              patch.object(d.threading,'Thread',return_value=thread),patch.object(d.sys,'stderr',captured),\
              patch.object(d.shutil,'disk_usage',return_value=types.SimpleNamespace(free=32*1024**3)),\
              patch.object(guard,'context',return_value=('tag','a'*40)),patch.object(guard,'api',return_value={}),\
              patch.object(guard,'validate_release',return_value={}):
                expected={'body_failure':primary,'malformed_command':primary,'cleanup_failure':cleanup,
                  'source_failure':source,'body_and_cleanup':primary,'inventory_failure':inv,
                  'command_read_failure':command_read,'heartbeat_stop_failure':heartbeat_stop,
                  'terminal_save_failure':terminal_save,'body_and_terminal_save':primary}.get(mode)
                try:d.run()
                except BaseException as got:assert got is expected,(mode,got,expected)
                else:assert expected is None
            disk=json.loads((out/'result.json').read_bytes());fallback=captured.getvalue()
            if mode in ('terminal_save_failure','body_and_terminal_save'):
                prefix='CURRENT_TWO_SIGNAL_READBACK_UNSAVED_RESULT '
                assert fallback.startswith(prefix)and len(fallback.splitlines())==1
                saved=json.loads(fallback[len(prefix):])
                assert saved['terminal_save_error']==repr(terminal_save)and saved['terminal_result_persisted']is False
                assert disk['status']=='RUNNING_CURRENT_TWO_SIGNAL_TEXT_READBACK'
                assert calls['result_save']==2
            else:
                assert fallback=='';saved=disk
            assert saved['repair_succeeded']is saved['postroute_bridge_eligible']is False
            assert [x['label']for x in saved['terminal_checks']]==[
              'owned-process-cleanup','heartbeat-stop','heartbeat-join',
              'restore-signal-'+str(d.signal.SIGINT),'restore-signal-'+str(d.signal.SIGTERM)]
            assert calls['thread_start']==calls['thread_join']==1 and calls['method']==2
            assert event.is_set()is(mode!='heartbeat_stop_failure')
            assert (out/'saved/retained.json').read_bytes()==b'{"retained":true}'
            assert saved['status']==('COMPLETE_CURRENT_TWO_SIGNAL_TEXT_READBACK_UNSUCCESSFUL_REPAIR_RETAINED'if mode=='complete'else'FAIL_OR_INTERRUPTED_CURRENT_TWO_SIGNAL_READBACK')
            if mode!='inventory_failure':
                assert saved['outputs']=={p:x['sha256']for p,x in original_inventory(out).items()if p!='result.json'}
            if mode=='malformed_command':assert saved['terminal_command_parse_error']and 'terminal_command_record'not in saved
            if mode=='command_read_failure':
                assert saved['terminal_command_acquisition_error']==repr(command_read)
                assert 'terminal_command_raw'not in saved and 'terminal_command_record'not in saved
                assert calls['command_read']>=2
            if mode=='heartbeat_stop_failure':
                assert saved['terminal_checks'][1]['error']==repr(heartbeat_stop)
                assert saved['terminal_checks'][2]['status']=='PASS'
            if mode=='body_and_cleanup':
                assert saved['error']==repr(primary)and saved['terminal_checks'][0]['error']==repr(cleanup)
            if mode=='body_and_terminal_save':assert saved['error']==repr(primary)
            cases.append(mode)
    assert len(cases)==11
    return dict(actual_run_finally_cases=cases,real_error_identity_preserved=True,
      complete_unsaved_terminal_result_fallback=True,independent_heartbeat_stop_and_join=True,
      synthetic_worker_supervisor_and_thread_collaborators=True)

def authorization_controls():
    positive=[];negative=[]
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);(root/'scripts').mkdir()
        (root/'scripts/fixture.py').write_bytes(b'# explicit synthetic source\n')
        path=root/'method.json'
        tested=dict(source_controls_authorized=True,cloud_readback_authorized=False,
          native_execution_authorized=False,native_routing_authorized=False,simulation_authorized=False,
          rc_sta_execution_authorized=False,full_phy_accepted=False,source_unit_complete=True,
          readback_seconds=1200,original_run=a.RUN,completed_controls=None,
          protected={'scripts/fixture.py':a.c.file_sha(root/'scripts/fixture.py')})
        paths=['proof/tested.json','proof/boundary.json','proof/imports.json']
        values={paths[0]:tested,paths[1]:dict(status='PASS_CURRENT_TWO_SIGNAL_TEXT_READBACK_SOURCE_CONTROLS',source_head='a'*40),
          paths[2]:dict(status='PASS_ACTUAL_CURRENT_TWO_SIGNAL_READBACK_IMPORT_DATA_CLOSURE')}
        for p,v in values.items():
            target=root/p;target.parent.mkdir(exist_ok=True);target.write_bytes(encoded(v))
        enabled=copy.deepcopy(tested);enabled['cloud_readback_authorized']=True
        enabled['protected'].update({p:a.c.file_sha(root/p)for p in paths})
        enabled['completed_controls']=dict(source_head='a'*40,proof_paths=paths,
          tested_method=paths[0],boundary=paths[1],imports=paths[2])
        with patch.object(d,'ROOT',root),patch.object(d,'METHOD',path):
            disabled=copy.deepcopy(tested);disabled['source_controls_authorized']=False
            for label,m in [('disabled',disabled),('controls_only',tested),('readback_after_complete_proof',enabled)]:
                path.write_bytes(encoded(m));assert d.methods()==m;positive.append(label)
            for label,fn in [
              ('native',lambda m:m.update(native_execution_authorized=True)),
              ('routing',lambda m:m.update(native_routing_authorized=True)),
              ('simulation',lambda m:m.update(simulation_authorized=True)),
              ('RC_STA',lambda m:m.update(rc_sta_execution_authorized=True)),
              ('physical_acceptance',lambda m:m.update(full_phy_accepted=True)),
              ('source_false',lambda m:m.update(source_controls_authorized=False)),
              ('readback_not_bool',lambda m:m.update(cloud_readback_authorized=1)),
              ('wrong_budget',lambda m:m.update(readback_seconds=1201)),
              ('wrong_original_run',lambda m:m.update(original_run=1)),
              ('incomplete_source',lambda m:m.update(source_unit_complete=False)),
              ('missing_complete_proof',lambda m:m.update(completed_controls=None)),
              ('untested_metadata',lambda m:m.update(extra_untested_field=True))]:
                m=copy.deepcopy(enabled);fn(m);path.write_bytes(encoded(m))
                negative.append(reject(label,d.methods))
    assert len(positive)==3 and len(negative)==12
    return dict(positive=positive,rejected=negative,actual_methods_and_normalization=True,
      synthetic_source_and_control_proof_files=True)

def controls():
    assert d.methods()['source_controls_authorized']is True
    boundary=boundary_controls();authorization=authorization_controls()
    # Invoke the inherited actual publication/pack/reserved-only fixtures against this new driver.
    with patch.object(old,'d',d):
        publication=old.publication_controls()
    import check_mainchip_saved_postroute_publication as pubcheck
    import publish_mainchip_saved_postroute as publisher
    import wait_cloud_tested_source_release as waiter
    with patch.object(publisher,'GROUP',d.GROUP):transport=pubcheck.controls()
    wait=waiter.controls()
    assert len(transport['positives'])==3 and len(transport['rejected'])==13
    assert len(wait['positive_cases'])==3 and len(wait['rejected'])==4
    return dict(status='PASS_CURRENT_TWO_SIGNAL_TEXT_READBACK_SOURCE_CONTROLS',source_head=os.environ['GITHUB_SHA'],
      boundary=boundary,authorization=authorization,lifecycle=lifecycle_controls(),publication=publication,
      inherited_transport=transport,inherited_reservation=wait,
      native_or_input_archive_accessed=False,accepted=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);r=dict(status='RUNNING_SOURCE_CONTROLS',source_head=os.environ['GITHUB_SHA'])
    try:r.update(controls())
    except BaseException as exc:r.update(status='FAIL_SOURCE_CONTROLS',error=repr(exc));raise
    finally:d.save(OUT/'boundary-controls.json',r)
if __name__=='__main__':main()
