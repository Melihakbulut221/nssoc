#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual-function source fixtures; explicitly synthetic API, no archive or CAD."""
import ast,contextlib,copy,hashlib,json,os,sys,tempfile,threading,types
from pathlib import Path
from unittest.mock import patch
import mainchip_two_signal_api_probe as c
import mainchip_two_signal_api_probe_native as native
import cloud_mainchip_two_signal_api_probe as wrapper
from mainchip_two_signal_api_probe_fixture import fixture
from check_mainchip_original_clock_restoration_driver import emit
OUT=c.ROOT/'cloud-mainchip-two-signal-api-controls'

def census_controls():
    f=fixture();got=native.census(f.odb,f.db,f.block)
    assert got['complete_census_counts']['net']==143820 and got['complete_census_counts']['instance']==153130
    assert got['disconnected_iterms']==got['disconnected_bterms']==1
    assert got['raw_operand_native_lookups']['layers']=={'73':native.layer(f.lower)}
    row=got['raw_operand_native_lookups']['layers']['73']
    assert row['layer_number_observed_not_used_as_OID']==7 and row['routing_level_observed_not_used_as_OID']==5
    assert len(got['raw_operand_native_lookups']['vias']['tech:44']['components'])==4
    assert got['raw_terminal_named_joins']==[
        dict(kind='iterm',raw_OID=11,named_identity=['i000000','A'],owner=f.nets[0].getName()),
        dict(kind='bterm',raw_OID=12,named_identity=['connected_port'],owner=f.nets[0].getName())]
    assert all(not r['api']['methods']['getId']['present']and not r['api']['methods']['getOID']['present']
        for r in got['representative_api_surfaces'].values())
    positive=['actual_full_synthetic_census_without_getId_or_getOID','raw_OID_73_distinct_from_number7_level5',
        'both_raw_terminal_names_reconciled_and_all_duplicate_via_boxes_retained']
    rejected=[]
    def refuse(name,changes,error_type=AssertionError,message=None):
        partial={}
        with contextlib.ExitStack()as stack:
            for obj,key,value in changes:stack.enter_context(patch.object(obj,key,value))
            try:native.census(f.odb,f.db,f.block,partial)
            except error_type as exc:
                if message is not None:assert message in str(exc),(name,exc)
            else:raise AssertionError('Actual census fault accepted: '+name)
        assert partial['status']=='INCOMPLETE_API_CENSUS_PREFIX_ONLY'and partial['complete']is False
        rejected.append(name);return partial
    refuse('same_owner_absent_ITerm',[(f.odb.dbITerm,'getITerm',lambda scope,oid:f.ITerm(f.nets[0],'ABSENT'))],
        message='Raw ITerm named identity is absent')
    refuse('same_owner_absent_BTerm',[(f.odb.dbBTerm,'getBTerm',lambda scope,oid:f.BTerm(f.nets[0],'ABSENT'))],
        message='Raw BTerm named identity is absent')
    refuse('wrong_raw_terminal_owner',[(f.odb.dbITerm,'getITerm',lambda scope,oid:f.ITerm(f.nets[1]))])
    bad=f.Layer('Metal5',7,5);bad.getWidth=lambda:401
    refuse('raw_layer_differs_from_enumeration',[(f.odb.dbTechLayer,'getTechLayer',lambda scope,oid:bad)],
        message='Static raw layer lookup differs')
    refuse('duplicate_block_terminal',[(f.block,'getITerms',lambda:[f.it,f.it])])
    refuse('omitted_connected_BTerm',[(f.block,'getBTerms',lambda:[])])
    refuse('unknown_raw_via',[(f.odb.dbTechVia,'getTechVia',lambda scope,oid:None)])
    refuse('boolean_raw_operand',[(f.wire,'getData',lambda i:True)],message='Native integer is not exact int')
    refuse('duplicate_layer_name',[(f.tech,'getLayers',lambda:[f.lower,f.lower])])
    injected=AttributeError('exact late master API fixture')
    def late(*args):raise injected
    partial={}
    with patch.object(f.master,'getObstructions',late):
        try:native.census(f.odb,f.db,f.block,partial)
        except AttributeError as exc:assert exc is injected
        else:raise AssertionError('Late actual getter failure swallowed')
    assert partial['observed_counts']['instance']==153130
    assert partial['observed_counts']['net']==143820
    assert partial['streamed_prefix_sha256']['net']==got['complete_census_sha256']['net']
    assert partial['representative_api_surfaces']['net']==got['representative_api_surfaces']['net']
    assert partial['observed_raw_terminal_lookups']==got['raw_terminal_named_joins']
    assert not partial['complete']and 'complete_census_sha256'not in partial
    rejected.append('late_actual_getter_retains_explicit_incomplete_prefix')
    assert len(positive)==3 and len(rejected)==10
    return dict(positive=positive,rejected=rejected,explicit_synthetic_143820_nets_153130_instances=True),got

