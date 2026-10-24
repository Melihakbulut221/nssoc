#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify actual native children and explicitly prescribed fast-stage rows."""
import copy,json,sys,tarfile,hashlib,re
from pathlib import Path
import pya
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];source=Path(sys.argv[1])
pin=json.loads((ROOT/'docs/evidence/tx-v5-return64-physical-pass-20261018.json').read_text())
baseline=source/'geometry-baseline';baseline.mkdir(exist_ok=False)
packed=baseline/'source.tar.gz';fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
with tarfile.open(packed)as t:
    prefix='cloud-tx-balanced-v5-return64-assembly/'
    raw=t.extractfile(prefix+'result.json').read();assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256'];prior=json.loads(raw)
    for name in ['layout/result.json','layout/schematic.cir',*[n for n in prior['outputs']if n.startswith('layout/')and n.endswith('.gds')]]:
        b=t.extractfile(prefix+name).read();assert hashlib.sha256(b).hexdigest()==prior['outputs'][name];(baseline/Path(name).name).write_bytes(b)
packed.unlink()
old=json.loads((baseline/'result.json').read_text());new=json.loads((source/'layout/result.json').read_text())
physical=json.loads((source/'candidate-physical.json').read_text());assert physical['physical']['status']=='PASS_NATIVE_PDK_TX_TREE1674_DRC_LVS_AND_FAULT_CONTROLS'
assert physical['return_rail']['profile']=='wide64'and physical['return_rail']['trunk_and_bus_width_um']==64
assert old['placement_pitch']==dict(column_um=1000.,row_um=600.)
def load(folder,record):
    name=next(n for n in record['outputs']if n.endswith('.gds'));path=folder/name;assert sha(path)==record['outputs'][name]
    L=pya.Layout();L.read(str(path));assert L.dbu==.001 and len(L.top_cells())==1;return L,path
A,oldpath=load(baseline,old);B,newpath=load(source/'layout',new)
def box(raw):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)))
ROW_TARGETS={'a':4200.,'b':4800.,'p4_0':3600.,'p4_2':4200.,'p4_1':4800.,'p4_3':5400.}
def shifted(raw,dx,dy=0.):
    x1,y1,x2,y2=box(raw);return [x1+dx,y1+dy,x2+dx,y2+dy]
def eq(a,b):assert len(a)==len(b)and all(abs(x-y)<1e-8 for x,y in zip(a,b))
def verify(L,record):
    assert record['placement_pitch']==dict(column_um=700.,row_um=600.)
    assert record['frozen_child_drawing_regions_equal']and record['total_devices']==1674
    assert set(record['placements'])==set(old['placements'])and len(record['placements'])==31
    actual=[];dx,dy=record['origin_translation_um']
    for inst in L.top_cell().each_inst():
        cell=L.cell(inst.cell_index)
        if not cell.name.startswith('core_'):continue
        assert not inst.is_regular_array();b=cell.dbbox().transformed(inst.dcplx_trans)
        actual.append((cell.name,str(inst.dcplx_trans),[b.left-dx,b.bottom-dy,b.right-dx,b.top-dy]))
    assert len(actual)==31
    used=set()
    for tag,p in record['placements'].items():
        before=old['placements'][tag];ob=box(before['bbox_um']);level=round(ob[0]/1000.)
        assert abs(ob[0]-level*1000)<1e-8 and 0<=level<=4
        offset=-300.*level;row_shift=ROW_TARGETS.get(tag,ob[1])-ob[1]
        assert p['kind']==before['kind']and set(p['ports'])==set(before['ports'])
        target=shifted(before['bbox_um'],offset,row_shift);eq(box(p['bbox_um']),target)
        for port in p['ports']:eq(box(p['ports'][port]),shifted(before['ports'][port],offset,row_shift))
        matches=[i for i,(name,tr,b)in enumerate(actual)if name=='core_'+p['kind']and all(abs(x-y)<1e-8 for x,y in zip(b,target))]
        assert len(matches)==1 and matches[0]not in used;used.add(matches[0])
        assert target[3]-target[1]<600 and target[2]-target[0]+300<700
    for kind in ('pre','pre_low','final'):
        ca=A.cell('core_'+kind);cb=L.cell('core_'+kind);assert ca is not None and cb is not None
        infos={(A.get_info(i).layer,A.get_info(i).datatype)for i in A.layer_indexes()}|{(L.get_info(i).layer,L.get_info(i).datatype)for i in L.layer_indexes()}
        for layer,dt in infos:
            if dt!=0:continue
            ra=pya.Region(ca.begin_shapes_rec(A.layer(layer,dt))).merged();rb=pya.Region(cb.begin_shapes_rec(L.layer(layer,dt))).merged()
            assert (ra^rb).is_empty(),('Child drawing changed',kind,layer)
    assert len(record['signal_routes'])==len(old['signal_routes'])==60
    for r,o in zip(record['signal_routes'],old['signal_routes'],strict=True):
        assert all(r[k]==o[k]for k in ('net','endpoints','width_um'))
        child=o['endpoints'][0].split('.')[0];parent=o['endpoints'][1].split('.')[0]
        level=round(box(old['placements'][parent]['bbox_um'])[0]/1000.)
        shifts=[ROW_TARGETS.get(tag,box(old['placements'][tag]['bbox_um'])[1])-box(old['placements'][tag]['bbox_um'])[1]for tag in (child,parent)]
        ys=[a+b for a,b in zip(o['y_um'],shifts,strict=True)];eq(r['y_um'],ys)
        track_shift={'p8_2p':48.,'p8_2n':48.,'p8_7p':24.,'p8_7n':24.}.get(r['net'],0.)
        assert abs(r['x_um']-(o['x_um']-300*level+track_shift))<1e-8
        expected=o['centerline_length_um']-300+2*track_shift+abs(ys[1]-ys[0])-abs(o['y_um'][1]-o['y_um'][0])
        assert abs(r['centerline_length_um']-expected)<1e-8
        if parent in ('f','a','b'):assert r['centerline_length_um']<o['centerline_length_um']-300
    # Verify every declared TM1 trunk exists in the actual parent geometry.
    region=pya.Region(L.top_cell().shapes(L.layer(126,0))).merged()
    for i,r in enumerate(record['signal_routes']):
        x=r['x_um'];y0,y1=r['y_um'];b=pya.DBox(x-2+dx,min(y0,y1)-2+dy,x+2+dx,max(y0,y1)+2+dy)
        assert (pya.Region(b.to_itype(L.dbu))-region).is_empty()
        for q in record['signal_routes'][i+1:]:
            if abs(r['x_um']-q['x_um'])>=4:continue
            assert max(min(r['y_um']),min(q['y_um']))-min(max(r['y_um']),max(q['y_um']))>=4,('Parent trunks short',r['net'],q['net'])
    lengths=[x['centerline_length_um']for x in record['signal_routes']]
    assert abs(record['parent_signal_centerline_sum_um']-sum(lengths))<1e-7
    assert abs(record['parent_signal_centerline_max_um']-max(lengths))<1e-8
    # Prove actual bodies stay separated after row compression, per physical column.
    for level in range(5):
        bodies=sorted((box(p['bbox_um'])for p in record['placements'].values()if abs(box(p['bbox_um'])[0]-700*level)<1e-8),key=lambda b:b[1])
        assert all(b[1]-a[3]>=7.9 for a,b in zip(bodies,bodies[1:]))
