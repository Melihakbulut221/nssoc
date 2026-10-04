#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Unmodified native ESD PCells in eight orientations, plus real GDS faults."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdk', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve(); out.mkdir()
    source = a.pdk/'libs.tech/klayout/python'
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    inputs = {str(x): sha(x) for x in [Path(__file__).resolve(),
              *source.rglob('*.py'), *source.rglob('*.json')]}
    l = pya.Layout(); top = l.create_cell('nssoc_esd_fixture')
    ports, devices, refs, instances = {}, [], [], []
    for index in range(32):
        model = 'diodevdd_2kv' if index < 16 else 'diodevss_2kv'
        ori = index % 8
        c = l.create_cell('esd', 'SG13_dev', {'model': model})
        assert c and not c.is_empty()
        t = pya.DTrans(ori % 4, ori >= 4, 60.0+(index % 8)*70, 60.0+(index//8)*80)
        inst = top.insert(pya.DCellInstArray(c.cell_index(), t)); instances.append(inst)
        boxes = {ly: sorted([s.dbbox() for s in c.each_shape(l.layer(ly,2))],
                            key=lambda b: b.center().x) for ly in (8,10)}
        assert len(boxes[8]) == 1 and len(boxes[10]) == 2
        mapping = {'PAD': (10,boxes[10][0]),
                   'VDD': (10,boxes[10][1]) if index < 16 else (8,boxes[8][0]),
                   'SUB': (8,boxes[8][0]) if index < 16 else (10,boxes[10][1])}
        for label, (layer, box) in mapping.items():
            name = 'SUB' if label == 'SUB' else f'{label}{index:02d}'
            b = box.transformed(t)
            top.shapes(l.layer(layer,2)).insert(b)
            top.shapes(l.layer(layer,25)).insert(pya.DText(name,pya.DTrans(b.center().x,b.center().y)))
            ports.setdefault(name,[]).append(dict(layer=layer,box=[b.left,b.bottom,b.right,b.top]))
        devices.append(dict(index=index, model=model, orientation=ori,
                            terminals=[f'VDD{index:02d}',f'PAD{index:02d}','SUB']))
        refs.append(f'D{index} VDD{index:02d} PAD{index:02d} SUB {model} m=1')
    l.write(str(out/'fixture.gds'))
    (out/'schematic.cir').write_text('.subckt nssoc_esd_fixture '+' '.join(ports)+'\n'
                                   +'\n'.join(refs)+'\n.ends nssoc_esd_fixture\n')
    for fault in ('width_vdd','width_vss','removed_device','pad_open','pad_short','collector_open','excluded_geometry','well_split'):
        test = pya.Layout(); test.read(str(out/'fixture.gds'))
        dst = test.cell('nssoc_esd_fixture')
        index = 16 if fault in ('width_vss','collector_open','well_split') else 0
        found = [i for i in dst.each_inst() if i.dtrans == instances[index].dtrans]
        assert len(found) == 1
        inst = found[0]
        if fault == 'removed_device':
            inst.delete()
        else:
            c = test.create_cell('actual_'+fault); c.copy_tree(test.cell(inst.cell_index)); inst.cell_index = c.cell_index()
            if fault.startswith('width'):
                shapes = c.shapes(test.layer(1,0))
                chosen = [s for s in shapes.each() if s.dbbox() == pya.DBox(4.23,4.73,5.49,32.51)]
                assert len(chosen) == 1
                chosen[0].delete(); shapes.insert(pya.DBox(4.23,4.73,5.29,32.51))
            elif fault == 'pad_open':
                shapes = c.shapes(test.layer(19,0))
                chosen = [s for s in shapes.each() if 4 < s.dbbox().center().x < 6]
                assert len(chosen) == 72
                for s in chosen:
                    s.delete()
            elif fault == 'pad_short':
                c.shapes(test.layer(10,0)).insert(pya.DBox(-.5,18.4,9.5,18.6))
            elif fault == 'collector_open':
                shapes = c.shapes(test.layer(6,0))
                chosen = [s for s in shapes.each() if s.dbbox().center().x < 1 or s.dbbox().center().x > 8.5
                          or s.dbbox().center().y < 1 or s.dbbox().center().y > 36]
                assert len(chosen) == 242
                for s in chosen:
                    s.delete()
            elif fault == 'well_split':
                li = test.layer(31,0)
                region = pya.Region(c.begin_shapes_rec(li))
                cut = pya.Region(pya.DBox(-1,18.4,11,18.6).to_itype(test.dbu))
                c.shapes(li).clear(); c.shapes(li).insert(region-cut)
            else:
                c.shapes(test.layer(111,0)).insert(pya.DBox(4.3,5,5,6))
        test.write(str(out/(fault+'.gds')))
    # Generic operator regression independent of any device or model name.
    test = pya.Layout(); c = test.create_cell('interact_probe')
    candidates = [[0,0,10,10],[20,0,30,10],[40,0,50,10],[60,0,70,4],[60,4,64,10]]
    queries = [[2,2,3,3],[30,2,31,3],[62,8,63,9]]
    for layer, rows in [(200,candidates),(201,queries)]:
        for b in rows:
            c.shapes(test.layer(layer,0)).insert(pya.DBox(*b))
    test.write(str(out/'interact.gds'))
    (out/'interact-expected.json').write_text(json.dumps(dict(
        interacting=candidates[:2]+candidates[3:], noninteracting=[candidates[2]]),indent=2)+'\n')
    assert all(sha(Path(x)) == h for x,h in inputs.items())
    record = dict(top='nssoc_esd_fixture', inputs=inputs, ports=ports, devices=devices,
                  outputs={x.name:sha(x) for x in out.iterdir() if x.is_file()},
                  scope='32 literal native ESD PCells, both ordinary 2-kV families, 8 orientations twice; no stress/PEX qualification')
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__ == '__main__':
    main()
