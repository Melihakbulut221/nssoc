#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Unexecuted source controls for the exact saved AVSS ledger; no native engine."""
import ast,copy,inspect,json,math
from decimal import Decimal
from collections import Counter
from pathlib import Path
import tx_phase_reset334_return_ledger as ledger

def refused(label,fn,rejected):
    try:fn()
    except (AssertionError,KeyError,ValueError,IndexError,ZeroDivisionError):rejected.append(label)
    else:raise AssertionError('Accepted ledger fault '+label)
def physical_route_seam(physical,terminals_by_sign):
    # Execute the actual inventory geometry statements, not a copied fixture implementation.
    original=inspect.getsource(ledger.inventory)
    def evaluate(text,sign):
        fn=ast.parse(text).body[0]
        loop=next(n for n in fn.body if isinstance(n,ast.For))
        starts=[i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign)
            and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='gen']
        assert len(starts)==1
        statements=loop.body[starts[0]:starts[0]+4]
        assert len(statements)==4 and isinstance(statements[-1],ast.Assert)
        names=[n.targets[0].id for n in statements[:3] if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)]
        assert names==['gen','route_inventory','geometry']
        env=dict(physical=physical,sign=sign,terminals=terminals_by_sign[sign],physical_routes=ledger.physical_routes)
        exec(compile(ast.fix_missing_locations(ast.Module(body=statements,type_ignores=[])),
            '<actual-inventory-geometry-seam>','exec'),env)
        geometry=env['geometry'];proof=env['route_inventory']
        assert geometry['routes']==proof['AVSS_routes'] and len(geometry['routes'])==85
        assert Counter(x['schema'] for x in geometry['routes'])==Counter(scalar=83,MIM=2)
        assert geometry['route_inventory']=={k:v for k,v in proof.items() if k!='AVSS_routes'}
        return dict(actual_inventory_statements=4,retained_scalar_AVSS=83,retained_MIM_AVSS=2)
    positives={};rejected=[]
    old="routes=route_inventory['AVSS_routes']"
    assert original.count(old)==1
    for sign in ('p','n'):
        positives[sign]=evaluate(original,sign)
        for name,new in [('old_uniform_net_filter',"routes=[x for x in gen['routes'] if x['net']=='AVSS']"),
                         ('silently_omit_MIM',"routes=[x for x in route_inventory['AVSS_routes'] if x['schema']=='scalar']")]:
            text=original.replace(old,new,1)
            refused(sign+':'+name,lambda text=text,sign=sign:evaluate(text,sign),rejected)
    assert len(rejected)==4
    return dict(positives=positives,rejected=rejected,actual_inventory_geometry_statements_executed=True,
        native_R_graph_or_waveform_executed=False)

