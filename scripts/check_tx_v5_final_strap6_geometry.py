#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent whole drawing comparison; no electrical acceptance."""
import hashlib,json,re,sys,tarfile
from pathlib import Path
import pya
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1])
pin=json.loads((ROOT/'docs/evidence/tx-v5-fast-stage-isolated-physical-pass-20261018.json').read_text())
assert pin['source_run']==39156383821 and pin['summary_sha256']=='e1c75799b04645647e12b078dbc26e2b829ef3e92f9faedc67d371b04d09ddef'
baseline=source/'strap-baseline';baseline.mkdir(exist_ok=False)
packed=baseline/'source.tar.gz';fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
with tarfile.open(packed)as tar:
    prefix='cloud-tx-v5-fast-stage-isolated-assembly/'
    raw=tar.extractfile(prefix+'result.json').read()
    assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256']
    prior=json.loads(raw)
    assert prior['status']=='PASS_TREE32_1674_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
    for name in prior['outputs']:
        if not name.startswith('layout/'):continue
        data=tar.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==prior['outputs'][name]
        (baseline/Path(name).name).write_bytes(data)
packed.unlink()
old=json.loads((baseline/'result.json').read_text());new=json.loads((source/'layout/result.json').read_text())
for key in ('placements','origin_translation_um','signal_routes','placement_pitch','ports','bbox_um','total_devices'):
    assert old[key]==new[key],key
def load(folder,record):
    name=next(n for n in record['outputs']if n.endswith('.gds'));path=folder/name
    assert sha(path)==record['outputs'][name]
    layout=pya.Layout();layout.read(str(path));assert layout.dbu==.001 and len(layout.top_cells())==1
    return layout,path
A,ap=load(baseline,old);B,bp=load(source/'layout',new)
plan=json.loads((source/'plan.json').read_text())
final=next(n for n in plan['nodes']if n['label']=='f')
dx,dy=new['origin_translation_um']
x=final['x_um']+334.785-280.875+dx
y=final['y_um']+dy
before=pya.Region(pya.DBox(x-2,y+130.230,x+2,y+332.24).to_itype(.001))
after=pya.Region(pya.DBox(x-3,y+130.230,x+3,y+332.24).to_itype(.001))
infos={(A.get_info(i).layer,A.get_info(i).datatype)for i in A.layer_indexes()}|{(B.get_info(i).layer,B.get_info(i).datatype)for i in B.layer_indexes()}
def regions(layout):
    return {k:pya.Region(layout.top_cell().begin_shapes_rec(layout.layer(*k))).flatten().merged()for k in infos if k[1]==0}
original=regions(A);candidate=regions(B)
key=(126,0);assert key in original
assert (before-original[key]).is_empty()
expected=(original[key]|after).merged()
added=expected-original[key]
assert not added.is_empty(),'No new physical strap area'
def check(values):
    for k,region in original.items():
        wanted=expected if k==key else region
        assert (values[k]^wanted).is_empty(),('Unexpected drawing delta',k)
check(candidate)
# Independent corruptions: old width, missing strap, unrelated conductor.
controls=[]
for label,changed in [('old_width',original[key]),('removed_strap',candidate[key]-after),('unrelated_metal',candidate[key]|pya.Region(pya.Box(-10000,-10000,-9000,-9000)))]:
    values=dict(candidate);values[key]=changed
    try:check(values)
    except AssertionError:controls.append(label)
    else:raise AssertionError('Accepted '+label)
assert len(controls)==3
def netlist(path):
    result=[]
    for line in path.read_text().splitlines():
        f=line.split()
        if not f or f[0].startswith('*'):continue
        if f[0].lower()in ('.subckt','.ends'):f[1]='SAME_TOP'
        result.append(f)
    return result
assert netlist(baseline/'schematic.cir')==netlist(source/'layout/schematic.cir')
assert sha(ap)==old['outputs'][ap.name] and sha(bp)==new['outputs'][bp.name]
r=dict(status='PASS_ONLY_FINAL_TM1_STRAP4TO6_GDS_DELTA',source_run=pin['source_run'],before_width_um=4,after_width_um=6,added_area_um2=added.area()*1e-6,original_vias_unchanged=True,all_other_drawing_layers_unchanged=True,reference_devices_unchanged=True,controls=controls,electrical_accepted=False,qualified_pex=False,full_phy_accepted=False,inputs={str(p):sha(p)for p in (ap,bp,Path(__file__))})
(source/'strap6-geometry-delta.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],r['added_area_um2'])
