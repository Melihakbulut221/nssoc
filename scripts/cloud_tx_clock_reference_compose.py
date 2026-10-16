#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compose all six native clock devices with every actual wire R/C and finite body contacts."""
import argparse,json,os,re
import compare_cloud_routed_endpoints as reports
from collections import Counter
from pathlib import Path
import cloud_tx_input_driver_localpins as physical
import cloud_tx_clock_reference_intrinsic as intrinsic
from run_cloud_tx_layout_repair import fetch,sha
import build_pcie_local_vco_hybrid_v6 as helper
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-localpins-compose'
INPUTS={'l6p2': [{'run': 38950420186, 'group': 'tx-clock-reference-intrinsic-l6p2', 'summary': 'da43047928d4ba122351696639184455d714a4dcbd8596e18b1499647e674d57', 'parts': 'c57d46789591ee888d162ffb29fadb2590a734dbe8749ec36c04f806bd22c9ce', 'model': 'f79e78675852d9956a7eb0682f864be0e369b5c299046be7c73136d277933ef0'}, {'run': 38949849842, 'group': 'tx-clock-reference-rc-l6p2', 'summary': 'dea7ba09906d0d5f600f2ee6510c38e4aeb4fb42995bbd50a49b05741f5ac02e', 'parts': 'fb512bfc64e354706bcd41c3f32858ebaf16d5986f59965ecd673b860fdb7f69'}], 'l6p5': [{'run': 38950420186, 'group': 'tx-clock-reference-intrinsic-l6p5', 'summary': '6dd6f611a34325b085c3349f7d41c6c45c4c37465f72e68ac214583265e3fb68', 'parts': 'be3e5e5fae3f9a1e5dc8efac999f73594472841c7e62a97a4271db6dc0fdbf8b', 'model': 'ee2135cd05e50ce9be452197dc1dcc5847078ea479012bc791fcf963489c73cc'}, {'run': 38949849842, 'group': 'tx-clock-reference-rc-l6p5', 'summary': '6ad3a8c7c79e393b9014a0d0c3bf5db7cf96da458338750c1df712ea0b982805', 'parts': 'a2a10f25c879383434e4d051fc309935c89f411d35aaa5ee23383d16575f2e51'}]}

def restore(spec):
    stem=spec['group']+'-'+str(spec['run'])+'-1'
    url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(spec['run'])+'-1-'+spec['group']+'/'+stem+'.summary.json'
    summary=OUT/(spec['group']+'.json');fetch(url,spec['summary'],summary);frozen=json.loads(summary.read_text())
    destination=OUT/'inputs'/spec['group']
    prior,proof=reports.restore_report(spec['group'],spec['run'],spec['summary'],spec['parts'],destination,tuple(frozen['outputs']))
    assert prior==frozen
    # RC reports prove their inputs in the controller but have no source_unchanged field.
    # Require every restored file hash directly, for both producer schemas.
    assert all(sha(destination/name)==digest for name,digest in prior['outputs'].items())
    return destination,prior

TOP='nssoc_tx_driver_native100_localpins_wire_v1';PORTS=intrinsic.PORTS+['wire_cref']

def prepare(compact,wire,native,planes,tech):
    rows=native['modes']['lvs_flat']['devices'];intrinsic.verify(compact,rows,tech,INTRINSIC_TOP)
    old=helper.statements(compact);devices={line[0]:line for line in old[1:-1]};assert len(devices)==6
    lines=helper.statements(wire)
    assert lines[0][0].lower()=='.subckt' and lines[0][1]=='clock_reference_wires' and lines[-1][0].lower()=='.ends'
    records=lines[1:-1];assert Counter(r[0][0]for r in records)==dict(R=13,C=28)
    assert all(len(r)==4 for r in records) and len({r[0].lower()for r in records})==41
    anchors={a['label']:a for a in planes['anchors']};assert len(anchors)==14 and len(lines[0][2:])==14 and set(lines[0][2:])==set(anchors)
    public={a['reference_label']:a['name']for a in planes['public']};assert set(public.values())==set(intrinsic.PORTS) and len(public)==4
    names={n for r in records for n in r[1:3]};assert set(anchors)<=names and 'sub'in names
    mapping={n:public[n] if n in public else 'wire_cref' if n=='sub' else 'w'+str(i).zfill(5) for i,n in enumerate(sorted(names))}
    assert len(mapping)==len({v.lower()for v in mapping.values()})
    by_terminal={(r['device'],r['terminal']):r for r in planes['rows']};assert len(by_terminal)==16
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
    text='\n'.join(['* Actual raw6 clock devices and13R28C metal/via model, not qualified PEX.',
        '* wire_cref is the native extraction C reference; declare its external boundary explicitly.',
        '* Poly/diffusion R and body spreading remain unmodeled.',
        '.subckt '+TOP+' '+' '.join(PORTS),*[' '.join(r)for r in expected.values()],*[' '.join(r)for r in wires],'.ends '+TOP,''])
    return text,expected,wires,mapping,converted

def verify(text,expected,wires,mapping,native,planes):
    lines=helper.statements(text);assert lines[0]==['.subckt',TOP,*PORTS] and lines[-1]==['.ends',TOP],'Model boundary changed'
    assert len({r[0].lower()for r in lines[1:-1]})==len(lines)-2,'Duplicated physical element'
    actual={r[0]:r for r in lines[1:-1]if r[0].startswith('XD')}
    assert set(actual)==set(expected) and len(actual)==6,'Intrinsic device missing'
    for name,row in expected.items():assert actual[name]==row,'Native terminal or intrinsic parameter changed'
    actual_wires=[r for r in lines[1:-1]if r[0][0]in 'RC']
    assert len(actual_wires)==41 and Counter(tuple(r)for r in actual_wires)==Counter(tuple(r)for r in wires),'Native wire record changed'
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
    assert len(owner)==5 and len(components)==5 and all(len(v)==1 for v in components.values()),'Physical wire topology changed'
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
    assert count==16
    return dict(devices=6,wire_resistors=13,wire_capacitors=28,terminals=count,wire_components=5,body_nodes=1,ports=PORTS)

