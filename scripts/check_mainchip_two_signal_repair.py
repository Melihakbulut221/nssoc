#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls for actual ownership functions and conditional driver. No CAD."""
import ast,copy,contextlib,json,os,sys,tempfile,types
from pathlib import Path
from unittest.mock import patch
import mainchip_two_signal_geometry as g
import mainchip_two_signal_repair as s
import cloud_mainchip_two_signal_repair as driver
from check_mainchip_original_clock_restoration_driver import emit
OUT=s.ROOT/'cloud-mainchip-two-signal-controls'

def catalog():
    return dict(layers={1:dict(name='Metal5',width=10,wrong_way_width=14,direction='HORIZONTAL'),
        2:dict(name='Metal6',width=12,wrong_way_width=18,direction='VERTICAL')},
        rules={'tech:1':18,'block:1':22},
        vias={'tech:1':dict(name='V56',top=2,bottom=1,box=[-2,-2,2,2],components=[
            dict(layer=1,box=[-2,-2,2,2],box_id=7),
            dict(layer=2,box=[-1,-1,1,1],box_id=8)])})

def projection_controls():
    positive=[];rejected=[]
    def check(name,raw,boxes):
        value=g.project_wire(raw,catalog())
        assert [x['box']for x in value['shapes']]==boxes,(name,value)
        assert value['raw_count']==len(raw)and value['raw_sha256']==g.digest(raw)
        positive.append(name);return value
    check('horizontal_and_wrong_way_vertical',[[96,1],[4,0],[5,0],[4,20],[5,30]],
          [[-5,-5,25,5],[13,-5,27,35]])
    check('explicit_zero_and_end_extension',[[96,1],[4,0],[133,0],[11,0],[132,20],[11,3]],
          [[0,-5,23,5]])
    check('decreasing_axis_and_point',[[96,1],[4,20],[5,20],[4,0],[6,0]],
          [[-5,15,25,25],[-5,15,5,25]])
    check('junction_restores_native_point_and_layer',[[96,1],[4,0],[5,0],[4,20],[98,3],[6,0],[5,20]],
          [[-5,-5,25,5],[13,-5,27,25]])
    via=check('every_via_component_and_next_layer',[[96,1],[4,0],[5,0],[136,1],[5,20]],
          [[-2,-2,2,2],[-1,-1,1,1],[-6,-6,6,26]])
    assert [x['native_box_id']for x in via['shapes'][:2]]==[7,8]
    check('rect_operands_preserved',[[96,1],[4,10],[5,20],[14,-2],[11,-3],[11,4],[11,5]],
          [[8,17,14,25]])
    check('block_rule_width',[[96,1],[131,1],[4,0],[5,0],[4,20]],[[-11,-11,31,11]])
    check('cpp_width_flag_persists_at_new_path',[[96,1],[3,1],[4,0],[5,0],[4,20],
          [96,2],[4,0],[5,0],[4,20]],[[-9,-9,29,9],[-6,-6,26,6]])
    check('collinear_extension_and_cancellation',[[96,1],[4,0],[5,0],[134,3],[6,0],[4,20]],
          [[-5,-5,25,5]])
    def reject(name,fn,message):
        try:fn()
        except AssertionError as exc:assert message in str(exc),(name,exc)
        else:raise AssertionError('Mutation accepted: '+name)
        rejected.append(name)
    raw=[[96,1],[4,0],[5,0],[4,20]]
    for name,value,message in [
        ('bool_opcode',[[True,1]],'Invalid raw'),('float_coordinate',[[96,1],[4,0.0]],'Invalid raw'),
        ('unknown_opcode',[[31,1]],'Unknown wire'),('truncated_initial_point',[[96,1],[4,0]],'Truncated'),
        ('wrong_initial_Y',[[96,1],[4,0],[6,0]],'Initial X'),('Y_without_X',[[96,1],[5,0]],'Initial Y'),
        ('missing_layer',[[96,99],[4,0],[5,0]],'Unknown path'),
        ('extension_wrong_operand',[[96,1],[4,0],[133,0],[12,2]],'Extension operand'),
        ('rect_wrong_operand',[[96,1],[4,0],[5,0],[14,0],[12,0],[11,2],[11,2]],'RECT operand'),
        ('rect_zero_area',[[96,1],[4,0],[5,0],[14,0],[11,0],[11,0],[11,2]],'Positive-area'),
        ('junction_outside',[[98,99]],'out of bounds'),('junction_cycle',[[98,0]],'Cyclic')]:
        reject(name,lambda value=value:g.project_wire(value,catalog()),message)
    reject('diagonal_segment',lambda:g.segment([0,0],[1,2],None,None,2,2),'Nonorthogonal')
    reject('bool_marker_units',lambda:g.marker_boxes(True),'')
    reject('off_grid_marker',lambda:g.marker_boxes(1),'grid')
    bad=catalog();bad['vias']['tech:1']['components']=[]
    reject('empty_via_material',lambda:g.project_wire(raw,bad),'')
    bad=catalog();bad['layers'][1]['width']=0
    reject('zero_wire_width',lambda:g.project_wire(raw,bad),'routing width')
    assert len(positive)==9 and len(rejected)==17
    return dict(positive=positive,rejected=rejected,synthetic_explicit_DBU_oracles=True)

