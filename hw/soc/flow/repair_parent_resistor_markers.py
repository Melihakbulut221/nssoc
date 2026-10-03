#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add exactly 26 missing RC clamp markers; preserve every original GDS byte.

Only the already measured straight source mask intersections may receive 128/0.
This isolated seven-instance parent is not a full-chip or manufacturing result.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from extract_gds_hierarchy import index_stream  # noqa: E402
from io_parent_path_probe import db_module, require  # noqa: E402
from repair_io_resistor_markers import EXPECTED  # noqa: E402

CELL = 'sg13g2_RCClampResistor'
BOXES = EXPECTED[CELL]


def record(kind, dtype=0, data=b''):
    return struct.pack('>HBB', 4 + len(data), kind, dtype) + data


def marker_records():
    data = b''
    for left, bottom, right, top in BOXES:
        points = [(left, bottom), (right, bottom), (right, top), (left, top), (left, bottom)]
        data += (record(8) + record(13, 2, struct.pack('>h', 128)) + record(14, 2, b'\0\0')
                 + record(16, 3, b''.join(struct.pack('>ii', *p) for p in points)) + record(17))
    return data


def insert_records(raw):
    before = index_stream(io.BytesIO(raw))
    require(CELL in before['cells'] and not before['cells'][CELL]['references'], 'Missing or non-flat clamp cell')
    offset = before['cells'][CELL]['end'] - 4
    require(raw[offset:offset+4] == record(7), 'Missing exact ENDSTR')
    addition = marker_records()
    changed = raw[:offset] + addition + raw[offset:]
    after = index_stream(io.BytesIO(changed))
    require(changed[:offset] + changed[offset+len(addition):] == raw, 'Original bytes changed')
    require(before['cells'].keys() == after['cells'].keys(), 'Cell catalog changed')
    for name, old in before['cells'].items():
        if name != CELL:
            require(old['sha256'] == after['cells'][name]['sha256'], 'Unrelated cell bytes changed')
    return changed, dict(insertion_offset=offset, added_bytes=len(addition), added_boundaries=len(BOXES),
        addition_sha256=hashlib.sha256(addition).hexdigest(),
        every_original_byte_preserved=True, original_cell_sha256=before['cells'][CELL]['sha256'])


def region(db, layout, cell, pair):
    index = layout.find_layer(*pair)
    return db.Region() if index is None else db.Region(cell.shapes(index)).merged()


def preflight(db, layout):
    require(layout.dbu == .001, 'Expected 1 nm database unit')
    cell = layout.cell(CELL)
    require(cell is not None and not list(cell.each_inst()), 'Expected flat clamp cell')
    require(region(db, layout, cell, (128, 0)).is_empty(), 'PolyRes marker already present')
    masks = [(5, 0), (28, 0), (14, 0), (111, 0)]
    body = region(db, layout, cell, masks[0])
    for pair in masks[1:]:
        body &= region(db, layout, cell, pair)
    expected = db.Region([db.Box(*box) for box in BOXES])
    require((body ^ expected).is_empty() and body.count() == 26, 'Resistor mask intersection differs')
    require((body & region(db, layout, cell, (1, 0))).is_empty(), 'Resistor overlaps active silicon')
    return dict(cell=CELL, marker_layer=[128, 0], original_marker_empty=True,
        intersection_layers=masks, exact_intersection_boxes=BOXES, no_active_overlap=True)


def verify_geometry(db, before, after):
    require(before.dbu == after.dbu, 'Database unit changed')
    require({c.name for c in before.each_cell()} == {c.name for c in after.each_cell()}, 'Cell catalog changed')
    layers = {(i.layer, i.datatype) for layout in (before, after) for i in layout.layer_infos()}
    for cell in before.each_cell():
        other = after.cell(cell.name)
        def instances(c):
            return sorted((i.cell.name, str(i.cplx_trans), str(i.a), str(i.b), i.na, i.nb)
                          for i in c.each_inst())
        require(instances(cell) == instances(other), 'Instance transform changed: ' + cell.name)
        for pair in layers:
            difference = region(db, before, cell, pair) ^ region(db, after, other, pair)
            if cell.name == CELL and pair == (128, 0):
                difference ^= db.Region([db.Box(*box) for box in BOXES])
            require(difference.is_empty(), 'Unexpected geometry change: ' + str((cell.name, pair)))
            def texts(layout, c):
                index = layout.find_layer(*pair)
                return [] if index is None else sorted(str(s.text) for s in c.shapes(index).each() if s.is_text())
            require(texts(before, cell) == texts(after, other), 'Text changed: ' + cell.name)
    return dict(status='PASS_ALL_GEOMETRY_TEXT_AND_INSTANCE_TRANSFORMS_EXCEPT_26_MARKERS',
                cells=before.cells(), layer_pairs=len(layers))