INPUTS['l5p7']=[dict(run=38962062682,group='tx-clock-reference-intrinsic-l5p7',head='1c804f1faca16917fade3ed7d5371098bdae86be',summary='c2b4f6ece07c28178a788059c7e2f444bdf23de93532d0d684c4dc302f35538a',parts='a817e81c588165aadeb3912b976a868e187374f2b5a985f0e4618df8a4764364',model='07314432a9efb4d37cb1c1cde2aa9429d060750517d01063036a22a6e1e8461b'),dict(run=38962725630,group='tx-clock-reference-rc-l5p7',head='aee605d5ecbe2ae4cdbb84e532fc7a160d9af29b',summary='a9441ba286414e1dd008517a4ccb8afb80057f74c253ce6f53e4c300969547a5',parts='44a153f7ec874f72fa5d0c6e68fd7c7a65161e63ca40f0bec0637a6a72a5372f')]

def main():
    global OUT,TOP,INTRINSIC_TOP
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(INPUTS),required=True);args=parser.parse_args()
    SOURCES=INPUTS[args.variant];OUT=ROOT/('hw/soc/out/cloud-tx-clock-reference-compose-'+args.variant)
    TOP='nssoc_clock_reference_'+args.variant+'_native6_wire_v1'
    INTRINSIC_TOP='nssoc_clock_reference_'+args.variant+'_native6_intrinsic_v1'
    reports.OUT=OUT
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],sources=SOURCES,qualified_pex=False,qualified_substrate=False,poly_diffusion_resistance_included=False,simulator_checked=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        restored=[restore(s)for s in SOURCES];(i,ir),(w,wr)=restored
        assert ir['variant']==wr['variant']==args.variant and ir['source_unchanged'];result['variant']=args.variant
        assert ir['source_head']==SOURCES[0].get('head','8d1fde01d81e4a6d282fb498094a0f76f4ae51fa') and wr['source_head']==SOURCES[1].get('head','e775fc822e4587e520f37078f95a5b42f913375e')and wr['source_unchanged']
        assert ir['status']=='PASS_NATIVE_CLOCK6_INTRINSIC_FINITE_CONTACTS_AND_EIGHT_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert wr['status']=='PASS_FRESH_ACTUAL_CLOCK_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert len(ir['controls'])==8 and all(c['rejected']for c in ir['controls'])and len(wr['controls']['cases'])==13 and all(c['rejected_by']for c in wr['controls']['cases'])
        compact=(i/'clock6.spice').read_text();assert sha(i/'clock6.spice')==ir['model_sha256']==SOURCES[0]['model']
        native=json.loads((i/'source/native.json').read_text())
        physical_root=w/'source/wire/source'
        assert sha(physical_root/'layout/nssoc_tx_clock_reference_layout_v1.gds')==native['gds_sha256']
        assert sha(physical_root/'check/lvs_flat/result.lvsdb')==native['modes']['lvs_flat']['database_sha256']
        assert sha(w/'rc01/wires.spice')==wr['outputs']['rc01/wires.spice']
        planes=json.loads((w/'anchors03.json').read_text());assert planes['counts']['unique_reference_planes']==14
        tech=json.loads((i/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        text,expected,wires,mapping,bindings=prepare(compact,(w/'rc01/wires.spice').read_text(),native,planes,tech)
        model=OUT/'clock6-wire.spice';model.write_text(text)
        result['positive']=verify(model.read_text(),expected,wires,mapping,native,planes);result['bindings']=bindings;result['wire_node_map']=mapping;save()
        controls=[]
        for fault in ['missing_HBT','wrong_Nx','swap_B_E','body_short','wrong_contact_R','drop_wire_R','change_wire_R','change_wire_C','move_wire_C','Cref_as_supply','swap_C_B_planes']:
            lines=text.splitlines();mos=next(j for j,s in enumerate(lines)if ' npn13G2 'in s);contact=next(j for j,s in enumerate(lines)if ' ptap1 'in s);rr=next(j for j,s in enumerate(lines)if s.startswith('R'));cc=next(j for j,s in enumerate(lines)if s.startswith('C'))
            if fault=='missing_HBT':del lines[mos]
            elif fault=='wrong_Nx':lines[mos]=re.sub(r'Nx=\S+','Nx=2',lines[mos])
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
                elif fault=='swap_C_B_planes':
                    assert words[1]!=words[2];words[1],words[2]=words[2],words[1]
                else:words[2],words[3]=words[3],words[2]
                lines[mos]=' '.join(words)
            bad='\n'.join(lines)+'\n';assert bad!=text;(OUT/(fault+'.spice')).write_text(bad)
            try:verify(bad,expected,wires,mapping,native,planes)
            except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Accepted actual physical model corruption '+fault)
        assert len(controls)==11 and all(c['rejected']for c in controls)
        result['controls']=controls;result['model_sha256']=sha(model);result['source_unchanged']=True
        assert all(all(sha(p/n)==v for n,v in r['outputs'].items())for p,r in restored)
        result['status']='PASS_RAW6_AND_ALL13R28C_EXACT_CLOCK_COMPOSITION_WITH11_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
