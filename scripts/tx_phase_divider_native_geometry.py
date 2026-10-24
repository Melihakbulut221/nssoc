#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent material and hierarchy comparison; new master-port access only."""
import json,sys,hashlib
from pathlib import Path
import pya
base,candidate,output=map(Path,sys.argv[1:])
a=pya.Layout();a.read(str(base/'nssoc_hbt_highinput43_v1_layout.gds'))
b=pya.Layout();b.read(str(candidate/'nssoc_tx_phase_divider55_v1.gds'))
x=a.top_cell();y=b.top_cell();assert a.dbu==b.dbu
ra=json.loads((base/'result.json').read_text());rb=json.loads((candidate/'result.json').read_text())
assert ra['instances']==rb['instances'] or all({k:v for k,v in p.items()if k!='nets'}=={k:v for k,v in q.items()if k!='nets'}for p,q in zip(ra['instances'],rb['instances'],strict=True))
assert len(ra['instances'])==len(rb['instances'])==55
assert ra['bbox_um']==rb['bbox_um']
assert all(ra['ports'][n]==rb['ports'][n]for n in ra['ports'])
assert set(rb['ports'])==set(ra['ports'])|{'MP','MN'}
assert all(ra['local_buses'][i]['y_um']==rb['local_buses'][i]['y_um']for i in range(len(ra['local_buses'])))
layers={(a.get_info(i).layer,a.get_info(i).datatype)for i in a.layer_indexes()}|{(b.get_info(i).layer,b.get_info(i).datatype)for i in b.layer_indexes()}
changes=[]
for layer,datatype in sorted(layers):
    if datatype!=0:continue
    old=pya.Region(x.begin_shapes_rec(a.layer(layer,datatype))).merged()
    new=pya.Region(y.begin_shapes_rec(b.layer(layer,datatype))).merged()
    assert(old-new).is_empty(),('Removed original material',layer,datatype)
    delta=new-old
    if not delta.is_empty():
        assert layer==67,('Changed intrinsic/non-Metal5 geometry',layer)
        allowed=pya.Region()
        for name in ('MP','MN'):
            row=next(v for v in rb['local_buses']if v['net']==name)
            yy=row['y_um']+rb['origin_translation_um'][1]
            allowed.insert(pya.DBox(0,yy-1,rb['bbox_um'][2],yy+1).to_itype(b.dbu))
        assert(delta-allowed).is_empty(),'New material outside two real master-net buses'
        changes.append(dict(layer=layer,datatype=datatype,added_area_dbu2=delta.area()))
assert len(changes)==1
# Cell definitions and transforms below the root are identical, including all native PCells.
def children(layout,cell):
    return sorted((i.cell.name,i.to_s())for i in cell.each_inst())
assert children(a,x)==children(b,y),'Native child hierarchy changed'
for cell in a.each_cell():
    if cell.cell_index()==x.cell_index():continue
    other=b.cell(cell.name);assert other is not None
    for layer,datatype in sorted(layers):
        assert(pya.Region(cell.begin_shapes_rec(a.layer(layer,datatype)))^pya.Region(other.begin_shapes_rec(b.layer(layer,datatype)))).is_empty(),('Changed child material',cell.name,layer,datatype)
result=dict(status='PASS_SAME55_DEVICES_ALL_INTRINSICS_CHILDREN_AND_OLD_MATERIAL_ONLY_TWO_M5_MASTER_ACCESS_EXTENSIONS',
    changes=changes,devices=55,ports=9,phase_or_electrical_acceptance=False,
    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [base/'nssoc_hbt_highinput43_v1_layout.gds',candidate/'nssoc_tx_phase_divider55_v1.gds']})
output.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