def decision_fixture():
    markers=g.marker_boxes(2000);rows=[]
    for m in markers:
        for owner,kind in ((m['target'],'wire'),(g.CLOCK,'wire')):
            rows.append(dict(record_id=str([m['ordinal'],owner]),owner=owner,kind=kind,
                layer='Metal5',box=list(m['box']),route_class='ROUTED',
                source_indices=[[other['ordinal'],i]for other in markers for i,name in enumerate(other['source_names'])if name==owner]))
    return markers,rows

def decision_controls():
    markers,rows=decision_fixture()
    result=g.ownership_decision(markers,rows)
    assert result['eligible_for_one_two_net_attempt']and not result['blockers']
    # Overlapping marker rectangles intentionally retain repeated native observations.
    assert {x['marker']for x in result['witnesses']}=={0,1,2}
    positives=['all_three_exact_source_pair_overlaps']
    rejected=[]
    for kind in ('iterm-pin','bterm-pin','master-obstruction','block-obstruction','special-wire','special-via','metal-fill'):
        bad=copy.deepcopy(rows);bad[0]['kind']=kind
        if 'obstruction'in kind or kind=='metal-fill':bad[0].update(owner=None,source_indices=[])
        r=g.ownership_decision(markers,bad)
        assert not r['eligible_for_one_two_net_attempt']and r['blockers'];rejected.append('immutable:'+kind)
    for name,mutate in [
        ('foreign_net',lambda b:b[0].update(owner='third_net',source_indices=[])),
        ('unknown_owner',lambda b:b[0].update(owner=None,source_indices=[])),
        ('encoded_fixed_target',lambda b:b[0].update(route_class='FIXED')),
        ('source_pair_no_overlap',lambda b:[r.update(box=[0,0,1,1])for r in b if r['owner']=='net459']),
        ('wrong_layer',lambda b:[r.update(layer='Metal4')for r in b if r['owner']=='net459'])]:
        bad=copy.deepcopy(rows);mutate(bad);r=g.ownership_decision(markers,bad)
        assert not r['eligible_for_one_two_net_attempt']and r['blockers'];rejected.append(name)
    bad=copy.deepcopy(rows);bad[1]['record_id']=bad[0]['record_id']
    try:g.ownership_decision(markers,bad)
    except AssertionError as exc:assert str(exc)=='Duplicate native ownership record'
    else:raise AssertionError('duplicate native record accepted')
    rejected.append('duplicate_native_id')
    bad=copy.deepcopy(rows);bad[0]['source_indices']=[[2,1]]
    try:g.ownership_decision(markers,bad)
    except AssertionError as exc:assert str(exc)=='Original source index mapping differs'
    else:raise AssertionError('Wrong original source index accepted')
    rejected.append('wrong_original_source_index')
    # A fixed clock pin is immutable, but a target wire overlapping it can move.
    # Conversely a target pin is never movable; both cases are explicit.
    bad=copy.deepcopy(rows)
    for row in bad:
        if row['owner']==g.CLOCK:row['kind']='iterm-pin'
    assert g.ownership_decision(markers,bad)['eligible_for_one_two_net_attempt']
    positives.append('clock_pin_only_target_wire_may_move')
    assert len(positives)==2 and len(rejected)==14
    return dict(positive=positives,rejected=rejected)

