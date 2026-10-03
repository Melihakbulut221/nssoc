#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Recover missing resistor recognition markers in the pinned c4b8b4e I/O views.

Produces a separate diagnostic library, never edits the installed PDK. Only
27 PolyRes (128/0) rectangles are added. Native tap comparisons remain enabled;
this conversion does not establish I/O, whole-chip or manufacturing acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from normalize_io_cdl import normalize

PINNED = {
    'libs.ref/sg13g2_io/gds/sg13g2_io.gds':
        'aafb713ba3cd547ca48e919ec68eb6a8ed0f09051fed0fad813d3fdb043a4fa5',
    'libs.ref/sg13g2_io/cdl/sg13g2_io.cdl':
        '33217c1d8efc201d7183c1179f58dca4217cf9ab4630f1ddff80d6c4a6e89752',
    'libs.tech/ngspice/models/resistors_mod.lib':
        '98fa5436f6df86dc1dd35e9f16383c4eba4c36d478d7eec203a0295dc1259e51',
}
EXPECTED = {'sg13g2_SecondaryProtection': [(940, 1370, 1940, 3370)],
            'sg13g2_RCClampResistor': [(1650*i, 430, 1650*i+1000, 20430) for i in range(26)]}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonicalize_straight_spacing(text):
    """Canonicalize only explicit b=0 rppd, under the CLI's exact model hash.

    In that model ps occurs only as a default and in
    leff=(b+1)*l+(2/kappa*weff+ps)*b. At b=0, leff=l for every ps.
    All terminals, w/l, multiplicity, resistance and tap parameters stay intact.
    Bent resistors are left unchanged. Missing/duplicate parameters fail closed.
    """
    lines, changes = [], []
    for line in text.splitlines():
        if line.startswith('+'):
            if not lines:
                raise ValueError('Orphan continuation')
            lines[-1] += ' ' + line[1:].strip()
        else:
            lines.append(line)
    for i, line in enumerate(lines):
        if line.lstrip().startswith('*') or '$[rppd]' not in line:
            continue
        if not line.startswith('R'):
            raise ValueError('Unsupported rppd declaration')
        bends = re.findall(r'\bb=([^\s]+)', line)
        spacing = re.findall(r'\bps=([^\s]+)', line)
        if len(bends) != 1 or len(spacing) != 1:
            raise ValueError('Explicit unique b and ps are required')
        if not re.fullmatch(r'\d+', bends[0]):
            raise ValueError('Unsupported bend count')
        if int(bends[0]) != 0:
            continue
        if not re.fullmatch(r'\d+(?:\.\d*)?(?:[eE][-+]?\d+)?[fpnum]?', spacing[0]):
            raise ValueError('Unsupported spacing')
        lines[i] = re.sub(r'\bps=[^\s]+', 'ps=0', line)
        if lines[i] != line:
            changes.append({'before': line, 'after': lines[i]})
    return '\n'.join(lines) + '\n', changes


def repair(layout):
    import klayout.db as db
    if layout.dbu != 0.001:
        raise ValueError('Expected 1 nm database unit')
    additions = {}
    # Validate every cell first; a failed precondition must not partly mutate it.
    for name, boxes in EXPECTED.items():
        cell = layout.cell(name)
        if cell is None or list(cell.each_inst()):
            raise ValueError('Expected flat resistor cell: ' + name)
        def region(pair):
            return db.Region(cell.shapes(layout.layer(*pair))).merged()
        if not region((128, 0)).is_empty():
            raise ValueError('Marker already present: ' + name)
        body = region((5, 0)) & region((28, 0)) & region((14, 0)) & region((111, 0))
        expected = db.Region([db.Box(*box) for box in boxes])
        if not (body ^ expected).is_empty():
            raise ValueError('Resistor masks differ from source CDL geometry: ' + name)
        if not (body & region((1, 0))).is_empty():
            raise ValueError('Resistor overlaps active silicon: ' + name)
        additions[name] = body
    for name, region in additions.items():
        layout.cell(name).shapes(layout.layer(128, 0)).insert(region)
    return {name: region.count() for name, region in additions.items()}


def verify_preservation(before, after):
    """Compare actual round-trip geometry, texts and instance transforms."""
    import klayout.db as db
    if before.dbu != after.dbu:
        raise ValueError('Database unit changed')
    if {c.name for c in before.each_cell()} != {c.name for c in after.each_cell()}:
        raise ValueError('Cell catalog changed')
    layers = {(x.layer, x.datatype) for l in (before, after) for x in l.layer_infos()}
    for c in before.each_cell():
        d = after.cell(c.name)
        def instances(cell):
            return sorted((i.cell.name, str(i.cplx_trans), str(i.a), str(i.b), i.na, i.nb)
                          for i in cell.each_inst())
        if instances(c) != instances(d):
            raise ValueError('Instances changed: ' + c.name)
        for pair in layers:
            a = c.shapes(before.layer(*pair))
            b = d.shapes(after.layer(*pair))
            difference = db.Region(a) ^ db.Region(b)
            expected = db.Region([db.Box(*box) for box in EXPECTED.get(c.name, [])])
            if pair == (128, 0):
                difference ^= expected
            if not difference.is_empty():
                raise ValueError(f'Unexpected geometry change: {c.name} {pair}')
            if sorted(str(s.text) for s in a.each() if s.is_text()) != sorted(
                    str(s.text) for s in b.each() if s.is_text()):
                raise ValueError('Texts changed: ' + c.name)
    return {'cells': before.cells(), 'layer_pairs': len(layers),
            'status': 'PASS_EXACT_GEOMETRY_TEXT_AND_INSTANCE_PRESERVATION_EXCEPT_27_MARKERS'}


def main():
    import klayout.db as db
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdk', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    files = [args.pdk / name for name in PINNED]
    pins = {str(p): digest(p) for p in files}
    if list(pins.values()) != list(PINNED.values()):
        parser.error('Unsupported PDK input hashes')
    args.output.mkdir(exist_ok=False)
    original = db.Layout()
    original.read(str(files[0]))
    layout = original.dup()
    counts = repair(layout)
    gds = args.output / 'sg13g2_io.gds'
    layout.write(str(gds))
    restored = db.Layout()
    restored.read(str(gds))
    preservation = verify_preservation(original, restored)
    text, dialect = normalize(files[1].read_text())
    text, spacing = canonicalize_straight_spacing(text)
    if len(spacing) != 29:
        raise ValueError('Expected 29 explicit straight resistors')
    cdl = args.output / 'sg13g2_io.cdl'
    cdl.write_text(text)
    if any(digest(p) != h for p, h in pins.items()):
        raise ValueError('Inputs changed during conversion')
    receipt = dict(status='REPAIRED_RECOGNITION_REQUIRES_LVS_AND_DRC',
                   input_sha256=pins, source_sha256=digest(__file__),
                   output_sha256={str(p): digest(p) for p in (gds, cdl)},
                   marker_counts=counts, preservation=preservation,
                   dialect_changes=dialect, straight_spacing_changes=spacing,
                   lvs_accepted=False, manufacturing_approval=False)
    (args.output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'])


if __name__ == '__main__':
    main()
