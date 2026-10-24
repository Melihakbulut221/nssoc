#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reorder complete v16 physical bands; rebuild only actual global TM1 trunks."""
import argparse,copy,itertools,json,re,sys
from pathlib import Path
from run_cloud_tx_layout_repair import sha
TOP='nssoc_cdr_pd484_localbus_v12'
ROOT=Path(__file__).resolve().parents[1]
PREFIX=('bd','sb','sa','sd','sc','ac')
TARGET=('aqp','aqn','bqp','bqn','cup','cun','dup','dun')
def generate(out):
    import pya
    source=out/'baseline/layout';dest=out/'layout';dest.mkdir()
    old=json.loads((source/'result.json').read_text())
    L=pya.Layout();L.read(str(source/(TOP+'.gds')));T=L.cell(TOP)
    assert T is not None and L.dbu==.001
    def box(s):
        v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)))
        assert len(v)==4
        return pya.DBox(*v)
    def region(rect):return pya.Region(rect.to_itype(L.dbu))
    def geometries(layout,cell):
        return {(layout.get_info(i).layer,layout.get_info(i).datatype):pya.Region(cell.begin_shapes_rec(i)).flatten().merged() for i in layout.layer_indexes()}
    before=geometries(L,T);bounds=T.dbbox()
    placements=old['placements'];tags=sorted(placements,key=lambda t:box(placements[t]['bbox_um']).bottom)
    assert len(tags)==16 and tuple(tags[:6])==PREFIX
    assert sum(old['primitive_census'].values())==484
    edges=[224.]+[box(placements[t]['bbox_um']).bottom-48 for t in tags[1:]]+[bounds.top]
    assert all(abs(round(y/.005)*.005-y)<1e-7 for y in edges)
    bands={t:(edges[i],edges[i+1])for i,t in enumerate(tags)}
    assert all(bands[t][0]<=box(placements[t]['bbox_um']).bottom and box(placements[t]['bbox_um']).top<=bands[t][1]for t in tags)
    public={n:box(s) for n,s in old['ports'].items()}
    supplies={'avdd','avss','sub'}
    def owner(y):
        hit=[t for t,(lo,hi)in bands.items()if lo<=y<hi]
        assert len(hit)==1,(y,hit)
        return hit[0]
    def offsets(order):
        cursor=edges[0];result={}
        for tag in order:
            low,high=bands[tag];result[tag]=round((cursor-low)*1000);cursor+=high-low
        assert abs(cursor-bounds.top)<1e-6
        return result
    def spans(shifts):
        result={n:[]for n in old['source_plan']['nets']}
        for r in old['routes']:result[r['net']].append(box(r['box_um']).center().y+shifts[r['tag']]/1000)
        return {n:max(v)-min(v)for n,v in result.items()}
    zero={t:0 for t in tags};baseline=spans(zero)
    assert set(TARGET)<=set(baseline)
    def weighted(s):
        return sum(v*(8 if n in TARGET else 0 if n in supplies else 2 if n in ('cp','cn','dp','dn')else 1)for n,v in s.items())
    # Enumerate all six-macro permutations, with explicit limits on input/clock
    # geometry. These are planning constraints, never electrical acceptance.
    max_extra=max(bands[t][1]-bands[t][0]for t in ('ac','bd'))
    evaluated=[];eligible=[]
    for perm in itertools.permutations(PREFIX):
        order=list(perm)+tags[6:];delta=offsets(order);s=spans(delta)
        valid=all(s[n]<=baseline[n]+max_extra+1e-6 for n in ('cp','cn','dp','dn'))
        valid=valid and all(s[n]<=baseline[n]+1e-6 for n in ('dp','dn'))
        score=weighted(s);target=sum(s[n]for n in TARGET)
        row=dict(order=order,weighted_span=score,target_span_um=target,eligible=valid)
        evaluated.append(row)
        if valid:eligible.append((score,target,tuple(order),delta,s))
    (out/'placement-planning.json').write_text(json.dumps(dict(original_order=tags,original_spans_um=baseline,evaluated=evaluated),indent=2)+'\n')
    assert len(evaluated)==720 and eligible
    score,target,order,delta,selected=min(eligible,key=lambda r:r[:3])
    assert order!=tuple(tags) and target<sum(baseline[n]for n in TARGET)-1e-6
    assert score<weighted(baseline)-1e-6
    # Preserve actual child hierarchy: extraction must still see native PCells.
    child_instances=[];child_regions={}
    for inst in T.each_inst():
        if not inst.cell.name.startswith('pd_child_'):continue
        tr=inst.dcplx_trans
        assert tr.mag==1 and tr.angle==0 and not tr.is_mirror()
        b=inst.dbbox()
        found=[t for t in tags if box(placements[t]['bbox_um'])==b and inst.cell.name=='pd_child_'+placements[t]['kind']]
        assert len(found)==1
        tag=found[0];child_instances.append((tag,inst.cell_index,tr.disp.x,tr.disp.y))
        for k,r in geometries(L,inst.cell).items():
            moved=r.transformed(pya.Trans(round(tr.disp.x*1000),round(tr.disp.y*1000)))
            child_regions[k]=(child_regions.get(k,pya.Region())+moved).merged()
    assert len(child_instances)==16 and len({t for t,_,_,_ in child_instances})==16
    parent={k:(r-child_regions.get(k,pya.Region())).merged()for k,r in before.items()}
    assert all(k[0]in (8,10,19,29,30,49,50,66,67,125,126,133,134)and k[1]in (0,2,25)
        for k,r in parent.items()if not r.is_empty()),'Unexpected parent device geometry outside immutable children'
    buses={};cursor=8.
    for n in old['source_plan']['nets']:
        width=256. if n=='avss'else 64. if n in ('avdd','sub')else 3.2
        buses[n]=(cursor+width/2,width);cursor+=width+8
    assert abs(cursor+40-box(placements[tags[0]]['bbox_um']).left)<1e-6
    def public_after(n):
        b=public[n]
        dy=0 if n in supplies else delta[owner(b.center().y)]/1000
        return b.transformed(pya.DTrans(0.,dy))
    new_public={n:public_after(n)for n in public}
    def trunks(shifts,pins):
        result=pya.Region();rows=[]
        for n,(x,w)in buses.items():
            ys=[box(r['box_um']).center().y+shifts[r['tag']]/1000 for r in old['routes']if r['net']==n]
            if n in pins:ys.append(pins[n].center().y)
            ext=32 if n=='avss'else w/2
            b=pya.DBox(x-w/2,min(ys)-ext,x+w/2,max(ys)+ext)
            result+=region(b);rows.append(dict(net=n,box_um=str(b)))
        return result.merged(),rows
    old_bus,old_bus_rows=trunks(zero,public);new_bus,new_bus_rows=trunks(delta,new_public)
    assert (old_bus-parent[(126,0)]).is_empty(),'Original trunk is not present in actual parent geometry'
    parent[(126,0)]=(parent[(126,0)]-old_bus).merged()
    # Every remaining parent conductor is local to one physical band or the
    # unchanged supply entry region. Never slice a conductor crossing a boundary.
    for k,r in parent.items():
        for polygon in r.each():
            b=polygon.bbox()
            assert not any(b.bottom<round(y*1000)<b.top for y in edges[:-1]),('Conductor crosses movable band',k,str(b))
    fixed=region(pya.DBox(bounds.left-1,bounds.bottom-1,bounds.right+1,edges[0]))
    windows={t:region(pya.DBox(bounds.left-1,lo,bounds.right+1,hi)) for t,(lo,hi)in bands.items()}
    moved_parent={}
    for k,r in parent.items():
        conserved=(r&fixed).merged();result=conserved
        for tag,w in windows.items():
            piece=(r&w).merged();conserved=(conserved+piece).merged()
            result=(result+piece.transformed(pya.Trans(0,delta[tag]))).merged()
        assert (conserved^r).is_empty(),('Unaccounted parent geometry',k)
        moved_parent[k]=result
    moved_parent[(126,0)]=(moved_parent[(126,0)]+new_bus).merged()
    T.name=TOP+'_original_v16'
    top=L.create_cell(TOP);expected=dict(moved_parent)
    for tag,index,x,y in child_instances:
        dy=delta[tag]/1000
        top.insert(pya.DCellInstArray(index,pya.DTrans(x,y+dy)))
        for k,r in geometries(L,L.cell(index)).items():
            moved=r.transformed(pya.Trans(round(x*1000),round(y*1000)+delta[tag]))
            expected[k]=(expected.get(k,pya.Region())+moved).merged()
    for (layer,datatype),r in moved_parent.items():
        if not r.is_empty():top.shapes(L.layer(layer,datatype)).insert(r)
    for n,b in new_public.items():top.shapes(L.layer(134,25)).insert(pya.DText(n,b.center().x,b.center().y))
    opt=pya.SaveLayoutOptions();opt.select_cell(top.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
    check=pya.Layout();check.read(str(dest/(TOP+'.gds')))
    actual=geometries(check,check.cell(TOP));keys=set(actual)|set(expected)
    def equal(got):
        return all((got.get(k,pya.Region())^expected.get(k,pya.Region())).is_empty()for k in keys|set(got))
    assert equal(actual),'Serialized geometry differs from conserved physical bands and replaced trunks'
    # Geometry controls corrupt actual output regions. Native circuit/DRC
    # corruptions are separately executed by the original full physical checker.
    faults=[]
    bad=dict(actual);cut=region(box(new_bus_rows[0]['box_um']))
    bad[(126,0)]=actual[(126,0)]-cut
    assert not equal(bad);faults.append('remove_actual_rebuilt_trunk')
    bad=dict(actual);key=next(k for k,r in actual.items()if k[0]==5 and k[1]==0 and not r.is_empty())
    bad[key]=pya.Region()
    assert not equal(bad);faults.append('remove_actual_native_gate_geometry')
    assert check.cell(TOP).dbbox()==bounds
    (dest/'schematic.cir').write_bytes((source/'schematic.cir').read_bytes())
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    import make_pcie_clock_vco_v6_local_v1 as writer
    writer.TOP=TOP;writer.PORTS=old['source_plan']['ports']
    writer.use_direction=lambda n:('POWER','INOUT')if n=='avdd'else('GROUND','INOUT')if n in ('avss','sub')else('SIGNAL','OUTPUT'if n in ('xp','xn','yp','yn','vip','vin')else'INPUT')
    (dest/(TOP+'.lef')).write_text(writer.lef(pya,L.dbu,top.dbbox(),{n:('TopMetal2',b)for n,b in new_public.items()}))
    new_placements=copy.deepcopy(placements)
    for tag,p in new_placements.items():
        tr=pya.DTrans(0.,delta[tag]/1000);p['bbox_um']=str(box(p['bbox_um']).transformed(tr))
        p['ports']={n:str(box(s).transformed(tr))for n,s in p['ports'].items()}
    routes=copy.deepcopy(old['routes'])
    for r in routes:r['box_um']=str(box(r['box_um']).transformed(pya.DTrans(0.,delta[r['tag']]/1000)))
    proof=dict(status='GENERATED_V16_REORDERED_PHYSICAL_BANDS_REQUIRES_NATIVE_DRC_LVS_AND_FRESH_RC',
        source_gds_sha256=sha(source/(TOP+'.gds')),candidate_gds_sha256=sha(dest/(TOP+'.gds')),
        original_order=tags,candidate_order=order,translations_y_dbu=delta,
        band_edges_um=edges,original_spans_um=baseline,candidate_spans_um=selected,
        original_weighted_span=weighted(baseline),candidate_weighted_span=score,
        original_target_span_um=sum(baseline[n]for n in TARGET),candidate_target_span_um=target,
        planning_clock_extra_limit_um=max_extra,planning_data_input_extra_limit_um=0,
        enumerated=len(evaluated),eligible=len(eligible),evaluated=evaluated,
        original_trunks=old_bus_rows,candidate_trunks=new_bus_rows,
        original_child_hierarchy_preserved=True,all_parent_band_geometry_conserved=True,
        all_original_v13_v14_v15_v16_local_overlays_preserved=True,
        exact_serialized_geometry_checked=True,reference_byte_identical=True,controls=faults,
        scope='Only macro-band ordering, global TM1 trunk lengths and corresponding public pin coordinates change. No intrinsic device, local access geometry, load or electrical gate change. Native DRC/LVS and new full extraction/waveforms remain required.',
        accepted=False,full_phy_accepted=False)
    (out/'geometry-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    inputs={str(p):sha(p)for p in [Path(__file__),source/(TOP+'.gds'),source/'result.json',source/'schematic.cir',source/(TOP+'.lef'),ROOT/'hw/soc/flow/make_pcie_clock_vco_v6_local_v1.py']}
    data=dict(status=proof['status'],inputs=inputs,ports={n:str(b)for n,b in new_public.items()},
        bbox_um=str(top.dbbox()),placements=new_placements,routes=routes,
        primitive_census=old['primitive_census'],source_plan=old['source_plan'],
        native_reorder=proof,full_phy_accepted=False,qualified_pex=False,closed_loop=False,main_chip_integrated=False)
    data['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()}
    (dest/'result.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in proof.items()if k in ('status','original_order','candidate_order','original_target_span_um','candidate_target_span_um','original_spans_um','candidate_spans_um')}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.out.resolve())
