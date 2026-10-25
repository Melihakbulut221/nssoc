#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Narrow only28 actual parent signal routes; preserve native devices and landings."""
import copy,json,re,sys
from pathlib import Path
import pya
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
def generate(out):
    source=out/'source/layout'
    old=json.loads((source/'result.json').read_text())
    name=next(n for n in old['outputs']if n.endswith('.gds'))
    path=source/name;assert sha(path)==old['outputs'][name]
    A=pya.Layout();A.read(str(path));B=pya.Layout();B.read(str(path))
    assert A.dbu==B.dbu==.001 and len(A.top_cells())==len(B.top_cells())==1
    top=A.top_cell();target=B.top_cell();assert top.name==target.name
    assert old['total_devices']==1674 and len(old['signal_routes'])==60
    dx,dy=old['origin_translation_um'];selected=[r for r in old['signal_routes']if not r['net'].startswith('p16_')]
    assert len(selected)==28 and {r['endpoints'][1].split('.')[0]for r in selected}=={'f','a','b',*[f'p4_{i}'for i in range(4)]}
    def rect(x1,y1,x2,y2):
        return pya.Region(pya.DBox(x1+dx,y1+dy,x2+dx,y2+dy).to_itype(.001))
    oldmask={126:pya.Region(),134:pya.Region()};newmask={126:pya.Region(),134:pya.Region()}
    for r in selected:
        assert r['width_um']==4
        x=r['x_um'];ys=r['y_um'];oldmask[126]+=rect(x-2,min(ys)-2,x+2,max(ys)+2)
        newmask[126]+=rect(x-1.0,min(ys)-1.0,x+1.0,max(ys)+1.0)
        for end,y in zip(r['endpoints'],ys,strict=True):
            tag,port=end.split('.');bb=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',old['placements'][tag]['ports'][port])))
            assert len(bb)==4;px=(bb[0]+bb[2])/2
            assert abs((bb[1]+bb[3])/2-y)<1e-7
            oldmask[134]+=rect(min(px,x)-2,y-2,max(px,x)+2,y+2)
            newmask[134]+=rect(min(px,x)-1.0,y-1.0,max(px,x)+1.0,y+1.0)
            # Original4um square at both ends and each original via remains.
            for xx in (px,x):newmask[134]+=rect(xx-2,y-2,xx+2,y+2)
            newmask[126]+=rect(x-2,y-2,x+2,y+2)
    expected={};removed={};before={}
    for layer in (126,134):
        idx=A.layer(layer,0);original=pya.Region(top.shapes(idx)).merged()
        assert (oldmask[layer]-original).is_empty(),'Declared original route missing from actual GDS'
        assert (newmask[layer]-oldmask[layer]).is_empty(),'Unexpected added metal'
        cut=(oldmask[layer]-newmask[layer]).merged();assert not cut.is_empty()
        before[layer]=original;removed[layer]=cut;expected[layer]=(original-cut).merged()
        assert expected[layer].area()<original.area()
        target.shapes(B.layer(layer,0)).clear();target.shapes(B.layer(layer,0)).insert(expected[layer])
    def instances(L,c):
        return sorted((L.cell(i.cell_index).name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in c.each_inst())
    cells={c.name:c for c in A.each_cell()}
    def verify(L):
        assert L.dbu==A.dbu and L.top_cell().name==top.name
        actual={c.name:c for c in L.each_cell()};assert set(actual)==set(cells)
        infos={(A.get_info(i).layer,A.get_info(i).datatype)for i in A.layer_indexes()}|{(L.get_info(i).layer,L.get_info(i).datatype)for i in L.layer_indexes()}
        for name,ca in cells.items():
            cb=actual[name];assert instances(A,ca)==instances(L,cb),('Changed instance placement',name)
            for layer,dt in infos:
                ia=A.layer(layer,dt);ib=L.layer(layer,dt)
                if dt==0:
                    want=expected[layer]if name==top.name and layer in expected else pya.Region(ca.shapes(ia)).merged()
                    got=pya.Region(cb.shapes(ib)).merged()
                    assert (want^got).is_empty(),('Unplanned drawing change',name,layer)
                else:
                    assert sorted(str(s)for s in ca.shapes(ia).each())==sorted(str(s)for s in cb.shapes(ib).each()),('Label/pin changed',name,layer,dt)
        assert L.top_cell().bbox()==top.bbox()
    verify(B)
    dest=out/'layout';dest.mkdir();B.write(str(dest/name))
    C=pya.Layout();C.read(str(dest/name));verify(C)
    for filename in old['outputs']:
        if filename.endswith(('.lef','.cir')):(dest/filename).write_bytes((source/filename).read_bytes())
    metadata=copy.deepcopy(old)
    for r in metadata['signal_routes']:
        if not r['net'].startswith('p16_'):r['width_um']=2.0;r['landing_width_um']=4.
    metadata.update(status='GENERATED_UNVERIFIED_28_PARENT_FAST_DATA_ROUTES_2P0UM',
        inputs={str(p):sha(p)for p in (Path(__file__),path,source/'result.json')},
        outputs={p.name:sha(p)for p in dest.iterdir()},
        scope='Only28 parent fast data trunks/stubs narrowed4to2.0um with original4um end landings. Native devices, vias, macro positions, clock connections, supply routes, public ports and schematic unchanged. Fresh native DRC/LVS/RC/fullwaves required.')
    (dest/'result.json').write_text(json.dumps(metadata,indent=2)+'\n')
    faults=[];faultdir=out/'geometry-faults';faultdir.mkdir()
    def rejected(label,L):
        f=faultdir/(label+'.gds');L.write(str(f))
        try:verify(L)
        except AssertionError:faults.append(dict(name=label,rejected=True,gds_sha256=sha(f)))
        else:raise AssertionError('Geometry control accepted '+label)
    # Real changes to geometry, not assertions on a manufactured pass flag.
    li=B.layer(126,0);saved=pya.Region(target.shapes(li))
    poly=next(removed[126].each());target.shapes(li).insert(poly)
    rejected('restore_removed_wide_metal',B);target.shapes(li).clear();target.shapes(li).insert(saved)
    x1,y1,x2,y2=selected[0]['fault_cut_um'];cut=pya.Region(pya.DBox(x1,y1,x2,y2).to_itype(.001))
    assert not (saved&cut).is_empty()
    target.shapes(li).clear();target.shapes(li).insert(saved-cut)
    rejected('cut_actual_narrow_trunk',B);target.shapes(li).clear();target.shapes(li).insert(saved)
    victim=next(c for c in B.each_cell()if c.name!=target.name and any(B.get_info(i).datatype==0 and not c.shapes(i).is_empty()for i in B.layer_indexes()))
    vi=next(i for i in B.layer_indexes()if B.get_info(i).datatype==0 and not victim.shapes(i).is_empty())
    original=pya.Region(victim.shapes(vi));victim.shapes(vi).clear()
    rejected('change_native_child_geometry',B);victim.shapes(vi).insert(original);verify(B)
    result=dict(status='PASS_EXACT28_PARENT_SIGNAL_WIDTHS_NATIVE_DEVICES_VIAS_PORTS_AND_THREE_FAULTS',
        source_gds_sha256=sha(path),candidate_gds_sha256=sha(dest/name),changed_routes=[r['net']for r in selected],
        widths_um=dict(original=4.,candidate=2.0,retained_landings=4.),
        removed_area_um2={str(k):v.area()*1e-6 for k,v in removed.items()},
        original_vias_children_placements_pins_and_other_layers_equal=True,
        serialized_gds_verified=True,controls=faults,electrical_accepted=False,qualified_pex=False)
    (out/'geometry-delta.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':generate(Path(sys.argv[1]).resolve())
