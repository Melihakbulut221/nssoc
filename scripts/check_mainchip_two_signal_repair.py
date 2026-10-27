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
    return dict(layers={'Metal5':dict(name='Metal5',width=10,wrong_way_width=14,direction='HORIZONTAL'),
        'Metal6':dict(name='Metal6',width=12,wrong_way_width=18,direction='VERTICAL')},
        path_layers={1:'Metal5',2:'Metal6'},rules={'tech:1':18,'block:1':22},
        vias={'tech:1':dict(name='V56',top='Metal6',bottom='Metal5',box=[-2,-2,2,2],components=[
            dict(layer='Metal5',box=[-2,-2,2,2],component_ordinal=0),
            dict(layer='Metal6',box=[-1,-1,1,1],component_ordinal=1)])})

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
    assert [x['component_identity']for x in via['shapes'][:2]]==[['tech:1',0],['tech:1',1]]
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
    bad=catalog();bad['layers']['Metal5']['width']=0
    reject('zero_wire_width',lambda:g.project_wire(raw,bad),'routing width')
    bad=catalog();bad['layers'][1]=bad['layers'].pop('Metal5')
    reject('raw_ID_used_as_named_layer_key',lambda:g.project_wire(raw,bad),'Named native layer catalogue key differs')
    bad=catalog();bad['path_layers']={True:'Metal5',2:'Metal6'}
    reject('bool_raw_path_layer_key',lambda:g.project_wire(raw,bad),'Invalid raw path layer join')
    bad=catalog();bad['vias']['tech:1']['components'][1]['component_ordinal']=0
    reject('duplicate_scoped_component_ordinal',lambda:g.project_wire(raw,bad),'Scoped via component ordinal differs')
    assert len(positive)==9 and len(rejected)==20
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
    """Actual native adapter with raw OIDs distinct from every named/numbered identity."""
    with patch.dict(sys.modules,{'odb':types.ModuleType('odb')}):
        import mainchip_two_signal_ownership_native as native
    class Layer:
        def __init__(self,name,width,number,level,direction):
            self.name=name;self.width=width;self.number=number;self.level=level;self.direction=direction
        def getName(self):return self.name
        def getWidth(self):return self.width
        def getWrongWayWidth(self):return self.width+4 if self.width else 0
        def getNumber(self):return self.number
        def getRoutingLevel(self):return self.level
        def getDirection(self):return self.direction
    lower=Layer('Metal5',10,7,5,'HORIZONTAL');upper=Layer('Metal6',12,9,6,'VERTICAL')
    cut=Layer('Via5',0,8,0,'NONE')
    class Box:
        def __init__(self,layer,coords=(-2,-2,2,2)):self.layer=layer;self.coords=coords
        def getTechLayer(self):return self.layer
        def xMin(self):return self.coords[0]
        def yMin(self):return self.coords[1]
        def xMax(self):return self.coords[2]
        def yMax(self):return self.coords[3]
        def isVia(self):return False
    class Via:
        def __init__(self):self.components=[Box(lower),Box(cut),Box(upper),Box(upper)]
        def getName(self):return 'V56'
        def getTopLayer(self):return upper
        def getBottomLayer(self):return lower
        def getBBox(self):return Box(lower)
        def getBoxes(self):return self.components
    via=Via()
    tech=types.SimpleNamespace(getLayers=lambda:[lower,upper,cut])
    db=types.SimpleNamespace(getTech=lambda:tech);block=object()
    proof=dict(complete_census_counts={'technology-layer':3},raw_operand_native_lookups=dict(
        layers={'73':dict(name='Metal5',width=10,wrong_way_width=14,direction='HORIZONTAL',
            layer_number_observed_not_used_as_OID=7,routing_level_observed_not_used_as_OID=5),
            '82':dict(name='Metal6',width=12,wrong_way_width=16,direction='VERTICAL',
            layer_number_observed_not_used_as_OID=9,routing_level_observed_not_used_as_OID=6)},
        rules={'block:52':dict(width=18)},vias={'tech:44':dict(name='V56',top='Metal6',bottom='Metal5',
            bbox=[-2,-2,2,2],components=[dict(layer=name,rect=[-2,-2,2,2],component_ordinal=i)
                for i,name in enumerate(['Metal5','Via5','Metal6','Metal6'])])}))
    calls=[]
    def lookup_layer(scope,oid):
        assert scope is tech;calls.append(('layer',oid))
        value={73:lower,82:upper}[oid]
        # A fresh wrapper-shaped object must join by validated record, never Python identity.
        return Layer(value.name,value.width,value.number,value.level,value.direction)
    def lookup_rule(scope,oid):
        assert scope is block and oid==52;calls.append(('rule',oid))
        return types.SimpleNamespace(getWidth=lambda:18)
    def lookup_via(scope,oid):
        assert scope is tech and oid==44;calls.append(('via',oid));return via
    odb=types.SimpleNamespace(dbTechLayer=types.SimpleNamespace(getTechLayer=lookup_layer),
        dbTechLayerRule=types.SimpleNamespace(getTechLayerRule=lookup_rule),
        dbTechVia=types.SimpleNamespace(getTechVia=lookup_via))
    class Wire:
        def __init__(self,raw,coordinates):self.raw=raw;self.coordinates=coordinates
        def length(self):return len(self.raw)
        def getOpcode(self,i):return self.raw[i][0]
        def getData(self,i):return self.raw[i][1]
        def getCoord(self,i):return self.coordinates[i]
    plain=Wire([[96,73],[4,0],[5,0],[4,20]],{2:[0,0],3:[20,0]})
    vwire=Wire([[96,73],[131,52],[4,0],[5,0],[136,44],[5,20]],{3:[0,0],5:[0,20]})
    positive=[];rejected=[]
    def reject(name,fn,message):
        try:fn()
        except AssertionError as exc:assert message in str(exc),(name,repr(exc))
        else:raise AssertionError('Actual native identity mutation admitted: '+name)
        rejected.append(name)
    with patch.object(native,'odb',odb):
        layers=native.named_layers(tech,proof)
        got=native.native_wire(db,block,plain,layers,proof)
        assert got['shapes'][0]['box']==[-5,-5,25,5]and got['raw']==plain.raw
        assert got['catalog']['path_layers']=={73:'Metal5'}and set(got['catalog']['layers'])=={'Metal5','Metal6','Via5'}
        assert calls==[('layer',73)]and not hasattr(lower,'getId')and not hasattr(lower,'getOID')
        positive.append('actual_raw_OID_73_distinct_from_number7_level5_and_fresh_wrapper')
        got=native.native_wire(db,block,vwire,layers,proof)
        assert [x['box']for x in got['shapes']]==[[-2,-2,2,2]]*4+[[-9,-9,9,29]]
        assert [x['component_identity']for x in got['shapes'][:4]]==[['tech:44',i]for i in range(4)]
        assert got['shapes'][2]['box']==got['shapes'][3]['box']and got['shapes'][2]['component_identity']!=got['shapes'][3]['component_identity']
        positive.append('actual_block_rule_tech_via_named_cut_layer_duplicate_multiplicity')
        with patch.object(plain,'getCoord',lambda i:[1,1]):
            reject('native_coordinate_disagreement',lambda:native.native_wire(db,block,plain,layers,proof),'Native coordinate mismatch')
        for value in (7,5,74):
            bad=copy.deepcopy(plain);bad.raw[0][1]=value
            reject('unobserved_layer_'+str(value),lambda bad=bad:native.native_wire(db,block,bad,layers,proof),'Unobserved raw layer OID')
        for kind in (9,10):
            bad=copy.deepcopy(plain);bad.raw.append([kind,11])
            reject('unobserved_raw_terminal_'+str(kind),lambda bad=bad:native.native_wire(db,block,bad,layers,proof),'Raw terminal static getter was not exercised')
        bad=copy.deepcopy(vwire);bad.raw[1][0]=3
        reject('unobserved_tech_rule_scope',lambda:native.native_wire(db,block,bad,layers,proof),'Unobserved raw layer-rule scope/OID')
        with patch.object(odb.dbTechLayerRule,'getTechLayerRule',lambda scope,oid:types.SimpleNamespace(getWidth=lambda:20)):
            reject('raw_rule_width_changed',lambda:native.native_wire(db,block,vwire,layers,proof),'Raw layer-rule width differs')
        for op,oid in ((135,44),(136,45)):
            bad=copy.deepcopy(vwire);bad.raw[4]=[op,oid]
            reject('unobserved_via_'+str(op)+'_'+str(oid),lambda bad=bad:native.native_wire(db,block,bad,layers,proof),'Unobserved raw via static getter scope/OID')
        with patch.object(odb.dbTechLayer,'getTechLayer',lambda scope,oid:upper):
            reject('static_layer_wrong_name',lambda:native.native_wire(db,block,plain,layers,proof),'Raw layer OID/name/geometry join differs')
        bad_layers=copy.deepcopy(layers);bad_layers['Metal5']['width']=22
        reject('independent_named_layer_differs',lambda:native.native_wire(db,block,plain,bad_layers,proof),'Raw layer differs from independent named census')
        with patch.object(via,'components',via.components[:-1]):
            reject('duplicate_via_component_dropped',lambda:native.native_wire(db,block,vwire,layers,proof),'Raw via OID/name/component join differs')
        with patch.object(via,'components',[Box(lower,(-3,-2,2,2)),*via.components[1:]]):
            reject('via_geometry_changed',lambda:native.native_wire(db,block,vwire,layers,proof),'Raw via OID/name/component join differs')
        with patch.object(odb.dbTechVia,'getTechVia',lambda scope,oid:None):
            reject('missing_actual_via',lambda:native.native_wire(db,block,vwire,layers,proof),'Missing native via geometry')
        bad=copy.deepcopy(plain);bad.raw.append([31,0])
        reject('unsupported_opcode',lambda:native.native_wire(db,block,bad,layers,proof),'Unknown wire opcode')
        bad=copy.deepcopy(plain);bad.raw[1][1]=True
        reject('bool_raw_coordinate',lambda:native.native_wire(db,block,bad,layers,proof),'Invalid native raw operand')
    assert len(positive)==2 and len(rejected)==17
    return dict(positive=positive,rejected=rejected,actual_native_adapter_functions=True,native_odb_executed=False,
        synthetic_API_objects_without_getId_or_getOID=True)

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
    scenarios=('success','ownership-block','prepare-failure','route-failure','final-source-failure',
               'cleanup-failure','terminal-source-failure','body-and-cleanup-failure')
    for scenario in scenarios:
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
            injected=RuntimeError('exact '+scenario)
            cleanup_error=ValueError('exact secondary cleanup fixture')
            def cleanup(process):
                stopped.append(process)
                if scenario=='cleanup-failure':raise injected
                if scenario=='body-and-cleanup-failure':raise cleanup_error
            oldout,oldtrace=object(),object()
            sup=types.SimpleNamespace(OUT=oldout,TRACE=oldtrace,ACTIVE=None,STOP=threading.Event(),
                heartbeat=lambda:None,interrupted=lambda *a:None,stop_process=cleanup)
            def method():
                nonlocal gate_calls
                gate_calls+=1
                if (scenario=='final-source-failure'and gate_calls==2)or(
                    scenario=='terminal-source-failure'and gate_calls==3):raise injected
                return dict(cloud_restore_authorized=True,native_execution_authorized=True,native_routing_authorized=True)
            def execute(sup,argv,label):
                calls.append(label)
                if (scenario in ('prepare-failure','body-and-cleanup-failure')and label=='prepare-fixed')or(
                    scenario=='route-failure'and label=='one-two-signal-routing-attempt'):raise injected
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
                    assert scenario!='success'
                    if scenario=='ownership-block':assert isinstance(exc,AssertionError)and 'forbids routing'in str(exc)
                    else:assert exc is injected,(scenario,exc)
                else:assert scenario=='success','Real outer failure fixture returned success'
            result=json.loads((out/'result.json').read_bytes())
            assert result['original_guard_failure_preserved']and not result['accepted']
            assert len(stopped)==1 and sup.STOP.is_set()
            assert sup.OUT is oldout and sup.TRACE is oldtrace
            checks=result['terminal_checks']
            assert [x['label']for x in checks]==['owned-process-cleanup','heartbeat-stop',
                'restore-signal-2','restore-signal-15','final-source-integrity']
            failed=[x for x in checks if x['status']=='FAIL']
            if scenario in ('ownership-block','prepare-failure','body-and-cleanup-failure'):
                assert 'one-two-signal-routing-attempt'not in calls and not result['native_routing_started']
            else:assert calls.count('one-two-signal-routing-attempt')==1
            assert 'work/ownership.json'in result['outputs']
            if scenario=='success':
                assert result['status']=='COMPLETE_CONDITIONAL_TWO_SIGNAL_ATTEMPT_NOT_RC_STA_OR_PHY_ACCEPTANCE'
                assert not failed and gate_calls==3 and len(calls)==13
                positive.append('actual_successful_outer_run_terminal_guards')
                continue
            assert result['status']=='FAIL_OR_BLOCKED_TWO_SIGNAL_ATTEMPT'
            if scenario in ('cleanup-failure','body-and-cleanup-failure'):
                assert len(failed)==1 and failed[0]['label']=='owned-process-cleanup'
                expected=cleanup_error if scenario=='body-and-cleanup-failure'else injected
                assert failed[0]['error']==repr(expected)and result['error']==repr(injected)
                assert gate_calls==(2 if scenario=='body-and-cleanup-failure'else 3)
            elif scenario=='terminal-source-failure':
                assert gate_calls==3 and len(failed)==1 and failed[0]['label']=='final-source-integrity'
                assert failed[0]['error']==repr(injected)and result['error']==repr(injected)
            else:assert not failed
            failures.append(dict(name=scenario,actual_calls=calls,result=result))
    positive.append('actual_outer_run_finally_and_exact_failure_records')
    assert len(positive)==2 and len(failures)==7
    return dict(positive=positive,rejected=failures,all_CAD_and_remote_IO_explicit_stubs=True)

