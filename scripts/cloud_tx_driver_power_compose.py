#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compose all raw full-driver devices with all actual wire R/C, no ideal aliases."""
import json,os,re
from collections import Counter
from pathlib import Path
import cloud_tx_input_driver_power as physical
import cloud_tx_driver_power_intrinsic as intrinsic
from run_cloud_tx_layout_repair import sha
import build_pcie_local_vco_hybrid_v6 as helper
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-power-compose'
SOURCES=[{'run': 38899911036, 'group': 'tx-driver-power-intrinsic', 'root': 'cloud-tx-driver-power-intrinsic', 'bytes': 1354224, 'sha': '787ce6d769aa15cbe4932d4c8e2dc5f67cdf376a877d5974f65dc1f8f8171910', 'summary': 'd96e2746144c573ec503140a13c969e4058f1a937b3672bfa2a93f8553dad662'}, {'run': 38900317579, 'group': 'tx-driver-power-rc', 'root': 'cloud-tx-driver-power-rc', 'bytes': 6910070, 'sha': '3e2bcfa16db10928fc2a274a5285c8f527771d0b7cc49786755244baf470bfdc', 'summary': '9a27cd21cd2cc67b397a5e0ed0ec8b633c32047cd01d34a440991d655fad56d2'}]
TOP='nssoc_tx_driver_native100_power_wire_v1';PORTS=intrinsic.PORTS+['wire_cref']

def prepare(compact,wire,native,planes,tech):
    rows=native['native']['raw_flat_lvs']['devices'];intrinsic.verify(compact,rows,tech)
    old=helper.statements(compact);devices={line[0]:line for line in old[1:-1]};assert len(devices)==100
    lines=helper.statements(wire)
    assert lines[0][0].lower()=='.subckt' and lines[0][1]=='full_driver_wires' and lines[-1][0].lower()=='.ends'
    records=lines[1:-1];assert Counter(r[0][0]for r in records)==dict(R=260,C=300)
    assert all(len(r)==4 for r in records) and len({r[0].lower()for r in records})==560
    anchors={a['label']:a for a in planes['anchors']};assert len(anchors)==164 and len(lines[0][2:])==164 and set(lines[0][2:])==set(anchors)
    public={a['reference_label']:a['name']for a in planes['public']};assert set(public.values())==set(intrinsic.PORTS) and len(public)==6
    names={n for r in records for n in r[1:3]};assert set(anchors)<=names and 'sub'in names
    mapping={n:public[n] if n in public else 'wire_cref' if n=='sub' else 'w'+str(i).zfill(5) for i,n in enumerate(sorted(names))}
    assert len(mapping)==len({v.lower()for v in mapping.values()})
    by_terminal={(r['device'],r['terminal']):r for r in planes['rows']};assert len(by_terminal)==372
    expected={};converted=[]
    for r in rows:
        line=devices['XD'+str(r['id'])];order=intrinsic.order(r);nets=[];bindings=[]
        for term in order:
            plane=by_terminal[(r['id'],term)];native_term=r['terminals'][term]
            assert plane['model']==r['model'] and str(plane['native_cluster'])==native_term['cluster']
            if 'reference_label'in plane:
                anchor=anchors[plane['reference_label']];assert anchor['native_cluster']==plane['native_cluster'] and anchor['point_dbu']==plane['point_dbu']
                name=mapping[plane['reference_label']]
            else:
                assert term in ('B','rppd_sub','WELL') and native_term['logical_net']in ('BULK','NWELL')
                name=native_term['logical_net']
            nets.append(name);bindings.append(dict(terminal=term,node=name,native_cluster=native_term['cluster'],reference=plane.get('reference_label')))
        new=[line[0],*nets,*line[len(order)+1:]];expected[new[0]]=new;converted.append(dict(instance=new[0],native_id=r['id'],bindings=bindings))
    wires=[[r[0],mapping[r[1]],mapping[r[2]],r[3]]for r in records]
    text='\n'.join(['* Actual raw100 devices and260R300C metal/via model, not qualified PEX.',
        '* wire_cref is the native extraction C reference; declare its external boundary explicitly.',
        '* Poly/diffusion R and body spreading remain unmodeled.',
        '.subckt '+TOP+' '+' '.join(PORTS),*[' '.join(r)for r in expected.values()],*[' '.join(r)for r in wires],'.ends '+TOP,''])
    return text,expected,wires,mapping,converted