def report_controls(got):
    report=copy.deepcopy(got)
    report['input']=dict(member=c.original.INPUT,sha256=c.original.INPUT_SHA,bytes=c.original.INPUT_BYTES)
    report['terminal_checks']=[dict(label=x,status='PASS')for x in ('destroy-read-only-database','unchanged-source-file')]
    assert c.validate_report(report)['repair_eligible']is False
    rejected=[]
    faults=[('status','FAIL_READ_ONLY_API_CENSUS'),('all_net_count',143819),
        ('all_instance_count',153129),('complete_raw_opcode_data_pairs',0),
        ('every_raw_terminal_lookup_reconciled_with_both_censuses',False),
        ('every_block_terminal_reconciled_with_connected_net_census',False),
        ('ownership_eligible',True),('native_routing_started',True),('table_OIDs_invented',True),
        ('source_geometry_mutated',True),('original_getId_failure_preserved',False),
        ('terminal_checks',[dict(label='unchanged-source-file',status='FAIL')]),
        ('input',dict(member='wrong.odb',sha256=c.original.INPUT_SHA,bytes=c.original.INPUT_BYTES))]
    for key,value in faults:
        bad=copy.deepcopy(report);bad[key]=value
        try:c.validate_report(bad)
        except AssertionError:pass
        else:raise AssertionError('Report fault accepted: '+key)
        rejected.append(key)
    assert len(rejected)==13
    return dict(positive=['actual_complete_report_validation_remains_ineligible'],rejected=rejected),report

def native_main_controls(report):
    positive=[];rejected=[]
    for scenario in ('success','late-getter','cleanup','source-changed','body-and-cleanup'):
        with tempfile.TemporaryDirectory(prefix='api-native-main-')as temp:
            root=Path(temp);source=root/'source';source.mkdir();out=root/'out';out.mkdir()
            payload=b'explicit synthetic database fixture, not ODB';path=source/'fixture.odb';path.write_bytes(payload)
            injected=RuntimeError('exact '+scenario);secondary=ValueError('exact secondary destroy failure')
            destroyed=[];database=object();block=object()
            def census(odb,db,b,partial):
                assert db is database and b is block
                partial.update(status='INCOMPLETE_API_CENSUS_PREFIX_ONLY',complete=False,observed_counts={'net':1})
                if scenario in ('late-getter','body-and-cleanup'):raise injected
                if scenario=='source-changed':path.write_bytes(payload+b'changed')
                return copy.deepcopy(report)
            def destroy(db):
                assert db is database;destroyed.append(True)
                if scenario=='cleanup':raise injected
                if scenario=='body-and-cleanup':raise secondary
            odb=types.ModuleType('odb');odb.dbDatabase=types.SimpleNamespace(destroy=destroy)
            qualified=types.ModuleType('mainchip_original_clock_restoration_native')
            qualified.load=lambda p:(database,block)
            with contextlib.ExitStack()as stack:
                stack.enter_context(patch.dict(sys.modules,{'odb':odb,'mainchip_original_clock_restoration_native':qualified}))
                stack.enter_context(patch.dict(os.environ,{'GITHUB_ACTIONS':'true','GITHUB_RUN_ATTEMPT':'1',
                    'NSSOC_TWO_SIGNAL_FAILED_SOURCE':str(source),'NSSOC_TWO_SIGNAL_OUT':str(out)}))
                for obj,key,value in [(native,'census',census),(c,'methods',lambda:dict(native_api_probe_authorized=True,cloud_restore_authorized=True)),
                    (native.source,'INPUT','fixture.odb'),(native.source,'INPUT_SHA',hashlib.sha256(payload).hexdigest()),
                    (native.source,'INPUT_BYTES',len(payload))]:stack.enter_context(patch.object(obj,key,value))
                try:native.main()
                except BaseException as exc:
                    if scenario=='source-changed':assert type(exc)is AssertionError and 'Read-only input bytes changed'in str(exc)
                    else:assert scenario!='success'and exc is injected
                else:assert scenario=='success'
            saved=json.loads((out/'api-identity-census.json').read_bytes())
            assert destroyed==[True]and len(saved['terminal_checks'])==2
            if scenario=='success':
                assert saved['status'].startswith('COMPLETE_');positive.append(scenario)
            else:
                assert saved['status']=='FAIL_READ_ONLY_API_CENSUS'
                if scenario in ('late-getter','body-and-cleanup'):
                    assert saved['partial_census']['observed_counts']=={'net':1}and not saved['complete_census']
                rejected.append(scenario)
    return dict(positive=positive,rejected=rejected,actual_main_and_finally=True,ODB_executed=False)