def disconnected_pin_controls():
    """Actual collect() with a full synthetic census and unowned native API-shaped pins."""
    with patch.dict(sys.modules,{'odb':types.ModuleType('odb')}):
        import mainchip_two_signal_ownership_native as native
    class Layer:
        def getName(self):return 'Metal5'
        def getNumber(self):return 14
        def getRoutingLevel(self):return 5
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
            self.index=index;self.raw=[[96,73],[4,start],[5,3580080],[4,end]]
        def length(self):return len(self.raw)
        def getOpcode(self,i):return self.raw[i][0]
        def getData(self,i):return self.raw[i][1]
        def getCoord(self,i):return [self.raw[1 if i==2 else 3][1],3580080]
    wires={g.CLOCK:Wire(1,1887270,1901760),'net36993':Wire(2,1887270,1895040),
           'net459':Wire(3,1901660,1901860)}
    class Net:
        def __init__(self,index,name):self.index=index;self.name=name
        def getName(self):return self.name
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
        def getNet(self):return None
        def getGeometries(self):return [(layer,Box(marker_box))]
        def getInst(self):return instances[0]
        def getMTerm(self):return types.SimpleNamespace(getName=lambda:'A')
    class BTerm:
        def getName(self):return 'unowned_port'
        def getNet(self):return None
        def getBPins(self):return [types.SimpleNamespace(getBoxes=lambda:[Box(marker_box)])]
    class Block:
        iterms=[];bterms=[];fills=[];obstructions=[]
        def getChildren(self):return []
        def getFills(self):return self.fills
        def getDbUnitsPerMicron(self):return 2000
        def getNets(self):return nets
        def getITerms(self):return self.iterms
        def getBTerms(self):return self.bterms
        def getInsts(self):return instances
        def getObstructions(self):return self.obstructions
    block=Block();tech=types.SimpleNamespace(getDbUnitsPerMicron=lambda:2000,getLayers=lambda:[layer])
    db=types.SimpleNamespace(getTech=lambda:tech)
    def evidence():
        import hashlib
        stream=hashlib.sha256()
        for name,wire in sorted(wires.items()):
            raw=g.canonical([['net',name,'wire'],wire.raw]);stream.update(len(raw).to_bytes(8,'big'));stream.update(raw)
        return dict(complete_census_sha256={'ordinary-wire':stream.hexdigest()},complete_census_counts={'technology-layer':1,'ordinary-wire':3,
            'instance-terminal':len(block.iterms),'block-terminal':len(block.bterms)},
            complete_raw_opcode_data_pairs=12,
            disconnected_iterms=sum(t.getNet()is None for t in block.iterms),
            disconnected_bterms=sum(t.getNet()is None for t in block.bterms),
            raw_operand_native_lookups=dict(layers={'73':dict(name='Metal5',width=400,wrong_way_width=400,
                direction='HORIZONTAL',layer_number_observed_not_used_as_OID=14,
                routing_level_observed_not_used_as_OID=5)},rules={},vias={}))
    def lookup(scope,oid):
        assert scope is tech and oid==73
        return Layer()
    odb=types.SimpleNamespace(dbTechLayer=types.SimpleNamespace(getTechLayer=lookup))
    def collect(proof_override=None):
        source=evidence if proof_override is None else lambda:proof_override
        with patch.object(native,'api_evidence',source),patch.object(native,'odb',odb):
            return native.collect(db,block)
    pristine=collect()
    assert pristine['eligible_for_one_two_net_attempt']and pristine['native_geometry_census']['all-block-iterm']==0
    rejected=[]
    for name,key,value,message in [
        ('pair_count','complete_raw_opcode_data_pairs',11,'Raw opcode/data pair census changed'),
        ('full_raw_digest','complete_census_sha256',{'ordinary-wire':'0'*64},'Full raw wire stream differs')]:
        bad=evidence();bad[key]=value
        try:collect(bad)
        except AssertionError as exc:assert message in str(exc)
        else:raise AssertionError('Incomplete acquired raw stream admitted')
        rejected.append('actual_collect_'+name+'_refused')
    for kind,pins in [('iterm',[ITerm()]),('bterm',[BTerm()])]:
        block.iterms=pins if kind=='iterm'else[]
        block.bterms=pins if kind=='bterm'else[]
        result=collect()
        assert not result['eligible_for_one_two_net_attempt']
        found=[r for r in result['records']if r['owner']is None and r['kind']==kind+'-pin']
        assert len(found)==1 and found[0]['source_indices']==[]
        assert result['native_geometry_census']['disconnected-'+kind]==1
        rejected.append('actual_collect_unowned_overlapping_'+kind)
    block.iterms=[];block.bterms=[]
    block.fills=[object()]
    try:collect()
    except AssertionError as exc:assert 'Nonempty fill census'in str(exc)
    else:raise AssertionError('Unqualified native fill instance accepted')
    rejected.append('actual_collect_unobserved_fill_refused_before_getters');block.fills=[]
    block.obstructions=[object()]
    try:collect()
    except AssertionError as exc:assert 'Nonempty block-obstruction census'in str(exc)
    else:raise AssertionError('Unqualified native block-obstruction accepted')
    rejected.append('actual_collect_unobserved_block_obstruction_refused_before_getters');block.obstructions=[]
    for kind,pins,message in [('iterm',[ITerm(),ITerm()],'Duplicate block ITerm identity'),
                              ('bterm',[BTerm(),BTerm()],'Duplicate block BTerm identity')]:
        block.iterms=pins if kind=='iterm'else[];block.bterms=pins if kind=='bterm'else[]
        try:collect()
        except AssertionError as exc:assert message in str(exc)
        else:raise AssertionError('Duplicate named terminal admitted')
        rejected.append('actual_collect_duplicate_'+kind+'_identity_refused')
    block.iterms=[];block.bterms=[]
    # Connected block terminals omitted by a net enumeration cannot silently disappear.
    class MissingConnected(ITerm):
        def getNet(self):return nets[0]
    block.iterms=[MissingConnected()];block.bterms=[]
    try:collect()
    except AssertionError as exc:assert 'Connected ITerm census mismatch'in str(exc)
    else:raise AssertionError('Unreconciled native terminal accepted')
    rejected.append('actual_collect_connected_terminal_census_mismatch')
    assert len(rejected)==9
    return dict(positive=['actual_full_synthetic_collector_pristine'],rejected=rejected,
        native_execution=False,all_143820_nets_and_153130_instances_explicitly_synthetic=True)

