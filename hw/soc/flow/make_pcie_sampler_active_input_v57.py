#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native active-input sampler: one existing reference, original latches and real gain geometry."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

TOP = "nssoc_rx_sampler_active_input_layout_v57"
PORTS = ("DP", "DN", "QP", "QN", "CLKP", "CLKN", "AVDD", "AVSS", "SUB", "IREF")
CIRCUIT = "hw/soc/analog/pcie/rx_sampler_active_input_v57.spice"
CIRCUIT_SHA256 = "05f5e3e389643704cbea8ccf9a700237f05a2e77b639db48d7ea7f18103d1ade"
TAPS = 25
BASE_TAPS = 17
GAIN_NAMES = ("GP","GN","GT0","GT1","UP","UN","DP","DN")
SHIFT_X = 320.


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def devices(text):
    """Flatten only the exact three fixed subcircuits, preserving terminal order."""
    if hashlib.sha256(text.encode()).hexdigest() != CIRCUIT_SHA256:
        raise ValueError("Sampler circuit differs from the frozen v32 source")
    definitions = {}
    for line in text.splitlines():
        f = line.upper().split()
        if not f or f[0].startswith("*"):
            continue
        if f[0] == ".SUBCKT":
            current = (f[2:], [])
            definitions[f[1]] = current
        elif f[0] != ".ENDS":
            current[1].append(f)
    rows = []

    def expand(cell, nets, prefix):
        formal, body = definitions[cell]
        mapping = dict(zip(formal, nets, strict=True))

        def net(n):
            return mapping[n] if n in mapping else prefix + n

        for fields in body:
            name = prefix + fields[0][1:]
            if len(fields) > 5 and fields[5] == "NPN13G2":
                rows.append(dict(kind="hbt", name=name, nets=[net(v) for v in fields[1:5]],
                                 nx=int(fields[6].removeprefix("NX="))))
            elif len(fields) > 5 and fields[5] == "SG13_LV_NMOS":
                params = dict(v.split("=") for v in fields[6:])
                assert set(params) == {"W", "L", "NG"} and params["NG"] == "1"
                rows.append(dict(kind="nmos", name=name, nets=[net(v) for v in fields[1:5]],
                                 width_um=float(params["W"][:-1]), length_um=float(params["L"][:-1]), ng=1))
            elif len(fields) > 4 and fields[4] == "RPPD":
                rows.append(dict(kind="resistor", name=name, nets=[net(v) for v in fields[1:4]],
                                 width_um=float(fields[5][2:-1]), length_um=float(fields[6][2:-1])))
            else:
                expand(fields[-1], [net(v) for v in fields[1:-1]], name + "_")
    expand("NSSOC_RX_SAMPLER_ACTIVE_INPUT_V57", list(PORTS), "")
    if len(rows) != 41 or {k: sum(r["kind"] == k for r in rows) for k in ("hbt", "nmos", "resistor")} != {"hbt": 18, "nmos": 11, "resistor": 12}:
        raise ValueError("Sampler primitive census differs")
    assert all(1 <= r["nx"] <= 10 for r in rows if r["kind"] == "hbt")
    return rows


def physical_reference(text):
    lines = ["* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
             "* SPDX-License-Identifier: CERN-OHL-W-2.0",
             ".subckt " + TOP + " " + " ".join(PORTS)]
    for row in devices(text):
        nets = " ".join("BULK" if n == "SUB" else n for n in row["nets"])
        if row["kind"] == "hbt":
            lines.append(f"Q{row['name']} {nets} npn13G2 Nx={row['nx']} we=0.07u le=0.9u m=1")
        elif row["kind"] == "nmos":
            lines.append(f"M{row['name']} {nets} sg13_lv_nmos w={row['width_um']:g}u l={row['length_um']:g}u ng=1 m=1")
        else:
            lines.append(f"R{row['name']} {nets} rppd w={row['width_um']:g}u l={row['length_um']:g}u b=0 m=1")
    lines += [f"RTAP{i} SUB BULK ptap1 A=4p P=8u" for i in range(BASE_TAPS)]
    for i,name in enumerate(GAIN_NAMES):
        length=20 if name in ("GT0","GT1") else 2
        lines.append(f"RGAIN_TAP{i} SUB BULK ptap1 A={2*length}p P={2*(2+length)}u")
    return "\n".join(lines + [".ends " + TOP, ""])


