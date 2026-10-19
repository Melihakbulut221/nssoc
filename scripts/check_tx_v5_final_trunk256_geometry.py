#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prove measured native branch ownership and exact final trunk drawing delta."""
import hashlib,json,re,shlex,sys,tarfile
from pathlib import Path
import pya
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];source=Path(sys.argv[1])
pin=json.loads((ROOT/'docs/evidence/tx-v5-final-strap6-physical-pass-20261019.json').read_text())
assert pin['source_run']==39217390888
baseline=source/'trunk-baseline';baseline.mkdir(exist_ok=False)
packed=baseline/'source.tar.gz';fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
with tarfile.open(packed)as tar:
    prefix='cloud-tx-v5-final-strap6-assembly/'
    raw=tar.extractfile(prefix+'result.json').read();assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256']
    prior=json.loads(raw);assert prior==pin['report']
    assert prior['status']=='PASS_TREE32_1674_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
    for name,digest in prior['outputs'].items():
        if not name.startswith('layout/'):continue
        data=tar.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==digest
        (baseline/Path(name).name).write_bytes(data)
packed.unlink()
old=json.loads((baseline/'result.json').read_text());new=json.loads((source/'layout/result.json').read_text())
for key in ('placements','placement_pitch','total_devices','core_devices','substrate_contacts'):
    assert old[key]==new[key],key
dx,dy=old['origin_translation_um'];nx,ny=new['origin_translation_um']
def rect(s):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',s)))
def eq(a,b):assert len(a)==len(b)and all(abs(x-y)<1e-7 for x,y in zip(a,b))
def shift(b,x,y):return [b[0]+x,b[1]+y,b[2]+x,b[3]+y]
assert old['ports'].keys()==new['ports'].keys()
for key in old['ports']:eq(shift(rect(old['ports'][key]),nx-dx,ny-dy),rect(new['ports'][key]))
assert len(old['signal_routes'])==len(new['signal_routes'])==60
for a,b in zip(old['signal_routes'],new['signal_routes'],strict=True):
    assert {k:v for k,v in a.items()if k!='fault_cut_um'}=={k:v for k,v in b.items()if k!='fault_cut_um'}
    eq(shift(a['fault_cut_um'],nx-dx,ny-dy),b['fault_cut_um'])
oldrects=old['parent_return_geometry_before_origin_translation'];newrects=new['parent_return_geometry_before_origin_translation']
assert len(oldrects)==len(newrects)==6
selected=[i for i,q in enumerate(oldrects)if q['layer']=='TopMetal1'and q['width_um']==128.]
assert selected==[4];idx=selected[0];b=oldrects[idx]['box_um']
expected_box=[b[0]-64,b[1]-64,b[2]+64,b[3]+64]
for i,(a,z)in enumerate(zip(oldrects,newrects,strict=True)):
    if i!=idx:assert a==z
    else:
        assert z['layer']=='TopMetal1'and z['width_um']==256.
        eq(z['box_um'],expected_box)
# Bind measured native endpoints to this exact prior layout, using EXT units:
# https://opencircuitdesign.com/~tim/programs/magic/manpages/ext_manpage.html
evidence=json.loads((ROOT/'docs/evidence/tx-v5-final-strap6-return-coordinates-20261019.json').read_text())
assert evidence['run']==39222023394
review=evidence['report'];assert review['sources_unchanged']
assert review['layout']['sha256']==prior['outputs']['layout/result.json']
native=next(x for x in review['native_coordinate_matches']if x['path']=='wire96/rc03/pump_wires.res.ext')
scale=shlex.split(native['header'][0]);assert scale==['scale','1000','1','0.5']
um_per_unit=float(scale[3])*.01
rows=[shlex.split(x['text'])for x in native['snippets']]
points={}
for name in ('P_avss.n5354','P_avss.n5353'):
    matches=[v for v in rows if v[:2]==['rnode',name]];assert len(matches)==1
    points[name]=[float(v)*um_per_unit for v in matches[0][4:6]]
actual_box=shift(b,dx,dy)
assert all(actual_box[0]<=q[0]<=actual_box[2]and actual_box[1]<=q[1]<=actual_box[3]for q in points.values())
assert abs(points['P_avss.n5354'][1]-points['P_avss.n5353'][1])>4000
resistors=[v for v in rows if v[:3]==['resist','P_avss.n5354','P_avss.n5353']]
assert len(resistors)==1 and abs(float(resistors[0][3])*float(scale[1])/1000-.706551)<1e-12
def load(folder,record):
    name=next(n for n in record['outputs']if n.endswith('.gds'));path=folder/name
    assert sha(path)==record['outputs'][name]
    layout=pya.Layout();layout.read(str(path));assert layout.dbu==.001 and len(layout.top_cells())==1
    return layout,path
A,ap=load(baseline,old);B,bp=load(source/'layout',new)
# Normalize the changed origin only in the in-memory comparison; source stays immutable.
B.top_cell().transform(pya.Trans(round((dx-nx)/B.dbu),round((dy-ny)/B.dbu)))
infos={(A.get_info(i).layer,A.get_info(i).datatype)for i in A.layer_indexes()}|{(B.get_info(i).layer,B.get_info(i).datatype)for i in B.layer_indexes()}
def regions(layout):
    return {k:pya.Region(layout.top_cell().begin_shapes_rec(layout.layer(*k))).flatten().merged()for k in infos if k[1]==0}
original=regions(A);candidate=regions(B);key=(126,0)
before=pya.Region(pya.DBox(*actual_box).to_itype(.001))
after=pya.Region(pya.DBox(*shift(expected_box,dx,dy)).to_itype(.001))
assert (before-original[key]).is_empty()
expected=(original[key]|after).merged();added=expected-original[key]
assert not added.is_empty()
def check(values):
    for k,region in original.items():
        assert (values[k]^(expected if k==key else region)).is_empty(),('Unexpected drawing delta',k)
check(candidate)
controls=[]
for label,value in [('old_width',original[key]),('removed_trunk',candidate[key]-after),('unrelated_metal',candidate[key]|pya.Region(pya.Box(-10000,-10000,-9000,-9000)))]:
    changed=dict(candidate);changed[key]=value
    try:check(changed)
    except AssertionError:controls.append(label)
    else:raise AssertionError('Accepted '+label)
assert len(controls)==3
def normalized(path):
    values=[]
    for line in path.read_text().splitlines():
        row=line.split()
        if not row or row[0].startswith('*'):continue
        if row[0].lower()in ('.subckt','.ends'):row[1]='SAME_TOP'
        values.append(row)
    return values
assert normalized(baseline/'schematic.cir')==normalized(source/'layout/schematic.cir')
assert sha(ap)==old['outputs'][ap.name]and sha(bp)==new['outputs'][bp.name]
r=dict(status='PASS_ONLY_FINAL_TM1_TRUNK128TO256_GDS_DELTA',source_run=pin['source_run'],before_width_um=128,after_width_um=256,added_area_um2=added.area()*1e-6,measured_branch=dict(name='R105585',ohm=.706551,native_points_um=points,prior_trunk_box_um=actual_box,coordinate_source_run=evidence['run']),original_vias_unchanged=True,local_strap6_unchanged=True,all_other_drawing_layers_unchanged=True,reference_devices_unchanged=True,controls=controls,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False,inputs={str(p):sha(p)for p in (ap,bp,Path(__file__))})
(source/'trunk256-geometry-delta.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],r['added_area_um2'])
