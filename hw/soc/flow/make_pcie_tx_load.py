#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate the experimental TX resistor from the unmodified IHP PCell."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdk', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(root/'hw/soc/out'):
        parser.error('Use a fresh directory below hw/soc/out')
    source = args.pdk.resolve()/'libs.tech/klayout/python'
    inputs = [p for p in source.rglob('*') if p.is_file() and p.suffix in ('.py', '.json')]
    inputs.extend([Path(__file__).resolve(), source.parent/'tech/sg13g2.lyp'])
    hashes = {str(p): sha(p) for p in inputs}
    # Do not leave bytecode or edits in the PDK.
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- registers the unmodified native PCells
    layout = pya.Layout()
    cell = layout.create_cell('rsil', 'SG13_dev', {'w': '10u', 'l': '70.215u'})
    if cell is None or cell.is_empty():
        raise RuntimeError('Native resistor PCell generation failed')
    top = layout.create_cell('tx_load_resistor')
    top.insert(pya.DCellInstArray(cell.cell_index(), pya.DTrans()))
    # Label the actual two pin shapes. No guessed pin coordinates or GDS scaling.
    pins = sorted([item.shape().dbbox() for item in cell.begin_shapes_rec(layout.layer(8, 2))],
                  key=lambda box: box.center().y)
    if len(pins) != 2:
        raise RuntimeError('Unexpected resistor terminal geometry')
    for name, box in zip(('PLUS', 'MINUS'), pins):
        top.shapes(layout.layer(8, 25)).insert(pya.DText(name, pya.DTrans(box.center().x, box.center().y)))
    out.mkdir(parents=True)
    gds = out/'tx_load_resistor.gds'
    layout.write(str(gds))
    (out/'schematic.cir').write_text('* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\n'
                                   '* SPDX-' 'License-Identifier: CERN-OHL-W-2.0\n'
                                   '.subckt tx_load_resistor PLUS MINUS\n'
                                   'RLOAD PLUS MINUS BULK rsil w=10u l=70.215u m=1\n'
                                   '.ends tx_load_resistor\n')
    if any(sha(Path(p)) != digest for p, digest in hashes.items()):
        raise RuntimeError('PCell inputs changed during generation')
    result = dict(status='GENERATED_REQUIRES_DRC_LVS_AND_CURRENT_QUALIFICATION',
                  scope='One native load resistor only; implicit untapped substrate. No substrate contact, complete TX or PHY layout.',
                  input_sha256=hashes, output_sha256={p.name: sha(p) for p in out.iterdir()},
                  bbox_um=str(top.dbbox()), klayout_version=pya.__version__,
                  geometry=dict(width_m=10e-6, length_m=70.215e-6), manufacturing_approval=False)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