verify(B,new)
def normalized(path):
    rows=[]
    for line in path.read_text().splitlines():
        f=line.split()
        if not f or f[0].startswith('*'):continue
        if f[0].lower()in ('.subckt','.ends'):f[1]='SAME_TOP'
        rows.append(f)
    return rows
assert normalized(baseline/'schematic.cir')==normalized(source/'layout/schematic.cir')
faults=[]
for name in ('wrong_column','moved_row'):
    changed=copy.deepcopy(new)
    if name=='wrong_column':changed['placement_pitch']['column_um']=701
    else:
        p=changed['placements']['f'];b=box(p['bbox_um']);b[1]+=1;b[3]+=1;p['bbox_um']='('+','.join(map(str,b[:2]))+';'+','.join(map(str,b[2:]))+')'
    try:verify(B,changed)
    except AssertionError:faults.append(name)
    else:raise AssertionError('Accepted '+name)
# Alter an actual native child conductor in memory. Source GDS remains immutable.
cell=B.cell('core_pre_low');idx=next(i for i in B.layer_indexes()if B.get_info(i).datatype==0 and B.get_info(i).layer in (126,134)and not cell.shapes(i).is_empty())
cell.shapes(idx).clear()
try:verify(B,new)
except AssertionError:faults.append('actual_child_conductor_removed')
else:raise AssertionError('Accepted actual child geometry corruption')
assert len(faults)==3 and sha(newpath)==new['outputs'][newpath.name]
r=dict(status='PASS_FAST_STAGE_ROWS_FROZEN_CHILDREN_TOPOLOGY_AND_NATIVE_PLACEMENT',baseline_source=pin['source_run'],baseline_summary_sha256=pin['summary_sha256'],controls=faults,actual_macro_instances=31,actual_cells_unchanged=True,all_reference_device_cards_unchanged=True,signal_connections=60,centerline_sum_before_um=old['parent_signal_centerline_sum_um'],centerline_sum_after_um=new['parent_signal_centerline_sum_um'],reduction_um=old['parent_signal_centerline_sum_um']-new['parent_signal_centerline_sum_um'],fast_stage_rows_um=ROW_TARGETS,fast_stage_routes_shorter=12,inputs={str(p):sha(p)for p in [Path(__file__),oldpath,newpath,baseline/'schematic.cir',source/'layout/schematic.cir']},electrical_passed=False,qualified_pex=False,full_phy_accepted=False)
(source/'column-geometry-delta.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
