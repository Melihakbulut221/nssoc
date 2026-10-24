#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add real parallel power wiring to the exact failing padded bank; no device change."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

TOP = 'nssoc_pcie_padded_clocked_bank_power_v1'
OLD = 'nssoc_pcie_padded_clocked_bank4_v1'
PINS = {'gds': 'a6973418f56cb907d263854cc735466e0f8706b883f0247d9d398c4e39df0616',
        'wire_l2n': 'ad81e3a4f445968e0b3140c7cd051c8342a320ba44ea371e96f491b638ad72b7',
        'reference': '1521b7b9dd8a3d463c121300a386d762ec0da1239cc4043781298920dc44912d',
        'parent_result': '5cb7191bd667bc0b05701525a872efbc51727487b126fe982121adc9d81262b3'}
METALS = (8, 10, 30, 50, 67, 126, 134)
VIAS = (19, 29, 49, 66, 125, 133)
POWERS = {'AVSS': 15, 'AVDD1V8': 22, 'AVDD2V5': 28, 'AVDD2V3': 127}
LAYERS = {'Metal4': 50, 'Metal5': 67, 'TopMetal1': 126, 'TopMetal2': 134}
SPINES = {'AVSS': (2585, 96, 500, 3430), 'AVDD1V8': (350, 80, 400, 3335),
          'AVDD2V5': (280, 30, 500, 3270), 'AVDD2V3': (2500, 30, 3206, 3440)}
BRIDGES = {'AVSS': (1530, 3390, 80, 16), 'AVDD1V8': (1490, 3310, 50, 12),
           'AVDD2V5': (1510, 3255, 30, 12)}