def native_api_controls():
    # Import the real native adapter with an explicit empty odb stand-in only in controls.
    stub=types.ModuleType('odb')
    with patch.dict(sys.modules,{'odb':stub}):
        import mainchip_two_signal_ownership_native as native
        class Wire:
            def __init__(self):self.raw=[[96,1],[4,0],[5,0],[4,20]]
            def length(self):return len(self.raw)
            def getOpcode(self,i):return self.raw[i][0]
            def getData(self,i):return self.raw[i][1]
            def getCoord(self,i):return {2:[0,0],3:[20,0]}[i]
        wire=Wire();layers=catalog()['layers']
        got=native.native_wire(None,None,wire,layers)
        assert got['native_coordinate_checks_passed']
        assert got['shapes'][0]['box']==[-5,-5,25,5]
        with patch.object(Wire,'getCoord',lambda self,i:[1,1]):
            try:native.native_wire(None,None,wire,layers)
            except AssertionError as exc:assert 'Native coordinate mismatch'in str(exc)
            else:raise AssertionError('Native coordinate mismatch accepted')
        return dict(positive=['actual_native_wire_with_documented_raw_API_shape'],
            rejected=['actual_native_getCoord_disagreement'],native_odb_executed=False)

def budget_controls():
    positive=[];rejected=[]
    with tempfile.TemporaryDirectory(prefix='two-signal-budget-')as temp:
        trace=Path(temp);calls=[]
        def supervised(argv,label,seconds,cwd):
            calls.append((argv,label,seconds,cwd))
            driver.save(trace/(label+'.command.json'),dict(label=label,returncode=0))
        sup=types.SimpleNamespace(TRACE=trace,supervised=supervised)
        with patch.object(driver.base,'terminal_stream',lambda record,root,label:None):
            for label in sorted(driver.SHORT_PHASES):
                r=driver.execute_command(sup,['explicit-fixture'],label)
                assert r['requested_timeout_seconds']==1200 and calls[-1][2]==1200;positive.append(label)
            r=driver.execute_command(sup,['explicit-fixture'],'one-two-signal-routing-attempt')
            assert r['requested_timeout_seconds']==14400 and calls[-1][2]==14400
            positive.append('one-two-signal-routing-attempt')
            for label in ('unknown','one-signal-routing-attempt','one-two-signal-routing-attempt ',None,True):
                before=len(calls)
                try:driver.execute_command(sup,['explicit-fixture'],label)
                except AssertionError:pass
                else:raise AssertionError('Unknown phase launched')
                assert len(calls)==before;rejected.append(repr(label))
            error=RuntimeError('exact fixture supervisor error')
            def fail(*a,**k):raise error
            with patch.object(sup,'supervised',fail):
                try:driver.execute_command(sup,[],'ownership')
                except RuntimeError as exc:assert exc is error
                else:raise AssertionError('Supervisor error swallowed')
            rejected.append('exact_supervisor_exception_preserved')
    assert len(positive)==13 and len(rejected)==6
    return dict(positive=positive,rejected=rejected)

