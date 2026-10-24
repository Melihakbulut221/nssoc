#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Connect every PD394 native terminal to every audited actual wire R/C record.

Preserves intrinsic body nets and finite contacts without aliasing to supplies.
This is a model assembly screen, not qualified device/wire/RF capacitance or a
closed-loop simulation. MIM plate parasitic separation remains an explicit gate.
"""
import copy,difflib,hashlib,json,os
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-retimed-composition'
MODEL='nssoc_cdr_pd394_wire_v1'

def assemble(binding,anchors,geometry,wiretext):
    rows=parser.statements(wiretext);assert rows[0][:2]==['.subckt','pump_wires'] and rows[-1][0]=='.ends'
    ports=rows[0][2:];physical={a['label']:a for a in anchors['anchors']}
    assert len(ports)==len(set(ports))==len(physical)==776 and set(ports)==set(physical)
    assert anchors['logical_anchor_count']==anchors['physical_anchor_count']==776
    assert all(k==v for k,v in anchors['logical_anchor_aliases'].items())
    assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=751,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=383)
    assert geometry['native_device_count']==394 and geometry['native_terminal_count']==1134 and geometry['wire_component_count']==111
    native={d['native_id']:d for d in binding['devices']};assert len(native)==394
    terminals={(x['device'],x['terminal']):x for x in anchors['rows']};assert len(terminals)==len(anchors['rows'])==1134
    assert set(terminals)=={(d['native_id'],t)for d in binding['devices']for t in d['native_nodes']}
    public={a['label']:a['detail']['public_port']for a in anchors['anchors']if 'public_port'in a['detail']}
    assert len(public)==25 and set(public.values())==set(binding['native_ports']) and all(k=='P_'+v for k,v in public.items())
    source=rows[1:-1];assert Counter(r[0][0]for r in source)==dict(R=8933,C=7649)
    assert len({r[0].lower()for r in source})==len(source)
    for r in source:
        assert len(r)==4 and r[1]!=r[2]
        assert parser.number(r[3])>0 if r[0].startswith('R')else parser.number(r[3])>=0
    raw_nodes={n for row in source for n in row[1:3]};assert set(ports)<=raw_nodes and 'sub'in raw_nodes
    def wire_node(n):return 'wire_cref'if n=='sub'else public.get(n,'w_'+n)
    wire_map={n:wire_node(n)for n in raw_nodes};assert len(set(v.lower()for v in wire_map.values()))==len(wire_map)
    component_native={r['component']:r['native_cluster']for r in geometry['wire_components']}
    out=[];device_records=[];body_map={}
    for d in binding['devices']:
        nodes=[];witnesses=[]
        for terminal in d['compact_model_order']:
            x=terminals[d['native_id'],terminal]
            assert x['model']==d['native_model'] and x['native_net']==d['native_nodes'][terminal]
            if x['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE':
                label=x['wire_anchor'];a=physical[label]
                assert label==f"T{d['native_id']:03d}_{terminal}"
                assert a['native_cluster']==x['native_cluster']==component_native[x['wire_component']]
                assert a['wire_component']==x['wire_component']and a['point_dbu']==x['point_dbu']and a['metal']==x['metal']
                net=wire_map[label]
            else:
                assert x['disposition']=='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE'
                net='body_'+str(x['native_cluster']);body_map.setdefault(x['native_cluster'],dict(net=net,native_net=x['native_net']))
                assert body_map[x['native_cluster']]['native_net']==x['native_net'];label=None
            nodes.append(net);witnesses.append(dict(terminal=terminal,node=net,anchor=label,native_cluster=x['native_cluster'],native_net=x['native_net']))
        row=[d['instance'],*nodes,d['model'],*[k+'='+v for k,v in d['parameters'].items()]]
        out.append(row);device_records.append(dict(native_id=d['native_id'],instance=d['instance'],model=d['model'],parameters=d['parameters'],terminals=witnesses))
    assert not({x['net']for x in body_map.values()}&set(wire_map.values()))
    for row in source:out.append([row[0],wire_map[row[1]],wire_map[row[2]],row[3]])
    interface=[*binding['native_ports'],'wire_cref'];assert len(interface)==len(set(interface))==26
    text='\n'.join(['* Native394 devices + all8933R/7649C. MIM separation/RF/body PEX NOT qualified.','.subckt '+MODEL+' '+' '.join(interface),*[' '.join(r)for r in out],'.ends '+MODEL,''])
    contract=dict(interface=interface,device_records=device_records,wire_node_map=wire_map,body_map=body_map,counts=dict(devices=394,R=8933,C=7649),qualified_pex=False,mim_device_wire_capacitance_separation_qualified=False)
    return text,contract

def verify(text,binding,anchors,geometry,wiretext):
    # Re-derive the physical mapping from source native identities and geometry.
    expected,contract=assemble(binding,anchors,geometry,wiretext)
    got=parser.statements(text);wanted=parser.statements(expected)
    assert got[0]==wanted[0]and got[-1]==wanted[-1]
    by={r[0].lower():r for r in got[1:-1]};ref={r[0].lower():r for r in wanted[1:-1]}
    assert len(by)==len(got)-2 and set(by)==set(ref)
    for name,row in ref.items():
        actual=by[name]
        if name.startswith(('r','c')):
            assert actual[:3]==row[:3] and len(actual)==4 and parser.number(actual[3])==parser.number(row[3])
        else:assert actual==row
    return contract

def faults(text,binding,anchors,geometry,wiretext):
    original=parser.statements(text);result=[]
    cases=('missing_mim','wrong_mim_width','swapped_mim_plates','missing_contact','wrong_hbt_size','wrong_metal_terminal','short_body_supply','short_cref_sub','dropped_wire_r','changed_wire_r','dropped_wire_c','changed_wire_c','extra_alias_resistor')
    for name in cases:
        rows=copy.deepcopy(original)
        if name=='extra_alias_resistor':rows.insert(-1,['R_ALIAS','dp','dn','1'])
        elif name in ('short_cref_sub','short_body_supply'):
            if name=='short_cref_sub':i=next(i for i,r in enumerate(rows)if r[0].startswith('C')and 'wire_cref'in r[1:3]);k=rows[i].index('wire_cref');rows[i][k]='sub'
            else:i=next(i for i,r in enumerate(rows)if r[0].startswith('XD')and any(n.startswith('body_')for n in r));k=next(k for k,n in enumerate(rows[i])if n.startswith('body_'));rows[i][k]='avss'
        elif 'wire_'in name:
            prefix='R'if name.endswith('_r')else'C';i=next(i for i,r in enumerate(rows)if r[0].startswith(prefix))
            if name.startswith('dropped'):del rows[i]
            else:rows[i][3]=str(parser.number(rows[i][3])*2+1)
        else:
            model='cap_cmim'if 'mim'in name else'ptap1'if name=='missing_contact'else'npn13g2'
            d=next(d for d in binding['devices']if d['model']==model);i=next(i for i,r in enumerate(rows)if r[0]==d['instance'])
            if name.startswith('missing'):del rows[i]
            elif name=='swapped_mim_plates':rows[i][1],rows[i][2]=rows[i][2],rows[i][1];assert rows[i][1]!=rows[i][2]
            elif name=='wrong_metal_terminal':rows[i][1]='avdd';assert rows[i][1]!=original[i][1]
            else:
                key='w'if name=='wrong_mim_width'else'nx';k=next(k for k,v in enumerate(rows[i])if v.startswith(key+'='));rows[i][k]=key+'=999'
        mutated='\n'.join(' '.join(r)for r in rows)+'\n'
        try:verify(mutated,binding,anchors,geometry,wiretext)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('Accepted '+name)
        result.append(dict(name=name,rejected=True,sha256=hashlib.sha256(mutated.encode()).hexdigest(),diff=''.join(difflib.unified_diff(text.splitlines(True),mutated.splitlines(True)))))
    assert len(result)==13;return result

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,mim_device_wire_capacitance_separation_qualified=False,loaded_simulation_passed=False,closed_loop=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-retimed-rc-pass-20261018.json').read_text())
        selected=['wire/anchors08.json','wire/native05/result.json','wire/rc03/wires.spice','wire/audit.json','wire/native-mutations01.json']
        rc,rcproof=reports.restore_report('cdr-retimed-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'rc',selected)
        assert rc['status']==pin['status'] and rc['source_head']==pin['source_head']and rc['sources_unchanged']
        assert rc['audit']==pin['audit']and rc['controls']==pin['controls'];r['rc_source']=rcproof
        bp=json.loads((ROOT/'docs/evidence/cdr-retimed-binding-pass-20261018.json').read_text())
        names=['binding.json','pd394-compact.spice','native-devices.json'];prior,bproof=reports.restore_report('cdr-retimed-binding',bp['run'],bp['summary_sha256'],bp['parts_sha256'],OUT/'binding',names)
        assert prior==bp['report']and prior['sources_unchanged']and len(prior['controls'])==8;r['binding_source']=bproof
        binding=json.loads((OUT/'binding/binding.json').read_text());assert binding==prior['binding']
        anchors=json.loads((OUT/'rc/wire/anchors08.json').read_text());geometry=json.loads((OUT/'rc/wire/native05/result.json').read_text());wiretext=(OUT/'rc/wire/rc03/wires.spice').read_text()
        assert anchors==rc['anchors']and geometry==rc['geometry']
        text,contract=assemble(binding,anchors,geometry,wiretext);verify(text,binding,anchors,geometry,wiretext)
        r['controls']=faults(text,binding,anchors,geometry,wiretext);r['composition']=contract
        (OUT/'pd394-wire.spice').write_text(text);(OUT/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
        assert all(sha(OUT/'rc'/n)==rc['outputs'][n]for n in selected)and all(sha(OUT/'binding'/n)==prior['outputs'][n]for n in names)
        r['sources_unchanged']=True;r['status']='PASS_PD394_ALL16582_WIRE_ELEMENTS_AND13_COMPOSITION_CONTROLS_REQUIRES_MIM_REVIEW_AND_LOADED_WAVES'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
