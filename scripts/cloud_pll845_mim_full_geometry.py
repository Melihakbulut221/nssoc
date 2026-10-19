#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the entire actual PLL845 metal graph and all26 intrinsic MIM masks.

This is the geometry/reference-plane input to whole-parent extraction.
It is not a capacitor-window proxy or accepted distributed/electrical model.
"""
import argparse,copy,hashlib,json,os,subprocess
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll845-mim-full-geometry'
TOP='nssoc_pll845_divider3p2_c8_v2_development'
GDS_SHA='79b2f5869f620cb5d6ce57756bab18f6ef10743aee953fb9c140202a6b225cdc'
METALS=(8,10,30,50,67,126,134)
VIAS=(19,29,49,66,125,133)

def generate():
    import pya
    P=OUT/'parent';G=P/'integrated'/(TOP+'.gds');D=P/'physical/lvs_flat/result.lvsdb'
    assert sha(G)==GDS_SHA
    L=pya.Layout();L.read(str(G));T=L.cell(TOP);assert T is not None and L.dbu==.001
    native=pya.LayoutVsSchematic();native.read(str(D));c=native.netlist().top_circuit()
    assert c.name==TOP and c.pin_count()==17 and len(list(c.each_device()))==845
    geo=json.loads((OUT/'wire/native05/result.json').read_text())
    wire=pya.LayoutToNetlist();wire.read(str(OUT/'wire/native05/wires.l2n'))
    regions={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in METALS+VIAS+(36,129)}
    mapping={int(k):v for k,v in geo['native_layer_mapping'].items()}
    caps=[];terminal_inventory=[]
    for dev in c.each_device():
        cls=dev.device_class();terms=[];cap_box=pya.Box()
        for td in cls.terminal_definitions():
            pieces=native.shapes_of_terminal(dev.terminal_ref(td.id()));assert pieces
            net=dev.net_for_terminal(td.id());box=pya.Box()
            for r in pieces.values():box+=r.bbox()
            terms.append(dict(terminal=td.name,native_cluster=net.cluster_id,native_net=net.name,
                bbox_dbu=[box.left,box.bottom,box.right,box.top],
                layers=[dict(layer=i,area_dbu2=r.area(),polygons=r.count())for i,r in pieces.items()]))
            if cls.name=='cap_cmim':cap_box+=box
        row=dict(native_id=dev.id(),model=cls.name,parameters={p.name:dev.parameter(p.id())for p in cls.parameter_definitions()},terminals=terms)
        terminal_inventory.append(row)
        if cls.name=='cap_cmim':
            assert {t['terminal']for t in terms}=={'mim_top','mim_btm'}
            row['terminal_enclosure_dbu']=[cap_box.left,cap_box.bottom,cap_box.right,cap_box.top];caps.append(row)
    assert len(caps)==26 and len(terminal_inventory)==845
    masks=regions[36];assert masks.count()==26 and not regions[129].is_empty()
    def bind_masks(mask_region):
        assert mask_region.count()==26,'Missing or merged actual MIM mask'
        polygons=list(mask_region.each());used=set();rows=[]
        for cap in caps:
            box=pya.Box(*cap['terminal_enclosure_dbu'])
            candidates=[(i,p)for i,p in enumerate(polygons)if (pya.Region(p)-pya.Region(box)).is_empty()]
            assert len(candidates)==1,('MIM mask does not bind uniquely to native device',cap['native_id'],str(box),len(candidates))
            i,p=candidates[0];assert i not in used;used.add(i);b=p.bbox()
            assert(pya.Region(p)^pya.Region(b)).is_empty(),'Intrinsic MIM mask is not rectangular'
            actual=sorted([b.width()*L.dbu,b.height()*L.dbu])
            expected=sorted([cap['parameters']['w'],cap['parameters']['l']])
            assert all(abs(x-y)<1e-9 for x,y in zip(actual,expected)),('Native MIM dimensions differ',cap['native_id'],actual,expected)
            points=[];window=pya.Region(b.enlarged(1000))
            for name,metal in [('mim_top',126),('mim_btm',67)]:
                term=next(t for t in cap['terminals']if t['terminal']==name)
                net=next(n for n in c.each_net()if n.cluster_id==term['native_cluster'])
                area=(regions[metal]&window&native.shapes_of_net(net,native.layer_by_index(mapping[metal]),True)).merged()
                area=(area&pya.Region(p))if name=='mim_top'else(area-mask_region)
                boxes=[p.bbox()for p in area.decompose_trapezoids_to_region().each()if p.area()==p.bbox().area()and p.bbox().width()>20 and p.bbox().height()>20]
                assert boxes,('No actual native metal access outside intrinsic mask',cap['native_id'],name)
                q=max(boxes,key=lambda b:b.area()).center()
                witness=pya.Region(pya.Box(q.x-1,q.y-1,q.x+1,q.y+1))
                assert(witness-area).is_empty()
                wn=wire.probe_net(wire.layer_by_name('gds_'+str(metal)),q)
                nn=native.probe_net(native.layer_by_index(mapping[metal]),q)
                assert wn is not None and nn is not None and nn.cluster_id==term['native_cluster']
                owner=next(r for r in geo['wire_components']if r['component']==wn.cluster_id)
                assert owner['native_cluster']==nn.cluster_id
                points.append(dict(label='T'+str(cap['native_id'])+'_'+name,terminal=name,metal=metal,point_dbu=[q.x,q.y],wire_component=wn.cluster_id,native_cluster=nn.cluster_id))
            assert points[0]['wire_component']!=points[1]['wire_component'],'MIM plates physically shorted'
            rows.append(dict(native_id=cap['native_id'],mask_bbox_dbu=[b.left,b.bottom,b.right,b.top],parameters=cap['parameters'],points=points))
        assert len(used)==26
        return rows
    bound=bind_masks(masks)
    def validate_points(rows):
        assert len(rows)==26 and {r['native_id']for r in rows}=={r['native_id']for r in bound}
        for row in rows:
            original=next(r for r in bound if r['native_id']==row['native_id'])
            assert row['parameters']==original['parameters']and row['mask_bbox_dbu']==original['mask_bbox_dbu']
            assert len(row['points'])==2 and {p['terminal']for p in row['points']}=={'mim_top','mim_btm'}
            for p in row['points']:
                expected=next(x for x in original['points']if x['terminal']==p['terminal'])
                assert p['metal']==expected['metal']and p['native_cluster']==expected['native_cluster']and p['wire_component']==expected['wire_component']
                point=pya.Point(*p['point_dbu']);wn=wire.probe_net(wire.layer_by_name('gds_'+str(p['metal'])),point)
                nn=native.probe_net(native.layer_by_index(mapping[p['metal']]),point)
                assert wn is not None and nn is not None and wn.cluster_id==p['wire_component']and nn.cluster_id==p['native_cluster']
                if p['terminal']=='mim_btm':assert(pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))&masks).is_empty()
    validate_points(bound);faults=[]
    for label in ['missing_actual_mim_mask','wrong_actual_mim_dimension','swapped_plate_owner','off_geometry_plate_point','missing_mim_identity']:
        try:
            if label=='missing_actual_mim_mask':
                changed=pya.Region()
                for p in list(masks.each())[1:]:changed.insert(p)
                bind_masks(changed)
            elif label=='wrong_actual_mim_dimension':
                changed=pya.Region();parts=list(masks.each());b=parts[0].bbox()
                changed.insert(pya.Box(b.left+5,b.bottom,b.right,b.top))
                for p in parts[1:]:changed.insert(p)
                bind_masks(changed)
            else:
                changed=copy.deepcopy(bound)
                if label=='swapped_plate_owner':
                    a,b=changed[0]['points'];a['native_cluster'],b['native_cluster']=b['native_cluster'],a['native_cluster']
                elif label=='off_geometry_plate_point':
                    changed[0]['points'][0]['point_dbu']=[T.bbox().right+10000,T.bbox().top+10000]
                else:changed.pop()
                validate_points(changed)
        except (AssertionError,StopIteration)as error:faults.append(dict(name=label,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted actual MIM geometry/identity fault '+label)
    W=pya.Layout();W.read(str(OUT/'wire/native05/wires.gds'));WT=W.top_cell()
    assert WT.name=='pump_wires'
    for m in METALS+VIAS:assert(pya.Region(WT.begin_shapes_rec(W.layer(m,0)))^regions[m]).is_empty()
    for m in (36,129):
        assert pya.Region(WT.begin_shapes_rec(W.layer(m,0))).is_empty()
        WT.shapes(W.layer(m,0)).insert(regions[m])
    target=OUT/'wire/whole-pll-mim-masks.gds';W.write(str(target))
    read=pya.Layout();read.read(str(target))
    for m in METALS+VIAS+(36,129):assert(pya.Region(read.top_cell().begin_shapes_rec(read.layer(m,0)))^regions[m]).is_empty()
    result=dict(status='PASS_WHOLE_PLL845_METAL_GRAPH_AND_ALL26_NATIVE_MIM_MASK_PLANES_REQUIRES_WHOLE_RC',
        source_gds_sha256=sha(G),output_gds_sha256=sha(target),native_devices=845,native_mim_devices=26,
        public_ports=17,wire_components=geo['wire_component_count'],native_terminal_count=geo['native_terminal_count'],
        all_parent_and_child_metal_via_polygons_preserved=True,all26_mim_masks_preserved=True,
        native_mim_bindings=bound,controls=faults,device_terminal_inventory=terminal_inventory,
        full_intrinsic_terminal_anchors_bound=False,wire_rc_extracted=False,qualified_pex=False,
        closed_loop_electrical_accepted=False,scope='Complete physical parent geometry, not clipped windows.52MIM plate references bound; all remaining device-terminal reference planes and fresh distributed RC still required.')
    (OUT/'native-mim-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['status','native_devices','native_mim_devices','wire_components','native_terminal_count']}))

def main():
    p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.generate:generate();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(Path(__file__)),full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label):
        path=OUT/(label+'.log')
        with path.open('w')as log:rc=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(path)));save()
        if rc:print(path.read_text(errors='replace')[-15000:],flush=True)
        assert rc==0,(label,rc)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/pll-c8-v2-parent-pass-20261017.json').read_text())
        names=['integrated/'+TOP+'.gds','integrated/result.json','physical/lvs_flat/result.lvsdb','physical/lvs_flat/audit.json','physical/lvs_flat/extracted.cir']
        prior,proof=reports.restore_report('pll-c8-v2-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',names)
        assert prior['source_head']==pin['source_head']and prior['status']==pin['status']
        assert prior['physical']['status']=='PASS_ACTUAL845_FILTER_PARENT_NATIVE_DRC_LVS_AND_FAULTS_NOT_RC'
        r['physical_source']=proof
        methods=json.loads((ROOT/'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']
        original=methods['probe01.py'];text=original['text'];assert hashlib.sha256(text.encode()).hexdigest()==original['sha256']
        changes=[]
        def replace(a,b):
            nonlocal text
            count=text.count(a);assert count>=1,(a,count);text=text.replace(a,b);changes.append(dict(before=a,after=b,count=count))
        replace("/'layout91/","/'parent/integrated/")
        replace("/'physical92/lvs/","/'parent/physical/lvs_flat/")
        replace('nssoc_tx_mux2_passive_topmetal_layout_v1',TOP)
        replace('c.pin_count()==12','c.pin_count()==17')
        replace("assert classes==dict(npn13G2=19,rppd=8,ptap1=27),classes","assert sum(classes.values())==845 and classes['cap_cmim']==26,classes\nimport sys\nsys.path.insert(0,str(R/'scripts'))\nimport build_pcie_local_vco_hybrid_v6 as parser\nexport=parser.statements((P/'parent/physical/lvs_flat/extracted.cir').read_text())\nassert export[0][:2]==['.SUBCKT','"+TOP+"'] and export[-1]==['.ENDS','"+TOP+"']\nknown={name.lower()for name in classes};observed=Counter()\nfor row in export[1:-1]:\n found=[token.lower()for token in row if token.lower()in known];assert len(found)==1,row\n observed[found[0]]+=1\nassert observed==Counter({k.lower():v for k,v in classes.items()}),observed")
        wire=OUT/'wire';wire.mkdir();method=wire/'probe01.py';method.write_text(text)
        r['method']=dict(baseline_sha256=original['sha256'],adapted_sha256=sha(method),edits=changes)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        r['runtime_sha256']=sha(app);save()
        run([app,'python',method],'whole-native-metal-graph')
        r['whole_wire_graph']=json.loads((wire/'native05/result.json').read_text());save()
        run([app,'python',Path(__file__),'--generate'],'whole26-mim-native-planes')
        r['geometry']=json.loads((OUT/'native-mim-geometry.json').read_text())
        assert all(sha(OUT/'parent'/n)==prior['outputs'][n]for n in names)and sha(method)==r['method']['adapted_sha256']
        assert sha(Path(__file__))==r['controller_sha256']
        r['sources_unchanged']=True;r['status']='PASS_PLL845_WHOLE_GEOMETRY_AND26_MIM_PLANES_REQUIRES_COMPLETE_TERMINAL_RC'
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
