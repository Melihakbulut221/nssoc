#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Require the actual GDS change to be exactly six AVSS rectangle expansions."""
import json,sys,tarfile,hashlib
from pathlib import Path
import pya
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]);result_path=source/'return-geometry-delta.json'
receipt=json.loads((ROOT/'docs/evidence/tx-tree32-balanced-v5-physical-pass-20261017.json').read_text())
wide_receipt=dict(candidate_physical_sha256=sha(source/'candidate-physical.json'),layout_sha256=sha(source/'layout/result.json'))
wide=json.loads((source/'layout/result.json').read_text())
physical=json.loads((source/'candidate-physical.json').read_text())
assert physical['return_rail']['profile']=='wide64'and physical['return_rail']['trunk_and_bus_width_um']==64.
assert physical['physical']['status']=='PASS_NATIVE_PDK_TX_TREE1674_DRC_LVS_AND_FAULT_CONTROLS'
baseline=source/'geometry-baseline';baseline.mkdir(exist_ok=False)
archive=baseline/'source.tar.gz';fetch(receipt['url'],receipt['sha256'],archive);assert archive.stat().st_size==receipt['bytes']
with tarfile.open(archive)as t:
    prefix='cloud-tx-tree32-balanced-v5-assembly/'
    raw=t.extractfile(prefix+'result.json').read();assert hashlib.sha256(raw).hexdigest()==receipt['summary_sha256']
    oldphysical=json.loads(raw);(baseline/'physical-result.json').write_bytes(raw)
    for name in ['layout/result.json',*[n for n in oldphysical['outputs']if n.endswith('.gds')and n.startswith('layout/')]]:
        raw=t.extractfile(prefix+name).read();assert hashlib.sha256(raw).hexdigest()==oldphysical['outputs'][name]
        (baseline/Path(name).name).write_bytes(raw)
archive.unlink()
old=json.loads((baseline/'result.json').read_text())
assert oldphysical['status']==physical['status']=='PASS_TREE32_1674_NATIVE_DRC_LVS_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
assert old['placements']==wide['placements']
assert old['parent_signal_centerline_sum_um']==wide['parent_signal_centerline_sum_um']
assert old['parent_signal_centerline_max_um']==wide['parent_signal_centerline_max_um']
assert [{k:v for k,v in r.items()if k!='fault_cut_um'}for r in old['signal_routes']]==[{k:v for k,v in r.items()if k!='fault_cut_um'}for r in wide['signal_routes']]

def drawings(folder,report):
    filename=next(n for n in report['outputs']if n.endswith('.gds'))
    path=folder/filename;assert sha(path)==report['outputs'][filename]
    layout=pya.Layout();layout.read(str(path));assert layout.dbu==.001 and len(layout.top_cells())==1
    top=layout.top_cell();dx,dy=report['origin_translation_um']
    shift=pya.Trans(round(-dx/layout.dbu),round(-dy/layout.dbu));regions={}
    for index in layout.layer_indexes():
        info=layout.get_info(index)
        if info.datatype!=0:continue
        region=pya.Region(top.begin_shapes_rec(index)).merged().transformed(shift)
        if not region.is_empty():regions[info.layer]=region
    return regions,path
old_regions,old_gds=drawings(baseline,old);new_regions,new_gds=drawings(source/'layout',wide)
allowed={126:pya.Region(),134:pya.Region()};rectangles=wide['parent_return_geometry_before_origin_translation']
assert len(rectangles)==6 and [r['layer']for r in rectangles].count('TopMetal1')==5
for row in rectangles:
    assert row['width_um']==64.
    layer={'TopMetal1':126,'TopMetal2':134}[row['layer']]
    a,b,c,d=row['box_um']
    assert(abs((c-a)-64.)<1e-8 if layer==126 else abs((d-b)-64.)<1e-8)
    actual=pya.Region(pya.DBox(a,b,c,d).to_itype(.001))
    original=pya.Region(pya.DBox(a+16,b+16,c-16,d-16).to_itype(.001))
    assert(original-old_regions[layer]).is_empty(),'Original32um rectangle is not in baseline GDS'
    allowed[layer]+=actual
allowed={k:v.merged()for k,v in allowed.items()}

def verify(candidate):
    rows={}
    for layer in set(old_regions)|set(candidate)|set(allowed):
        oldr=old_regions.get(layer,pya.Region());newr=candidate.get(layer,pya.Region())
        expected=(oldr+allowed.get(layer,pya.Region())).merged()
        assert(newr^expected).is_empty(),('Unexpected actual drawing change',layer)
        removed=oldr-newr;assert removed.is_empty()
        rows[str(layer)]=dict(original_area_dbu2=oldr.area(),new_area_dbu2=newr.area(),added_area_dbu2=(newr-oldr).area())
    assert all(rows[str(layer)]['added_area_dbu2']>0 for layer in (126,134))
    return rows
measured=verify(new_regions);faults=[]
for kind in ('unrelated_topmetal','missing_device_layer','missing_widening'):
    bad=dict(new_regions)
    if kind=='unrelated_topmetal':bad[126]=bad[126]+pya.Region(pya.Box(-500000,-500000,-499000,-499000))
    elif kind=='missing_device_layer':bad[next(k for k in sorted(old_regions)if k not in (126,134))]=pya.Region()
    else:bad=dict(old_regions)
    try:verify(bad)
    except AssertionError:faults.append(dict(case=kind,rejected=True))
    else:raise AssertionError('Accepted altered drawing: '+kind)
result=dict(status='PASS_EXACT_SIX_AVSS_EXPANSIONS_ALL_OTHER_DRAWING_GEOMETRY_UNCHANGED',
    sources=dict(baseline=receipt,candidate=wide_receipt),layer_areas=measured,controls=faults,
    inputs={str(p):sha(p)for p in [Path(__file__),old_gds,new_gds,source/'layout/result.json',baseline/'result.json']},
    scope='All datatype0 drawing geometry compared after undoing recorded origins. Only union with six exact64um AVSS rectangles permitted. Pin/text metadata are outside this region comparison; separate actual native LVS/DRC already checks connectivity. No RC or electrical acceptance.')
result_path.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
