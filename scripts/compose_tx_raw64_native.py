#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose the actual raw8074 parent at every native terminal reference plane."""
import copy,hashlib
from collections import Counter
import networkx as nx
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_tx_raw64_intrinsic as intrinsic
MODEL='nssoc_tx_full32_raw8074_wire_v1'
def prepare(native,binding,anchors,compact,wire):
    assert native['counts']==binding['counts']==dict(devices=8074,terminals=28582,ports=163,body_nets=65,wire_nets=698,mos_fingers=5376)
    assert anchors['counts']==dict(devices=8074,terminals=28582,metal_terminals=20508,body_terminals=8074,public_ports=163,unique_reference_planes=13344,wire_components=698)
    ports=[p['name']for p in native['ports']]
    assert ports==binding['ports']and len(ports)==len(set(ports))==163 and 'wire_cref'not in ports
    refs={a['label']:a for a in anchors['anchors']};assert len(refs)==13344
    public={x['reference_label']:x['name']for x in anchors['public']}
    assert set(public.values())==set(ports)and len(public)==163
    native_ports={x['name']:x['cluster']for x in native['ports']}
    assert all(refs[label]['native_cluster']==native_ports[name]for label,name in public.items())
    w=parser.statements(wire)
    assert w[0][:2]==['.subckt','full_raw64_core_wires']and w[-1]in (['.ends'],['.ends','full_raw64_core_wires'])
    assert len(w[0][2:])==len(set(w[0][2:]))==13344 and set(w[0][2:])==set(refs)
    wr=w[1:-1];assert Counter(x[0][0]for x in wr)==dict(R=137221,C=98241)
    assert all(len(x)==4 for x in wr)and len({x[0]for x in wr})==len(wr)
    all_nodes={n for x in wr for n in x[1:3]}|set(refs)
    assert 'sub'in all_nodes and 'sub'not in refs
    wire_map={name:public[name]if name in public else'wire_cref'if name=='sub'else'w'+str(i).zfill(7)for i,name in enumerate(sorted(all_nodes))}
    assert len(set(wire_map.values()))==len(wire_map)
    graph=nx.Graph();graph.add_nodes_from(refs)
    for row in wr:
        if row[0].startswith('R'):
            assert row[1]!=row[2]and parser.number(row[3])>0
            graph.add_edge(row[1],row[2])
    owner={};components=[]
    for nodes in nx.connected_components(graph):
        physical={refs[n]['native_cluster']for n in nodes if n in refs}
        assert len(physical)==1,'Unanchored or shorted physical resistance component'
        cluster=next(iter(physical));owner.update({n:cluster for n in nodes})
        components.append(cluster)
    assert len(components)==len(set(components))==698 and set(components)==set(native['wire_clusters'])
    assert set(owner)==all_nodes-{'sub'},'Capacitor node absent from actual R graph'
    body_map={str(n):'body'+str(i).zfill(3)for i,n in enumerate(native['body_clusters'])}
    assert len(body_map)==65 and not set(body_map.values())&set(wire_map.values())
    terms={(r['device'],r['terminal']):r for r in anchors['rows']}
    assert len(terms)==28582
    compact_rows=parser.statements(compact)
    assert compact_rows[0]==['.subckt',intrinsic.MODEL,*ports]and compact_rows[-1]==['.ends',intrinsic.MODEL]
    source_cards={row[0]:row for row in compact_rows[1:-1]}
    assert len(source_cards)==len(compact_rows)-2==8074
    records={d['native_id']:d for d in binding['devices']}
    native_by_id={d['id']:d for d in native['devices']}
    assert len(records)==len(native_by_id)==8074 and set(records)==set(native_by_id)
    expected_devices={};witnesses=[]
    for did,d in records.items():
        source=source_cards[d['instance']];original=native_by_id[did]
        order=intrinsic.ORDER[original['model']]
        assert d['native_model']==original['model']and d['named_terminal_order']==order
        assert d['terminals']==original['terminals']
        assert source==[d['instance'],*d['nodes'],d['model'],*[k+'='+v for k,v in d['parameters'].items()]]
        nodes=[];device_witness=[]
        for terminal in order:
            t=terms[did,terminal];n=original['terminals'][terminal]
            assert t['model']==original['model']and t['native_cluster']==n['cluster']and t['disposition']==n['disposition']
            if t['disposition']=='ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R':
                label=t['reference_label'];assert label==n['reference_label']
                assert owner[label]==t['native_cluster']==refs[label]['native_cluster']
                mapped=wire_map[label]
            else:
                assert t['disposition']=='RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R'and 'reference_label'not in t
                assert t['native_cluster']in native['body_clusters']
                mapped=body_map[str(t['native_cluster'])]
            nodes.append(mapped)
            device_witness.append(dict(terminal=terminal,native_cluster=t['native_cluster'],node=mapped,reference_label=t.get('reference_label'),disposition=t['disposition']))
        expected_devices[d['instance']]=[d['instance'],*nodes,*source[1+len(order):]]
        witnesses.append(dict(instance=d['instance'],native_id=did,model=d['model'],parameters=d['parameters'],terminals=device_witness))
    expected_wires=[[r[0],wire_map[r[1]],wire_map[r[2]],r[3]]for r in wr]
    assert len(expected_devices)==8074 and len(expected_wires)==235462
    return dict(ports=ports,wire_map=wire_map,body_map=body_map,expected_devices=expected_devices,expected_wires=expected_wires,witnesses=witnesses,reference_planes=refs,owner=owner)
