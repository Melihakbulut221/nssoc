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
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-active-input-v57-parent-m4-review'
TOP='nssoc_cdr_pd500_active_input_v57'
def native():
    import pya
    OLD='nssoc_cdr_pd476_follower_v23';LEAF='nssoc_rx_sampler_active_input_layout_v57'
    O=pya.Layout();O.read(str(OUT/'old/layout'/(OLD+'.gds')));OT=O.cell(OLD)
    F=pya.Layout();F.read(str(OUT/'leaf/layout'/(LEAF+'.gds')));FT=F.cell(LEAF)
    L=pya.Layout();L.read(str(OUT/'source/layout'/(TOP+'.gds')));T=L.cell(TOP)
    assert O.dbu==F.dbu==L.dbu==.001
    oldall=pya.Region(OT.begin_shapes_rec(O.layer(50,0))).flatten().merged()
    oldroot=pya.Region(OT.shapes(O.layer(50,0))).flatten().merged()
    newroot=pya.Region(T.shapes(L.layer(50,0))).flatten().merged()
    assert(oldroot^newroot).is_empty()
    FD=pya.LayoutVsSchematic();FD.read(str(OUT/'leaf/physical/lvs/result.lvsdb'))
    fc=FD.netlist().top_circuit();full=pya.Region(FT.begin_shapes_rec(F.layer(50,0))).flatten().merged()
    inds=[i for i in FD.layer_indexes()if (FD.layer_by_index(i)^full).is_empty()]
    assert len(inds)==1;fl=FD.layer_by_index(inds[0])
    nets={p.name().lower():fc.net_for_pin(p.id())for p in fc.each_pin()}
    assert nets['avss'].cluster_id!=nets['sub'].cluster_id
    records=[]
    for inst in T.each_inst():
        if inst.cell.name!='pd_child_sampler_cd':continue
        oldinst=[i for i in OT.each_inst()if i.cell.name=='pd_child_sampler'and i.dcplx_trans==inst.dcplx_trans]
        assert len(oldinst)==1;oi=oldinst[0]
        oldchild=pya.Region(oi.cell.begin_shapes_rec(O.layer(50,0))).transformed(oi.cplx_trans).flatten().merged()
        newchild=full.transformed(inst.cplx_trans).merged()
        region=pya.Region(inst.bbox())
        for poly in oldroot.interacting(region).each():
            r=pya.Region(poly)
            oldtouch=oldchild.interacting(r);newtouch=newchild.interacting(r)
            oldvias={v:pya.Region(OT.begin_shapes_rec(O.layer(v,0))).flatten().merged().interacting(r)for v in(49,66)}
            rootvias={v:pya.Region(OT.shapes(O.layer(v,0))).flatten().merged().interacting(r)for v in(49,66)}
            root_attachments={}
            for via,othermetal in((49,30),(66,67)):
                vr=rootvias[via]
                parent_other=pya.Region(OT.shapes(O.layer(othermetal,0))).flatten().merged().interacting(vr)
                leaf_other=pya.Region(oi.cell.begin_shapes_rec(O.layer(othermetal,0))).transformed(oi.cplx_trans).flatten().merged().interacting(vr)
                root_attachments[str(via)]=dict(cuts=[str(q)for q in vr.each()],
                    other_root_metal=[str(q)for q in parent_other.each()],
                    other_child_metal=[str(q)for q in leaf_other.each()])

            supply={name:FD.shapes_of_net(nets[name],fl,True).transformed(inst.cplx_trans).interacting(r)for name in('avss','sub')}
            shifted=r.transformed(pya.Trans(320000,0))
            records.append(dict(transform=str(inst.dcplx_trans),polygon_dbu=str(poly),bbox_dbu=str(poly.bbox()),area_dbu2=poly.area(),
                old_child_touch_count=oldtouch.count(),old_child_overlap_area_dbu2=(oldchild&r).area(),
                new_child_touch_count=newtouch.count(),new_child_overlap_area_dbu2=(newchild&r).area(),
                old_via_counts={str(v):x.count()for v,x in oldvias.items()},
                root_via_counts={str(v):x.count()for v,x in rootvias.items()},root_via_attachments=root_attachments,
                old_via_overlap_areas={str(v):(x&r).area()for v,x in oldvias.items()},
                old_merged_component_count=oldall.interacting(r).count(),
                old_component_only_this_root=(oldall.interacting(r)^r).is_empty(),
                new_supply_touch_counts={name:x.count()for name,x in supply.items()},
                shifted_old_attachment_matches=((oldtouch.transformed(pya.Trans(320000,0)))^newchild.interacting(shifted)).is_empty(),
                shifted_new_touch_count=newchild.interacting(shifted).count()))
    assert records
    result=dict(status='COMPLETE_ACTUAL_ROOT_M4_OLD_NEW_ATTACHMENT_READBACK',records=records,geometry_edited=False,full_phy_accepted=False)
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='records'}),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT;r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-m3-detour-drc-pass-lvs-rejection-20261024.json').read_text())
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
        r['sources_unchanged']=True;r['status']='COMPLETE_ACTUAL500_ROOT_M4_ATTACHMENTS_NOT_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
