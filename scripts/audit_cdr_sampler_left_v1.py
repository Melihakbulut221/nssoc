#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare actual native leaf drawings and placements, not inferred RC benefits."""
import argparse,json,hashlib
from pathlib import Path
import pya
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out
old=json.loads((out/'baseline/result.json').read_text());new=json.loads((out/'layout/result.json').read_text())
for key in ('instances','routes','primitive_counts','source_circuit_sha256','origin_translation_um'):
    assert old[key]==new[key],key
assert [r for r in new['vias']if r['top']<=5]==old['vias']
assert {r['net']for r in new['vias']if r['top']==7}=={'QP','QN'}
for name,port in old['ports'].items():
    if name not in ('QP','QN'):assert port==new['ports'][name]
    else:
        q=new['ports'][name];assert port['layer']==q['layer']=='Metal5'
        assert q['rect_um'][0]==0 and q['rect_um'][2]==2
        assert [port['rect_um'][i]for i in (1,3)]==[q['rect_um'][i]for i in (1,3)]
oldtop='nssoc_rx_sampler_hbt_v2_compact_v1';newtop='nssoc_rx_sampler_hbt_v2_left_v1'
assert (out/'layout/schematic.cir').read_text()==(out/'baseline/schematic.cir').read_text().replace(oldtop,newtop)
A=pya.Layout();A.read(str(out/'baseline'/(oldtop+'.gds')));B=pya.Layout();B.read(str(out/'layout'/(newtop+'.gds')))
assert A.dbu==B.dbu==.001
allowed={(67,0),(67,2),(67,25),(125,0),(126,0),(133,0),(134,0)}
keys={(L.get_info(i).layer,L.get_info(i).datatype)for L in (A,B)for i in L.layer_indexes()};changed=[];retained=[]
for key in sorted(keys):
    ar=pya.Region(A.cell(oldtop).begin_shapes_rec(A.layer(*key))).merged();br=pya.Region(B.cell(newtop).begin_shapes_rec(B.layer(*key))).merged()
    if (ar^br).is_empty():retained.append(key)
    else:
        assert key in allowed,('Unexpected layer edit',key)
        changed.append(dict(layer=key,removed_area_dbu2=(ar-br).area(),added_area_dbu2=(br-ar).area()))
assert {tuple(x['layer'])for x in changed}>={(67,0),(134,0)}
r=dict(status='PASS_NATIVE_LEFT_OUTPUT_GEOMETRY_DELTA_NOT_ELECTRICAL_ACCEPTANCE',all_primitive_records_placements_and_internal_escapes_unchanged=True,all_original_low_metal_vias_unchanged=True,all_eight_other_ports_unchanged=True,source_reference_unchanged_except_top_name=True,allowed_layers=sorted(allowed),changed=changed,retained_layers=retained,output_shunts=new['output_shunts'],old_bbox_um=old['bbox_um'],new_bbox_um=new['bbox_um'],fresh_parent_rc_required=True,full_phy_accepted=False)
(out/'layout-change-audit.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
