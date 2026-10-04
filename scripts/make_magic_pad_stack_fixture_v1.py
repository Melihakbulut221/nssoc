#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real native no-fill bondpads/TopVia2, both metal routes, eight orientations."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdk',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a = p.parse_args(); out = a.out.resolve();out.mkdir()
    src = a.pdk/'libs.tech/klayout/python';sys.dont_write_bytecode=True
    sys.path[:0] = [str(src),str(src/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    inputs = {str(p):sha(p) for p in [Path(__file__).resolve(),*src.rglob('*.py'),*src.rglob('*.json')]}
    l = pya.Layout(); top = l.create_cell('nssoc_pad_stack_fixture')
    pad = l.create_cell('bondpad','SG13_dev',dict(shape='octagon',stack='nil',fill='nil',diameter='70u',
                        topMetal='TM2',bottomMetal='1',padType='bondpad',padPin='PAD',addFillerEx='t'))
    via = l.create_cell('via_stack','SG13_dev',dict(b_layer='TopMetal1',t_layer='TopMetal2',
                        vn_columns=1,vn_rows=2,vt1_columns=1,vt1_rows=1,vt2_columns=1,vt2_rows=1))
    assert pad and via and not pad.is_empty() and not via.is_empty()
    ports,chains = {},[]
    for i in range(16):
        ori = i % 8; route_metal = 134 if i < 8 else 126
        c = l.create_cell('route_'+str(i)); pb=pad.dbbox();vb=via.dbbox()
        c.insert(pya.DCellInstArray(pad.cell_index(),pya.DTrans(-pb.center().x,-pb.center().y)))
        vy = 80.0 if route_metal == 134 else 0.0
        c.insert(pya.DCellInstArray(via.cell_index(),pya.DTrans(-vb.center().x,vy-vb.center().y)))
        c.shapes(l.layer(route_metal,0)).insert(pya.DBox(-2,0,2,82))
        c.shapes(l.layer(126,0)).insert(pya.DBox(-2,78,42,82))
        t = pya.DTrans(ori % 4,ori >= 4,120.0+(i % 8)*240,120.0+(i//8)*240)
        top.insert(pya.DCellInstArray(c.cell_index(),t))
        for label,layer,b in [('PAD',134,pya.DBox(-5,-5,5,5)),('CORE',126,pya.DBox(38,79,40,81))]:
            name=f'{label}{i:02d}';box=b.transformed(t)
            top.shapes(l.layer(layer,2)).insert(box)
            top.shapes(l.layer(layer,25)).insert(pya.DText(name,pya.DTrans(box.center().x,box.center().y)))
            ports[name]=dict(layer=layer,box=[box.left,box.bottom,box.right,box.top])
        chains.append(dict(index=i,orientation=ori,route_layer=route_metal,ports=[f'PAD{i:02d}',f'CORE{i:02d}']))
    l.write(str(out/'fixture.gds'))
    for fault in ('missing_via_m7','missing_via_m6','wire_open','wrong_layer','pair_short'):
        test=pya.Layout();test.read(str(out/'fixture.gds'));dst=test.cell('nssoc_pad_stack_fixture')
        index=8 if fault=='missing_via_m6' else 0; cell=test.cell('route_'+str(index))
        if fault.startswith('missing_via'):
            insts=[i for i in cell.each_inst() if test.cell(i.cell_index).name.startswith('via_stack')]
            assert len(insts)==1;insts[0].delete()
        elif fault=='wire_open':
            k=test.layer(134,0);r=pya.Region(cell.shapes(k));r-=pya.Region(pya.DBox(-3,50,3,52).to_itype(test.dbu))
            cell.shapes(k).clear();cell.shapes(k).insert(r)
        elif fault=='wrong_layer':
            k=test.layer(134,0);r=pya.Region(cell.shapes(k));assert not r.is_empty()
            cell.shapes(k).clear();cell.shapes(test.layer(67,0)).insert(r)
        else:
            boxes=[ports[f'PAD{i:02d}']['box'] for i in (0,1)]
            points=[((b[0]+b[2])/2,(b[1]+b[3])/2) for b in boxes]
            (x,y),(xx,yy)=points;assert y==yy
            dst.shapes(test.layer(134,0)).insert(pya.DBox(x,y-1,xx,y+1))
        test.write(str(out/(fault+'.gds')))
    assert all(sha(Path(p))==value for p,value in inputs.items())
    (out/'result.json').write_text(json.dumps(dict(top='nssoc_pad_stack_fixture',ports=ports,chains=chains,
        inputs=inputs,outputs={p.name:sha(p) for p in out.iterdir() if p.is_file()},
        scope='Actual native pad no-fill masks and TopVia2; no device/body/stress/PEX claim'),indent=2)+'\n')


if __name__ == '__main__':
    main()