def derived_controls(report):
    ns,proof=wrapper.namespace();positive=[];rejected=[]
    with tempfile.TemporaryDirectory(prefix='api-budget-')as temp:
        trace=Path(temp);calls=[]
        def supervised(argv,label,seconds,cwd):
            calls.append((label,seconds));ns['save'](trace/(label+'.command.json'),dict(label=label,returncode=0))
        sup=types.SimpleNamespace(TRACE=trace,supervised=supervised)
        with patch.object(ns['base'],'terminal_stream',lambda *a:None):
            for label in c.LABELS:
                assert ns['execute_command'](sup,[],label)['requested_timeout_seconds']==1200
                assert calls[-1]==(label,1200);positive.append(label)
            for label in ('ownership','one-two-signal-routing-attempt','api-identity-census ',True,None):
                before=len(calls)
                try:ns['execute_command'](sup,[],label)
                except AssertionError:pass
                else:raise AssertionError('Forbidden command reached supervisor')
                assert len(calls)==before;rejected.append(repr(label))
            error=ValueError('exact supervisor failure')
            def fail(*a,**k):raise error
            with patch.object(sup,'supervised',fail):
                try:ns['execute_command'](sup,[],'api-identity-census')
                except ValueError as exc:assert exc is error
                else:raise AssertionError('Supervisor failure swallowed')
            rejected.append('supervisor_exception_identity')
    tree=ast.parse(wrapper.derive()[0]);run=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='run')
    commands=[]
    for node in ast.walk(run):
        if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):
            if node.func.id=='phase'and node.args and isinstance(node.args[0],ast.Constant):commands.append((node.lineno,node.args[0].value))
            if node.func.id=='command'and len(node.args)==2 and isinstance(node.args[1],ast.Constant):commands.append((node.lineno,node.args[1].value))
    assert [x[1]for x in sorted(commands)]==list(c.LABELS)
    return dict(positive=positive,rejected=rejected,actual_phase_sequence=list(c.LABELS),derivation=proof)

def outer_controls(report):
    import ensure_cloud_tested_source_release as guard
    positives=[];rejected=[]
    scenarios=('success','partial-native-failure','malformed-native-failure','cleanup-failure','terminal-source-failure','body-and-cleanup')
    for scenario in scenarios:
        ns,_=wrapper.namespace()
        with tempfile.TemporaryDirectory(prefix='api-outer-')as temp:
            root=Path(temp);out=root/'out';transport=root/'transport';app=root/'explicit-stub.AppImage'
            app.write_bytes(b'explicit nonexecutable fixture')
            primary=RuntimeError('exact '+scenario);secondary=ValueError('exact cleanup secondary')
            oldout,oldtrace=object(),object();stopped=[];calls=[];gates=0
            def stop(process):
                stopped.append(process)
                if scenario=='cleanup-failure':raise primary
                if scenario=='body-and-cleanup':raise secondary
            sup=types.SimpleNamespace(OUT=oldout,TRACE=oldtrace,ACTIVE=None,STOP=threading.Event(),
                heartbeat=lambda:None,interrupted=lambda *a:None,stop_process=stop)
            def methods():
                nonlocal gates
                gates+=1
                if scenario=='terminal-source-failure'and gates==3:raise primary
                return dict(cloud_restore_authorized=True,native_execution_authorized=True,native_api_probe_authorized=True)
            def execute(sup,argv,label):
                calls.append(label)
                if label=='api-identity-census':
                    path=out/'work/api-identity-census.json'
                    if scenario=='malformed-native-failure':path.write_bytes(b'{"status":')
                    elif scenario in ('partial-native-failure','body-and-cleanup'):
                        ns['save'](path,dict(status='FAIL_READ_ONLY_API_CENSUS',complete_census=False,
                            partial_census=dict(status='INCOMPLETE_API_CENSUS_PREFIX_ONLY',observed_counts={'net':7})))
                    else:ns['save'](path,report)
                    if scenario in ('partial-native-failure','malformed-native-failure','body-and-cleanup'):raise primary
                return dict(label=label,returncode=0)
            ns.update(ROOT=root,OUT=out,TRANSPORT=transport,APP_SHA=c.c.file_sha(app),space=lambda stage:{'stage':stage},
                execute_command=execute,restored_inputs=lambda:{'explicit_fixture':True})
            with contextlib.ExitStack()as stack:
                for obj,key,value in [(ns['base'],'supervisor',lambda:sup),(ns['s'],'methods',methods),
                    (guard,'context',lambda group,env:('fixture','f'*40)),(guard,'api',lambda path:{}),
                    (guard,'validate_release',lambda *a:None)]:stack.enter_context(patch.object(obj,key,value))
                stack.enter_context(patch.dict(os.environ,{'CLOUD_APPIMAGE':str(app)}))
                try:ns['run']()
                except BaseException as exc:assert scenario!='success'and exc is primary
                else:assert scenario=='success'
            saved=json.loads((out/'result.json').read_bytes())
            assert calls==list(c.LABELS)and stopped==[None]and sup.STOP.is_set()
            assert sup.OUT is oldout and sup.TRACE is oldtrace
            assert len(saved['terminal_checks'])==6 and saved['terminal_checks'][-1]['label']=='preserve-api-diagnostic'
            assert saved['api_probe_saved_file']['sha256']==c.c.file_sha(out/'work/api-identity-census.json')
            assert saved['outputs']['work/api-identity-census.json']==saved['api_probe_saved_file']['sha256']
            assert saved['native_routing_started']is False and saved['accepted']is False
            if scenario=='success':
                assert saved['status']=='COMPLETE_READ_ONLY_API_IDENTITY_CENSUS_NOT_REPAIR';positives.append(scenario)
            else:
                assert saved['status']=='FAIL_OR_BLOCKED_READ_ONLY_API_CENSUS'
                assert saved['error']==repr(primary)
                if scenario=='malformed-native-failure':
                    assert saved['api_probe_saved_file']['complete']is False
                    assert saved['terminal_checks'][-1]['status']=='FAIL'
                if scenario in ('partial-native-failure','body-and-cleanup'):
                    assert saved['api_probe']['partial_census']['observed_counts']=={'net':7}
                rejected.append(scenario)
    return dict(positive=positives,rejected=rejected,actual_derived_run_and_finally=True)

