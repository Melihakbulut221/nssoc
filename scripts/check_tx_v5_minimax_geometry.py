#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent native placement/drawing check of the minimax tree candidate."""
import copy,hashlib,json,re,sys,tarfile
from pathlib import Path
import pya
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];source=Path(sys.argv[1])
pin=json.loads((ROOT/'docs/evidence/tx-v5-final-strap6-physical-pass-20261019.json').read_text())
assert pin['source_run']==39217390888 and pin['sha256']=='66b00b9660184ccdadc0223f5ebef22fa1b9edb4faedba5fdd9010631848e2a5'
baseline=source/'minimax-baseline';baseline.mkdir(exist_ok=False)
packed=baseline/'source.tar.gz';fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
with tarfile.open(packed)as tar:
    prefix='cloud-tx-v5-final-strap6-assembly/'
    raw=tar.extractfile(prefix+'result.json').read();assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256']
    prior=json.loads(raw);assert prior==pin['report']
    for name in prior['outputs']:
        if not name.startswith('layout/'):continue
        data=tar.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==prior['outputs'][name]
        (baseline/Path(name).name).write_bytes(data)
packed.unlink()
old=json.loads((baseline/'result.json').read_text());new=json.loads((source/'layout/result.json').read_text())
plan=json.loads((source/'plan.json').read_text())['data_route_plan']
assert plan['status']=='PLANNED_ALL60_LEG_MINIMAX_ROWS_AND_RAIL_AWARE_CHANNELS_NOT_PHYSICAL_OR_ELECTRICAL_ACCEPTANCE'
def box(raw):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)))
def eq(a,b):assert len(a)==len(b)and all(abs(x-y)<1e-7 for x,y in zip(a,b)),(a,b)
def shifted(raw,y):
    a,b,c,d=box(raw);return [a,b+y,c,d+y]
def load(folder,record):
    name=next(n for n in record['outputs']if n.endswith('.gds'));path=folder/name
    assert sha(path)==record['outputs'][name]
    L=pya.Layout();L.read(str(path));assert L.dbu==.001 and len(L.top_cells())==1
    return L,path
A,ap=load(baseline,old);B,bp=load(source/'layout',new)
def actual(L,r):
    dx,dy=r['origin_translation_um'];out=[]
    for i in L.top_cell().each_inst():
        cell=L.cell(i.cell_index)
        if not cell.name.startswith('core_'):continue
        assert not i.is_regular_array()
        bb=cell.dbbox().transformed(i.dcplx_trans)
        out.append((cell.name,[bb.left-dx,bb.bottom-dy,bb.right-dx,bb.top-dy],i.dcplx_trans.angle,i.dcplx_trans.is_mirror()))
    assert len(out)==31
    return out
oldactual=actual(A,old)
def find_actual(values,kind,target):
    matches=[v for v in values if v[0]=='core_'+kind and all(abs(a-b)<1e-7 for a,b in zip(v[1],target))]
    assert len(matches)==1,(kind,target,matches)
    return matches[0]