def assemble(contract):
    rows=[['.subckt',MODEL,*contract['ports'],'wire_cref'],*contract['expected_devices'].values(),*contract['expected_wires'],['.ends',MODEL]]
    return '* Actual8074 native devices and137221R98241C; device-access/body/RF PEX unqualified.\n'+'\n'.join(' '.join(row)for row in rows)+'\n'
def verify(text,contract):
    rows=parser.statements(text)
    assert rows[0]==['.subckt',MODEL,*contract['ports'],'wire_cref']and rows[-1]==['.ends',MODEL],'Physical interface changed'
    assert len({r[0]for r in rows[1:-1]})==len(rows)-2,'Duplicate circuit card'
    devices={r[0]:r for r in rows[1:-1]if r[0].startswith('X')}
    assert devices==contract['expected_devices'],'Native device/parameter/reference/body binding changed'
    wires=[r for r in rows[1:-1]if not r[0].startswith('X')]
    assert Counter(tuple(r)for r in wires)==Counter(tuple(r)for r in contract['expected_wires']),'Raw R/C endpoint/value multiset changed'
    assert len(devices)==8074 and Counter(r[0][0]for r in wires)==dict(R=137221,C=98241)
    return True
def controls(text,contract):
    original=parser.statements(text);results=[]
    names=['missing_mos','wrong_mos_junction','swapped_mos_drain_source','missing_hbt','wrong_hbt_size','missing_contact','wrong_contact_R','short_body_to_supply','cross_driver_well_short','drop_resistor','change_resistor','drop_capacitor','change_capacitor','move_capacitor','cap_reference_as_substrate','extra_public_port','short_data_conductors','moved_actual_mos_reference_within_conductor','swap_hbt_collector_base','wrong_physical_resistor_width']
    for fault in names:
        rows=[r.copy()for r in original]
        if fault in ('drop_resistor','change_resistor','drop_capacitor','change_capacitor','move_capacitor','cap_reference_as_substrate'):
            kind='R'if'resistor'in fault else'C'
            i=next(i for i,r in enumerate(rows)if r[0].startswith(kind)and (fault!='cap_reference_as_substrate'or'wire_cref'in r[1:3]))
            if fault.startswith('drop_'):del rows[i]
            elif fault.startswith('change_'):rows[i][3]='999'
            elif fault=='move_capacitor':rows[i][1]=next(v for v in contract['wire_map'].values()if v not in rows[i][1:3]and v!='wire_cref')
            else:
                j=rows[i].index('wire_cref');rows[i][j]='sub'
        elif fault=='extra_public_port':rows[0].append('extra_port')
        elif fault=='short_data_conductors':
            assert 'd0p0'in contract['ports']and'd0n0'in contract['ports']
            rows.insert(-1,['R_INJECTED_SHORT','d0p0','d0n0','1'])
        else:
            kind='npn13g2'if'hbt'in fault else'ptap1'if'contact'in fault else'sg13_lv_pmos'if fault=='cross_driver_well_short'else'rppd'if fault=='wrong_physical_resistor_width'else'sg13_lv_nmos'
            i=next(i for i,r in enumerate(rows)if kind in r)
            if fault.startswith('missing_'):del rows[i]
            elif fault in ('wrong_mos_junction','wrong_hbt_size','wrong_contact_R','wrong_physical_resistor_width'):
                key={'wrong_mos_junction':'ad','wrong_hbt_size':'nx','wrong_contact_R':'R','wrong_physical_resistor_width':'w'}[fault]
                j=next(j for j,s in enumerate(rows[i])if s.startswith(key+'='));rows[i][j]=key+'=999'
            elif fault in ('swapped_mos_drain_source','swap_hbt_collector_base'):
                x,y=(1,3)if fault=='swapped_mos_drain_source'else(1,2)
                assert rows[i][x]!=rows[i][y];rows[i][x],rows[i][y]=rows[i][y],rows[i][x]
            elif fault=='short_body_to_supply':
                assert rows[i][4].startswith('body');rows[i][4]='avss'
            elif fault=='cross_driver_well_short':
                rows[i][4]=next(r[4]for r in rows if kind in r and r[4]!=rows[i][4])
            else:
                reverse={v:k for k,v in contract['wire_map'].items()}
                source=reverse[rows[i][1]];cluster=contract['owner'][source]
                destination=next(label for label,n in contract['owner'].items()if n==cluster and label!=source and label in contract['reference_planes'])
                assert contract['wire_map'][destination]!=rows[i][1]
                rows[i][1]=contract['wire_map'][destination]
        changed='\n'.join(' '.join(r)for r in rows)+'\n'
        try:verify(changed,contract)
        except (AssertionError,ValueError):results.append(dict(name=fault,rejected=True,sha256=hashlib.sha256(changed.encode()).hexdigest()))
        else:raise AssertionError('Accepted '+fault)
    assert len(results)==20
    return results
