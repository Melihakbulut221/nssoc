#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual native PCells: 108 finite substrate ties, 24 well ties, geometry faults."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdk', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir()
    source = args.pdk/'libs.tech/klayout/python'
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    from sg13g2_pycell_lib.ihp.utility_functions import CbTapCalc

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p): sha(p) for p in [Path(__file__).resolve(), *source.rglob('*.py'),
                                    *source.rglob('*.json')]}
    layout = pya.Layout()
    top = layout.create_cell('nssoc_finite_taps')
    ports, devices, refs, instances = {}, [], [], []

    def port(name, layer, box):
        top.shapes(layout.layer(layer, 2)).insert(box)
        top.shapes(layout.layer(layer, 25)).insert(pya.DText(
            name, pya.DTrans(box.center().x, box.center().y)))
        ports[name] = dict(layer=layer, box=[box.left, box.bottom, box.right, box.top])

    for index in range(132):
        model = 'ptap1' if index < 108 else 'ntap1'
        ordinal = index if index < 108 else index-108
        w, length = [(0.78, 0.78), (2.0, 2.0), (2.0, 3.0)][ordinal//8 % 3]
        if index >= 24 and index < 108:
            w = length = 2.0
        ori = ordinal % 8
        cell = layout.create_cell(model, 'SG13_dev', {'w': f'{w}u', 'l': f'{length}u'})
        assert cell and not cell.is_empty()
        transform = pya.DTrans(ori % 4, ori >= 4, 10+(index % 12)*15, 10+(index//12)*15)
        inst = top.insert(pya.DCellInstArray(cell.cell_index(), transform))
        instances.append(inst)
        boxes = [s.dbbox() for s in cell.each_shape(layout.layer(8, 2))]
        assert len(boxes) == (1 if model == 'ptap1' else 2)
        boxes.sort(key=lambda b: b.area())
        assert all((b & boxes[0]) == boxes[0] for b in boxes)
        name = f'T{index:03d}'
        port(name, 8, boxes[0].transformed(transform))
        body = 'BULK'
        if model == 'ntap1':
            well = [s.dbbox() for s in cell.each_shape(layout.layer(31, 2))]
            assert well
            assert all(b == well[0] for b in well)
            body = f'W{index:03d}'
            port(body, 31, well[0].transformed(transform))
        resistance = CbTapCalc('R', 0.0, length*1e-6, w*1e-6, model)
        devices.append(dict(tie=name, body=body, model=model, w_um=w, l_um=length,
                            orientation=ori, resistance_ohm=resistance))
        refs.append(f'R{index} {name} {body} {model} A={w*length:.12g}p P={2*(w+length):.12g}u')
    layout.write(str(out/'fixture.gds'))
    (out/'schematic.cir').write_text('.subckt nssoc_finite_taps '+' '.join(ports)+'\n'
                                   +'\n'.join(refs)+'\n.ends nssoc_finite_taps\n')
    # Literal native geometry changes; positives are never replaced or patched.
    for fault in ('missing_contact', 'width_change', 'tie_short'):
        test = pya.Layout(); test.read(str(out/'fixture.gds'))
        target = test.cell('nssoc_finite_taps')
        if fault == 'tie_short':
            a, b = [ports[f'T{i:03d}']['box'] for i in (24, 25)]
            ax, ay = (a[0]+a[2])/2, (a[1]+a[3])/2
            bx, by = (b[0]+b[2])/2, (b[1]+b[3])/2
            target.shapes(test.layer(8, 0)).insert(pya.DBox(min(ax,bx)-.1, ay-.1, max(ax,bx)+.1, ay+.1))
            target.shapes(test.layer(8, 0)).insert(pya.DBox(bx-.1, min(ay,by)-.1, bx+.1, max(ay,by)+.1))
        else:
            chosen = [i for i in target.each_inst() if i.dtrans == instances[24].dtrans]
            assert len(chosen) == 1
            inst = chosen[0]; original = test.cell(inst.cell_index)
            copy = test.create_cell('fault_'+fault); copy.copy_tree(original)
            inst.cell_index = copy.cell_index()
            if fault == 'missing_contact':
                assert not copy.shapes(test.layer(6, 0)).is_empty()
                copy.shapes(test.layer(6, 0)).clear()
            else:
                active = copy.shapes(test.layer(1, 0))
                shapes = list(active.each()); assert len(shapes) == 1
                box = shapes[0].dbbox(); active.clear()
                active.insert(pya.DBox(box.left, box.bottom, box.right-.2, box.top))
        test.write(str(out/(fault+'.gds')))
    assert all(sha(Path(p)) == h for p, h in pins.items())
    record = dict(top='nssoc_finite_taps', inputs=pins, ports=ports, devices=devices,
                  outputs={p.name: sha(p) for p in out.iterdir() if p.is_file()},
                  scope='132 literal native PCells; 108 ptap and 24 ntap; no bank acceptance')
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')


if __name__ == '__main__':
    main()
