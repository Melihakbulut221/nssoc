#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Capture full native PD484 RC with actual MIM masks and explicit-device semantics.

No raw RC audit or physical PEX qualification is claimed by this capture stage.
Eleven native MIM devices must remain matched to their actual KLayout terminal
components. Their compact models are not to be added twice during composition.
"""
import argparse,copy,hashlib,json,os,shutil,subprocess,sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-retime-trunks-v22-mim-parent-rc'
TOP='nssoc_cdr_pd484_localbus_v12'

def generate():
    import pya
    P=OUT/'source';G=P/'parent/layout'/(TOP+'.gds');D=P/'parent/physical/lvs_flat/result.lvsdb'
    L=pya.Layout();L.read(str(G));T=L.cell(TOP);assert L.dbu==.001 and T is not None
    native=pya.LayoutVsSchematic();native.read(str(D));assert native.netlist().top_circuit().name==TOP
    original=json.loads((P/'wire/anchors08.json').read_text());a=copy.deepcopy(original);geo=json.loads((P/'wire/native05/result.json').read_text());devices=json.loads((P/'wire/device-locations01.json').read_text())['devices']
    oldwire=pya.LayoutToNetlist();oldwire.read(str(P/'wire/native05/wires.l2n'))
    rows={(r['device'],r['terminal']):r for r in a['rows']};labels={r['label']:r for r in a['anchors']};changes=[]
    mask=pya.Region(T.begin_shapes_rec(L.layer(36,0))).merged();vias=pya.Region(T.begin_shapes_rec(L.layer(129,0))).merged();assert not mask.is_empty()and not vias.is_empty()
    native_masks={36:pya.Region(),129:pya.Region()}
    def replace_points(value,point):
        if isinstance(value,dict):
            for k,v in value.items():
                if k=='point_dbu':value[k]=list(point)
                else:replace_points(v,point)
        elif isinstance(value,list):
            for v in value:replace_points(v,point)
    caps=[d for d in devices if d['model']=='cap_cmim'];assert len(caps)==11
    for d in caps:
        c=L.cell(d['pcell']['cell']);dt=pya.DCplxTrans.from_s(d['pcell']['transform']);tr=pya.ICplxTrans(dt.mag,dt.angle,dt.is_mirror(),round(dt.disp.x/L.dbu),round(dt.disp.y/L.dbu))
        for layer in native_masks:native_masks[layer]+=pya.Region(c.begin_shapes_rec(L.layer(layer,0))).transformed(tr)
        metal=pya.Region(c.begin_shapes_rec(L.layer(67,0))).transformed(tr).merged();access=(metal-mask).merged()
        boxes=[p.bbox()for p in access.decompose_trapezoids_to_region().each()if p.area()==p.bbox().area()and p.bbox().width()>20 and p.bbox().height()>20];assert boxes
        point=max(boxes,key=lambda b:b.area()).center();label=f"T{d['native_id']:03d}_mim_btm";row=rows[d['native_id'],'mim_btm'];anchor=labels[label]
        assert row['metal']==anchor['metal']==67 and row['wire_anchor']==label
        old=anchor['point_dbu'];new=[point.x,point.y];assert old!=new
        replace_points(anchor,new);row['point_dbu']=new
        changes.append(dict(native_id=d['native_id'],label=label,old_point_dbu=old,new_point_dbu=new,reason='Actual bottom Metal5 access outside the intrinsic MIM mask; no logical net or geometry edited.'))
    assert (native_masks[36]^mask).is_empty()and(native_masks[129]^vias).is_empty(),'Intrinsic masks must be exactly the eleven native PCells'
    W=pya.Layout();W.read(str(P/'wire/native05/wires.gds'));WT=W.top_cell();assert WT.name=='pump_wires'and W.dbu==L.dbu
    for layer in (8,10,30,50,67,126,134,19,29,49,66,125,133):
        assert(pya.Region(WT.begin_shapes_rec(W.layer(layer,0)))^pya.Region(T.begin_shapes_rec(L.layer(layer,0)))).is_empty()
    for layer,region in ((36,mask),(129,vias)):
        assert pya.Region(WT.begin_shapes_rec(W.layer(layer,0))).is_empty();WT.shapes(W.layer(layer,0)).insert(region)
    for anchor in a['anchors']:
        m=anchor['metal'];point=pya.Point(*anchor['point_dbu']);n=native.probe_net(native.layer_by_index(geo['native_layer_mapping'][str(m)]),point);assert n is not None and n.cluster_id==anchor['native_cluster']
        wn=oldwire.probe_net(oldwire.layer_by_name('gds_'+str(m)),point);assert wn is not None and wn.cluster_id==anchor['wire_component']
        witness=pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))
        if m==67:assert (witness&mask).is_empty(),'A Metal5 label would be painted onto the MIM top plate'
    assert len(a['anchors'])==len({(x['metal'],*x['point_dbu'])for x in a['anchors']})==946
    wire=OUT/'wire';wire.mkdir();(wire/'native05').mkdir();W.write(str(wire/'native05/wires.gds'))
    a['inputs']={str(p):sha(p)for p in [Path(__file__),G,D,P/'wire/anchors08.json',P/'wire/native05/result.json',P/'wire/native05/wires.l2n',P/'wire/device-locations01.json',wire/'native05/wires.gds']}
    a['status']='PASS_ALL946_NATIVE_POINTS_WITH_ELEVEN_MIM_BOTTOM_ACCESS_REBINDINGS';a['mim_bottom_point_changes']=changes
    (wire/'anchors08.json').write_text(json.dumps(a,indent=2)+'\n')
    result=dict(status='PASS_FULL_PD_MASK_GEOMETRY_AND_NATIVE_POINT_BINDING',original_metal_and_vias_unchanged=True,actual_mim_devices=11,actual_mim_masks_exact=True,point_changes=changes,all946points_match_original_native_clusters_and_physical_components=True,qualified_pex=False,output_gds_sha256=sha(wire/'native05/wires.gds'))
    (OUT/'native-binding.json').write_text(json.dumps(result,indent=2)+'\n')

def check_capture(text,anchors,binding):
    rows=parser.statements(text);assert rows[0][:2]==['.subckt','pump_wires']and rows[-1][0]=='.ends'
    points={x['label']:x for x in anchors['anchors']};assert len(rows[0][2:])==946 and set(rows[0][2:])==set(points)
    R=[];C=[];X=[]
    for r in rows[1:-1]:
        if r[0].startswith('R'):assert len(r)==4 and parser.number(r[3])>0;R.append(r)
        elif r[0].startswith('C'):assert len(r)==4 and parser.number(r[3])>=0;C.append(r)
        else:assert r[0].startswith('X')and len(r)==6 and r[3]=='cap_cmim';X.append(r)
    assert len({x[0]for x in rows[1:-1]})==len(rows)-2 and len(X)==11
    graph=parser.Union()
    for _,a,b,v in R:graph.join(a,b)
    owners={}
    for name,point in points.items():
        assert name in graph.parent,'Unattached physical point'
        root=graph.find(name);owners.setdefault(root,point['wire_component']);assert owners[root]==point['wire_component'],'Physical conductor short'
    assert len(owners)==len(set(owners.values()))==111
    assert all(graph.find(n)in owners for n in graph.parent)
    for _,a,b,v in C:assert all(n=='sub'or n in graph.parent for n in (a,b))
    native_rows={(r['device'],r['terminal']):r for r in anchors['rows']};expected={}
    for d in binding['devices']:
        if d['model']!='cap_cmim':continue
        plus=native_rows[d['native_id'],'mim_top']['wire_component'];minus=native_rows[d['native_id'],'mim_btm']['wire_component']
        key=(plus,minus,Decimal(d['native_parameters']['w']),Decimal(d['native_parameters']['l']));assert key not in expected;expected[key]=d['native_id']
    found={};devices=[]
    for x in X:
        assert all(n in graph.parent for n in x[1:3]);p=dict(v.split('=')for v in x[4:]);assert set(p)=={'w','l'}
        key=(owners[graph.find(x[1])],owners[graph.find(x[2])],parser.number(p['w'])/Decimal('1e-6'),parser.number(p['l'])/Decimal('1e-6'))
        assert key in expected and key not in found,'Wrong/duplicate native MIM geometry or terminal ownership';found[key]=x[0]
        devices.append(dict(native_id=expected[key],export=x,plus_component=key[0],minus_component=key[1]))
    assert set(found)==set(expected)
    return dict(status='PASS_CAPTURE_COMPONENTS_AND_ELEVEN_INTRINSIC_MIM_IDENTITIES_REQUIRES_RAW_RC_AUDIT',R=len(R),C=len(C),native_mim_devices=devices,physical_components=111,physical_points=946,raw_point_capacitance_audited=False,qualified_pex=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT;r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_phy_accepted=False,closed_loop=False,raw_rc_audit_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label):
        path=OUT/(label+'.log')
        with path.open('w')as log:rc=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(path)));save()
        if rc:print(path.read_text(errors='replace')[-15000:],flush=True)
        assert rc==0,(label,rc)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-rc-pass-20261020.json').read_text());prior,proof=reports.restore_report('cdr-retime-trunks-v22-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',list(pin['outputs']))
        assert prior['status']==pin['status']and prior['sources_unchanged'];r['original_wire_source']=proof
        assert prior['source_head']==pin['source_head'] and prior['outputs']==pin['outputs']
        bp=json.loads((ROOT/'docs/evidence/cdr-retime-trunks-v22-binding-pass-20261020.json').read_text())
        bound,bproof=reports.restore_report('cdr-retime-trunks-v22-binding',bp['run'],bp['summary_sha256'],bp['parts_sha256'],OUT/'model-binding',['binding.json'])
        assert bound==bp['report'] and bound['sources_unchanged']
        assert bound['physical_source']['summary_sha256']==prior['physical_inputs']['summary_sha256']
        binding=json.loads((OUT/'model-binding/binding.json').read_text());assert binding==bound['binding']
        r['model_binding_source']=bproof

        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        run([app,'python',Path(__file__),'--generate'],'native-geometry-and-points');r['native_binding']=json.loads((OUT/'native-binding.json').read_text())
        pilot=json.loads((ROOT/'docs/evidence/cdr-mim-explicit-model-pilot-pass-20261018.json').read_text())['report'];patch=pilot['private_ngspice_tech']
        original=OUT/'source/magic-cloud/tech';private=OUT/'ngspice-mim-tech';shutil.copytree(original,private)
        path=private/'ihp-sg13g2-extract.tech';assert sha(path)==patch['original_sha256'];text=path.read_text()
        for line in patch['removed_cdl_device_estimate_lines']:assert text.count(line)==1;text=text.replace(line,'')
        path.write_text(text);assert sha(path)==patch['private_sha256']
        assert all(sha(private/p.name)==sha(p)for p in original.iterdir()if p.is_file()and p.name!='ihp-sg13g2-extract.tech');r['private_tech']=patch
        meta=json.loads((ROOT/'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']['run-rc01.py'];text=meta['text'];assert hashlib.sha256(text.encode()).hexdigest()==meta['sha256']
        edits=[]
        for a,b in [("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B.parent/'source/magic-cloud/runtime/lib'"),("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B.parent/'ngspice-mim-tech'"),('(2*1024**3,)*2','(4*1024**3,)*2'),('size>80*1024**2','size>1024*1024**2'),('OWNED_SCRATCH_80MIB_LIMIT','OWNED_SCRATCH_1024MIB_LIMIT')]:
            assert text.count(a)==1;text=text.replace(a,b);edits.append(dict(before=a,after=b))
        method=OUT/'wire/run-rc01.py';method.write_text(text);r['method']=dict(original_sha256=meta['sha256'],adapted_sha256=sha(method),edits=edits);save()
        run([sys.executable,method],'native-mim-aware-rc');capture=json.loads((OUT/'wire/rc03/result.json').read_text());r['capture']=capture;save()
        assert capture['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'and capture['returncode']==0
        anchors=json.loads((OUT/'wire/anchors08.json').read_text());text=(OUT/'wire/rc03/wires.spice').read_text()
        r['intrinsic_capture_binding']=check_capture(text,anchors,binding)
        base=parser.statements((OUT/'wire/rc03/baseline.spice').read_text());assert len([x for x in base if x[0].startswith('X')])==11
        r['controls']=[];original_rows=parser.statements(text)
        for label in ('missing_mim','wrong_mim_width','swapped_mim_plates','wrong_mim_model','cross_wire_short'):
            changed=copy.deepcopy(original_rows);i=next(i for i,x in enumerate(changed)if x[0].startswith('X'))
            if label=='missing_mim':del changed[i]
            elif label=='wrong_mim_width':k=next(k for k,x in enumerate(changed[i])if x.startswith('w='));changed[i][k]='w=999u'
            elif label=='swapped_mim_plates':changed[i][1],changed[i][2]=changed[i][2],changed[i][1]
            elif label=='wrong_mim_model':changed[i][3]='cap_rfcmim'
            else:changed.insert(-1,['R_FAULT','P_dp','P_dn','1'])
            mutant='\n'.join(' '.join(x)for x in changed)+'\n'
            try:check_capture(mutant,anchors,binding)
            except (AssertionError,ValueError):r['controls'].append(dict(name=label,rejected=True,mutated_sha256=hashlib.sha256(mutant.encode()).hexdigest()))
            else:raise AssertionError('Accepted '+label)
        assert all(sha(OUT/'source'/n)==v for n,v in prior['outputs'].items());assert sha(method)==r['method']['adapted_sha256']and sha(path)==patch['private_sha256']
        r['sources_unchanged']=True;r['status']='PASS_PD484_MIM_AWARE_NATIVE_CAPTURE_AND_INTRINSIC_BINDING_REQUIRES_RAW_RC_AUDIT'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