def use_direction(name):
    if name == "AVDD":
        return "POWER", "INOUT"
    if name in ("AVSS", "SUB"):
        return "GROUND", "INOUT"
    return "SIGNAL", "OUTPUT" if name in ("QP", "QN") else "INPUT"


def lef(pya, dbu, box, ports):
    if set(ports) != set(PORTS):
        raise ValueError("Sampler physical pin inventory differs")
    result = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;',
              "MACRO " + TOP, "  CLASS BLOCK ;", "  ORIGIN 0 0 ;",
              f"  SIZE {box.width():.3f} BY {box.height():.3f} ;"]
    for name in PORTS:
        metal, b = ports[name]
        use, direction = use_direction(name)
        result += ["  PIN " + name, "    DIRECTION " + direction + " ;", "    USE " + use + " ;",
                   "    PORT", "      LAYER " + metal + " ;",
                   f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;",
                   "    END", "  END " + name]
    result += ["  OBS"]
    for metal in ("Metal1", "Metal2", "Metal3", "Metal4", "Metal5", "TopMetal1", "TopMetal2"):
        region = pya.Region(box.to_itype(dbu))
        for layer, b in ports.values():
            if layer == metal:
                region -= pya.Region(b.to_itype(dbu))
        result += ["    LAYER " + metal + " ;"]
        for polygon in region.decompose_trapezoids_to_region().each():
            if polygon.area() != polygon.bbox().area():
                raise ValueError("Nonrectangular obstruction")
            b = polygon.bbox().to_dtype(dbu)
            result += [f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;"]
    return "\n".join(result + ["  END", "END " + TOP, "END LIBRARY", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--placement-baseline",type=Path,required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not (out.is_relative_to(root / "hw/soc/out") or
                           out.is_relative_to(Path("/dev/shm")) and out.name.startswith("nssoc-sampler-")):
        parser.error("Use a fresh project or /dev/shm/nssoc-sampler- directory")
    circuit = root / CIRCUIT
    rows = devices(circuit.read_text())
    source = args.pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    inputs = [args.placement_baseline, *source.rglob("*.py"), *source.rglob("*.json"), lyp, circuit, Path(__file__).resolve()]
    pins = {str(path): sha(path) for path in inputs}
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- native PCell registration

    layout = pya.Layout()
    top = layout.create_cell(TOP)
    layers = {prop.findtext("name")[:-8]: int(prop.findtext("source").split("/")[0])
              for prop in ET.parse(lyp).getroot().iter("properties")
              if prop.findtext("name", "").endswith(".drawing")}
    records, routes, vias, terminals, ports = [], [], [], {}, {}

    def pc(name, parameters):
        cell = layout.create_cell(name, "SG13_dev", parameters)
        if cell is None or cell.is_empty():
            raise ValueError("Native PCell failed: " + name)
        return cell

    def instance(cell, x, y):
        trans = pya.DTrans(round(x / .005) * .005, round(y / .005) * .005)
        top.insert(pya.DCellInstArray(cell.cell_index(), trans))
        return trans

    def rect(metal, x1, y1, x2, y2):
        box = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers["Metal" + str(metal)], 0)).insert(box)
        return box

    def via(bottom, upper, x, y, net, cols=2, rows=1):
        cell = pc("via_stack", dict(b_layer="Metal" + str(bottom), t_layer="Metal" + str(upper),
                                    vn_columns=cols, vn_rows=rows))
        b = cell.dbbox()
        t = instance(cell, x - b.center().x, y - b.center().y)
        b = b.transformed(t)
        vias.append(dict(net=net, bottom=bottom, top=upper, center_um=[x, y], bbox_um=str(b)))
        return b

    def cover_topmetal1(cell, trans):
        # The native two-column/one-row via PCell has a narrow TM1 landing.
        # Add actual top-level metal; never waive TM1.a or edit the PCell/deck.
        li=layout.layer(126,0);region=pya.Region(cell.begin_shapes_rec(li))
        assert not region.is_empty()
        b=region.bbox().to_dtype(layout.dbu).transformed(trans)
        cx,cy=b.center().x,b.center().y;hw=max(b.width(),1.64)/2;hh=max(b.height(),1.64)/2
        left=math.floor((cx-hw)/.005+1e-8)*.005;right=math.ceil((cx+hw)/.005-1e-8)*.005
        bottom=math.floor((cy-hh)/.005+1e-8)*.005;upper=math.ceil((cy+hh)/.005-1e-8)*.005
        assert right-left>=1.64-1e-8 and upper-bottom>=1.64-1e-8
        top.shapes(li).insert(pya.DBox(left,bottom,right,upper))

    def escape(pin, metal, net, lane, label, cols, offset=0, wide=False, collector=False):
        y = round((pin.center().y + offset) / .005) * .005
        x = round(pin.center().x / .005) * .005
        # Preserve resistor access and widen only native HBT collector escapes.
        # Single-row via arrays stay at the original physical pin centers.
        half=1.0 if wide else .6 if collector else .2
        via(metal, 3, x, y, net, 16 if wide or collector else cols)
        rect(3, lane - half, y - half, x + half, y + half)
        via(3, 4, lane, y, net, 8)
        terminals.setdefault(net, []).append((lane, y))
        routes.append(dict(device=label, net=net, source_layer=metal, actual_pin_um=str(pin),
                           escape_lane_um=lane, escape_y_um=y, escape_width_um=2*half, pin_via_columns=16 if wide or collector else cols, lane_via_columns=8))

    # Physical placement and wire straps only: retain all37 original primitive rows/parameters.
    # Exact native widths determine locations, avoiding uniform shape scaling.
    geometry = {}
    for row in rows:
        if row["kind"] == "hbt":
            cell = pc("npn13G2", {"Nx": row["nx"]})
        else:
            params = {"w": f"{row['width_um']:g}u", "l": f"{row['length_um']:g}u"}
            if row["kind"] == "nmos": params["ng"] = 1
            cell = pc("nmos" if row["kind"] == "nmos" else "rppd", params)
        geometry[row["name"]] = cell.dbbox()
    source_layout=json.loads(args.placement_baseline.read_text())
    assert source_layout['source_circuit_sha256']=='c9c78b752e4ec5d17169b3254afa603b3d0b7702f164f8414356d54aa25b6db4'
    assert source_layout['primitive_counts']==dict(hbt=16,nmos=9,rppd=12,physical_tap=17)
    source_rows={r['name']:r for r in source_layout['instances'] if r['kind']!='substrate_tap'}
    byname={r['name']:r for r in rows};base_names=set(source_rows)-{'IP','IN','BP','BN'}
    assert len(base_names)==33 and set(byname)==base_names|set(GAIN_NAMES)
    for name in base_names:
        assert byname[name]=={k:source_rows[name][k] for k in byname[name]},('Changed latch primitive',name)
    base_order=[name for name in source_layout['placement_plan']['folded_rows']['actual_order'] if name in base_names]
    folded={name:[source_rows[name]['placement_um'][0]+SHIFT_X,source_rows[name]['placement_um'][1]] for name in base_order}
    gain_x=dict(GP=30,GN=60,GT0=90,GT1=120,UP=180,UN=210,DP=240,DN=270)
    folded.update({name:[gain_x[name],30.] for name in GAIN_NAMES})
    rows=[byname[name] for name in [*base_order,*GAIN_NAMES]]
    assert len(rows)==41
    placement_plan=dict(source_placement_sha256=sha(args.placement_baseline),
       unchanged_latch_and_reference_primitives=sorted(base_names),removed_passive_input_primitives=['IP','IN','BP','BN'],
       original_primitive_translation_um=[SHIFT_X,0.],gain_primitives=list(GAIN_NAMES),positions=folded,
       one_original_8um_reference=True,no_gain_reference=True,physical_electrical_acceptance=False)
    gain_points=set()
    def gain_escape(pin,metal,net,lane,label,cols,offset=0,rows=1,width=.4,upper_rows=4,pin_bounds=None):
        x=round(pin.center().x/.005)*.005;y=round((pin.center().y+offset)/.005)*.005
        low=via(metal,3,x,y,net,cols,rows)
        if pin_bounds is not None:
            assert low.bottom>=pin_bounds.bottom-1e-8 and low.top<=pin_bounds.top+1e-8
        rect(3,min(x,lane)-width/2,y-width/2,max(x,lane)+width/2,y+width/2)
        via(3,4,lane,y,net,8,upper_rows)
        terminals.setdefault(net,[]).append((lane,y));gain_points.add((net,lane,y))
        routes.append(dict(device=label,net=net,source_layer=metal,actual_pin_um=str(pin),escape_lane_um=lane,
          escape_y_um=y,escape_width_um=width,pin_via_columns=cols,pin_via_rows=rows,lane_via_columns=8,lane_via_rows=upper_rows))
    for index, row in enumerate(rows):
        if row["kind"] == "hbt":
            cell = pc("npn13G2", {"Nx": row["nx"]})
        else:
            params = {"w": f"{row['width_um']:g}u", "l": f"{row['length_um']:g}u"}
            if row["kind"] == "nmos":
                params["ng"] = 1
            cell = pc("nmos" if row["kind"] == "nmos" else "rppd", params)
        raw = cell.dbbox()
        x,y = folded[row["name"]]
        t = instance(cell, x, y)
        actual = raw.transformed(t)
        assert actual.top<y+60
        for prior in records:
            b=pya.DBox(*[float(v) for v in prior["bbox_um"].strip("()").replace(";",",").split(",")])
            assert actual.left>=b.right+1-1e-8 or actual.right<=b.left-1+1e-8 or actual.bottom>=b.top+1-1e-8 or actual.top<=b.bottom-1+1e-8
        if row["name"] in GAIN_NAMES:
            n=row["nets"];name=row["name"]
            if row["kind"]=="hbt":
                m1=sorted([s.dbbox().transformed(t)for s in cell.each_shape(layout.layer(8,2))],key=lambda b:b.center().y)
                m2=[s.dbbox().transformed(t)for s in cell.each_shape(layout.layer(10,2))]
                assert len(m1)==2 and len(m2)==1
                base,collector=m1
                gain_escape(collector,1,n[0],x-18,name,16,.04,width=1.2)
                gain_escape(base,1,n[1],x-12,name,4,-.04)
                gain_escape(m2[0],2,n[2],x-6,name,16,width=.6,upper_rows=2)
            elif row["kind"]=="nmos":
                mp=sorted([s.dbbox().transformed(t)for s in cell.each_shape(layout.layer(8,2))],key=lambda b:b.center().x)
                gp=[s.dbbox().transformed(t)for s in cell.each_shape(layout.layer(5,2))]
                assert len(mp)==2 and len(gp)==1 and row["width_um"]==53.335
                for k,(pin,net)in enumerate(zip(mp,[n[2],n[0]],strict=True)):
                    offset=min(3.,pin.height()/2-1.)
                    py=round((pin.center().y+(-offset if k==0 else offset))/.005)*.005
                    tiny=pya.DBox(pin.left,py-.1,pin.right,py+.1)
                    gain_escape(tiny,1,net,x-18+6*k,name,1,rows=16,width=1.6,pin_bounds=pin)
                gate=gp[0];gx=round(gate.center().x/.005)*.005;gy=round((gate.top+1)/.005)*.005
                top.shapes(layout.layer(5,0)).insert(pya.DBox(gate.left,gate.top-.1,gate.right,gy+.3))
                top.shapes(layout.layer(5,0)).insert(pya.DBox(gx-.3,gy-.3,gx+.3,gy+.3))
                top.shapes(layout.layer(6,0)).insert(pya.DBox(gx-.08,gy-.08,gx+.08,gy+.08))
                pin=rect(1,gx-.25,gy-.25,gx+.25,gy+.25)
                gain_escape(pin,1,n[1],x-6,name,1)
            else:
                assert row["kind"]=="resistor"
                ps=sorted([s.dbbox().transformed(t)for s in cell.each_shape(layout.layer(8,2))],key=lambda b:b.center().y)
                assert len(ps)==2
                for k,pin in enumerate(ps):
                    lane=x+6 if n[k]=="AVDD" else x-12+6*k
                    gain_escape(pin,1,n[k],lane,name,16,width=2.)
        elif row["kind"] == "hbt":
            m1 = sorted([s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                        key=lambda b: b.center().y)
            m2 = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(10, 2))]
            if len(m1) != 2 or len(m2) != 1:
                raise ValueError("Native HBT pin inventory differs")
            base, collector = m1
            for pin, metal, net, lane, offset in [(collector, 1, row["nets"][0], x - 18, .04),
                                                  (base, 1, row["nets"][1], x - 12, -.04),
                                                  (m2[0], 2, row["nets"][2], x - 6, 0)]:
                escape(pin, metal, net, lane, row["name"], 4, offset, collector=lane==x-18)
        elif row["kind"] == "nmos":
            mp = sorted([s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                        key=lambda b: b.center().x)
            gp = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(5, 2))]
            assert len(mp) == 2 and len(gp) == 1
            # Native PCell: left source, right drain; separate vertical access levels.
            for k, (pin, net) in enumerate(zip(mp, [row["nets"][2], row["nets"][0]], strict=True)):
                py = round((pin.bottom + .4 if k == 0 else pin.top - .4) / .005) * .005
                tiny = pya.DBox(pin.left, py-.1, pin.right, py+.1)
                assert pin.contains(pya.DPoint(tiny.left,tiny.bottom)) and pin.contains(pya.DPoint(tiny.right,tiny.top))
                escape(tiny, 1, net, x-18+6*k, row["name"], 1)
            gate = gp[0]
            gx = round(gate.center().x/.005)*.005
            gy = round((gate.top+1)/.005)*.005
            top.shapes(layout.layer(5,0)).insert(pya.DBox(gate.left,gate.top-.1,gate.right,gy+.3))
            top.shapes(layout.layer(5,0)).insert(pya.DBox(gx-.3,gy-.3,gx+.3,gy+.3))
            top.shapes(layout.layer(6,0)).insert(pya.DBox(gx-.08,gy-.08,gx+.08,gy+.08))
            pin = rect(1,gx-.25,gy-.25,gx+.25,gy+.25)
            escape(pin, 1, row["nets"][1], x-6, row["name"], 1)
            assert row["nets"][3] == "SUB"  # connected through all seventeen finite ptap1 devices below
        else:
            ps = sorted([s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                        key=lambda b: b.center().y)
            if len(ps) != 2:
                raise ValueError("Native rppd pin inventory differs")
            for k, pin in enumerate(ps):
                escape(pin, 1, row["nets"][k], x - 12 + 6*k, row["name"],
                       1 if row["width_um"] == 1 else 4, wide=row["width_um"]==32)
        records.append(dict(**row, placement_um=[x, y], bbox_um=str(cell.dbbox().transformed(t))))
    def safe_tap_x(desired, min_x=None, search_steps=6):
        # Reserve an independent M4 column before placing the actual tap.
        # DRC alone cannot detect an accidental union of two labelled nets.
        foreign = [x for points in terminals.values() for x, _ in points]
        for offset in [0, *[v for k in range(1,search_steps+1) for v in (-.5*k,.5*k)]]:
            x = round((desired+offset)/.005)*.005
            if (min_x is None or x >= min_x) and all(abs(x+1-col) >= 5.0-1e-8 for col in foreign):
                return x
        raise ValueError("No independent local body-contact routing column")
    # One real local body contact beside the middle of each MOS active strip.
    # Actual36um tails need local contacts; reserve diffusion AND all M4 column spacing.
    mos_rows = [r for r in records if r["kind"] == "nmos" and r["name"] not in GAIN_NAMES]
    assert len(mos_rows) == 9
    for index, row in enumerate(mos_rows, start=BASE_TAPS-9):
        x = safe_tap_x(row["placement_um"][0] + 3, row["placement_um"][0] + 1.98)
        y = row["placement_um"][1] + row["width_um"]/2 - 1
        cell = pc("ptap1", {"w": "2u", "l": "2u"})
        t = instance(cell, x, y)
        tap_box = cell.dbbox().transformed(t)
        # Native tap diffusion/contacts must stay outside every primitive.
        for primitive in records:
            if primitive["kind"] == "substrate_tap":
                continue
            values = [float(v) for v in primitive["bbox_um"].strip("()").replace(";", ",").split(",")]
            left, bottom, right, upper = values
            assert (tap_box.left >= right + 1 - 1e-8 or tap_box.right <= left - 1 + 1e-8 or
                    tap_box.bottom >= upper + 1 - 1e-8 or tap_box.top <= bottom - 1 + 1e-8), (
                    "Local substrate contact overlaps native primitive clearance", row["name"], primitive["name"])
        ps = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8,2))]
        assert len(ps) == 1
        pin = ps[0]
        via(1,4,pin.center().x,pin.center().y,"SUB",3)
        terminals.setdefault("SUB",[]).append((pin.center().x,pin.center().y))
        records.append(dict(kind="substrate_tap",name=f"TAP{index}",nets=["SUB","BULK"],
                            placement_um=[x,y],area_um2=4,perimeter_um=8,local_mos=row["name"]))
    # Independent square taps: SUB is a real conductor, BULK is the extracted substrate.
    for index in range(BASE_TAPS - 9):
        x, y = safe_tap_x(SHIFT_X + 22 + index * 60.0, min_x=SHIFT_X+20, search_steps=80), 4.0
        cell = pc("ptap1", {"w": "2u", "l": "2u"})
        t = instance(cell, x, y)
        ps = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))]
        if len(ps) != 1:
            raise ValueError("Native substrate contact pin differs")
        pin = ps[0]
        via(1, 4, pin.center().x, pin.center().y, "SUB", 3)
        terminals.setdefault("SUB", []).append((pin.center().x, pin.center().y))
        records.append(dict(kind="substrate_tap", name=f"TAP{index}", nets=["SUB", "BULK"],
                            placement_um=[x, y], area_um2=4, perimeter_um=8))
    for i,name in enumerate(GAIN_NAMES):
        row=byname[name];x,y=folded[name];length=20 if row["kind"]=="nmos" else 2
        tx,ty=(x+4,y+row["width_um"]/2-length/2) if row["kind"]=="nmos" else (x+10,10.)
        cell=pc("ptap1",{"w":"2u","l":str(length)+"u"});t=instance(cell,tx,ty);tb=cell.dbbox().transformed(t)
        for primitive in records:
            if primitive["kind"]=="substrate_tap":continue
            b=pya.DBox(*[float(v)for v in primitive["bbox_um"].strip("()").replace(";",",").split(",")])
            assert tb.left>=b.right+1-1e-8 or tb.right<=b.left-1+1e-8 or tb.bottom>=b.top+1-1e-8 or tb.top<=b.bottom-1+1e-8
        ps=[s.dbbox().transformed(t)for s in cell.each_shape(layout.layer(8,2))];assert len(ps)==1
        lane=x+12 if name in ("UP","UN") else x+6
        gain_escape(ps[0],1,"SUB",lane,"GAIN_TAP"+str(i),3)
        records.append(dict(kind="substrate_tap",name="GAIN_TAP"+str(i),nets=["SUB","BULK"],placement_um=[tx,ty],area_um2=2*length,perimeter_um=2*(2+length),gain_owner=name))
    assert sum(r["kind"]=="substrate_tap"for r in records)==TAPS
    columns = [(net,x) for net,points in terminals.items() for x,_ in points]
    for i,(net,x) in enumerate(columns):
        for other,ox in columns[i+1:]:
            assert (net==other and abs(x-ox)<1e-8) or abs(x-ox)>=5.-1e-8, ("Distinct M4 routing columns overlap",net,other,x,ox)
    output_shunts = []
    nets = list(PORTS) + sorted(set(terminals) - set(PORTS))
    # Keep every public pin at its old Y. Move only internal horizontal buses
    # toward their actual highest terminal, with20um vertical clearance and
    # unchanged6um bus pitch. All primitive placements/escape columns stay fixed.
    original_bus_y = {net:180.0+index*6 for index,net in enumerate(nets)}
    local_bus_y = {net:original_bus_y[net] for net in PORTS}
    occupied_y = list(local_bus_y.values())
    # Every vertical TM1 strap has a real M5 landing at its native start.
    # A shortened horizontal M5 bus must avoid OTHER-net start landings,
    # including ones whose terminals lie in the opposite folded row.
    landing_cell = pc("via_stack", dict(b_layer="Metal4",t_layer="TopMetal1",
        vn_columns=8,vn_rows=1,vt1_columns=2,vt1_rows=1))
    landing_all = landing_cell.dbbox()
    landing_region = pya.Region(landing_cell.begin_shapes_rec(layout.layer(layers["Metal5"],0)))
    assert not landing_region.is_empty()
    landing_box = landing_region.bbox().to_dtype(layout.dbu)
    landing_offsets = [landing_box.left-landing_all.center().x,
        landing_box.bottom-landing_all.center().y,landing_box.right-landing_all.center().x,
        landing_box.top-landing_all.center().y]
    start_landings = [(other,x+landing_offsets[0],start+landing_offsets[1],
        x+landing_offsets[2],start+landing_offsets[3]) for other,points in terminals.items()
        for x,start in points]
    # This2um is an additional geometric planning margin, not a changed DRC rule.
    landing_margin = 2.
    skipped_landings = []
    def landing_conflicts(net,y):
        left=min(x for x,_ in terminals[net])-1.
        right=max(x for x,_ in terminals[net])+1.
        return [dict(net=other,box_um=[x1,y1,x2,y2]) for other,x1,y1,x2,y2 in start_landings
            if other!=net and left<x2+landing_margin and right>x1-landing_margin
            and y-1.<y2+landing_margin and y+1.>y1-landing_margin]
    for net in nets:
        if net in PORTS:
            continue
        minimum_y = max(start for _,start in terminals[net])+20.
        y = math.ceil(minimum_y/6.)*6.
        while True:
            collision=landing_conflicts(net,y)
            if not any(abs(y-other)<6.-1e-8 for other in occupied_y) and not collision:
                break
            if collision:skipped_landings.append(dict(net=net,bus_y_um=y,conflicts=collision))
            y += 6.
        assert y<=original_bus_y[net]+1e-8, ("Internal wire would lengthen",net,y,original_bus_y[net])
        local_bus_y[net]=y;occupied_y.append(y)
    before_length = sum(original_bus_y[net]-start for net in nets for _,start in terminals[net])
    after_length = sum(local_bus_y[net]-start for net in nets for _,start in terminals[net])
    assert after_length<before_length
    critical = ("M_SE","M_TE","S_SE","S_TE")
    assert set(critical)<=set(nets)
    assert any(local_bus_y[n]<original_bus_y[n] for n in critical)
    placement_plan["local_bus_plan"] = dict(original_bus_y_um=original_bus_y,candidate_bus_y_um=local_bus_y,
        total_vertical_column_length_before_um=before_length,total_vertical_column_length_after_um=after_length,
        shortened_internal_nets=[n for n in nets if local_bus_y[n]<original_bus_y[n]],
        critical_buses={n:dict(before_um=original_bus_y[n],after_um=local_bus_y[n])for n in critical},
        minimum_terminal_to_bus_clearance_um=20.,minimum_horizontal_bus_pitch_um=6.,
        actual_native_m5_start_landing_offsets_um=landing_offsets,other_net_landing_margin_um=landing_margin,
        skipped_native_landing_conflicts=skipped_landings,
        primitive_placements_unchanged=True,public_bus_y_unchanged=True,
        scope="Actual shorter internal M4/TM1 columns and lower M5/TM2 buses. No intrinsic or public pin change. Length is not RC/timing acceptance.")
    for index, net in enumerate(nets):
        if net not in terminals:
            raise ValueError("Missing connected net: " + net)
        y = local_bus_y[net]
        xs = []
        for x, start in terminals[net]:
            gain_point=(net,x,start) in gain_points
            half=2. if gain_point else .6
            rect(4,x-half,start-.2,x+half,y+.2)
            via(4, 5, x, y, net, 8, 4 if gain_point else 1)
            assert start < y
            tmhalf=2. if gain_point else .82
            top.shapes(layout.layer(126,0)).insert(pya.DBox(x-tmhalf,start-tmhalf,x+tmhalf,y+tmhalf))
            for vy in (start,y):
                cell=pc("via_stack",dict(b_layer="Metal4",t_layer="TopMetal1",
                        vn_columns=8,vn_rows=4 if gain_point else 1,vt1_columns=4 if gain_point else 2,vt1_rows=4 if gain_point else 1))
                raw=cell.dbbox();trans=instance(cell,x-raw.center().x,vy-raw.center().y)
                cover_topmetal1(cell,trans)
                vias.append(dict(net=net,bottom=4,top=6,center_um=[x,vy],bbox_um=str(raw.transformed(trans))))
            xs.append(x)
        left, right = min(xs) - 1, max(xs) + 1
        if net in PORTS:
            left = 0
            b = pya.DBox(0, y - 1, 2, y + 1)
            ports[net] = ("Metal5", b)
            top.shapes(layout.layer(layers["Metal5"], 2)).insert(b)
            top.shapes(layout.layer(layers["Metal5"], 25)).insert(pya.DText(net, pya.DTrans(b.center().x, y)))
        rect(5, left, y - 1, right, y + 1)
        # Real upper-metal straps: vertical TopMetal1 and horizontal TopMetal2.
        # Every connection is drawn through native via PCells, never an ideal alias.
        # Keep the first 8um of each Metal5 boundary lead unshunted so the original
        # clock-open negative control still cuts the entire conducting path.
        shunt_left = 8.0 if net in PORTS else left
        assert net not in PORTS or min(xs) > shunt_left + 2
        shunt = pya.DBox(shunt_left, y-1.6, right, y+1.6)
        top.shapes(layout.layer(134, 0)).insert(shunt)
        centers = []
        for x in sorted(set(xs + ([8.0] if net in PORTS else []))):
            gain_x=any(n==net and abs(gx-x)<1e-8 for n,gx,_ in gain_points)
            cell = pc("via_stack", dict(b_layer="Metal5", t_layer="TopMetal2",
                      vn_columns=8, vn_rows=1, vt1_columns=2, vt1_rows=1,
                      vt2_columns=2 if gain_x else 1, vt2_rows=1))
            raw = cell.dbbox()
            trans = instance(cell, x-raw.center().x, y-raw.center().y)
            cover_topmetal1(cell,trans)
            vias.append(dict(net=net,bottom=5,top=7,center_um=[x,y],bbox_um=str(raw.transformed(trans))))
            centers.append([x,y])
        output_shunts.append(dict(net=net,metal=134,width_um=3.2,box_um=str(shunt),via_centers_um=centers))
    assert len(output_shunts)==len(nets) and {r['net']for r in output_shunts}==set(nets)
    box = top.dbbox()
    dx, dy = -box.left, -box.bottom
    top.transform(pya.Trans(round(dx/layout.dbu), round(dy/layout.dbu)))
    ports = {n: (metal, b.transformed(pya.DTrans(dx, dy))) for n, (metal, b) in ports.items()}
    box = top.dbbox()
    if box.left != 0 or box.bottom != 0 or any(not (b.left == 0 or b.right == box.right)
                                             for _, b in ports.values()):
        raise ValueError("Physical port boundary/origin differs")
    out.mkdir(parents=True)
    (out / "schematic.cir").write_text(physical_reference(circuit.read_text()))
    layout.write(str(out / (TOP + ".gds")))
    (out / (TOP + ".lef")).write_text(lef(pya, layout.dbu, box, ports))
    assert {n:dict(layer=metal,rect_um=[b.left,b.bottom,b.right,b.top])for n,(metal,b)in ports.items()}==source_layout["ports"],"External pins changed; requires parent reroute"
    assert box.width()>source_layout["bbox_um"][2] and box.height()==source_layout["bbox_um"][3]
    if any(sha(path) != expected for path, expected in pins.items()):
        raise ValueError("Generation input changed")
    result = dict(status="GENERATED_REQUIRES_NATIVE_DRC_LVS_AND_PEX", input_sha256=pins,
                  output_sha256={p.name: sha(p) for p in out.iterdir()}, source_circuit_sha256=sha(circuit),
                  instances=records, routes=routes, vias=vias, output_shunts=output_shunts, placement_plan=placement_plan,
                  output_pin_edge="left", origin_translation_um=[dx, dy],
                  ports={n: dict(layer=metal, rect_um=[b.left,b.bottom,b.right,b.top])
                         for n, (metal,b) in ports.items()}, bbox_um=[0,0,box.right,box.top],
                  primitive_counts=dict(hbt=18,nmos=11,rppd=12,physical_tap=TAPS), klayout_version=pya.__version__,
                  phy_complete=False, main_chip_integrated=False, qualified_pex=False, manufacturing_approval=False,
                  scope="Actual active-input sampler66:33 unchanged latch/reference primitives shifted320um plus8gain primitives,17original finite taps plus8gain taps. One existing8um reference. All public Metal5 pin positions retained. No parent or electrical acceptance.")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
