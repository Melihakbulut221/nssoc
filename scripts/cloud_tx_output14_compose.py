#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose actual TX output14 devices with every native wire R/C and eight finite body contacts."""
import json,os,re
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
import tx_output14_intrinsic_model as intrinsic
from run_cloud_tx_layout_repair import fetch,sha
import build_pcie_local_vco_hybrid_v6 as helper
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output14-compose'
TOP='nssoc_tx_output14_wire_v1'
INTRINSIC_TOP='nssoc_tx_output14_intrinsic_v1'
PORTS=intrinsic.PORTS+['wire_cref']
SOURCES=[{'run': 39567903604, 'group': 'tx-output14-intrinsic', 'head': '92de02d9740a2ce14ecaa7caed8aa41838b28290', 'summary_asset': 661818301, 'summary': 'd5ec4a87f88e21e8cfec51aec27a8d7227fb7dbe0158bb7453590cd95ab91a21', 'parts_asset': 661818372, 'parts': '369c3e2bc2e22837e1e0023235457f2d61dbcfbd4251403de7a5345bec5fbc25'}, {'run': 39567299858, 'group': 'tx-output14-rc', 'head': '6661b49607de04f07aa2627f9b0dd536a5a73c3b', 'summary_asset': 661805932, 'summary': '966a0dbf8d82772bd21bdc9ba8b70fe06c3249129d50e73d315f95c09cf009c9', 'parts_asset': 661806023, 'parts': '6d6f4f724789e605190f71fb0705c5b68a8d8f5f0db04923af4f0456cffbde17'}]

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

def prepare(compact,wire,native,planes,tech):
    rows=native['modes']['lvs_flat']['devices'];intrinsic.verify(compact,rows,tech,INTRINSIC_TOP)
    old=helper.statements(compact);devices={line[0]:line for line in old[1:-1]};assert len(devices)==14
    lines=helper.statements(wire)
    assert lines[0][0].lower()=='.subckt' and lines[0][1]=='tx_output_wires' and lines[-1][0].lower()=='.ends'
    records=lines[1:-1];assert Counter(r[0][0]for r in records)==dict(R=2619,C=1410)
    assert all(len(r)==4 for r in records) and len({r[0].lower()for r in records})==4029
    anchors={a['label']:a for a in planes['anchors']};assert len(anchors)==32 and len(lines[0][2:])==32 and set(lines[0][2:])==set(anchors)
    public={a['reference_label']:a['name'].lower()for a in planes['public']};assert set(public.values())==set(intrinsic.PORTS) and len(public)==8
    names={n for r in records for n in r[1:3]};assert set(anchors)<=names and 'sub'in names
    mapping={n:public[n] if n in public else 'wire_cref' if n=='sub' else 'w'+str(i).zfill(5) for i,n in enumerate(sorted(names))}
    assert len(mapping)==len({v.lower()for v in mapping.values()})
    by_terminal={(r['device'],r['terminal']):r for r in planes['rows']};assert len(by_terminal)==38
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
                assert term in ('S','rsil_sub','WELL') and native_term['logical_net']in ('BULK',)
                name=native_term['logical_net']
            nets.append(name);bindings.append(dict(terminal=term,node=name,native_cluster=native_term['cluster'],reference=plane.get('reference_label')))
        new=[line[0],*nets,*line[len(order)+1:]];expected[new[0]]=new;converted.append(dict(instance=new[0],native_id=r['id'],bindings=bindings))
    wires=[[r[0],mapping[r[1]],mapping[r[2]],r[3]]for r in records]
    text='\n'.join(['* Actual raw14 output devices and2619R1410C metal/via model, not qualified PEX.',
        '* wire_cref is the native extraction C reference; declare its external boundary explicitly.',
        '* Poly/diffusion R and body spreading remain unmodeled.',
        '.subckt '+TOP+' '+' '.join(PORTS),*[' '.join(r)for r in expected.values()],*[' '.join(r)for r in wires],'.ends '+TOP,''])
    return text,expected,wires,mapping,converted