def synthetic_controls():
    rejected=[]
    assert ledger.number('1.25k')==Decimal(1250)
    assert ledger.number('1e-3')==Decimal('.001')
    for value in ('nan','inf','1meg','1 ohm'):
        refused('native_number_'+value,lambda value=value:ledger.number(value),rejected)
    edges=[dict(a='a',b='b',ohm_token='2'),dict(a='a',b='b',ohm_token='3'),
           dict(a='b',b='c',ohm_token='4'),dict(a='bulk',b='sub',ohm_token='5')]
    assert sorted(sorted(c) for c in ledger.graph_components(edges))==[['a','b','c'],['bulk','sub']]
    assert len(edges)==4 # Parallel edges were not simplified into one resistor.
    for label,e in [('self',dict(a='a',b='a',ohm_token='1')),('zero',dict(a='a',b='b',ohm_token='0')),
                    ('negative',dict(a='a',b='b',ohm_token='-1'))]:
        refused(label,lambda e=e:ledger.graph_components([e]),rejected)
    edge=dict(id='R1',ohm_token='10')
    a=ledger.edge_state(edge,.25,.05);b=ledger.edge_state(edge,.05,.25)
    assert math.isclose(a['drop_a_minus_b_V'],.2) and math.isclose(a['linear_wire_resistor_current_a_to_b_A'],.02)
    assert math.isclose(a['linear_wire_power_W'],.004) and math.isclose(b['linear_wire_power_W'],.004)
    assert math.isclose(b['linear_wire_resistor_current_a_to_b_A'],-.02)
    for label,e,x,y in [('voltage_nan',edge,float('nan'),0),('voltage_inf',edge,0,float('inf')),
                        ('resistance_zero',dict(id='R1',ohm_token='0'),1,0),
                        ('resistance_overflow',dict(id='R1',ohm_token='1e400'),1,0),
                        ('current_overflow',dict(id='R1',ohm_token='1e-300'),1e300,0)]:
        refused(label,lambda e=e,x=x,y=y:ledger.edge_state(e,x,y),rejected)
    inst=dict(instance='xdut',actual_ports=['clkp','clkn','mp','mn','qp','qn','armp','armn','avdd','0','0','0'])
    assert ledger.model_node(inst,'AVSS')=='0'
    assert ledger.model_node(inst,'SUB')=='0'
    assert ledger.model_node(inst,'BULK')=='xdut.bulk'
    assert ledger.model_node(inst,'w00329')=='xdut.w00329'
    assert len(rejected)==12
    physical,mim=ledger.coordinates.provenance()
    coordinate_controls=ledger.coordinates.controls(physical,mim)
    text=(Path(__file__).resolve().parents[1]/'hw/soc/analog/pcie/clock_div2_assert_offset_v4.spice').read_text()
    source_terminals={}
    for sign in ('p','n'):
        canonical=ledger.bench.binding.source_rows(text,sign)
        source_terminals[sign]=[dict(source_instance=row['name'],model=row['model'],terminal=term,source_net=net)
            for row in canonical for term,net in zip(ledger.bench.binding.ORDER[row['model']],row['nets'],strict=True)
            if net=='AVSS']
    route_controls=ledger.physical_routes.controls(physical,source_terminals)
    route_controls['integration']=physical_route_seam(physical,source_terminals)
    return dict(status='PASS_SYNTHETIC_LEDGER_MATH_ONLY',rejected=rejected,
        actual_native_R_inventory_executed=False,actual_waveform_rows_executed=False,
        qualified_coordinate_controls=coordinate_controls,physical_route_controls=route_controls)