def verify(text,expected,wires,mapping,native,planes):
    lines=helper.statements(text);assert lines[0]==['.subckt',TOP,*PORTS] and lines[-1]==['.ends',TOP],'Model boundary changed'
    assert len({r[0].lower()for r in lines[1:-1]})==len(lines)-2,'Duplicated physical element'
    actual={r[0]:r for r in lines[1:-1]if r[0].startswith('XD')}
    assert set(actual)==set(expected) and len(actual)==100,'Intrinsic device missing'
    for name,row in expected.items():assert actual[name]==row,'Native terminal or intrinsic parameter changed'
    actual_wires=[r for r in lines[1:-1]if r[0][0]in 'RC']
    assert len(actual_wires)==560 and Counter(tuple(r)for r in actual_wires)==Counter(tuple(r)for r in wires),'Native wire record changed'
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
    assert len(owner)==10 and len(components)==10 and all(len(v)==1 for v in components.values()),'Physical wire topology changed'
    assert all(union.find(n)in owner for n in union.parent),'Unanchored wire node'
    body={}
    for d in native['native']['raw_flat_lvs']['devices']:
        for t in d['terminals'].values():
            if t['logical_net']in ('BULK','NWELL'):body[t['logical_net']]=t['cluster']
    assert len(body)==2 and set(body.values()).isdisjoint(owner.values())
    count=0
    for d in native['native']['raw_flat_lvs']['devices']:
        row=actual['XD'+str(d['id'])]
        for name,term in zip(row[1:1+len(intrinsic.order(d))],intrinsic.order(d)):
            nid=body[name]if name in body else owner[union.find(name)]
            assert nid==d['terminals'][term]['cluster'],'Collapsed native device topology changed';count+=1
    assert count==372
    return dict(devices=100,wire_resistors=260,wire_capacitors=300,terminals=count,wire_components=10,body_nodes=2,ports=PORTS)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],sources=SOURCES,qualified_pex=False,qualified_substrate=False,poly_diffusion_resistance_included=False,simulator_checked=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        physical.OUT=OUT;restored=[physical.restore(s)for s in SOURCES];(i,ir),(w,wr)=restored
        assert ir['status']=='PASS_RAW100_NAMED_MOS_JUNCTIONS_AND_FINITE_CONTACT_MODEL_WITH_SEVEN_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert wr['status']=='PASS_FRESH_FULL_DRIVER_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert len(ir['controls'])==7 and len(wr['controls']['cases'])==13
        compact=(i/'driver100.spice').read_text();assert sha(i/'driver100.spice')==ir['model_sha256']=='f0a4f8dae1fa2e7ae7894c6325d21ea35c9aadf8253f7bc4b90313113fdd2ca5'
        native=json.loads((i/'inputs/tx-driver-power-junctions/cloud-tx-driver-power-junctions/native.json').read_text())
        physical_root=w/'inputs/tx-driver-power-anchors/cloud-tx-driver-power-anchors/inputs/tx-driver-power-wires/cloud-tx-driver-power-wires/inputs/tx-input-driver-power/cloud-tx-input-driver-power'
        assert sha(physical_root/'base/layout.gds')==native['gds_sha256']
        assert sha(physical_root/'check-raw_flat_lvs/result.lvsdb')==native['native']['raw_flat_lvs']['database_sha256']
        assert sha(w/'rc01/wires.spice')=='81af7d4a18e04a65995806dde8abcd87b119c083185bfd87d373067a41fa8dd2'
        planes=json.loads((w/'anchors03.json').read_text());assert planes['counts']['unique_reference_planes']==164
        tech=json.loads((i/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        text,expected,wires,mapping,bindings=prepare(compact,(w/'rc01/wires.spice').read_text(),native,planes,tech)
        model=OUT/'driver100-wire.spice';model.write_text(text)
        result['positive']=verify(model.read_text(),expected,wires,mapping,native,planes);result['bindings']=bindings;result['wire_node_map']=mapping;save()
        controls=[]
        for fault in ['missing_MOS','wrong_junction','swap_D_S','body_short','wrong_contact_R','drop_wire_R','change_wire_R','change_wire_C','move_wire_C','Cref_as_supply']:
            lines=text.splitlines();mos=next(j for j,s in enumerate(lines)if ' sg13_lv_nmos 'in s);contact=next(j for j,s in enumerate(lines)if ' ptap1 'in s);rr=next(j for j,s in enumerate(lines)if s.startswith('R'));cc=next(j for j,s in enumerate(lines)if s.startswith('C'))
            if fault=='missing_MOS':del lines[mos]
            elif fault=='wrong_junction':lines[mos]=re.sub(r'ad=\S+','ad=99p',lines[mos])
            elif fault=='wrong_contact_R':lines[contact]=re.sub(r'R=\S+','R=1',lines[contact])
            elif fault=='drop_wire_R':del lines[rr]
            elif fault in ('change_wire_R','change_wire_C'):
                index=rr if fault=='change_wire_R'else cc;words=lines[index].split();words[3]=str(helper.number(words[3])*2);lines[index]=' '.join(words)
            elif fault=='move_wire_C':
                words=lines[cc].split();words[1]=next(n for n in mapping.values()if n not in words[1:3]);lines[cc]=' '.join(words)
            elif fault=='Cref_as_supply':lines=[s.replace('wire_cref','avss')for s in lines]
            else:
                words=lines[mos].split()
                if fault=='body_short':words[4]=words[3]
                else:words[1],words[3]=words[3],words[1]
                lines[mos]=' '.join(words)
            bad='\n'.join(lines)+'\n';assert bad!=text;(OUT/(fault+'.spice')).write_text(bad)
            try:verify(bad,expected,wires,mapping,native,planes)
            except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Accepted actual physical model corruption '+fault)
        result['controls']=controls;result['model_sha256']=sha(model)
        assert all(all(sha(p/n)==v for n,v in r['outputs'].items())for p,r in restored)
        result['status']='PASS_RAW100_AND_ALL260R300C_EXACT_PHYSICAL_COMPOSITION_WITH10_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
