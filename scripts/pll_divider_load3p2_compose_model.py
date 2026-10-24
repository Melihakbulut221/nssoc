#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full native91 divider composition; independent collapsed topology and exact RC records."""
from collections import Counter
import build_pcie_local_vco_hybrid_v6 as helper
import pll_divider_load3p2_intrinsic as intrinsic
TOP='nssoc_divider_load3p2_native91_wire_v1'
INTRINSIC_TOP='nssoc_divider_load3p2_native91_intrinsic_v1'
PORTS=intrinsic.PORTS+['wire_cref']

def prepare(compact,wire,native,planes,tech):
    rows=native['modes']['lvs_flat']['devices'];intrinsic.verify(compact,rows,tech,INTRINSIC_TOP)
    old=helper.statements(compact);devices={line[0]:line for line in old[1:-1]};assert len(devices)==91
    lines=helper.statements(wire)
    assert lines[0][0].lower()=='.subckt' and lines[0][1]=='divider_load3p2_wires' and lines[-1][0].lower()=='.ends'
    records=lines[1:-1];assert Counter(r[0][0]for r in records)==dict(R=382,C=649)
    assert all(len(r)==4 for r in records) and len({r[0].lower()for r in records})==1031
    anchors={a['label']:a for a in planes['anchors']};assert len(anchors)==205 and len(lines[0][2:])==205 and set(lines[0][2:])==set(anchors)
    public={a['reference_label']:a['name']for a in planes['public']};assert set(public.values())==set(intrinsic.PORTS) and len(public)==7
    names={n for r in records for n in r[1:3]};assert set(anchors)<=names and 'sub'in names
    mapping={n:public[n] if n in public else 'wire_cref' if n=='sub' else 'w'+str(i).zfill(5) for i,n in enumerate(sorted(names))}
    assert len(mapping)==len({v.lower()for v in mapping.values()})
    by_terminal={(r['device'],r['terminal']):r for r in planes['rows']};assert len(by_terminal)==283
    expected={};converted=[]
    for r in rows:
        line=devices['XD'+str(r['id'])];order=intrinsic.ORDER[r['model']];nets=[];bindings=[]
        for term in order:
            plane=by_terminal[(r['id'],term)];native_term=r['terminals'][term]
            assert plane['model']==r['model'] and str(plane['native_cluster'])==native_term['cluster']
            if 'reference_label'in plane:
                anchor=anchors[plane['reference_label']];assert anchor['native_cluster']==plane['native_cluster'] and anchor['point_dbu']==plane['point_dbu']
                name=mapping[plane['reference_label']]
            else:
                assert term in ('S','rppd_sub','WELL') and native_term['logical_net']in ('BULK',)
                name=native_term['logical_net']
            nets.append(name);bindings.append(dict(terminal=term,node=name,native_cluster=native_term['cluster'],reference=plane.get('reference_label')))
        new=[line[0],*nets,*line[len(order)+1:]];expected[new[0]]=new;converted.append(dict(instance=new[0],native_id=r['id'],bindings=bindings))
    wires=[[r[0],mapping[r[1]],mapping[r[2]],r[3]]for r in records]
    text='\n'.join(['* Actual raw91 divider devices and382R649C metal/via model, not qualified PEX.',
        '* wire_cref is the native extraction C reference; declare its external boundary explicitly.',
        '* Poly/diffusion R and body spreading remain unmodeled.',
        '.subckt '+TOP+' '+' '.join(PORTS),*[' '.join(r)for r in expected.values()],*[' '.join(r)for r in wires],'.ends '+TOP,''])
    return text,expected,wires,mapping,converted

def verify(text,expected,wires,mapping,native,planes):
    lines=helper.statements(text);assert lines[0]==['.subckt',TOP,*PORTS] and lines[-1]==['.ends',TOP],'Model boundary changed'
    assert len({r[0].lower()for r in lines[1:-1]})==len(lines)-2,'Duplicated physical element'
    actual={r[0]:r for r in lines[1:-1]if r[0].startswith('XD')}
    assert set(actual)==set(expected) and len(actual)==91,'Intrinsic device missing'
    for name,row in expected.items():assert actual[name]==row,'Native terminal or intrinsic parameter changed'
    actual_wires=[r for r in lines[1:-1]if r[0][0]in 'RC']
    assert len(actual_wires)==1031 and Counter(tuple(r)for r in actual_wires)==Counter(tuple(r)for r in wires),'Native wire record changed'
    assert len(actual)+len(actual_wires)==len(lines)-2,'Unknown model element'
    # Collapse only extracted wire resistors for a topology check. Contact models
    # remain devices, and original native aliases are never inserted as edges.
    union=helper.Union()
    for r in actual_wires:
        assert helper.number(r[3])>0 and r[1]!=r[2]
        if r[0].startswith('R'):union.join(r[1],r[2])
    owner={};components={}
    for a in planes['anchors']:
        root=union.find(mapping[a['label']]);nid=str(a['native_cluster'])
        assert root not in owner or owner[root]==nid,'Wire connects different native conductors'
        owner[root]=nid;components.setdefault(a['wire_component'],set()).add(root)
    assert len(owner)==37 and len(components)==37 and all(len(v)==1 for v in components.values()),'Physical wire topology changed'
    assert all(union.find(n)in owner for n in union.parent),'Unanchored wire node'
    body={}
    for d in native['modes']['lvs_flat']['devices']:
        for t in d['terminals'].values():
            if t['logical_net']in ('BULK',):body[t['logical_net']]=t['cluster']
    assert len(body)==1 and set(body.values()).isdisjoint(owner.values())
    count=0
    for d in native['modes']['lvs_flat']['devices']:
        row=actual['XD'+str(d['id'])]
        for name,term in zip(row[1:1+len(intrinsic.ORDER[d['model']])],intrinsic.ORDER[d['model']]):
            nid=body[name]if name in body else owner[union.find(name)]
            assert nid==d['terminals'][term]['cluster'],'Collapsed native device topology changed';count+=1
    assert count==283
    return dict(devices=91,wire_resistors=382,wire_capacitors=649,terminals=count,wire_components=37,body_nodes=1,ports=PORTS)