def transport_controls():
    # Run the original actual restoration/global/publisher fixtures against this exact derived namespace.
    import check_mainchip_two_signal_repair as inherited
    ns,_=wrapper.namespace()
    class BoundNamespace:
        def __getattr__(self,key):
            try:return ns[key]
            except KeyError:raise AttributeError(key)from None
        def __setattr__(self,key,value):ns[key]=value
        def __delattr__(self,key):del ns[key]
    derived=BoundNamespace()
    with patch.object(inherited,'driver',derived),patch.object(inherited,'s',ns['s']):
        result=inherited.transport_controls()
    assert len(result['positive'])==1 and len(result['rejected'])==3
    return result

def authorization_controls():
    method=c.methods();positive=[];rejected=[]
    with tempfile.TemporaryDirectory(prefix='api-authorization-')as temp:
        path=Path(temp)/'methods.json'
        disabled=copy.deepcopy(method)
        for key in ('source_controls_authorized','cloud_restore_authorized','native_execution_authorized','native_api_probe_authorized'):
            disabled[key]=False
        path.write_text(json.dumps(disabled))
        with patch.object(c,'METHOD',path):
            assert c.methods()==disabled
            positive.append('actual_disabled_method_remains_valid_but_cannot_execute')
            faults=[(key,True)for key in ('native_routing_authorized','geometry_mutation_authorized',
                'simulation_authorized','rc_sta_execution_authorized','timing_accepted','full_phy_accepted')]
            faults += [('native_execution_authorized',True),('source_controls_authorized',1),
                ('input',dict(member='wrong.odb')),('limits',dict(phase_seconds=14400))]
            for key,value in faults:
                bad=copy.deepcopy(disabled);bad[key]=value;path.write_text(json.dumps(bad))
                try:c.methods()
                except AssertionError:pass
                else:raise AssertionError('Authorization mutation admitted: '+key)
                rejected.append(key)
        ns,_=wrapper.namespace()
        with patch.object(ns['s'],'methods',lambda:disabled):
            try:ns['run']()
            except AssertionError:pass
            else:raise AssertionError('Disabled native probe launched')
        rejected.append('actual_outer_run_rejects_disabled_before_reservation_or_outputs')
    return dict(positive=positive,rejected=rejected)

def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert c.methods()['source_controls_authorized']is True
    census,report=census_controls();validation,report=report_controls(report)
    return dict(status='PASS_READ_ONLY_API_PROBE_SOURCE_CONTROLS',census=census,report=validation,
        native_main=native_main_controls(report),driver=derived_controls(report),outer=outer_controls(report),
        transport=transport_controls(),authorization=authorization_controls(),native_runtime_executed=False,archive_accessed=False,
        original_failures_preserved=True,repair_eligible=False)

def main():
    OUT.mkdir(exist_ok=False);result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'])
    try:result.update(controls())
    except BaseException as exc:result.update(status='FAIL_SOURCE_CONTROLS',error=repr(exc));raise
    finally:native.save(OUT/'api-controls.json',result)
if __name__=='__main__':main()