def phase_sequence(text):
    tree=ast.parse(text);run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
    rows=[]
    for node in ast.walk(run):
        if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):
            if node.func.id=='phase'and node.args and isinstance(node.args[0],ast.Constant):rows.append((node.lineno,node.args[0].value))
            elif node.func.id=='command'and len(node.args)==2 and isinstance(node.args[1],ast.Constant):rows.append((node.lineno,node.args[1].value))
    result=[v for _,v in sorted(rows)]
    assert result==['bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version',
        'ownership','prepare-fixed','paired-all-nontarget-fixed-import','fixed-audit',
        'one-two-signal-routing-attempt','route-audit','paired-original-class-return',
        'unfix-audit','full-original-class-read-only-DRT','drc-audit']
    return result

def sequence_controls():
    import check_mainchip_fixed_clock_signal_repair as inherited
    text=Path(driver.__file__).read_text();positive=phase_sequence(text);rejected=[]
    for kind,index,old,new in [('phase',0,'ownership','prepare-fixed'),
        ('phase',0,'fixed-audit','ownership'),('phase',0,'drc-audit','route-audit'),
        ('command',1,'full-original-class-read-only-DRT','paired-original-class-return')]:
        bad=inherited.mutate_phase_call(text,kind,index,old,new)
        try:phase_sequence(bad)
        except AssertionError:pass
        else:raise AssertionError('Actual phase-call mutation admitted')
        rejected.append(old)
    return dict(actual_sequence=positive,actual_call_mutations_refused=rejected)

def boundary_controls():
    names=[f'clock{i:04}'for i in range(1691)]
    names=sorted(names)
    other=[f'u{i:06}'for i in range(143820-len(names)-2)]
    order=[*names,*s.TARGETS,*other]
    records={}
    identity={};encoded={}
    for name in order:
        wired=name in names or name in s.TARGETS
        use='CLOCK'if name in names else'SIGNAL'
        records[name]=('- '+name+' ( u A ) ( v Z )\n  + USE '+use+
            ('\n  + ROUTED Metal5 ( 0 0 ) ( 20 * )'if wired else'')+'\n ;\n').encode()
        identity[name]=dict(name=name,sigtype=use,sha256=name)
        encoded[name]=dict(wire_present=wired,metadata='ROUTED',paths=['ROUTED']if wired else[])
    raw=b'VERSION 5.8 ;\nNETS 143820 ;\n'+b''.join(records.values())+b'END NETS\nEND DESIGN\n'
    baseline=dict(identity=identity,encoded=encoded,geometry={})
    with patch.object(s,'DEF_SHA',s.c.digest(raw)),patch.object(s.old,'SELECTED_SHA',s.c.digest(s.c.canonical(names))):
        owners,fixed,classes=s.ownership(raw,names,baseline)
    assert owners['mutable']==list(s.TARGETS)and len(owners['frozen'])==143818
    assert s.restore_expectation(fixed,classes)==raw
    after=s.c.replace_records(raw,{s.TARGETS[0]:records[s.TARGETS[0]].replace(b'( 20 * )',b'( 30 * )')})
    result=s.routing_delta(raw,after,owners);assert result['changed_signal_names']==[s.TARGETS[0]]
    positive=['full_143820_record_two_target_overlay','exact_original_class_roundtrip','only_one_allowed_signal_change']
    rejected=[]
    for name,bad in [('other_wire',s.c.replace_records(raw,{names[0]:records[names[0]].replace(b'( 20 * )',b'( 30 * )')})),
        ('target_connection',after.replace(b'- net36993 ( u A )',b'- net36993 ( wrong A )')),
        ('outside_NETS',after.replace(b'VERSION 5.8',b'VERSION 5.7')),
        ('protected_unwired',s.c.replace_records(raw,{other[0]:records[other[0]].replace(b'+ USE SIGNAL',b'+ USE RESET')}))]:
        try:s.routing_delta(raw,bad,owners)
        except AssertionError:pass
        else:raise AssertionError('Protected record accepted: '+name)
        rejected.append(name)
    rows={}
    for name in order:
        target=name in s.TARGETS;wired=encoded[name]['wire_present']
        rows[name]=dict(wire_present=wired,metadata='ROUTED'if target or not wired else'FIXED',
            paths=(['ROUTED']if target else['FIXED'])if wired else[],guides=1 if target else 0,
            terminals=2 if wired else 1,special=False)
    census=s.router_census(rows,owners);assert census['two_routed_nonfixed_guided_names']==sorted(s.TARGETS)
    positive.append('exact_two_router_candidates_with_unwired_nonguided_singletons')
    for name,key,value in [(names[0],'metadata','ROUTED'),(names[0],'paths',['ROUTED']),
        (other[0],'guides',1),(other[0],'terminals',2),(s.TARGETS[0],'guides',0),
        (s.TARGETS[0],'special',True)]:
        bad=dict(rows);bad[name]=dict(rows[name]);bad[name][key]=value
        try:s.router_census(bad,owners)
        except AssertionError:pass
        else:raise AssertionError('Router candidate escape accepted')
        rejected.append(name+':'+key)
    assert len(positive)==4 and len(rejected)==10
    return dict(positive=positive,rejected=rejected,synthetic_full_net_census=True)