def verify(text,expected,wires,mapping,native,planes):
    lines=helper.statements(text);assert lines[0]==['.subckt',TOP,*PORTS] and lines[-1]==['.ends',TOP],'Model boundary changed'
    assert len({r[0].lower()for r in lines[1:-1]})==len(lines)-2,'Duplicated physical element'
    actual={r[0]:r for r in lines[1:-1]if r[0].startswith('XD')}
    assert set(actual)==set(expected) and len(actual)==14,'Intrinsic device missing'
    for name,row in expected.items():assert actual[name]==row,'Native terminal or intrinsic parameter changed'
    actual_wires=[r for r in lines[1:-1]if r[0][0]in 'RC']
    assert len(actual_wires)==4029 and Counter(tuple(r)for r in actual_wires)==Counter(tuple(r)for r in wires),'Native wire record changed'
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
    assert len(owner)==9 and len(components)==9 and all(len(v)==1 for v in components.values()),'Physical wire topology changed'
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
    assert count==38
    return dict(devices=14,wire_resistors=2619,wire_capacitors=1410,terminals=count,wire_components=9,body_nodes=1,ports=PORTS)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,qualified_substrate=False,poly_diffusion_resistance_included=False,simulator_checked=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        restored=[]
        for spec in SOURCES:
            pin=json.loads((ROOT/'docs/evidence'/ (spec['group']+'-pass-20261021.json')).read_text())
            assert pin['run']==spec['run'] and pin['summary_sha256']==spec['summary'] and pin['parts_sha256']==spec['parts']
            p,r=restore(spec);assert r==pin['report'] and r['source_head']==spec['head'] and r['sources_unchanged']
            restored.append((p,r))
        (i,ir),(w,wr)=restored
        assert ir['status']=='PASS_NATIVE_TX_OUTPUT14_INTRINSIC_EIGHT_FINITE_CONTACTS_AND16_CONTROLS_REQUIRES_RC_COMPOSITION'
        assert wr['status']=='PASS_FRESH_TX_OUTPUT14_WIRE_RC_AND13_RAW_CONTROLS_REQUIRES_COMPOSITION_AND_PARENT_ROUTE'
        assert len(ir['controls'])==8 and all(c['rejected']for c in ir['controls'])
        assert len(ir['native_controls'])==8 and all(c['rejected']for c in ir['native_controls'])
        assert len(wr['controls']['cases'])==13 and all(c['rejected_by']for c in wr['controls']['cases'])
        compact=(i/'output14.spice').read_text()
        assert sha(i/'output14.spice')==ir['model_sha256']=='1b3892a819d13fd74f15783bbf4c87da95294eb24dbfbac489e2fcf03fcb43a7'
        native=json.loads((i/'native.json').read_text())
        result['native_topology']=intrinsic.validate_native(native)
        physical_root=w/'source/wire/source'
        assert sha(physical_root/'layout/nssoc_tx_cml_layout.gds')==native['gds_sha256']==ir['gds_sha256']
        assert sha(physical_root/'check/lvs_flat/result.lvsdb')==native['modes']['lvs_flat']['database_sha256']==ir['native_database_sha256']
        assert sha(w/'rc01/wires.spice')==wr['outputs']['rc01/wires.spice']
        planes=json.loads((w/'anchors03.json').read_text());assert planes['counts']['unique_reference_planes']==32
        tech=json.loads((i/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        text,expected,wires,mapping,bindings=prepare(compact,(w/'rc01/wires.spice').read_text(),native,planes,tech)
        model=OUT/'output14-wire.spice';model.write_text(text)
        result['positive']=verify(model.read_text(),expected,wires,mapping,native,planes)
        result['bindings']=bindings;result['wire_node_map']=mapping;save()
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
                if fault=='swap_C_B_planes':
                    # The REF C/B share a logical net but have distinct physical contact planes.
                    refs=[d for d in native['modes']['lvs_flat']['devices'] if d['model']=='npn13G2' and d['terminals']['C']['cluster']==d['terminals']['B']['cluster']]
                    assert len(refs)==1
                    name='XD'+str(refs[0]['id'])
                    mos=next(j for j,s in enumerate(lines)if s.split()and s.split()[0]==name)
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
        result['controls']=controls;result['model_sha256']=sha(model)
        assert all(all(sha(p/n)==v for n,v in r['outputs'].items())for p,r in restored)
        result['sources_unchanged']=True
        result['status']='PASS_RAW14_ALL2619R1410C_TX_OUTPUT_COMPOSITION_AND11_FAULTS_REQUIRES_LOADED_FULLWAVE_AND_PARENT_ROUTE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