def pin(path):
    path = Path(path)
    return dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('pdk', 'gds', 'wire_l2n', 'reference', 'parent_result', 'out'):
        ap.add_argument('--' + key.replace('_', '-'), type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists() or not str(a.out.resolve()).startswith('/dev/shm/nssoc-power-overlay-'):
        ap.error('Fresh bounded /dev/shm/nssoc-power-overlay- directory required')
    for key, wanted in PINS.items():
        if pin(getattr(a, key))['sha256'] != wanted:
            raise ValueError('Frozen physical input differs: ' + key)
    source = a.pdk / 'libs.tech/klayout/python'
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib  # noqa: F401
    import make_pcie_padded_clocked_bank as old
    inputs = {str(p): pin(p) for p in [Path(__file__), Path(old.__file__), a.gds, a.wire_l2n,
                                      a.reference, a.parent_result, *source.rglob('*.py'), *source.rglob('*.json')]}
    layout = pya.Layout(); layout.read(str(a.gds)); top = layout.cell(OLD)
    if top is None or layout.dbu != .001:
        raise ValueError('Exact source top/grid differs')
    top.name = TOP
    wire = pya.LayoutToNetlist(); wire.read(str(a.wire_l2n))
    nets = {n.cluster_id: n for n in wire.netlist().top_circuit().each_net()}
    before = {layer: pya.Region(top.begin_shapes_rec(layout.layer(layer, 0))).merged()
              for layer in METALS + VIAS}
    owners = {name: {layer: wire.shapes_of_net(nets[num], wire.layer_by_name('gds_' + str(layer)), True).merged()
                     for layer in METALS + VIAS} for name, num in POWERS.items()}
    added = {name: {layer: pya.Region() for layer in METALS + VIAS} for name in POWERS}
    routes, via_rows, conflicts = [], [], []
    a.out.mkdir()

    def save_failure(error):
        (a.out/'failure.json').write_text(json.dumps(dict(error=str(error), conflicts=conflicts,
            routes=routes, vias=via_rows, inputs=inputs, candidate_accepted=False), indent=2)+'\n')

    def collision_for(name, layer, region):
        if layer not in before:
            raise ValueError('Overlay may only add explicit routing material')
        other = before[layer] - owners[name][layer]
        for peer in POWERS:
            if peer != name:
                other += added[peer][layer]
        # Pure conductor preflight, separate from the mandatory foundry DRC.
        spacing = {8: 180, 10: 200, 30: 200, 50: 200, 67: 200, 126: 1640, 134: 2000}.get(layer, 180)
        return region & other.sized(spacing-1)

    def deposit(name, layer, region, context):
        collision = collision_for(name, layer, region)
        if not collision.is_empty():
            conflicts.append(dict(net=name, layer=layer, context=context, overlap=str(collision),
                                  proposed=str(region)))
            raise ValueError('Other-net geometry/clearance conflict: ' + context)
        if not (region - pya.Region(pya.Box(0, 0, 2940000, 3440000))).is_empty():
            raise ValueError('Overlay leaves fixed macro boundary')
        top.shapes(layout.layer(layer, 0)).insert(region)
        added[name][layer] += region

    def rectangle(name, metal, coords, context):
        b = pya.DBox(*coords).to_itype(layout.dbu)
        deposit(name, LAYERS[metal], pya.Region(b), context)
        routes.append(dict(net=name, layer=metal, rect_nm=[b.left,b.bottom,b.right,b.top], context=context))

    def via_material(lower, upper, x, y, columns, rows):
        cell = layout.create_cell('via_stack', 'SG13_dev', dict(b_layer=lower, t_layer=upper,
            vn_columns=columns, vn_rows=rows, vt1_columns=columns, vt1_rows=rows,
            vt2_columns=columns, vt2_rows=rows))
        if cell is None or cell.is_empty():
            raise ValueError('Native via PCell failed')
        center = cell.dbbox().center()
        tr = pya.Trans(round((x-center.x)/layout.dbu), round((y-center.y)/layout.dbu))
        materials={}
        for layer in METALS + VIAS:
            reg = pya.Region(cell.begin_shapes_rec(layout.layer(layer, 0))).transformed(tr)
            if not reg.is_empty():
                materials[layer]=reg
        return materials

    def via(name, lower, upper, x, y, context, columns=1, rows=1):
        # Deposit actual native via material only after all landing layers pass.
        materials=via_material(lower,upper,x,y,columns,rows)
        for layer,reg in materials.items():
            if not collision_for(name,layer,reg).is_empty():
                raise ValueError('Native via landing clearance: '+context+':'+str(layer))
        for layer,reg in materials.items():
            deposit(name, layer, reg, context + ':' + str(layer))
        via_rows.append(dict(net=name, lower=lower, upper=upper, center_um=[x,y],
                             columns=columns, rows=rows, context=context))

    try:
        for name, (x,w,lo,hi) in SPINES.items():
            rectangle(name, 'TopMetal2', (x-w/2,lo,x+w/2,hi), name+':independent_spine')
        for name, (padx,y,w,stem) in BRIDGES.items():
            x=SPINES[name][0]
            rectangle(name, 'TopMetal2', (padx-stem/2,y,padx+stem/2,3440), name+':public_pad_stem')
            rectangle(name, 'TopMetal1', (min(padx,x),y-w/2,max(padx,x),y+w/2), name+':public_pad_bridge')
            via(name,'TopMetal1','TopMetal2',padx,y,name+':public_pad_array',3,8)
            via(name,'TopMetal1','TopMetal2',x,y,name+':spine_array',8,8)
        # Native long horizontal buses and macro power feeders provide exact
        # geometry-derived attachment rows. No guessed device-name shortcut.
        rails={name:{} for name in POWERS}
        for name in POWERS:
            for layer in (67,126):
                for poly in owners[name][layer].decompose_trapezoids_to_region().each():
                    b=poly.bbox()
                    if poly.area()!=b.area() or b.width()<100000 or b.height()>10000:
                        continue
                    y=round(b.center().y/5)*5
                    # Thick RX supply rectangles are three decompositions of
                    # one native8um rail; the source middle strip fixes its row.
                    if name=='AVDD1V8' and layer==67 and b.height()!=2000:
                        continue
                    rails[name].setdefault(y,[]).append((layer,b))
            for y, pieces in sorted(rails[name].items()):
                yy=y/1000; x=SPINES[name][0]
                # The2.3V spine already has a native via at its old feed.
                # Offset the new array6um inside the30um spine; preserve the
                # original via instead of overlapping its unaligned cuts.
                contact_x=x+6 if name=='AVDD2V3' else x
                left=min(x,min(b.left/1000 for _,b in pieces));right=max(contact_x+3,max(b.right/1000 for _,b in pieces))
                rectangle(name,'TopMetal1',(left,yy-4,right,yy+4),name+':parallel_rail')
                via(name,'TopMetal1','TopMetal2',contact_x,yy,name+':rail_spine',3,2)
                for layer,b in pieces:
                    if layer!=67:continue
                    count=max(1,b.width()//80000)
                    for i in range(count):
                        xx=round((b.left+(i+.5)*b.width()/count)/5)*.005
                        via(name,'Metal5','TopMetal1',xx,yy,name+':native_M5_parallel_contact',2,1)
        # Bypass long1.2um M4 power legs on actual upper metal. Existing
        # geometry remains. All other-net intermediate landing metals checked.
        branch_count={name:0 for name in POWERS}
        for name in POWERS:
            for poly in owners[name][50].decompose_trapezoids_to_region().each():
                b=poly.bbox()
                if poly.area()!=b.area() or b.height()<30000 or b.width()!=1200:
                    continue
                x=b.center().x/1000
                ys=[y/1000 for y in rails[name] if abs(y-b.top)<3000]
                if len(ys)!=1:
                    raise ValueError('Power branch does not bind one actual supply rail')
                high=ys[0]
                low=None
                # Keep exact PCell/MIM geometry. Find a real landing on the
                # existing branch above any crossing plate, never delete it.
                for offset in (3,8,16,24):
                    trial=b.bottom/1000+offset
                    if trial>=high-3:continue
                    materials=via_material('Metal4','TopMetal2',x,trial,1,1)
                    if all(collision_for(name,layer,reg).is_empty() for layer,reg in materials.items()):
                        low=trial;break
                if low is None:raise ValueError('No physical via landing on original power leg')
                rectangle(name,'TopMetal2',(x-2,low,x+2,high),name+':parallel_M4_leg')
                via(name,'Metal4','TopMetal2',x,low,name+':native_M4_leg_contact')
                via(name,'TopMetal1','TopMetal2',x,high,name+':leg_rail_contact')
                branch_count[name]+=1
        # Every pre-existing drawing polygon remains; no circuit PCell, pin,
        # finite body contact, device or old routing shape is deleted.
        for layer, reg in before.items():
            after=pya.Region(top.begin_shapes_rec(layout.layer(layer,0)))
            if not (reg-after).is_empty():raise ValueError('Original routing material lost')
        parent=json.loads(a.parent_result.read_text())
        ports={n:(r['layer'],pya.DBox(*r['rect_um'])) for n,r in parent['ports'].items()}
        text=a.reference.read_text().replace('.subckt '+OLD+' ','.subckt '+TOP+' ').replace('.ends '+OLD,'.ends '+TOP)
        (a.out/'schematic.cir').write_text(text)
        (a.out/(TOP+'.lef')).write_text(old.lef(pya,layout.dbu,ports).replace('MACRO '+OLD,'MACRO '+TOP).replace('END '+OLD,'END '+TOP))
        layout.write(str(a.out/(TOP+'.gds')))
        if any(pin(path)!=expected for path,expected in inputs.items()):raise ValueError('Generation inputs changed')
        result=dict(status='GENERATED_PARALLEL_POWER_OVERLAY_REQUIRES_NATIVE_DRC_LVS_RC',inputs=inputs,
            routes=routes,vias=via_rows,branch_count=branch_count,ports=parent['ports'],bbox_um=parent['bbox_um'],
            device_geometry_unchanged=True,old_routing_preserved=True,no_body_union=True,
            full_pex_qualified=False,clock_load_qualified=False,bank_accepted=False,
            outputs={p.name:pin(p) for p in a.out.iterdir() if p.is_file()})
        (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(result['status'],branch_count,len(via_rows))
    except Exception as error:
        save_failure(error)
        raise


if __name__=='__main__':
    main()