def repair(source, output):
    db = db_module()
    require(source.is_file() and not source.is_symlink() and source.stat().st_size < 32 * 1024**2,
            'Source is not a bounded regular GDS')
    require(not output.exists(), 'Output already exists')
    raw = source.read_bytes()
    before = db.Layout(); before.read(str(source))
    conditions = preflight(db, before)
    changed, preservation = insert_records(raw)
    with output.open('xb') as stream:
        stream.write(changed)
    after = db.Layout(); after.read(str(output))
    geometry = verify_geometry(db, before, after)
    require(source.read_bytes() == raw, 'Source changed during repair')
    return dict(status='REPAIRED_RECOGNITION_REQUIRES_LVS_AND_DRC', preconditions=conditions,
        byte_preservation=preservation, native_roundtrip=geometry, klayout_version=db.__version__,
        source_sha256=hashlib.sha256(raw).hexdigest(), output_sha256=hashlib.sha256(changed).hexdigest(),
        lvs_accepted=False, manufacturing_approval=False)


def controls(output):
    """Small geometry controls, independent of any chip input or LVS execution."""
    db = db_module(); output.mkdir(parents=True, exist_ok=False)
    layout = db.Layout(); layout.dbu = .001
    cell = layout.create_cell(CELL); top = layout.create_cell('CONTROL')
    for pair in [(5, 0), (28, 0), (14, 0), (111, 0)]:
        for box in BOXES:
            cell.shapes(layout.layer(*pair)).insert(db.Box(*box))
    top.shapes(layout.layer(8, 2)).insert(db.Text('preserve-text', db.Trans(13, 27)))
    top.insert(db.CellInstArray(cell.cell_index(), db.Trans(3, False, 42, 76)))
    source = output/'original.gds'; layout.write(str(source))
    result = repair(source, output/'repaired.gds')
    negatives = {}
    for name in ('existing_marker', 'wrong_body', 'active_overlap', 'hierarchical_cell'):
        bad = layout.dup(); c = bad.cell(CELL)
        if name == 'existing_marker': c.shapes(bad.layer(128, 0)).insert(db.Box(*BOXES[0]))
        if name == 'wrong_body': c.shapes(bad.layer(5, 0)).clear()
        if name == 'active_overlap': c.shapes(bad.layer(1, 0)).insert(db.Box(*BOXES[0]))
        if name == 'hierarchical_cell': c.insert(db.CellInstArray(bad.create_cell('EXTRA').cell_index(), db.Trans()))
        try:
            preflight(db, bad)
        except ValueError as exc:
            negatives[name] = str(exc)
        else:
            raise ValueError('Negative geometry control accepted: ' + name)
    for name in ('changed_text', 'unrelated_polygon', 'instance_transform'):
        changed = db.Layout(); changed.read(str(output/'repaired.gds'))
        top = changed.cell('CONTROL')
        if name == 'changed_text': top.shapes(changed.layer(8, 2)).clear()
        if name == 'unrelated_polygon': top.shapes(changed.layer(8, 0)).insert(db.Box(1, 2, 3, 4))
        if name == 'instance_transform': next(top.each_inst()).trans = db.Trans(43, 76)
        try:
            verify_geometry(db, layout, changed)
        except ValueError as exc:
            negatives[name] = str(exc)
        else:
            raise ValueError('Unexpected alteration accepted: ' + name)
    return dict(status='PASS_TINY_NATIVE_MARKER_CONTROLS', repaired=result, rejected=negatives)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    sub.add_parser('controls').add_argument('output', type=Path)
    p = sub.add_parser('repair')
    for name in ('source', 'output', 'receipt'): p.add_argument(name, type=Path)
    args = parser.parse_args()
    result = controls(args.output) if args.mode == 'controls' else repair(args.source, args.output)
    receipt = args.output/'result.json' if args.mode == 'controls' else args.receipt
    receipt.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__': main()
