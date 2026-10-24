#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual failed LVS clusters without accepting or editing the geometry."""
import argparse,json,os,re,subprocess
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-active-input-v57-parent-short-review'
TOP='nssoc_cdr_pd500_active_input_v57'
def native():
    import pya
    metals=(8,10,30,50,67,126,134)
    def read(folder,top):
        L=pya.Layout();L.read(str(folder/'layout'/(top+'.gds')));T=L.cell(top)
        D=pya.LayoutVsSchematic();D.read(str(folder/'physical/lvs/result.lvsdb'))
        assert L.dbu==.001 and T is not None
        audit=json.loads((folder/'physical/lvs/audit.json').read_text())
        c=D.netlist().top_circuit()
        layers={}
        for metal in metals:
            full=pya.Region(T.begin_shapes_rec(L.layer(metal,0))).flatten().merged()
            candidates=[i for i in D.layer_indexes()if D.layer_by_index(i).bbox()==full.bbox()and D.layer_by_index(i).area()==full.area()and(D.layer_by_index(i)^full).is_empty()]
            assert len(candidates)==1,(top,metal,candidates)
            layers[metal]=D.layer_by_index(candidates[0])
        nets={p.name().lower():c.net_for_pin(p.id())for p in c.each_pin()}
        assert nets['avss'].cluster_id!=nets['sub'].cluster_id,(top,'Source already shorted')
        assert audit['status']=='PASS within comparison scope'
        return L,T,D,layers,nets
    oldL,oldT,oldD,oldlayers,oldnets=read(OUT/'old','nssoc_cdr_pd476_follower_v23')
    leafL,leafT,leafD,leaflayers,leafnets=read(OUT/'leaf','nssoc_rx_sampler_active_input_layout_v57')
    L=pya.Layout();L.read(str(OUT/'source/layout'/(TOP+'.gds')));T=L.cell(TOP)
    assert len(list(T.each_inst()))==16
    replacements=[i for i in T.each_inst()if i.cell.name=='pd_child_sampler_cd'];assert len(replacements)==2
    source_meta=json.loads((OUT/'source/layout/result.json').read_text())
    collisions=[];coverage=[]
    for metal in metals:
        direct=pya.Region(T.shapes(L.layer(metal,0))).flatten().merged()
        olddirect=pya.Region(oldT.shapes(oldL.layer(metal,0))).flatten().merged()
        for oldnet,newnet in [('avss','sub'),('sub','avss')]:
            oldpiece=oldD.shapes_of_net(oldnets[oldnet],oldlayers[metal],True)
            root=direct & olddirect & oldpiece
            leaf=leafD.shapes_of_net(leafnets[newnet],leaflayers[metal],True)
            for inst in replacements:
                placed=leaf.transformed(inst.cplx_trans)
                overlap=(root & placed).merged()
                coverage.append(dict(metal=metal,old_parent_net=oldnet,new_leaf_net=newnet,transform=str(inst.dcplx_trans),old_root_area_dbu2=root.area(),new_leaf_area_dbu2=placed.area(),overlap_area_dbu2=overlap.area()))
                if not overlap.is_empty():
                    collisions.append(dict(metal=metal,old_parent_net=oldnet,new_leaf_net=newnet,transform=str(inst.dcplx_trans),
                        intersections=[dict(polygon_dbu=str(p),bbox_dbu=str(p.bbox()),area_dbu2=p.area())for p in overlap.each()],
                        parent_components=[str(p)for p in root.interacting(overlap).each()],
                        leaf_components=[str(p)for p in placed.interacting(overlap).each()]))
    result=dict(status='COMPLETE_NATIVE_OLD_PARENT_VS_NEW_LEAF_SUPPLY_COLLISION_READBACK',
                collisions=collisions,coverage=coverage,geometry_edited=False,physical_accepted=False,
                old_avss_and_sub_separate=True,leaf_avss_and_sub_separate=True,
                gds_sha256={name:sha(OUT/name/'layout'/(top+'.gds'))for name,top in [('old','nssoc_cdr_pd476_follower_v23'),('leaf','nssoc_rx_sampler_active_input_layout_v57'),('source',TOP)]})
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(collisions=[{k:v for k,v in r.items()if k not in ('parent_components','leaf_components')}for r in collisions]),indent=2),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT;r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-drc-pass-lvs-rejection-20261024.json').read_text())
        selected=['layout/result.json','layout/schematic.cir','layout/'+TOP+'.gds',*['physical/lvs/'+n for n in ('result.lvsdb','extracted.cir','deck.log','run.log','audit.json')]]
        prior,proof=reports.restore_report('cdr-sampler-active-input-v57-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report']and prior['source_head']==pin['source_head'];r['original_source']=proof
        assert prior['physical']['steps']['drc']['measurement']['markers']==0 and prior['physical']['steps']['drc']['measurement']['category_count']==560
        for dirname,path,group,top in [
            ('old','cdr-sampler-settling-v32-parent-physical-pass-20261022.json','cdr-sampler-settling-v32-parent','nssoc_cdr_pd476_follower_v23'),
            ('leaf','cdr-sampler-active-input-v57-physical-pass-20261024.json','cdr-sampler-active-input-v57-physical','nssoc_rx_sampler_active_input_layout_v57')]:
            pin2=json.loads((ROOT/'docs/evidence'/path).read_text())
            selected2=['layout/'+top+'.gds','physical/lvs/result.lvsdb','physical/lvs/audit.json']
            loaded2,proof2=reports.restore_report(group,pin2['run'],pin2['summary_sha256'],pin2['parts_sha256'],OUT/dirname,selected2)
            assert loaded2['source_head']==pin2['source_head']and loaded2['sources_unchanged']
            assert all(sha(OUT/dirname/n)==loaded2['outputs'][n]for n in selected2)
            r[dirname+'_source']=proof2
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with (OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=rc
        if rc:print((OUT/'native.log').read_text()[-16000:],flush=True)
        assert rc==0;r['native']=json.loads((OUT/'native.json').read_text())
        r['native_extracted_reference']=(OUT/'source/physical/lvs/extracted.cir').read_text();r['schematic_reference']=(OUT/'source/layout/schematic.cir').read_text()
        r['deck_log']=(OUT/'source/physical/lvs/deck.log').read_text()
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_ACTUAL500_NATIVE_SUPPLY_COLLISION_DIAGNOSIS_NOT_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
