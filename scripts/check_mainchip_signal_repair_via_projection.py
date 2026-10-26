#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted actual snapshot/qualified via-helper fixtures; synthetic API objects, no CAD."""
import ast,copy,inspect,json,tempfile,types
from pathlib import Path
from unittest.mock import patch

def fixture():
    class Layer:
        def __init__(self,name):self.name=name
        def getName(self):return self.name
    class Box:
        def __init__(self,row):self.row=row
        def getTechLayer(self):return Layer(self.row[0])
        def xMin(self):return self.row[1]
        def yMin(self):return self.row[2]
        def xMax(self):return self.row[3]
        def yMax(self):return self.row[4]
    class Via:
        def __init__(self,name,rows):self.name,self.rows=name,rows
        def getName(self):return self.name
        def getBoxes(self):return [Box(row)for row in self.rows]
    block_via=Via('VB',[['Metal2',0,0,10,20],['Via2',2,2,8,18],['Metal3',0,0,10,20]])
    tech_via=Via('VT',[['Metal3',30,40,50,60],['Via3',32,42,48,58],['Metal4',30,40,50,60]])
    block_defs={'VB':block_via};tech_defs={'VT':tech_via}
    class Net:
        def __init__(self,name):self.name=name
        def getName(self):return self.name
        def getWire(self):return 'synthetic-used-vias'if self.name=='net_000000'else None
    # Exercise the real snapshot census and serialization boundary, not a copied snapshot function.
    nets={('net_%06d'%i):Net('net_%06d'%i)for i in range(143820)}
    block=types.SimpleNamespace(getNets=lambda:list(nets.values()),findNet=nets.__getitem__,
        findVia=block_defs.get)
    tech=types.SimpleNamespace(findVia=tech_defs.get)
    db=types.SimpleNamespace(getTech=lambda:tech)
    class Decoder:
        VIA=1;TECH_VIA=2;END_DECODE=3
        def begin(self,wire):assert wire=='synthetic-used-vias';self.index=0
        def next(self):
            answer=[self.VIA,self.TECH_VIA,self.END_DECODE][self.index];self.index+=1;return answer
        def getVia(self):return block_via
        def getTechVia(self):return tech_via
    return types.SimpleNamespace(db=db,block=block,decoder=Decoder,block_defs=block_defs,tech_defs=tech_defs)