def identity_contract_controls():
    """Actual acquired evidence, exact former failure and actual immutable-material gate."""
    import traceback
    with patch.dict(sys.modules,{'odb':types.ModuleType('odb')}):
        import mainchip_two_signal_ownership_native as native
    from mainchip_two_signal_api_probe_fixture import fixture
    positive=[];rejected=[]
    report=native.api_evidence()
    assert report['complete_raw_opcode_data_pairs']==13905578 and report['disconnected_iterms']==1000
    assert report['raw_operand_native_lookups']['layers']['15']['name']=='Metal5'
    assert report['raw_terminal_named_joins']==[]
    positive.append('actual_saved_native_census_exact_hash_and_observed_scope')
    original_path='docs/evidence/mainchip-two-signal-before-named-identity-20261027.py'
    raw=s.c.regular(s.ROOT/original_path).read_bytes()
    assert s.c.digest(raw)==s.methods()['protected'][original_path]
    old_tree=ast.parse(raw);assert sum(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='getId'for n in ast.walk(old_tree))==44
    f=fixture()
    with patch.object(f.block,'getFills',lambda:[]),patch.object(f.block,'getObstructions',lambda:[]):
        namespace={'__name__':'frozen_actual_getId_failure','__file__':str(s.ROOT/original_path)}
        with patch.dict(sys.modules,{'odb':f.odb}):
            exec(compile(raw,str(s.ROOT/original_path),'exec'),namespace)
        try:namespace['immutable_material'](f.db,f.block)
        except AttributeError as exc:
            assert exc.name=='getId'and exc.obj is f.lower
            frames=traceback.extract_tb(exc.__traceback__)
            assert any(x.name=='<lambda>'and x.filename==str(s.ROOT/original_path)for x in frames)
        else:raise AssertionError('Exact historical getId failure did not reproduce')
        rejected.append('exact_original_44_call_source_layer_getId_AttributeError')
        # The exact production structural gate, extracted without importing/running a CAD entry point.
        path=s.ROOT/'scripts/mainchip_two_signal_repair_native.py'
        text=s.c.regular(path).read_text();tree=ast.parse(text)
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='structural_equal']
        assert len(nodes)==1;ns={}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
        equal=ns['structural_equal']
        with patch.object(native,'odb',f.odb),patch.object(native,'api_evidence',lambda:dict(complete_census_counts={'technology-layer':3})):
            baseline=native.immutable_material(f.db,f.block)
            assert baseline['counts']=={'required-empty-native-material':1,'technology-layer':3,
                'master-obstruction':1,'special-wire':2}
            wrapped=lambda material:dict(identity={},geometry=material,via={})
            equal(wrapped(baseline),wrapped(native.immutable_material(f.db,f.block)))
            positive.append('actual_immutable_material_same_named_scope_and_order')
            via=f.odb.dbTechVia.getTechVia(f.tech,44)
            components=list(via.getBoxes())
            projected=native.via_record(via,native.named_layers(f.tech,dict(complete_census_counts={'technology-layer':3})))
            assert len(projected['components'])==4
            assert projected['components'][2]['box']==projected['components'][3]['box']
            assert [x['component_ordinal']for x in projected['components']]==[0,1,2,3]
            positive.append('actual_duplicate_via_material_retained_with_parent_scoped_ordinals')
            def reject_material(name):
                changed=native.immutable_material(f.db,f.block)
                try:equal(wrapped(baseline),wrapped(changed))
                except AssertionError as exc:assert str(exc)=='Native placement/pin/NDR/special geometry changed'
                else:raise AssertionError('Changed immutable material accepted: '+name)
                rejected.append(name)
            with patch.object(f.lower,'getWidth',lambda:402):reject_material('actual_layer_width_change_rejected')
            with patch.object(f.master,'getObstructions',lambda include:[]):reject_material('actual_master_obstruction_removed_rejected')
            with patch.object(via,'getBoxes',lambda:components[:-1]):reject_material('actual_duplicate_via_component_drop_rejected')
            sbox=f.nets[0].getSWires()[0].getWires()[1]
            with patch.object(type(sbox),'getViaXY',lambda self:[21,30]):reject_material('actual_special_via_origin_change_rejected')
            for method,message in (('getFills','Nonempty fill census'),('getObstructions','Nonempty block-obstruction census')):
                with patch.object(f.block,method,lambda:[object()]):
                    try:native.immutable_material(f.db,f.block)
                    except AssertionError as exc:assert message in str(exc)
                    else:raise AssertionError('Unqualified immutable material accepted')
                rejected.append('actual_immutable_'+method+'_unobserved_instance_refused')
    original=s.c.regular(s.ROOT/native.API_PATH).read_bytes()
    with tempfile.TemporaryDirectory(prefix='named-API-proof-')as temp:
        path=Path(temp)/'proof.json'
        for name,raw in [('truncated',original[:-1]),('different_layer_number',original.replace(b'"layer_number_observed_not_used_as_OID": 14',b'"layer_number_observed_not_used_as_OID": 15',1)),
                         ('extra_byte',original+b' ')]:
            assert raw!=original;path.write_bytes(raw)
            with patch.object(native.c,'regular',lambda unused:path):
                try:native.api_evidence()
                except AssertionError as exc:assert str(exc)=='Exact acquired API census differs'
                else:raise AssertionError('Changed API proof accepted')
            rejected.append('actual_api_file_'+name+'_rejected')
    assert len(positive)==3 and len(rejected)==10
    return dict(positive=positive,rejected=rejected,actual_original_failure_and_structural_gate=True,
        actual_CAD_executed=False,synthetic_material_collaborators=True)

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
        identity_contract=identity_contract_controls(),
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
