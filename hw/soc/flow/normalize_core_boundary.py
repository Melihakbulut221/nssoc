#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replace inherited macro density outlines with the real top-level die outline.

Only annotation layer 189/0 may change. Require exact per-cell preservation of
all other shapes, text and instance transforms after GDS serialization. This
does not insert fill, waive density rules or assert LVS/DRC on the new GDS.
"""
import argparse
import hashlib
import json
from pathlib import Path

import klayout.db as db


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def cell_records(layout):
    result = {}
    for cell in layout.each_cell():
        shapes = {}
        for index in layout.layer_indices():
            info = layout.get_info(index)
            if (info.layer, info.datatype) == (189, 0):
                continue
            values = sorted(shape.to_s() for shape in cell.shapes(index).each())
            if values:
                shapes[str(info)] = hashlib.sha256('\n'.join(values).encode()).hexdigest()
        instances = sorted((layout.cell(inst.cell_index).name, str(inst.cplx_trans),
                            str(inst.a), str(inst.b), inst.na, inst.nb)
                           for inst in cell.each_inst())
        result[cell.name] = dict(shapes=shapes, instances_sha256=hashlib.sha256(
            json.dumps(instances, separators=(',', ':')).encode()).hexdigest(),
            instance_count=len(instances))
    return result


def normalize(source, output, top_name):
    layout = db.Layout()
    layout.read(str(source))
    top = layout.cell(top_name)
    if top is None or len(layout.top_cells()) != 1:
        raise ValueError('Missing or ambiguous top')
    outline = layout.find_layer(189, 4)
    if outline is None:
        raise ValueError('Missing top-level die outline')
    shapes = list(top.shapes(outline).each())
    if len(shapes) != 1 or not shapes[0].is_box():
        raise ValueError('Expected one rectangular top-level die outline')
    die = shapes[0].box
    if top.bbox() != die:
        raise ValueError('Layout extent differs from declared top-level die')
    before = cell_records(layout)
    layer = layout.layer(189, 0)
    removed = {cell.name: cell.shapes(layer).size() for cell in layout.each_cell()
               if not cell.shapes(layer).is_empty()}
    for cell in layout.each_cell():
        cell.shapes(layer).clear()
    top.shapes(layer).insert(die)
    layout.write(str(output))
    reloaded = db.Layout()
    reloaded.read(str(output))
    if cell_records(reloaded) != before or reloaded.dbu != layout.dbu:
        raise ValueError('Non-boundary geometry, text or hierarchy changed')
    b = reloaded.find_layer(189, 0)
    cells = {c.name: c.shapes(b).size() for c in reloaded.each_cell()
             if not c.shapes(b).is_empty()}
    if cells != {top_name: 1} or reloaded.cell(top_name).shapes(b).each().__next__().box != die:
        raise ValueError('Density boundary is not exactly the original die')
    return dict(status='PASS_BOUNDARY_ONLY_TRANSFORM_REQUIRES_NEW_PHYSICAL_CHECKS',
                source_sha256=digest(source), output_sha256=digest(output),
                changed_layer=[189, 0], inherited_boundary_shapes_removed=removed,
                original_die_box_dbu=[die.left, die.bottom, die.right, die.top],
                dbu_um=layout.dbu, unchanged_other_layers_text_and_hierarchy=True,
                cell_records=before, tool_version=db.__version__,
                manufacturing_acceptance=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--top', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = normalize(args.source, args.output/'soc_top.gds', args.top)
    result['script_sha256'] = digest(Path(__file__))
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'])


if __name__ == '__main__':
    main()
