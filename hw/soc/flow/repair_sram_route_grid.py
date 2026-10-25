#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Repair six source-bound SRAM Metal2 routes; require fresh physical acceptance.

Only the explicitly audited polygons may change. Every other shape, label and
instance must survive a serialized GDS round trip unchanged. No rules change.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import klayout.db as db


EXPECTED = {'SP6TSRAM512x64': 2, 'DP8TSRAMDP256x16': 4}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def shape_text(shape):
    return ('P:' + shape.polygon.to_s() if shape.is_box() or shape.is_polygon()
            else 'S:' + shape.to_s())


def snapshot(layout):
    result = {}
    for cell in layout.each_cell():
        layers = {}
        for index in layout.layer_indexes():
            values = sorted(shape_text(s) for s in cell.shapes(index).each())
            if values:
                layers[layout.get_info(index).to_s()] = hashlib.sha256(
                    '\n'.join(values).encode()).hexdigest()
        instances = sorted((i.cell.name, i.cplx_trans.to_s(), i.a.to_s(),
                            i.b.to_s(), i.na, i.nb) for i in cell.each_inst())
        result[cell.name] = dict(layers=layers, instance_count=len(instances),
                                instances_sha256=hashlib.sha256(json.dumps(
                                    instances, separators=(',', ':')).encode()).hexdigest())
    return result


def rounded_polygon(polygon):
    if polygon.holes():
        raise ValueError('Unexpected hole in SRAM clock route')
    old = list(polygon.each_point_hull())
    new = [db.Point(((p.x+2)//5)*5, ((p.y+2)//5)*5) for p in old]
    if old == new:
        raise ValueError('Target polygon already on grid')
    for a, b in zip(new, new[1:] + new[:1]):
        if a == b or (a.x != b.x and a.y != b.y):
            raise ValueError('Collapsed or non-Manhattan route')
    output = db.Polygon(new)
    if output.num_points_hull() != len(old) or output.area() <= 0:
        raise ValueError('Route topology changed')
    maximum = max(max(abs(a.x-b.x), abs(a.y-b.y)) for a, b in zip(old, new))
    if maximum > 2:
        raise ValueError('Excessive coordinate displacement')
    return output, maximum


def repair(source, audit, output):
    expected_sha = audit.get('input_sha256', {}).get(str(source.resolve()))
    if not expected_sha or digest(source) != expected_sha:
        raise ValueError('Grid audit is not bound to this source')
    targets = audit.get('offgrid_polygons', [])
    if (audit.get('dbu_um') != .001 or audit.get('grid_dbu') != 5
            or audit.get('offgrid_instances')
            or Counter(row['cell'] for row in targets) != EXPECTED
            or any(row['layer'] != '10/0' for row in targets)):
        raise ValueError('Repair scope differs from the six audited Metal2 routes')
    keys = {(row['cell'], row['polygon']) for row in targets}
    if len(keys) != 6:
        raise ValueError('Duplicate repair target')
    layout = db.Layout()
    layout.read(str(source))
    if layout.dbu != .001 or len(layout.top_cells()) != 1:
        raise ValueError('Unexpected GDS unit or top cells')
    before = snapshot(layout)
    original_bbox = layout.top_cell().bbox()
    modified = []
    layer = layout.find_layer(10, 0)
    expected_routes = {}
    for name in EXPECTED:
        cell = layout.cell(name)
        if cell is None:
            raise ValueError('Missing SRAM cell')
        expected_routes[name] = Counter(shape_text(s) for s in cell.shapes(layer).each())
        for shape in cell.shapes(layer).each():
            if not (shape.is_box() or shape.is_polygon()):
                continue
            old = shape.polygon
            key = name, old.to_s()
            if key not in keys:
                continue
            new, maximum = rounded_polygon(old)
            modified.append(dict(cell=name, before=old.to_s(), after=new.to_s(),
                                 maximum_displacement_nm=maximum,
                                 xor_area_um2=(db.Region(old)^db.Region(new)).area()*layout.dbu**2))
            expected_routes[name]['P:' + old.to_s()] -= 1
            expected_routes[name]['P:' + new.to_s()] += 1
            shape.polygon = new
            keys.remove(key)
    if keys or len(modified) != 6:
        raise ValueError('Missing source polygons from grid audit')
    for name, values in expected_routes.items():
        actual = Counter(shape_text(s) for s in layout.cell(name).shapes(layer).each())
        if actual != +values:
            raise ValueError('Unrelated Metal2 route changed')
    expected = snapshot(layout)
    # Only the exact two cell/layer pairs may differ before serialization.
    for name in before:
        if (before[name]['instances_sha256'] != expected[name]['instances_sha256']
                or before[name]['instance_count'] != expected[name]['instance_count']):
            raise ValueError('Instance graph changed')
        for layer_name in set(before[name]['layers']) | set(expected[name]['layers']):
            if name in EXPECTED and layer_name == '10/0':
                continue
            if before[name]['layers'].get(layer_name) != expected[name]['layers'].get(layer_name):
                raise ValueError('Unrelated geometry or label changed')
    output.mkdir(parents=True, exist_ok=False)
    final = output/'soc_top.gds'
    layout.write(str(final))
    reloaded = db.Layout()
    reloaded.read(str(final))
    if (reloaded.dbu != layout.dbu or snapshot(reloaded) != expected
            or reloaded.top_cell().bbox() != original_bbox):
        raise ValueError('Serialized layout differs from the intended repair')
    macros = {}
    for name in EXPECTED:
        options = db.SaveLayoutOptions()
        options.select_cell(reloaded.cell(name).cell_index())
        path = output/(name+'.gds')
        reloaded.write(str(path), options)
        macros[name] = dict(path=str(path), sha256=digest(path))
    if digest(source) != expected_sha:
        raise ValueError('Source changed during repair')
    return dict(status='PASS_SCOPED_ROUTE_GRID_REPAIR_REQUIRES_PHYSICAL_CHECKS',
                source_sha256=expected_sha, output_sha256=digest(final),
                dbu_um=.001, grid_nm=5, modifications=modified,
                preserved_original_hierarchy=True, unchanged_other_geometry_and_text=True,
                cell_records=expected, macro_exports=macros, tool_version=db.__version__,
                full_drc_lvs_timing_acceptance=False, manufacturing_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--audit', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = repair(args.source, json.loads(args.audit.read_text()), args.output)
    result['input_sha256'] = {str(p.resolve()): digest(p) for p in [
        args.source, args.audit, Path(__file__)]}
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'])


if __name__ == '__main__':
    main()