def outer_controls():
    import threading
    import ensure_cloud_tested_source_release as guard
    positive=[];failures=[]
    for scenario in ('ownership-block','prepare-failure','route-failure','final-source-failure'):
        with tempfile.TemporaryDirectory(prefix='two-signal-main-')as temp:
            root=Path(temp);out=root/'out';transport=root/'transport';app=root/'explicit-stub.AppImage'
            app.write_bytes(b'explicit nonexecutable source fixture')
            marker,rows=decision_fixture();own=g.ownership_decision(marker,rows)
            own.update(read_only=True,source_net_count=3,all_net_count=143820,instance_count=153130,
                dbu_per_micron=2000,full_source_material={g.CLOCK:{},s.TARGETS[0]:{},s.TARGETS[1]:{}})
            if scenario=='ownership-block':
                own['records'][0]['kind']='iterm-pin'
                own.update(g.ownership_decision(own['markers'],own['records']))
            calls=[];stopped=[];gate_calls=0
            sup=types.SimpleNamespace(OUT=None,TRACE=None,ACTIVE=None,STOP=threading.Event(),
                heartbeat=lambda:None,interrupted=lambda *a:None,stop_process=lambda p:stopped.append(p))
            def method():
                nonlocal gate_calls
                gate_calls+=1
                if scenario=='final-source-failure'and gate_calls==2:raise AssertionError('exact final source fixture')
                return dict(cloud_restore_authorized=True,native_execution_authorized=True,native_routing_authorized=True)
            injected=RuntimeError('exact '+scenario)
            def execute(sup,argv,label):
                calls.append(label)
                if (scenario=='prepare-failure'and label=='prepare-fixed')or(scenario=='route-failure'and label=='one-two-signal-routing-attempt'):
                    raise injected
                if label=='ownership':driver.save(out/'work/ownership.json',own)
                if label=='one-two-signal-routing-attempt':
                    (out/'supervision'/('one-two-signal-routing-attempt.stdout')).write_bytes(b'explicit stub')
                if label=='drc-audit':driver.save(out/'work/drc-audit-result.json',dict(explicit_fixture=True))
                return dict(label=label,returncode=0)
            with contextlib.ExitStack()as stack:
                for obj,key,value in [(driver,'ROOT',root),(driver,'OUT',out),(driver,'TRANSPORT',transport),
                    (driver,'APP_SHA',s.c.file_sha(app)),(driver,'space',lambda stage:dict(stage=stage)),
                    (driver,'execute_command',execute),(driver,'restored_inputs',lambda:dict(explicit_fixture=True)),
                    (driver.base,'supervisor',lambda:sup),(s,'methods',method),
                    (s,'require_complete',lambda r:dict(explicit_fixture=True)),
                    (driver.qualified.s,'route_log',lambda b:dict(explicit_fixture=True)),
                    (guard,'context',lambda group,env:('fixture-tag','f'*40)),
                    (guard,'api',lambda path:{}),(guard,'validate_release',lambda *a:None)]:
                    stack.enter_context(patch.object(obj,key,value))
                stack.enter_context(patch.dict(os.environ,{'CLOUD_APPIMAGE':str(app)}))
                try:driver.run()
                except BaseException as exc:
                    if scenario in ('prepare-failure','route-failure'):assert exc is injected
                    elif scenario=='ownership-block':assert isinstance(exc,AssertionError)and 'forbids routing'in str(exc)
                    else:assert isinstance(exc,AssertionError)and str(exc)=='exact final source fixture'
                else:raise AssertionError('Real outer failure fixture returned success')
            result=json.loads((out/'result.json').read_bytes())
            assert result['status']=='FAIL_OR_BLOCKED_TWO_SIGNAL_ATTEMPT'
            assert result['original_guard_failure_preserved']and not result['accepted']
            assert len(stopped)==1 and sup.STOP.is_set()
            if scenario in ('ownership-block','prepare-failure'):
                assert 'one-two-signal-routing-attempt'not in calls and not result['native_routing_started']
            else:assert calls.count('one-two-signal-routing-attempt')==1
            assert 'work/ownership.json'in result['outputs']
            failures.append(dict(name=scenario,actual_calls=calls,result=result))
    positive.append('actual_outer_run_finally_and_exact_failure_records')
    assert len(failures)==4
    return dict(positive=positive,rejected=failures,all_CAD_and_remote_IO_explicit_stubs=True)