def controls(native):
    positives=[];refusals=[]
    def reject(label,fn,expected):
        try:fn()
        except AssertionError as error:
            assert expected in str(error),(label,'wrong refusal',str(error))
            refusals.append(label)
        else:raise AssertionError('Accepted '+label)
    f=fixture()
    with patch.object(native.n.odb,'dbWireDecoder',f.decoder,create=True):
        raw=native.n.vias(f.db,f.block,['net_000000'])
        assert raw and all(type(box)is tuple for boxes in raw.values()for box in boxes)
        assert raw!=json.loads(json.dumps(raw))
        projected=native.via_projection(raw)
        assert projected==json.loads(json.dumps(raw))==native.via_projection(projected)
        assert all(type(box)is list for boxes in projected.values()for box in boxes)
        positives.append('actual_qualified_tuple_boxes_exact_JSON_projection')
        # Only unrelated geometry/identity/DEF collaborators are synthetic here.
        def write_def(block,path):
            assert block is f.block;Path(path).write_bytes(b'synthetic unchanged DEF\n')
        with tempfile.TemporaryDirectory()as tmp,patch.object(native.n,'load',return_value=(f.db,f.block)),\
             patch.object(native.odb,'write_def',side_effect=write_def,create=True),\
             patch.object(native.n,'identity',side_effect=lambda db,net:dict(name=net.getName(),sigtype='SIGNAL')),\
             patch.object(native.n,'encoded',return_value=dict(wire_present=True,metadata='ROUTED',paths=['ROUTED'])),\
             patch.object(native.d,'geometry_projection',return_value=dict(sha256='synthetic-non-via-geometry',counts={'net':143820})):
            snap=native.snapshot(Path('/synthetic/source.odb'),Path(tmp),'roundtrip')
            loaded=json.loads(json.dumps(snap))
            assert snap==loaded and snap['via']==projected
            assert len(snap['identity'])==len(snap['encoded'])==143820
            positives.append('actual_full_snapshot_save_reload_equality')
            def old_snapshot_boundary():
                with patch.object(native,'via_projection',side_effect=lambda value:value):
                    old=native.snapshot(Path('/synthetic/source.odb'),Path(tmp),'old-boundary')
                assert old==json.loads(json.dumps(old)),'Actual snapshot does not survive exact JSON roundtrip'
            reject('actual_old_snapshot_tuple_boundary',old_snapshot_boundary,'Actual snapshot does not survive exact JSON roundtrip')
        paths=[Path('/synthetic/before.odb'),Path('/synthetic/after.odb')]
        calls=[]
        def load(path):
            calls.append(path);assert path in paths
            return f.db,f.block
        before={'via':json.loads(json.dumps(projected))};after={'via':copy.deepcopy(projected)}
        with patch.object(native.n,'load',side_effect=load):
            proof=native.compare_vias(before,after,*paths)
        assert calls==paths and proof['union_count']==2
        assert proof['definitions_present_and_identical_in_both_databases']is True
        positives.append('actual_qualified_required_vias_both_database_roundtrip')
        bad=copy.deepcopy(after);bad['via']['block:VB'][0][1]+=1
        reject('common_used_definition_changed',lambda:native.compare_vias(before,bad,*paths),'Common used via definition changed')
        # Execute the actual compare function with only its tuple adaptation removed.
        tree=ast.parse(inspect.getsource(native.compare_vias))
        targets=[n for n in ast.walk(tree)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='tuple']
        assert len(targets)==1 and len(targets[0].args)==1 and isinstance(targets[0].args[0],ast.Name)and targets[0].args[0].id=='box'
        target=targets[0]
        class RemoveTuple(ast.NodeTransformer):
            def visit_Call(self,node):
                if node is target:return copy.deepcopy(node.args[0])
                return self.generic_visit(node)
        mutant=RemoveTuple().visit(tree);ast.fix_missing_locations(mutant)
        namespace=dict(native.__dict__)
        exec(compile(mutant,'actual-compare-vias-without-tuple-adaptation','exec'),namespace)
        with patch.object(native.n,'load',side_effect=load):
            reject('required_tuple_adaptation_removed',lambda:namespace['compare_vias'](before,after,*paths),'donor/recipient via definition mismatch')
        for label,which,mutate,expected in [
            ('input_required_definition_missing',0,lambda g:g.block_defs.pop('VB'),'missing imported via'),
            ('output_required_definition_missing',1,lambda g:g.block_defs.pop('VB'),'missing imported via'),
            ('input_required_coordinate_changed',0,lambda g:g.block_defs['VB'].rows[0].__setitem__(1,1),'donor/recipient via definition mismatch'),
            ('output_required_coordinate_changed',1,lambda g:g.block_defs['VB'].rows[0].__setitem__(1,1),'donor/recipient via definition mismatch'),
            ('output_required_layer_changed',1,lambda g:g.block_defs['VB'].rows[0].__setitem__(0,'OtherMetal'),'donor/recipient via definition mismatch'),
            ('output_required_box_missing',1,lambda g:g.block_defs['VB'].rows.pop(),'donor/recipient via definition mismatch'),
            ('output_required_extra_box',1,lambda g:g.block_defs['VB'].rows.append(['Metal2',70,80,90,100]),'donor/recipient via definition mismatch')]:
            other=fixture();mutate(other);seen=[]
            def bad_load(path):
                seen.append(path);g=other if path==paths[which]else f
                return g.db,g.block
            with patch.object(native.n,'load',side_effect=bad_load):
                reject(label,lambda:native.compare_vias(before,after,*paths),expected)
            assert seen==paths[:which+1]
        schema_faults=[
            ('via_kind',lambda v:{'unknown:VB':v['block:VB']},'Unknown or empty via name'),
            ('via_empty_name',lambda v:{'block:':v['block:VB']},'Unknown or empty via name'),
            ('via_non_string_name',lambda v:{1:v['block:VB']},'Via key must be a typed name'),
            ('via_non_string_layer',lambda v:v['block:VB'][0].__setitem__(0,1),'Via layer must be a nonempty string'),
            ('via_empty_layer',lambda v:v['block:VB'][0].__setitem__(0,''),'Via layer must be a nonempty string'),
            ('via_short_box',lambda v:v['block:VB'][0].pop(),'Via box must have five fields'),
            ('via_extra_coordinate',lambda v:v['block:VB'][0].append(1),'Via box must have five fields'),
            ('via_bool_coordinate',lambda v:v['block:VB'][0].__setitem__(1,True),'Via coordinates must be exact integers'),
            ('via_float_coordinate',lambda v:v['block:VB'][0].__setitem__(1,0.0),'Via coordinates must be exact integers'),
            ('via_string_coordinate',lambda v:v['block:VB'][0].__setitem__(1,'0'),'Via coordinates must be exact integers'),
            ('via_wrong_boxes_container',lambda v:v.__setitem__('block:VB',tuple(v['block:VB'])),'Via boxes must be a list'),
            ('via_non_mapping',lambda v:[v],'Via projection must be a dictionary'),
            ('via_unsorted_boxes',lambda v:v['block:VB'].reverse(),'Via box order must match'),
        ]
        for label,mutate,expected in schema_faults:
            bad=copy.deepcopy(projected);replacement=mutate(bad)
            if label in ('via_kind','via_empty_name','via_non_string_name','via_non_mapping'):bad=replacement
            reject(label,lambda bad=bad:native.via_projection(bad),expected)
        bad=copy.deepcopy(after);bad['via']['block:VB'].insert(0,copy.deepcopy(bad['via']['block:VB'][0]))
        reject('duplicate_box_multiplicity_changed',lambda:native.compare_vias(before,bad,*paths),'Common used via definition changed')
    assert len(positives)==3 and len(refusals)==24,(len(positives),len(refusals))
    return dict(status='PASS_EXACT_VIA_JSON_BOUNDARIES_SOURCE_FIXTURES',positives=positives,refusals=refusals,
        actual_snapshot_net_census=143820,qualified_boxes_vias_executed_against_synthetic_API=True,
        native_CAD_executed=False,actual_archive_accessed=False,geometry_waiver=False)
