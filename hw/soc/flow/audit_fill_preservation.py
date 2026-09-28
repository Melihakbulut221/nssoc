#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Conservative geometry/instance preservation check, not physical acceptance."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import klayout.db as db

p=argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('filled'); p.add_argument('output'); a=p.parse_args()
allowed={(n,22) for n in (1,5,8,10,30,50,67,126,134)}
def sha(path):
    with open(path,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
inputs={path:sha(path) for path in (a.source,a.filled)}
x=db.Layout(); x.read(a.source); y=db.Layout(); y.read(a.filled)
def layers(layout):
    return {(layout.get_info(i).layer,layout.get_info(i).datatype):i for i in layout.layer_indexes()}
def shapes(cell,index):
    if index is None: return Counter()
    # Normalize boxes and polygons, since a GDS round trip may encode either.
    return Counter(('P:'+s.polygon.to_s()) if s.is_box() or s.is_polygon()
                   else 'S:'+s.to_s() for s in cell.shapes(index).each())
def instances(cell):
    return Counter((i.cell.name,i.cplx_trans.to_s(),i.a.to_s(),i.b.to_s(),i.na,i.nb) for i in cell.each_inst())
errors=[]; added=0
if x.dbu!=y.dbu: errors.append('Database unit changed')
if sorted(c.name for c in x.top_cells())!=sorted(c.name for c in y.top_cells()): errors.append('Top cells changed')
xl=layers(x); yl=layers(y)
for cell in x.each_cell():
    other=y.cell(cell.name)
    if other is None:
        errors.append('Missing original cell '+cell.name); continue
    before_instances=instances(cell)
    after_instances=Counter({key:value for key,value in instances(other).items() if x.cell(key[0]) is not None})
    if before_instances!=after_instances: errors.append('Original instance graph changed in '+cell.name)
    for layer in set(xl)|set(yl):
        before=shapes(cell,xl.get(layer)); after=shapes(other,yl.get(layer))
        if layer in allowed:
            if before-after: errors.append('Removed original fill in '+cell.name+' '+str(layer))
            added+=sum((after-before).values())
        elif before!=after:
            errors.append('Non-fill geometry changed in '+cell.name+' '+str(layer))
original_names={cell.name for cell in x.each_cell()}
new=[cell for cell in y.each_cell() if cell.name not in original_names]
for cell in new:
    for layer,index in yl.items():
        count=cell.shapes(index).size()
        if layer not in allowed and count: errors.append('New cell has non-fill geometry '+cell.name+' '+str(layer))
        if layer in allowed: added+=count
    for instance in cell.each_inst():
        if instance.cell.name in original_names: errors.append('New fill cell instantiates source geometry '+cell.name)
if not all(sha(path)==digest for path,digest in inputs.items()): errors.append('Input changed during audit')
result=dict(status='FAIL' if errors else 'PASS within geometry-preservation scope',errors=errors,
            input_sha256=inputs,source_cells=x.cells(),new_cells=len(new),added_fill_shape_definitions=added,
            scope='All original per-cell shapes and instances retained; additions confined to designated fill layers. Excludes DRC, LVS, density compliance, parasitic extraction, timing and manufacturing approval.')
Path(a.output).write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
raise SystemExit(bool(errors))