def disconnected_pin_controls():
    """Actual collect() with a full synthetic census and unowned native API-shaped pins."""
    with patch.dict(sys.modules,{'odb':types.ModuleType('odb')}):
        import mainchip_two_signal_ownership_native as native
    class Layer:
        def getId(self):return 1
        def getName(self):return 'Metal5'
        def getWidth(self):return 400
        def getWrongWayWidth(self):return 400
        def getDirection(self):return 'HORIZONTAL'
    layer=Layer()
    class Box:
        def __init__(self,values):self.values=values
        def xMin(self):return self.values[0]
        def yMin(self):return self.values[1]
        def xMax(self):return self.values[2]
        def yMax(self):return self.values[3]
        def getTechLayer(self):return layer
        def getId(self):return 99
        def isVia(self):return False
    class Master:
        def getName(self):return 'explicit_master'
        def getLib(self):return types.SimpleNamespace(getName=lambda:'explicit_lib')
        def getObstructions(self,include):assert include is True;return []
    master=Master()
    class Instance:
        def __init__(self,index):self.index=index
        def getName(self):return f'i{self.index:06}'
        def getMaster(self):return master
        def getTransform(self):return None
    instances=[Instance(i)for i in range(153130)]
    class Wire:
        def __init__(self,index,start,end):
            self.index=index;self.raw=[[96,1],[4,start],[5,3580080],[4,end]]
        def getId(self):return self.index
        def length(self):return len(self.raw)
        def getOpcode(self,i):return self.raw[i][0]
        def getData(self,i):return self.raw[i][1]
        def getCoord(self,i):return [self.raw[1 if i==2 else 3][1],3580080]
    wires={g.CLOCK:Wire(1,1887270,1901760),'net36993':Wire(2,1887270,1895040),
           'net459':Wire(3,1901660,1901860)}
    class Net:
        def __init__(self,index,name):self.index=index;self.name=name
        def getName(self):return self.name
        def getId(self):return self.index
        def getWire(self):return wires.get(self.name)
        def getWireType(self):return 'ROUTED'
        def getSigType(self):return 'CLOCK'if self.name==g.CLOCK else'SIGNAL'
        def isSpecial(self):return False
        def getITerms(self):return []
        def getBTerms(self):return []
        def getSWires(self):return []
    nets=[Net(i+1,name)for i,name in enumerate([g.CLOCK,*g.TARGETS,*[f'n{i:06}'for i in range(143817)]])]
    marker_box=g.marker_boxes(2000)[0]['box']
    class ITerm:
        def getId(self):return 501
        def getNet(self):return None
        def getGeometries(self):return [(layer,Box(marker_box))]
        def getInst(self):return instances[0]
        def getMTerm(self):return types.SimpleNamespace(getName=lambda:'A')
    class BTerm:
        def getId(self):return 601
        def getName(self):return 'unowned_port'
        def getNet(self):return None
        def getBPins(self):return [types.SimpleNamespace(getId=lambda:701,getBoxes=lambda:[Box(marker_box)])]
    class Block:
        iterms=[];bterms=[];fills=[]
        def getChildren(self):return []
        def getFills(self):return self.fills
        def getDbUnitsPerMicron(self):return 2000
        def getNets(self):return nets
        def getITerms(self):return self.iterms
        def getBTerms(self):return self.bterms
        def getInsts(self):return instances
        def getObstructions(self):return []
    block=Block();tech=types.SimpleNamespace(getDbUnitsPerMicron=lambda:2000,getLayers=lambda:[layer])
    db=types.SimpleNamespace(getTech=lambda:tech)
    pristine=native.collect(db,block)
    assert pristine['eligible_for_one_two_net_attempt']and pristine['native_geometry_census']['all-block-iterm']==0
    rejected=[]
    for kind,pins in [('iterm',[ITerm()]),('bterm',[BTerm()])]:
        block.iterms=pins if kind=='iterm'else[]
        block.bterms=pins if kind=='bterm'else[]
        result=native.collect(db,block)
        assert not result['eligible_for_one_two_net_attempt']
        found=[r for r in result['records']if r['owner']is None and r['kind']==kind+'-pin']
        assert len(found)==1 and found[0]['source_indices']==[]
        assert result['native_geometry_census']['disconnected-'+kind]==1
        rejected.append('actual_collect_unowned_overlapping_'+kind)
    block.iterms=[];block.bterms=[]
    block.fills=[types.SimpleNamespace(getId=lambda:801,getTechLayer=lambda:layer,
        getRect=lambda:Box(marker_box),maskNumber=lambda:0,needsOPC=lambda:False)]
    result=native.collect(db,block)
    assert not result['eligible_for_one_two_net_attempt']
    fills=[r for r in result['records']if r['kind']=='metal-fill']
    assert len(fills)==1 and fills[0]['owner']is None and fills[0]['source_indices']==[]
    rejected.append('actual_collect_unowned_overlapping_metal_fill');block.fills=[]
    # Connected block terminals omitted by a net enumeration cannot silently disappear.
    class MissingConnected(ITerm):
        def getNet(self):return nets[0]
    block.iterms=[MissingConnected()];block.bterms=[]
    try:native.collect(db,block)
    except AssertionError:pass
    else:raise AssertionError('Unreconciled native terminal accepted')
    rejected.append('actual_collect_connected_terminal_census_mismatch')
    return dict(positive=['actual_full_synthetic_collector_pristine'],rejected=rejected,
        native_execution=False,all_143820_nets_and_153130_instances_explicitly_synthetic=True)