def actual_controls(inputs,contract_raw,time,values,rows):
    """Run only on restored authenticated inputs, before one frozen waveform review.

    These inexpensive mutations never repeat the full original waveform review.
    """
    catalog=ledger.inventory(**inputs);rejected=[];positives={}
    physical,mim=ledger.coordinates.provenance()
    actual_points={sign:json.loads(inputs['raw_inputs'][sign]['anchors']) for sign in ('p','n')}
    coordinate_controls=ledger.coordinates.controls(physical,mim,actual_points)
    route_controls=ledger.physical_routes.controls(physical,
        {sign:catalog['polarities'][sign]['terminals'] for sign in ('p','n')},restored_terminal_owners=True)
    rc=json.loads(inputs['rc_raw'])
    for sign in ('p','n'):
        comp=rc['polarities'][sign]['composition'];audit=rc['polarities'][sign]['orders']['precise']['audit']
        _,_,wire=ledger.bench.model_records(inputs['models'][sign],sign)
        raw=inputs['raw_inputs'][sign]['res_ext']
        raw=raw.decode() if isinstance(raw,bytes) else raw
        fixture=dict(raw_text=raw,model_records=wire,mapping=comp['wire_node_map'],
            planes=json.loads(inputs['raw_inputs'][sign]['anchors']),audit=audit)
        positive=ledger.raw_graph(**fixture)
        positives[sign]=dict(nodes=len(positive['AVSS_nodes']),edges=len(positive['AVSS_edges']),
            terminals=len(catalog['polarities'][sign]['terminals']))
        ri=next(i for i,r in enumerate(wire) if r[0].startswith('R'))
        line=next(raw_line for _,raw_line,r in ledger.records(raw) if r[0]=='resist')
        tokens=next(r for _,_,r in ledger.records(raw) if r[0]=='resist')
        scale_line=next(raw_line for _,raw_line,r in ledger.records(raw) if r[0]=='scale')
        firstnode=next(raw_line for _,raw_line,r in ledger.records(raw) if r[0]=='rnode')
        def change_model_value(q):
            q['model_records'][ri][3]=str(ledger.number(q['model_records'][ri][3])+Decimal('.125'))
        def cross_model(q):
            q['model_records'][ri][1]='BULK'
        def bad_owner(q):
            a=next(a for a in q['planes']['anchors'] if a['label']=='P_AVSS')
            a['wire_component']=1
        def bad_count(q):
            next(a for a in q['audit']['components'] if a['component']==13)['nodes']+=1
        def bad_coordinate(q):
            r=ledger.records(firstnode)[0][2];r[4]='nan'
            q['raw_text']=q['raw_text'].replace(firstnode,' '.join(r),1)
        trials=[
            ('missing_model_R',lambda q:q['model_records'].pop(ri)),
            ('duplicate_model_R',lambda q:q['model_records'].append(copy.deepcopy(q['model_records'][ri]))),
            ('changed_model_R_value',change_model_value),
            ('body_as_metal_endpoint',cross_model),
            ('missing_raw_R',lambda q:q.update(raw_text=q['raw_text'].replace(line+'\n','',1))),
            ('duplicate_raw_R',lambda q:q.update(raw_text=q['raw_text']+'\n'+line+'\n')),
            ('zero_raw_R',lambda q:q.update(raw_text=q['raw_text'].replace(line,'resist "'+tokens[1]+'" "'+tokens[2]+'" 0',1))),
            ('collapsed_AVSS_SUB',lambda q:q['mapping'].update(P_AVSS='SUB')),
            ('cross_geometry_owner',bad_owner),('wrong_component_census',bad_count),
            ('wrong_scale',lambda q:q.update(raw_text=q['raw_text'].replace(scale_line,'scale 999 1 0.5',1))),
            ('nonfinite_native_coordinate',bad_coordinate)]
        for label,mutate in trials:
            q=copy.deepcopy(fixture);mutate(q);assert q!=fixture
            refused(sign+':'+label,lambda q=q:ledger.raw_graph(**q),rejected)
    for label,field,sign in [('binding_summary','binding_summary_raw',None),('RC_summary','rc_raw',None),
        ('physical_summary','physical_raw',None),('P_model','models','p'),('N_model','models','n'),
        ('P_roles','payload_raw','p'),('N_roles','payload_raw','n')]:
        q=dict(inputs)
        if sign:
            q[field]=dict(inputs[field]);old=q[field][sign];q[field][sign]=old+('\n' if isinstance(old,str) else b'\n')
        else:
            old=q[field];q[field]=old+('\n' if isinstance(old,str) else b'\n')
        refused(label,lambda q=q:ledger.inventory(**q),rejected)
    _,probes=ledger.probe_inventory(catalog,contract_raw,values)
    assert rows and len(probes['vectors'])>0
    key=probes['vectors'][0]
    q=dict(values);q.pop(key)
    refused('missing_endpoint_voltage',lambda:ledger.probe_inventory(catalog,contract_raw,q),rejected)
    refused('duplicate_native_row',lambda:ledger.row_ledger(catalog,contract_raw,time,values,[rows[0],rows[0]]),rejected)
    refused('out_of_capture_row',lambda:ledger.row_ledger(catalog,contract_raw,time,values,[len(time)]),rejected)
    q=dict(values);q[key]=values[key][:-1]
    refused('wrong_vector_extent',lambda:ledger.row_ledger(catalog,contract_raw,time,q,[rows[0]]),rejected)
    q=dict(values);q[key]=list(values[key]);q[key][rows[0]]=float('nan')
    refused('nonfinite_same_row_voltage',lambda:ledger.row_ledger(catalog,contract_raw,time,q,[rows[0]]),rejected)
    assert len(rejected)==36
    return catalog,dict(status='PASS_ACTUAL_GRAPH_AND_ROW_INPUT_REFUSALS_ONLY',
        positive_graphs=positives,rejected=rejected,qualified_coordinate_controls=coordinate_controls,
        physical_route_controls=route_controls,
        original_electrical_review_repeated=False,
        geometry_or_circuit_acceptance=False)