def verify(L,record):
    assert record['placement_pitch']==old['placement_pitch']==dict(column_um=700.,row_um=600.)
    assert record['total_devices']==old['total_devices']==1674
    assert record['frozen_child_drawing_regions_equal']
    assert set(record['placements'])==set(old['placements'])==set(plan['row_targets_um'])
    eq(record['origin_translation_um'],old['origin_translation_um'])
    native=actual(L,record);dy_by_tag={}
    for tag,p in record['placements'].items():
        o=old['placements'][tag];before=box(o['bbox_um']);delta=plan['row_targets_um'][tag]-before[1];dy_by_tag[tag]=delta
        assert plan['original_rows_um'][tag]==before[1]
        assert plan['row_lattice']['quantum_um']==600.
        assert plan['row_lattice']['original_residue_um'][tag]==before[1]%600.
        assert abs(delta/600.-round(delta/600.))<1e-9,('Macro left original row lattice',tag,delta)
        if tag.startswith('p16_')or tag=='f':assert delta==0 and tag in plan['fixed_rows_um']
        assert p['kind']==o['kind']and set(p['ports'])==set(o['ports'])
        expected=shifted(o['bbox_um'],delta);eq(box(p['bbox_um']),expected)
        for port,b in p['ports'].items():eq(box(b),shifted(o['ports'][port],delta))
        before_native=find_actual(oldactual,o['kind'],before);after_native=find_actual(native,p['kind'],expected)
        assert before_native[2:]==after_native[2:]
    for column in (0.,700.,1400.,2100.,2800.):
        tags=sorted((k for k,p in old['placements'].items()if box(p['bbox_um'])[0]==column),key=lambda k:box(old['placements'][k]['bbox_um'])[1])
        ys=[box(record['placements'][k]['bbox_um'])for k in tags]
        assert all(b[1]-a[1]>=600-1e-7 and b[1]-a[3]>=7.9 for a,b in zip(ys,ys[1:]))
    infos={(A.get_info(i).layer,A.get_info(i).datatype)for i in A.layer_indexes()}|{(L.get_info(i).layer,L.get_info(i).datatype)for i in L.layer_indexes()}
    for kind in ('pre','pre_low','final'):
        ca=A.cell('core_'+kind);cb=L.cell('core_'+kind);assert ca is not None and cb is not None
        for layer,dt in infos:
            if dt!=0:continue
            ra=pya.Region(ca.begin_shapes_rec(A.layer(layer,dt))).flatten().merged()
            rb=pya.Region(cb.begin_shapes_rec(L.layer(layer,dt))).flatten().merged()
            assert (ra^rb).is_empty(),('Native child drawing changed',kind,layer)
    assert len(record['signal_routes'])==60
    planned={r['net']:r for r in plan['routes']};dx,dy=record['origin_translation_um']
    tm1=pya.Region(L.top_cell().shapes(L.layer(126,0))).merged()
    tm2=pya.Region(L.top_cell().shapes(L.layer(134,0))).merged()
    def required(region,coords):
        rr=pya.Region(pya.DBox(*coords).to_itype(.001));assert (rr-region).is_empty(),('Missing native parent conductor',coords)
    for r,o in zip(record['signal_routes'],old['signal_routes'],strict=True):
        assert all(r[k]==o[k]for k in ('net','endpoints','width_um'))and r['width_um']==4
        parent=o['endpoints'][1].split('.')[0]
        yy=[v+dy_by_tag[end.split('.')[0]]for v,end in zip(o['y_um'],o['endpoints'],strict=True)]
        eq(r['y_um'],yy);x=plan['track_x_um'][r['net']];assert r['x_um']==x
        assert abs(r['centerline_length_um']-planned[r['net']]['after_um'])<1e-7
        required(tm1,[x-2+dx,min(yy)-2+dy,x+2+dx,max(yy)+2+dy])
        for end,y in zip(r['endpoints'],yy,strict=True):
            tag,port=end.split('.');b=box(record['placements'][tag]['ports'][port]);px=(b[0]+b[2])/2
            required(tm2,[min(px,x)-2+dx,y-2+dy,max(px,x)+2+dx,y+2+dy])
    for i,r in enumerate(record['signal_routes']):
        for q in record['signal_routes'][i+1:]:
            if abs(r['x_um']-q['x_um'])<8:
                assert max(min(r['y_um']),min(q['y_um']))-min(max(r['y_um']),max(q['y_um']))>=12-1e-7
    assert abs(record['parent_signal_centerline_sum_um']-sum(r['centerline_length_um']for r in record['signal_routes']))<1e-7
    assert abs(record['parent_signal_centerline_max_um']-plan['maximum_after_um'])<1e-7
    assert record['parent_signal_centerline_max_um']<old['parent_signal_centerline_max_um']*.8
verify(B,new)
def canonical(path):
    answer=[]
    for line in path.read_text().splitlines():
        row=line.split()
        if not row or row[0].startswith('*'):continue
        if row[0].lower()in('.subckt','.ends'):row[1]='SAME_TOP'
        answer.append(row)
    return answer
assert canonical(baseline/'schematic.cir')==canonical(source/'layout/schematic.cir')
faults=[]
bad=copy.deepcopy(new);bad['placements']['p8_0']['bbox_um']='(700,1;1053.985,593.04)'
try:verify(B,bad)
except AssertionError:faults.append('wrong_actual_row_metadata')
else:raise AssertionError('Accepted wrong row')
cell=B.cell('core_pre_low');li=next(i for i in B.layer_indexes()if B.get_info(i).datatype==0 and B.get_info(i).layer in(126,134)and not cell.shapes(i).is_empty())
saved=pya.Region(cell.shapes(li));cell.shapes(li).clear()
try:verify(B,new)
except AssertionError:faults.append('native_child_conductor_removed')
else:raise AssertionError('Accepted child drawing corruption')
cell.shapes(li).insert(saved)
li=B.layer(126,0);saved=pya.Region(B.top_cell().shapes(li))
r=new['signal_routes'][0];x1,y1,x2,y2=r['fault_cut_um'];cut=pya.Region(pya.DBox(x1,y1,x2,y2).to_itype(.001))
assert not (saved&cut).is_empty();B.top_cell().shapes(li).clear();B.top_cell().shapes(li).insert(saved-cut)
try:verify(B,new)
except AssertionError:faults.append('actual_parent_trunk_cut')
else:raise AssertionError('Accepted actual parent route cut')
assert len(faults)==3 and sha(ap)==old['outputs'][ap.name]and sha(bp)==new['outputs'][bp.name]
r=dict(status='PASS_MINIMAX_ACTUAL31_PLACEMENTS_FROZEN_CHILDREN_60_ROUTES_AND_THREE_FAULTS',
    baseline_source_run=pin['source_run'],reference_devices_unchanged=True,actual_native_children_unchanged=True,
    fixed_leaf_and_final_rows=17,signal_legs=60,controls=faults,maximum_before_um=old['parent_signal_centerline_max_um'],
    maximum_after_um=new['parent_signal_centerline_max_um'],sum_before_um=old['parent_signal_centerline_sum_um'],
    sum_after_um=new['parent_signal_centerline_sum_um'],plan=plan,electrical_accepted=False,full_phy_accepted=False,
    inputs={str(p):sha(p)for p in (ap,bp,baseline/'schematic.cir',source/'layout/schematic.cir',Path(__file__))})
(source/'minimax-geometry-delta.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],flush=True)
