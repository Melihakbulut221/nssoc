#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Place native IHP IO cells, corners and fillers in a provisional 4.0 x 3.2 mm ring.

No core, serial logic, signal routing, seal ring or accepted package is included.
Checks cover LEF footprints and abstract TopMetal1 power-rail abutment only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def parse_lef(text):
    macros = {}
    for m in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1\s*$', text, re.M | re.S):
        name, body = m.groups()
        size = re.search(r'\bSIZE ([\d.]+) BY ([\d.]+) ;', body)
        if not size:
            raise ValueError('Missing cell size: '+name)
        pins = {}
        for pin in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1\s*$', body, re.M | re.S):
            layer = None
            rects = []
            for line in pin[2].splitlines():
                if 'LAYER ' in line:
                    layer = line.split()[1]
                elif 'RECT ' in line and layer == 'TopMetal1':
                    xy = [round(float(v)*1000) for v in line.split()[1:5]]
                    rects.append(xy)
            pins[pin[1]] = rects
        macros[name] = dict(size=[round(float(v)*1000) for v in size.groups()], pins=pins)
    return macros


def box_transform(box, rotation, x, y):
    points = []
    for px, py in [(box[0],box[1]), (box[0],box[3]), (box[2],box[1]), (box[2],box[3])]:
        for _ in range(rotation):
            px, py = -py, px
        points.append((px+x,py+y))
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def contacts(a, b):
    dx = min(a[2],b[2])-max(a[0],b[0])
    dy = min(a[3],b[3])-max(a[1],b[1])
    return dx >= 0 and dy >= 0 and (dx > 0 or dy > 0)


def audit_rails(placements, macros):
    names = ('iovdd','iovss','vdd','vss')
    transformed = []
    footprints = []
    for p in placements:
        w, h = macros[p['master']]['size']
        footprint = box_transform([0,0,w,h],p['rotation'],p['x_nm'],p['y_nm'])
        if footprint[0] < 0 or footprint[1] < 0 or footprint[2] > 4000000 or footprint[3] > 3200000:
            raise ValueError('Cell outside provisional die')
        for other in footprints:
            if min(footprint[2],other[2]) > max(footprint[0],other[0]) and min(footprint[3],other[3]) > max(footprint[1],other[1]):
                raise ValueError('Overlapping LEF footprints')
        footprints.append(footprint)
        transformed.append({n: [box_transform(b,p['rotation'],p['x_nm'],p['y_nm'])
                               for b in macros[p['master']]['pins'][n]] for n in names})
    for i, a in enumerate(transformed):
        b = transformed[(i+1) % len(transformed)]
        for n in names:
            if not any(contacts(x,y) for x in a[n] for y in b[n]):
                raise ValueError(f'Open abstract rail {n}: {placements[i]["instance"]}')
            for other in names:
                if other != n and any(contacts(x,y) for x in a[n] for y in b[other]):
                    raise ValueError('Shorted abstract rails')
    return len(placements)*len(names)


def place(cells, macros):
    width, height, corner = 4000000, 3200000, 180000
    placements = []
    groups = [cells[i*len(cells)//4:(i+1)*len(cells)//4] for i in range(4)]
    origins = [(0,0), (width,0), (width,height), (0,height)]
    for side, group in enumerate(groups):
        ox, oy = origins[side]
        placements.append(dict(instance=f'u_corner_{side}',master='sg13g2_Corner',
                               rotation=side,x_nm=ox,y_nm=oy))
        span = (width if side%2 == 0 else height)-2*corner
        needed = sum(macros[c['master']]['size'][0] for c in group)
        if needed > span:
            raise ValueError('Insufficient pad-row space')
        slack = span-needed
        # Complete each row with native filler sizes read from LEF, not names.
        row = list(group)
        fillers = sorted(((name, entry['size'][0]) for name, entry in macros.items()
                          if name.startswith('sg13g2_Filler')), key=lambda pair: -pair[1])
        for master, step in fillers:
            assert macros[master]['size'][1] == corner and step > 0
            count, slack = divmod(slack,step)
            row += [dict(instance=f'u_fill_{side}_{master}_{j}',master=master) for j in range(count)]
        if slack:
            raise ValueError('Unfillable row remainder')
        offset = corner
        for cell in row:
            assert macros[cell['master']]['size'][1] == corner
            xy = [(offset,0),(width,offset),(width-offset,height),(0,height-offset)][side]
            placements.append(dict(instance=cell['instance'],master=cell['master'],
                                   rotation=side,x_nm=xy[0],y_nm=xy[1]))
            offset += macros[cell['master']]['size'][0]
    return placements


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdk',type=Path,required=True)
    ap.add_argument('--pads',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error('Refusing to replace prior evidence')
    args.output.mkdir(parents=True)
    base = args.pdk/'libs.ref/sg13g2_io'
    lef, gds = base/'lef/sg13g2_io.lef', base/'gds/sg13g2_io.gds'
    macros = parse_lef(lef.read_text()); cells = json.loads(args.pads.read_text())
    assert len({c['instance'] for c in cells}) == len(cells)
    placements = place(cells,macros)
    count = audit_rails(placements,macros)
    for mutation in ('missing_cell','wrong_rotation'):
        bad = [dict(p) for p in placements]
        if mutation == 'missing_cell':
            del bad[1]
        else:
            bad[1]['rotation'] = (bad[1]['rotation']+1)%4
        try:
            audit_rails(bad,macros)
        except ValueError:
            pass
        else:
            raise ValueError('Rail audit accepted '+mutation)
    import klayout.db as db
    layout = db.Layout(); layout.read(str(gds))
    top = layout.create_cell('nssoc_io_floorplan')
    for p in placements:
        cell = layout.cell(p['master'])
        if cell is None:
            raise ValueError('Missing native GDS cell: '+p['master'])
        x = round(p['x_nm']/1000/layout.dbu); y = round(p['y_nm']/1000/layout.dbu)
        top.insert(db.CellInstArray(cell.cell_index(),db.Trans(p['rotation'],False,x,y)))
    output = args.output/'io-floorplan.gds'
    top.write(str(output))
    check = db.Layout();check.read(str(output)); root = check.cell('nssoc_io_floorplan')
    assert root is not None and check.dbu == layout.dbu
    actual = sorted((i.cell.name, i.trans.angle, i.trans.is_mirror(), i.trans.disp.x, i.trans.disp.y)
                    for i in root.each_inst())
    expected = sorted((p['master'],p['rotation'],False,round(p['x_nm']/1000/layout.dbu),
                       round(p['y_nm']/1000/layout.dbu)) for p in placements)
    assert actual == expected, 'GDS placement readback differs from checked manifest'
    pins = {str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__),args.pads,lef,gds]}
    rec = dict(status='PASS_NATIVE_IO_PLACEMENT_AND_ABSTRACT_RAIL_ABUTMENT_ONLY',scope=__doc__,
               input_sha256=pins,placements=placements,die_um=[4000,3200],signal_and_supply_cells=len(cells),
               corners=4,rail_contacts_checked=count,negative_controls=['missing_cell','wrong_rotation'],
               output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
               contains_core=False,signals_routed=False,physical_drc_lvs_accepted=False,
               timing_accepted=False,manufacturing_approval=False)
    (args.output/'result.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(rec['status'],len(placements),count)


if __name__ == '__main__':
    main()
