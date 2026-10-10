#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject unsupported ESD semiconductor masks; never replace native terminals.

Requires actual GDS recognition polygons, not cell/instance names. Exact native
PCell semiconductor masks are compared under all eight rigid orientations.
This guards the limited ordinary 2-kV family against a device marker concealing
a split or additional well. Metal/contact opens and shorts remain independent
native extraction/LVS checks. No geometry is modified or used to invent nodes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

MASKS = ((1,0),(14,0),(31,0),(99,30))
EXCLUDED = ((7,21),(7,0),(26,0),(33,0),(156,0),(128,0),(111,0),(24,0),
            (27,0),(27,2),(5,0),(44,0),(28,0),(32,0),(46,21))


def inspect(gds, topname, pdk):
    source = pdk/'libs.tech/klayout/python'
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    inputs = {str(p):sha(p) for p in [Path(__file__).resolve(),gds,
               *source.rglob('*.py'),*source.rglob('*.json')]}
    l = pya.Layout(); l.read(str(gds)); c = l.cell(topname)
    if c is None:
        raise ValueError('Exact requested GDS top missing')
    actual = {k:pya.Region(c.begin_shapes_rec(l.layer(*k))).merged() for k in MASKS}
    excluded = pya.Region()
    for k in EXCLUDED:
        excluded += pya.Region(c.begin_shapes_rec(l.layer(*k)))
    templates = pya.Layout(); templates.dbu = l.dbu
    canonical = {}
    for model in ('diodevdd_2kv','diodevss_2kv'):
        cell = templates.create_cell('esd','SG13_dev',{'model':model})
        canonical[model] = {k:pya.Region(cell.begin_shapes_rec(templates.layer(*k))).merged() for k in MASKS}
    matches, rejected = [], []
    for marker in actual[(99,30)].each():
        region = pya.Region(marker); box = marker.bbox()
        if not marker.is_box() or not excluded.interacting(region).is_empty():
            rejected.append(dict(box=str(box),reason='Nonrectangular or excluded ESD region'))
            continue
        observed = {k:(r & region).merged() for k,r in actual.items()}
        found = []
        for model, layers in canonical.items():
            for ori in range(8):
                turn = pya.Trans(ori % 4,ori >= 4,0,0)
                bbox = layers[(99,30)].transformed(turn).bbox()
                transform = pya.Trans(ori % 4,ori >= 4,box.left-bbox.left,box.bottom-bbox.bottom)
                if all((observed[k] ^ layers[k].transformed(transform)).is_empty() for k in MASKS):
                    found.append(dict(model=model,orientation=ori))
        models = {f['model'] for f in found}
        if len(models) != 1:
            rejected.append(dict(box=str(box),reason='Unsupported or malformed semiconductor geometry',matches=found))
        else:
            matches.append(dict(box=str(box),model=next(iter(models)),orientations=[f['orientation'] for f in found],
                                mask_area_dbu2={str(k):observed[k].area() for k in MASKS}))
    if any(sha(Path(p)) != h for p,h in inputs.items()):
        raise ValueError('GDS/PCell source changed during geometry audit')
    return dict(status='PASS_FIXED_NATIVE_ESD_MASKS' if matches and not rejected else 'FAIL_NATIVE_ESD_MASKS',
                marker_count=len(matches)+len(rejected),matches=matches,rejected=rejected,
                inputs=inputs,dbu_um=l.dbu,qualified_pex=False,esd_stress_qualified=False,
                scope='Exact native semiconductor masks only; no reference netlist, node union or device replacement')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gds',type=Path,required=True)
    p.add_argument('--top',required=True)
    p.add_argument('--pdk',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args(); r = inspect(a.gds,a.top,a.pdk)
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    return 0 if r['status'].startswith('PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
