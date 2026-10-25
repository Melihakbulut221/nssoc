#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only ledger of exact native AVSS R edges and unaltered saved rows.

No extraction, simulator, circuit modification, interpolation, or acceptance.
The caller must authenticate complete archives and replay the frozen review.
"""
import hashlib,json,math,re,shlex
from collections import Counter,defaultdict,deque
from decimal import Decimal
import tx_phase_reset334_loaded_contract as bench
import tx_phase_reset334_qualified_anchor_points as coordinates

RC_SHA='a11da5bb7ee22134f9373d43a1fffda9d1f6538877b440031ffd910adec56bcf'
PHYSICAL_SHA='5591fe784df1cc1294302ac38a13a8db4b6285f37335fa7c2fbe2d477c7fa913'
NATIVE_CONTRACT_SHA='ac96181ace2135093d941a7c7f4c137de0acd7176ae5d7b49d55947eb61ed8ce'
RC_PREFIX='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-phase-reset334-mim-precision/'
FLAGS=dict(electrical_accepted=False,causal_conclusion=False,geometry_edit_justified=False,
    native_simulation=False,native_extraction=False,all31_clock_tree_accepted=False,
    PLL_connected=False,full_PHY_accepted=False)
def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()
def number(text):
    # Same Decimal grammar as frozen raw parser f8132c84; no binary rounding in edge equality.
    m=re.fullmatch(r'([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)([numkpf]?)',text.lower())
    assert m is not None,'Unsupported native numeric token'
    value=Decimal(m[1])*{'n':Decimal('1e-9'),'u':Decimal('1e-6'),'m':Decimal('1e-3'),
        'k':Decimal('1e3'),'p':Decimal('1e-12'),'f':Decimal('1e-15'),'':Decimal(1)}[m[2]]
    assert value.is_finite()
    return value
def records(text):
    return [(i,line,shlex.split(line)) for i,line in enumerate(text.splitlines(),1)
            if line.strip() and not line.lstrip().startswith('#')]
def graph_components(edges):
    adj=defaultdict(list)
    for e in edges:
        assert e['a']!=e['b'] and number(e['ohm_token'])>0
        adj[e['a']].append(e['b']);adj[e['b']].append(e['a'])
    result=[];seen=set()
    for start in sorted(adj):
        if start in seen:continue
        found={start};queue=deque([start]);seen.add(start)
        while queue:
            for n in adj[queue.popleft()]:
                if n not in seen:seen.add(n);found.add(n);queue.append(n)
        result.append(found)
    return result
def raw_graph(raw_text,model_records,mapping,planes,audit):
    """All R edges retain multiplicity; equiv/C/body records never become R edges."""
    rr=records(raw_text)
    assert [r for _,_,r in rr if r[0]=='scale']==[['scale','1000','1','0.5']]
    anchors={a['label']:a for a in planes['anchors']}
    assert len(anchors)==len(planes['anchors'])==695
    inv={v:k for k,v in mapping.items()};assert len(inv)==len(mapping)
    actual=[r for r in model_records if r[0].startswith('R')]
    assert len(actual)==len({r[0].lower() for r in actual})==1347
    raw_edges=[]
    for line,raw,r in rr:
        if r[0]!='resist':continue
        assert len(r)==4 and r[1]!=r[2] and number(r[3])>0
        raw_edges.append(dict(native_line=line,native_raw=raw,native_tokens=r,a=r[1],b=r[2],ohm_token=r[3]))
    key=lambda a,b,value:(tuple(sorted((a,b))),number(value))
    expected=Counter(key(e['a'],e['b'],e['ohm_token']) for e in raw_edges)
    actual_counter=Counter(key(inv[r[1]],inv[r[2]],r[3]) for r in actual)
    assert expected==actual_counter and len(raw_edges)==1347,'Raw/model edge multiset changed'
    # Equal parallel edges may have indistinguishable identities; preserve every occurrence.
    slots=defaultdict(deque)
    for e in raw_edges:slots[key(e['a'],e['b'],e['ohm_token'])].append(e)
    edges=[]
    for r in actual:
        raw=slots[key(inv[r[1]],inv[r[2]],r[3])].popleft()
        edges.append(dict(id=r[0],a=inv[r[1]],b=inv[r[2]],model_a=r[1],model_b=r[2],
            ohm_token=r[3],ohm=float(number(r[3])),model_tokens=r,raw=raw))
    assert not any(slots.values())
    components=graph_components(edges)
    assert len(components)==119
    by_audit={c['component']:c for c in audit['components']}
    assert len(by_audit)==len(audit['components'])==119
    owners={};groups={}
    for ns in components:
        aa=ns & anchors.keys();assert aa,'Unanchored R component'
        own={anchors[n]['wire_component'] for n in aa};assert len(own)==1,'Cross-owner R edge'
        cid=next(iter(own));want=by_audit[cid]
        assert cid not in groups and len(ns)==want['nodes'] and sorted(aa)==sorted(want['probes'])
        groups[cid]=ns
        for n in ns:owners[n]=cid
    assert set(groups)==set(by_audit)
    node_rows={}
    for line,raw,r in rr:
        if r[0]!='rnode':continue
        assert len(r)==7 and r[1] not in node_rows and number(r[2])==0 and number(r[3])>=0
        int(r[6])  # Preserve this raw token; no layer interpretation is authorized.
        x,y=int(r[4]),int(r[5])
        node_rows[r[1]]=dict(native_line=line,native_raw=raw,native_tokens=r,
            point_dbu=[5*x,5*y],native_type_token=r[6],native_layer=None,
            coordinate_basis='actual rnode x/y; pinned scale0.5 centimicron=5nm')
    avss=next(a for a in planes['public'] if a['name']=='AVSS')
    sub=next(a for a in planes['public'] if a['name']=='SUB')
    assert avss['reference_label']=='P_AVSS' and sub['reference_label']=='P_SUB'
    assert owners['P_AVSS']==13 and owners['P_SUB']==1 and groups[13].isdisjoint(groups[1])
    assert len(groups[13])==256 and len(groups[13]&anchors.keys())==86
    geometry={}
    for n in sorted(groups[13]):
        if n in node_rows:
            geometry[n]=node_rows[n]
        else:
            # No guessed nearest point: only the exact qualified terminal/public anchor.
            assert n in anchors,'Native R endpoint has no actual geometry witness'
            geometry[n]=dict(point_dbu=anchors[n]['point_dbu'],
                coordinate_basis='exact qualified anchor; no rnode coordinate supplied',
                native_layer=None,native_type_token=None)
        geometry[n]['wire_component']=13
        geometry[n]['model_node']=mapping[n]
        geometry[n]['anchor']=anchors.get(n)
    selected=[e for e in edges if owners[e['a']]==13]
    assert all(owners[e['b']]==13 for e in selected)
    adjacency=defaultdict(list)
    for e in selected:
        adjacency[e['a']].append((e['id'],e['b']))
        adjacency[e['b']].append((e['id'],e['a']))
    parents={'P_AVSS':None};queue=deque(['P_AVSS'])
    while queue:
        n=queue.popleft()
        for eid,other in sorted(adjacency[n]):
            if other not in parents:parents[other]=(n,eid);queue.append(other)
    assert set(parents)==groups[13]
    paths={}
    for terminal in sorted(groups[13]&anchors.keys()):
        n=terminal;steps=[]
        while parents[n] is not None:
            parent,eid=parents[n];steps.append(dict(edge=eid,from_node=n,to_node=parent));n=parent
        assert n=='P_AVSS'
        paths[terminal]=steps
    return dict(all_R_edges=len(edges),all_R_components=len(groups),AVSS_nodes=sorted(groups[13]),
        AVSS_edges=selected,AVSS_node_geometry=geometry,AVSS_component=13,SUB_component=1,
        terminal_return_paths=paths,return_path_basis='deterministic actual R graph path; not an equivalent resistance or unique physical current path',
        native_layer_of_R_edge_known=False,edge_segment_or_via_assignment_inferred=False,
        capacitor_or_intrinsic_alias_used_as_R_edge=False)
def inventory(binding_summary_raw,payload_raw,models,rc_raw,physical_raw,raw_inputs):
    assert digest(rc_raw)==RC_SHA and digest(physical_raw)==PHYSICAL_SHA
    rc=json.loads(rc_raw);physical=json.loads(physical_raw)
    assert rc['source_head']=='3cb1350dcbda569ac0073b0211cdaa2a47dc70ed'
    assert rc['both_polarities_and_orders_verified'] and rc['native_RC_and_device_records_equal_in_both_orders']
    assert physical['source_head']=='2e1f26e9c4fdf37d63433a0c859c2d305db3486b'
    _,proofs=bench.qualified_inputs(binding_summary_raw,payload_raw,models)
    physical_proof,mim_proof=coordinates.provenance()
    assert physical_proof==physical
    output={}
    for sign in ('p','n'):
        _,_,wire=bench.model_records(models[sign],sign)
        comp=rc['polarities'][sign]['composition'];audit=rc['polarities'][sign]['orders']['precise']['audit']
        selected=raw_inputs[sign];assert set(selected)=={'res_ext','anchors'}
        path=sign+'/precise/rc01/phase_reset334_wires.res.ext'
        assert digest(selected['res_ext'])==rc['outputs'][path]
        ap=RC_PREFIX+sign+'/precise/anchors03.json'
        assert digest(selected['anchors'])==audit['inputs'][ap]['sha256']
        assert mim_proof['outputs'][sign+'/mim/anchors.json']==rc['outputs'][sign+'/source/mim/anchors.json']
        planes=json.loads(selected['anchors'])
        point_map,point_proof=coordinates.validate(physical_proof,mim_proof,sign,planes,proofs[sign]['compact_roles'])
        text=selected['res_ext'].decode() if isinstance(selected['res_ext'],bytes) else selected['res_ext']
        graph=raw_graph(text,wire,comp['wire_node_map'],planes,audit)
        roles=proofs[sign]['compact_roles'];terminals=[]
        native_cluster=proofs[sign]['public_native_net_map']['AVSS']
        assert native_cluster==proofs[sign]['source_native_net_map']['AVSS']=='17'
        assert proofs[sign]['source_native_net_map']['SUB']!=proofs[sign]['public_native_net_map']['SUB']
        planes_by_ref={r['reference_label']:r for r in planes['rows'] if 'reference_label' in r}
        for name,role in roles.items():
            for terminal,t in role['terminals'].items():
                if t['source_net']!='AVSS':continue
                assert str(t['native_cluster'])==native_cluster and t['model_node']!='BULK'
                ref=t['reference_label'];assert ref in graph['AVSS_node_geometry']
                p=planes_by_ref[ref]
                point=point_map[ref]
                coordinates.terminal_point(sign,name,role,terminal,t,p,point)
                assert comp['wire_node_map'][ref]==t['model_node']
                terminals.append(dict(source_instance=name,native_id=role['native_id'],model=role['model'],
                    terminal=terminal,source_net='AVSS',RC_point_dbu=p['point_dbu'],
                    coordinate_binding=point,**{k:v for k,v in t.items() if k!='source_net'}))
        assert len(terminals)==85
        assert Counter(t['model'] for t in terminals)==Counter(npn13G2=28,rppd=55,cap_cmim=2)
        assert {t['reference_label'] for t in terminals}|{'P_AVSS'}==(set(graph['AVSS_nodes']) & set(planes_by_ref))|{'P_AVSS'}
        gen=physical['variants'][sign]['generation']
        geometry=dict(origin_translation_um=gen['origin_translation_um'],public_port=gen['ports']['AVSS'],
            local_buses=[x for x in gen['local_buses'] if x['net']=='AVSS'],
            straps=[x for x in gen['additive_power_straps'] if x['net']=='AVSS'],
            vias=[x for x in gen['additive_power_vias'] if x['net']=='AVSS'],
            routes=[x for x in gen['routes'] if x['net']=='AVSS'],
            component_signature=physical['variants'][sign]['wires']['graph'])
        assert len(geometry['local_buses'])==15 and len(geometry['straps'])==16 and len(geometry['vias'])==101
        output[sign]=dict(model_sha256=digest(models[sign]),raw_res_sha256=digest(selected['res_ext']),
            anchors_sha256=digest(selected['anchors']),terminals=terminals,graph=graph,
            actual_geometry=geometry,qualified_point_transition=point_proof,
            geometry_coordinates_are_not_all_in_same_origin=True)
    return dict(status='NATIVE_AVSS_R_GRAPH_INVENTORY_ONLY',polarities=output,**FLAGS)
def model_node(instance,node):
    ports=dict(zip(bench.binding.PORTS,instance['actual_ports'],strict=True))
    return ports[node] if node in ports else instance['instance']+'.'+node.lower()
def probe_inventory(catalog,contract_raw,values):
    assert digest(contract_raw)==NATIVE_CONTRACT_SHA
    c=json.loads(contract_raw);assert len(c['instances'])==3 and len(c['hbt'])==318 and len(c['vectors'])==4726
    required=set()
    for inst in c['instances']:
        pol=inst['variant'];graph=catalog['polarities'][pol]['graph']
        assert model_node(inst,'AVSS')=='0' and model_node(inst,'SUB')=='0'
        for n in graph['AVSS_nodes']:
            actual=model_node(inst,graph['AVSS_node_geometry'][n]['model_node'])
            if actual!='0':required.add('v('+actual+')')
    assert required<=set(c['vectors']) and required<=set(values),'Missing actual AVSS endpoint probe'
    return c,dict(count=len(required),vectors=sorted(required),no_aliases_injected=True)
def edge_state(edge,va,vb):
    assert math.isfinite(va) and math.isfinite(vb)
    resistance=float(number(edge['ohm_token']));assert resistance>0 and math.isfinite(resistance)
    drop=va-vb;current=drop/resistance
    assert all(math.isfinite(x) for x in (drop,current,drop*current))
    return dict(edge=edge['id'],a_voltage_V=va,b_voltage_V=vb,drop_a_minus_b_V=drop,
        linear_wire_resistor_current_a_to_b_A=current,linear_wire_power_W=drop*current)
def row_ledger(catalog,contract_raw,time,values,rows):
    """Every reported voltage/current uses one admitted native row; no interpolation."""
    c,probes=probe_inventory(catalog,contract_raw,values)
    assert len(rows)==len(set(rows)) and rows
    assert all(len(values[k])==len(time) for k in probes['vectors'])
    frames=[]
    for row in sorted(rows):
        assert isinstance(row,int) and 0<=row<len(time) and math.isfinite(float(time[row]))
        instances={}
        for inst in c['instances']:
            graph=catalog['polarities'][inst['variant']]['graph']
            states={}
            for n in graph['AVSS_nodes']:
                actual=model_node(inst,graph['AVSS_node_geometry'][n]['model_node'])
                states[n]=0.0 if actual=='0' else float(values['v('+actual+')'][row])
                assert math.isfinite(states[n])
            edges=[edge_state(e,states[e['a']],states[e['b']]) for e in graph['AVSS_edges']]
            terms=[];edge_by_id={e['id']:e for e in graph['AVSS_edges']};state_by_id={s['edge']:s for s in edges}
            for t in catalog['polarities'][inst['variant']]['terminals']:
                ref=t['reference_label'];path=graph['terminal_return_paths'][ref];drops=[]
                for step in path:
                    edge=edge_by_id[step['edge']]
                    assert {step['from_node'],step['to_node']}=={edge['a'],edge['b']}
                    sign=1 if edge['a']==step['from_node'] else -1
                    drops.append(sign*state_by_id[edge['id']]['drop_a_minus_b_V'])
                total=sum(drops);difference=states[ref]-states['P_AVSS']
                assert math.isclose(total,difference,rel_tol=0,abs_tol=1e-12),'Native same-row path does not telescope'
                terms.append(dict(reference=ref,voltage_V=states[ref],
                    voltage_minus_public_AVSS_V=difference,actual_path_signed_edge_drop_V=drops,
                    path_drop_sum_V=total))
            instances[inst['instance']]=dict(preset=inst['variant'],node_voltages_V=states,
                every_AVSS_edge=edges,every_compact_AVSS_terminal=terms)
        frames.append(dict(row=row,time_s=float(time[row]),instances=instances))
    return dict(status='EXACT_NATIVE_ROW_AVSS_WIRE_LEDGER_ONLY',probe_inventory=probes,frames=frames,
        capture_modified_by_ledger=False,interpolated=False,full_KCL_claimed=False,
        HBT_emitter_current_equals_collector_current_assumed=False,
        compact_rppd_current_inferred=False,thermal_state_used_as_electrical_node=False,
        measured_native_wire_branch_current=False,**FLAGS)
