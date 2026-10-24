#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind actual phase55 MIM drawings and outside-mask bottom reference planes."""
import copy,json,sys
from pathlib import Path
from collections import Counter
from run_cloud_tx_layout_repair import sha
TOP='nssoc_tx_phase_divider55_v1'
def generate(source,out):
    import pya
    source=Path(source);out=Path(out)
    gds=source/'source/layout'/(TOP+'.gds');dbpath=source/'source/flat_lvs/result.lvsdb'
    L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert L.dbu==.001 and T is not None
    native=pya.LayoutVsSchematic();native.read(str(dbpath));c=native.netlist().circuit_by_name(TOP)
    assert c is not None and c.pin_count()==9
    graph=json.loads((source/'native01/result.json').read_text())
    original=json.loads((source/'anchors.json').read_text());a=copy.deepcopy(original)
    rows={(r['device'],r['terminal']):r for r in a['rows']};labels={r['label']:r for r in a['anchors']}
    assert len(rows)==168 and len(labels)==126 and a['counts']['wire_components']==24
    caps={int(d.id()):d for d in c.each_device()if d.device_class().name=='cap_cmim'};assert len(caps)==4
    mask=pya.Region(T.begin_shapes_rec(L.layer(36,0))).merged()
    via=pya.Region(T.begin_shapes_rec(L.layer(129,0))).merged()
    assert not mask.is_empty()and not via.is_empty()
    leaves=[]
    def visit(cell,tr,ancestry):
        direct=pya.Region(cell.shapes(L.layer(36,0))).merged()
        if not direct.is_empty():
            assert not any(True for _ in cell.each_inst()),'MIM owning cell is not a direct PCell leaf'
            leaves.append(dict(cell=cell,transform=tr,path=ancestry,mask=direct.transformed(tr),
              via=pya.Region(cell.shapes(L.layer(129,0))).transformed(tr),
              bottom=pya.Region(cell.shapes(L.layer(67,0))).transformed(tr).merged()))
        for inst in cell.each_inst():
            assert not inst.is_regular_array(),'Unexpected array placement requires explicit native expansion'
            visit(inst.cell,tr*inst.cplx_trans,ancestry+[inst.cell.name])
    visit(T,pya.ICplxTrans(),[TOP]);assert len(leaves)==4
    masks=pya.Region();vias=pya.Region()
    for leaf in leaves:masks+=leaf['mask'];vias+=leaf['via']
    assert (masks^mask).is_empty()and(vias^via).is_empty(),'All intrinsic masks must equal actual four placed leaf drawings'
    wire=pya.LayoutToNetlist();wire.read(str(source/'native01/wires.l2n'))
    def probe(anchor,require_outside=True):
        point=pya.Point(*anchor['point_dbu']);m=anchor['metal']
        n=native.probe_net(native.layer_by_index(graph['native_layer_mapping'][str(m)]),point)
        w=wire.probe_net(wire.layer_by_name('gds_'+str(m)),point)
        assert n is not None and n.cluster_id==anchor['native_cluster'],'Native point ownership changed'
        assert w is not None and w.cluster_id==anchor['wire_component'],'Physical wire ownership changed'
        if require_outside and m==67:
            assert(pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))&mask).is_empty(),'Bottom reference lies on intrinsic MIM mask'
    changes=[];matched=[];used_points={(x['metal'],*x['point_dbu'])for x in a['anchors']}
    for did,d in sorted(caps.items()):
        top=rows[did,'mim_top'];bottom=rows[did,'mim_btm']
        tp=pya.Point(*top['point_dbu']);witness=pya.Region(pya.Box(tp.x-1,tp.y-1,tp.x+1,tp.y+1))
        candidates=[(i,l)for i,l in enumerate(leaves)if not(l['mask']&witness).is_empty()]
        assert len(candidates)==1,(did,'Unique actual MIM PCell');index,leaf=candidates[0];assert index not in matched;matched.append(index)
        params={p.name:d.parameter(p.id())for p in d.device_class().parameter_definitions()}
        assert set(params)=={'w','l','A','P','m'}and params['m']==1
        assert abs(params['A']-params['w']*params['l'])<1e-10 and abs(params['P']-2*(params['w']+params['l']))<1e-10
        polygons=list(leaf['mask'].merged().each());assert len(polygons)==1 and polygons[0].area()==polygons[0].bbox().area()
        box=polygons[0].bbox();assert sorted((box.width(),box.height()))==sorted((round(params['w']/L.dbu),round(params['l']/L.dbu))),'Native dimensions differ from placed MIM mask'
        anchor=labels[bottom['reference_label']];assert anchor['metal']==bottom['metal']==67
        old=anchor['point_dbu'];access=(leaf['bottom']-mask).merged()
        boxes=[p.bbox()for p in access.decompose_trapezoids_to_region().each()if p.area()==p.bbox().area()and min(p.bbox().width(),p.bbox().height())>20]
        assert boxes
        chosen=None
        for b in sorted(boxes,key=lambda b:(-b.area(),b.left,b.bottom)):
            point=b.center();trial=dict(anchor,point_dbu=[point.x,point.y])
            if (67,point.x,point.y)in used_points:continue
            probe(trial);chosen=trial;break
        assert chosen is not None and chosen['point_dbu']!=old
        used_points.remove((67,*old));used_points.add((67,*chosen['point_dbu']))
        anchor['point_dbu']=chosen['point_dbu'];bottom['point_dbu']=chosen['point_dbu']
        bottom['original_native_terminal_selection']=dict(selection=bottom['selection'],point_dbu=old,candidate_contacts=copy.deepcopy(bottom['candidate_contacts']))
        bottom['selection']='actual_placed_mim_bottom_Metal5_access_outside_intrinsic_mask'
        bottom['candidate_contacts']=[dict(metal=67,point_dbu=chosen['point_dbu'],kind=bottom['selection'])]
        changes.append(dict(native_id=did,reference_label=bottom['reference_label'],old_point_dbu=old,new_point_dbu=chosen['point_dbu'],
          native_cluster=bottom['native_cluster'],wire_component=bottom['wire_component'],native_parameters=params,
          actual_leaf_cell=leaf['cell'].name,actual_leaf_path=leaf['path'],actual_leaf_transform=str(leaf['transform']),
          actual_mask_bbox_dbu=str(box),actual_mask_area_dbu2=leaf['mask'].area(),actual_via_area_dbu2=leaf['via'].area()))
    assert len(matched)==len(set(matched))==4
    for anchor in a['anchors']:probe(anchor)
    assert len({(x['metal'],*x['point_dbu'])for x in a['anchors']})==126
    # All original terminal identity fields and non-MIM-bottom planes are exact.
    changed_ids={(r['native_id'],'mim_btm')for r in changes}
    for before,after in zip(original['rows'],a['rows'],strict=True):
        key=(before['device'],before['terminal'])
        if key not in changed_ids:assert before==after
        else:
            for name in ('device','model','terminal','native_cluster','disposition','reference_label','metal','wire_component'):assert before[name]==after[name]
    W=pya.Layout();W.read(str(source/'native01/wires.gds'));WT=W.top_cell();assert WT.name=='phase_divider55_wires'and W.dbu==L.dbu
    for layer in (8,10,30,50,67,126,134,19,29,49,66,125,133):
        assert(pya.Region(WT.begin_shapes_rec(W.layer(layer,0)))^pya.Region(T.begin_shapes_rec(L.layer(layer,0)))).is_empty()
    for layer,region in ((36,mask),(129,via)):
        assert pya.Region(WT.begin_shapes_rec(W.layer(layer,0))).is_empty();WT.shapes(W.layer(layer,0)).insert(region)
    controls=[]
    def reject(name,fn):
        try:fn()
        except AssertionError as e:controls.append(dict(name=name,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted MIM geometry/anchor fault '+name)
    def equal(actual,expected):assert(actual^expected).is_empty(),'Actual placed intrinsic drawing changed'
    reject('missing_mim_mask',lambda:equal(mask-leaves[0]['mask'],mask))
    reject('shifted_mim_mask',lambda:equal(mask.transformed(pya.Trans(1,0)),mask))
    reject('missing_mim_via',lambda:equal(via-leaves[0]['via'],via))
    original_bottom=next(r for r in original['rows']if r['model']=='cap_cmim'and r['terminal']=='mim_btm')
    wrong=dict(labels[original_bottom['reference_label']],point_dbu=original_bottom['point_dbu'])
    reject('bottom_reference_on_intrinsic_mask',lambda:probe(wrong))
    bottom=next(r for r in a['rows']if r['model']=='cap_cmim'and r['terminal']=='mim_btm')
    other=next(x for x in a['anchors']if x['metal']==67 and x['wire_component']!=bottom['wire_component'])
    reject('bottom_reference_on_foreign_conductor',lambda:probe(dict(labels[bottom['reference_label']],point_dbu=other['point_dbu'])))
    upper=rows[bottom['device'],'mim_top']
    reject('swapped_mim_plane_ownership',lambda:probe(dict(labels[bottom['reference_label']],native_cluster=upper['native_cluster'])))
    assert len(controls)==6 and all(x['rejected']for x in controls)
    target=out/'mim';target.mkdir();W.write(str(target/'wires.gds'))
    # Native reopen confirms serialization and preservation of every metal/via polygon.
    reopened=pya.Layout();reopened.read(str(target/'wires.gds'));rt=reopened.top_cell()
    for layer in (8,10,30,50,67,126,134,19,29,49,66,125,133,36,129):
        assert(pya.Region(rt.begin_shapes_rec(reopened.layer(layer,0)))^pya.Region(WT.begin_shapes_rec(W.layer(layer,0)))).is_empty()
    a['inputs']={str(p):sha(p)for p in [Path(__file__),gds,dbpath,source/'anchors.json',source/'native01/result.json',source/'native01/wires.l2n',target/'wires.gds']}
    a['mim_bottom_point_changes']=changes
    (target/'anchors.json').write_text(json.dumps(a,indent=2)+'\n')
    result=dict(status='PASS_ACTUAL_FOUR_MIM_DRAWINGS_AND_ALL126_NATIVE_PLANES_WITH_SIX_FAULTS_REQUIRES_RC',
      qualified_pex=False,electrical_accepted=False,deterministic_startup_verified=False,full_phy_accepted=False,
      actual_mim_devices=4,physical_points=126,wire_components=24,all_metal_via_drawings_unchanged=True,
      intrinsic_mask_union_exact=True,all_original_native_terminal_identities_unchanged=True,all126_native_and_physical_owners_verified=True,
      bottom_access_changes=changes,controls=controls,outputs={p.name:sha(p)for p in target.iterdir()if p.is_file()})
    (target/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':generate(sys.argv[1],sys.argv[2])
