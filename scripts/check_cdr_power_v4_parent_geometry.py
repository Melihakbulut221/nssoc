#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare actual whole-parent drawing delta with two placed leaf deltas."""
import hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(parent,baseline):
    import pya
    oldtop='nssoc_cdr_pd484_parallel_tail_v2';newtop='nssoc_cdr_pd484_power_access_v4'
    oldleaf='nssoc_cdr_xor_hybrid_tail_layout_v3';newleaf='nssoc_cdr_xor_power_access_layout_v4'
    a=json.loads((baseline/'layout/result.json').read_text());b=json.loads((parent/'layout/result.json').read_text())
    for key in ['placements','routes','ports','bbox_um','primitive_census','supply_overlay','routing_changes']:
        assert a[key]==b[key],('Unexpected parent placement/routing change',key)
    assert (baseline/'layout/schematic.cir').read_text().replace(oldtop,newtop)==(parent/'layout/schematic.cir').read_text()
    assert sum(b['primitive_census'].values())==484 and len(b['placements'])==16
    sources={}
    def read(path,top):
        l=pya.Layout();l.read(str(path));t=l.cell(top);assert t is not None and l.dbu==.001
        sources[str(path)]=sha(path)
        return {(l.get_info(i).layer,l.get_info(i).datatype):pya.Region(t.begin_shapes_rec(i)).merged()for i in l.layer_indexes()if l.get_info(i).datatype==0}
    before=read(baseline/'layout'/(oldtop+'.gds'),oldtop);after=read(parent/'layout'/(newtop+'.gds'),newtop)
    leaf_before=read(parent/'geometry-baseline/layout'/(oldleaf+'.gds'),oldleaf)
    leaf_after=read(parent/'inputs/xor/layout'/(newleaf+'.gds'),newleaf)
    keys=set(before)|set(after)|set(leaf_before)|set(leaf_after);empty=pya.Region();additions={k:pya.Region()for k in keys};places=[]
    for tag,p in b['placements'].items():
        if p['kind']!='xor':continue
        values=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',p['bbox_um'])));assert len(values)==4
        dx,dy=round(values[0]/.001),round(values[1]/.001);tr=pya.Trans(dx,dy)
        places.append(dict(tag=tag,translation_dbu=[dx,dy]))
        for key in keys:
            assert (leaf_before.get(key,empty)-leaf_after.get(key,empty)).is_empty(),('Leaf removed original drawing',key)
            delta=leaf_after.get(key,empty)-leaf_before.get(key,empty)
            additions[key]+=delta.transformed(tr)
    assert {p['tag']for p in places}=={'x','y'}
    expected={k:(before.get(k,empty)+additions[k]).merged()for k in keys}
    def verify(actual):
        for key in keys|set(actual):
            assert (expected.get(key,empty)^actual.get(key,empty)).is_empty(),('Whole parent differs outside two leaf additions',key)
    verify(after);changed=[]
    for k in sorted(keys):
        assert (before.get(k,empty)-after.get(k,empty)).is_empty()
        delta=after.get(k,empty)-before.get(k,empty)
        if not delta.is_empty():
            assert k in {(8,0),(10,0),(19,0),(29,0),(30,0)}
            changed.append(dict(layer=list(k),added_area_dbu2=delta.area()))
    controls=[]
    for name,k in [('remove_actual_added_via',(19,0)),('remove_actual_added_metal',(30,0))]:
        delta=after[k]-before[k];cut=pya.Region(next(delta.each()));bad=dict(after);bad[k]=after[k]-cut
        try:verify(bad)
        except AssertionError:controls.append(dict(name=name,removed_area_dbu2=cut.area(),rejected=True))
        else:raise AssertionError('Actual drawing corruption accepted')
    bad=dict(after);bad[(1,0)]=after.get((1,0),empty)+pya.Region(pya.Box(-10000,-10000,-9000,-9000))
    try:verify(bad)
    except AssertionError:controls.append(dict(name='extra_active_drawing_outside_chip',added_area_dbu2=1000000,rejected=True))
    else:raise AssertionError('Unrelated active-layer drawing accepted')
    assert len(controls)==3
    sources.update({str(p):sha(p)for p in [Path(__file__),baseline/'layout/result.json',parent/'layout/result.json',baseline/'layout/schematic.cir',parent/'layout/schematic.cir']})
    return dict(status='PASS_FULL_PD484_DRAWING_DELTA_ONLY_TWO_VERIFIED_XOR_POWER_ADDITIONS',all_drawing_layers_checked=len(keys),changed_layers=changed,placements=places,all_other_geometry_equal=True,all484_reference_devices_and_connections_unchanged=True,controls=controls,inputs=sources,electrical_accepted=False)