def transport_controls():
    import publish_mainchip_saved_postroute as publisher
    positives=[];rejected=[]
    original_out,original_transport=driver.qualified.OUT,driver.qualified.TRANSPORT
    original_selected=driver.capture.SELECTED
    for stage in ('qualified','failed'):
        with tempfile.TemporaryDirectory(prefix='two-signal-restore-')as temp:
            root=Path(temp);out=root/'out';out.mkdir();transport=root/'transport';seen=[]
            error=ValueError('exact '+stage+' transport fixture')
            def old_restore():
                assert driver.qualified.OUT==out and driver.qualified.TRANSPORT==transport/'qualified'
                seen.append('qualified')
                if stage=='qualified':raise error
            def failed_restore(path):
                assert path==transport/'failed'and s.INPUT in driver.capture.SELECTED
                assert set(original_selected)<=set(driver.capture.SELECTED)
                seen.append('failed');raise error
            with patch.object(driver,'OUT',out),patch.object(driver,'TRANSPORT',transport),\
                 patch.object(s,'methods',lambda:dict(cloud_restore_authorized=True)),\
                 patch.object(s,'readback',lambda:{}),patch.object(driver.qualified,'restore_worker',old_restore),\
                 patch.object(driver.capture,'restore',failed_restore):
                try:driver.restore_worker()
                except ValueError as exc:assert exc is error
                else:raise AssertionError('Transport failure swallowed')
            assert seen==(['qualified']if stage=='qualified'else['qualified','failed'])
            assert (driver.qualified.OUT,driver.qualified.TRANSPORT)==(original_out,original_transport)
            assert driver.capture.SELECTED==original_selected
            rejected.append('actual_restore_'+stage+'_failure_preserved')
    previous=publisher.GROUP;calls=[]
    def publish(root,destination):
        calls.append((root,destination,publisher.GROUP));return dict(explicit_fixture=True)
    with patch.object(driver,'space',lambda stage:{}),patch.object(publisher,'publish_evidence',publish):
        assert driver.publish()==dict(explicit_fixture=True)
    assert calls==[(driver.OUT,driver.ROOT/('publication-'+driver.GROUP),driver.GROUP)]and publisher.GROUP==previous
    positives.append('actual_reserved_publisher_group_and_paths')
    error=ValueError('exact new publisher fixture')
    def fail(root,destination):calls.append((root,destination,publisher.GROUP));raise error
    with patch.object(driver,'space',lambda stage:{}),patch.object(publisher,'publish_evidence',fail):
        try:driver.publish()
        except ValueError as exc:assert exc is error
        else:raise AssertionError('Publication failure swallowed')
    assert len(calls)==2 and publisher.GROUP==previous
    rejected.append('actual_new_publisher_error_and_finally')
    return dict(positive=positives,rejected=rejected)

def inherited_controls():
    import check_mainchip_fixed_clock_signal_repair as fixed
    import check_mainchip_signal_repair_readback as saved
    a=fixed.controls();b=saved.controls()
    assert len(a['positives'])==14 and len(a['refusals'])==50
    assert len(b['positives'])==4 and len(b['refusals'])==32
    return dict(qualified_fixed_class_restore_archive_publication=a,exact_failed_saved_capture=b)

def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    method=s.methods();assert method['source_controls_authorized']is True
    result=dict(status='PASS_TWO_SIGNAL_OWNERSHIP_AND_DRIVER_SOURCE_CONTROLS',
        projection=projection_controls(),decision=decision_controls(),native_API=native_api_controls(),
        budgets=budget_controls(),sequence=sequence_controls(),boundary=boundary_controls(),outer=outer_controls(),
        disconnected_pins=disconnected_pin_controls(),transport=transport_controls(),
        inherited=inherited_controls(),actual_runtime_executed=False,
        archive_accessed=False,synthetic_geometry_only=True)
    return result

def main():
    OUT.mkdir(exist_ok=False);r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'])
    try:r.update(controls())
    except BaseException as exc:r.update(status='FAIL_SOURCE_CONTROLS',error=repr(exc));raise
    finally:
        path=OUT/'boundary-controls.json';driver.save(path,r)
if __name__=='__main__':main()
