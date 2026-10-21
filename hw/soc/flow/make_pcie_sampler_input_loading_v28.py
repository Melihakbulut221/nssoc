#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native16HBT/9LVNMOS/12rppd parallel-drive sampler with finite substrate contacts."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

TOP = "nssoc_rx_sampler_input_access_layout_v26"
PORTS = ("DP", "DN", "QP", "QN", "CLKP", "CLKN", "AVDD", "AVSS", "SUB", "IREF")
CIRCUIT = "hw/soc/analog/pcie/rx_sampler_input_loading_v28.spice"
CIRCUIT_SHA256 = "17a5a52d6be61b4d2fec52ce8a6f2008d1d1ce068d3d4417740cf9c3ca4885fa"
TAPS = 17


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def devices(text):
    """Flatten only the exact three fixed subcircuits, preserving terminal order."""
    if hashlib.sha256(text.encode()).hexdigest() != CIRCUIT_SHA256:
        raise ValueError("Sampler circuit differs from the frozen v28 source")
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
    expand("NSSOC_RX_SAMPLER_INPUT_LOADING_V28", list(PORTS), "")
    if len(rows) != 37 or {k: sum(r["kind"] == k for r in rows) for k in ("hbt", "nmos", "resistor")} != {"hbt": 16, "nmos": 9, "resistor": 12}:
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
    lines += [f"RTAP{i} SUB BULK ptap1 A=4p P=8u" for i in range(TAPS)]
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

    def via(bottom, upper, x, y, net, cols=2):
        cell = pc("via_stack", dict(b_layer="Metal" + str(bottom), t_layer="Metal" + str(upper),
                                    vn_columns=cols, vn_rows=1))
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
    original_rows = list(rows)
    byname = {r["name"]: r for r in rows}
    assert len(byname) == len(rows) == 37
    def spans(order):
        points = {}; right = 0.
        for index, name in enumerate(order):
            row = byname[name]; box = geometry[name]
            x = math.ceil(max(40. + index * 30, right + 30 - box.left) / .005) * .005
            right = x + box.right
            for net in set(row["nets"]):
                if net not in ("AVDD", "AVSS", "SUB", "IREF"):
                    points.setdefault(net, []).append(x + box.center().x)
        for net in set(PORTS) & points.keys(): points[net].append(0.)
        return {net: max(v)-min(v) for net,v in points.items()}
    def cost(order):
        values = spans(order)
        return sum(v * (3 if n in ("M_MP", "M_MN", "MP", "MN", "QP", "QN") else 2 if n in ("CLKP", "CLKN", "DP", "DN", "LP", "LN") else 1) for n,v in values.items())
    source_layout=json.loads(args.placement_baseline.read_text())
    assert source_layout['source_circuit_sha256']=='339e9ff566cb4b52bd4aa476ab48e686418cf8a9a93620b4a915284874f97916'
    assert source_layout['primitive_counts']==dict(hbt=16,nmos=9,rppd=12,physical_tap=17)
    source_rows={r['name']:r for r in source_layout['instances']if r['kind']!='substrate_tap'}
    selected={'IP','IN','BP','BN'}
    assert set(source_rows)==set(byname)and len(source_rows)==37
    for name,row in byname.items():
        old={k:source_rows[name][k]for k in row}
        expected=dict(old)
        if name in selected:
            assert old['kind']=='resistor'and old['width_um']==4 and old['length_um']==.9
            expected['length_um']=2.4
        assert row==expected,('Unexpected intrinsic change',name)
    saved=source_layout['placement_plan']
    order=list(saved['candidate_order'])
    assert set(order)==set(byname)and len(order)==37
    actual_order=saved['folded_rows']['actual_order']
    assert set(actual_order)==set(byname)and len(actual_order)==37
    rows=[byname[name]for name in actual_order]
    folded={name:list(source_rows[name]['placement_um'])for name in actual_order}
    assert folded==saved['folded_rows']['positions']
    split=(len(rows)+1)//2
    clock_rows=[r for r in rows if set(r['nets'])&{'CLKP','CLKN'}]
    assert len(clock_rows)==8
    reserved=[];right_by_row=[0.,0.]
    for index,row in enumerate(rows):
        row_index=0 if index<split else 1
        x,y=folded[row['name']]
        assert y==20.+row_index*100.
        offsets=[-18.,-12.,-6.]if row['kind']in('hbt','nmos')else[-12.,-6.]
        lanes=[x+v for v in offsets]+([x+4.]if row['kind']=='nmos'else[])
        assert all(abs(a-b)>=5.-1e-8 for a in lanes for b in reserved),'Source escape-column separation changed'
        reserved.extend(lanes);right_by_row[row_index]=max(right_by_row[row_index],x+geometry[row['name']].right)
    placement_plan=dict(saved)
    placement_plan.update(unchanged_primitive_rows=False,source_placement_sha256=sha(args.placement_baseline),
       original_37_primitive_positions_preserved=True,changed_input_and_bias_resistor_lengths=sorted(selected),
       cost_metadata_scope='Inherited v27 planning metadata; no new placement optimization claimed.')
    assert len(folded)==len(rows)==37
    folded_points={}
    for row in rows:
        x,y=folded[row["name"]];box=geometry[row["name"]]
        for net in set(row["nets"]):
            if net not in ("AVDD","AVSS","SUB","IREF"):
                folded_points.setdefault(net,[]).append(x+box.center().x)
    for net in set(PORTS)&folded_points.keys():folded_points[net].append(0.)
    folded_spans={n:max(v)-min(v)for n,v in folded_points.items()}
    baseline_spans=spans(order)
    assert all(folded_spans[n]<.8*baseline_spans[n]for n in ("CLKP","CLKN")), (folded_spans,baseline_spans)
    assert max(right_by_row)<1200.,right_by_row
    placement_plan["folded_rows"] = dict(rows=2,row_y_um=[20.,120.],minimum_same_row_primitive_gap_um=30.,
        minimum_global_escape_column_gap_um=5.,positions=folded,
        signal_horizontal_spans_um=folded_spans,original_single_row_spans_um=baseline_spans,
        rightmost_native_primitive_um=max(right_by_row),
        actual_order=[r["name"]for r in rows],clock_primitives=[r["name"]for r in clock_rows],
        local_body_columns_reserved=True,
        scope="Real two-row geometry with unchanged intrinsic devices. Horizontal spans are not delay or electrical acceptance.")
    previous_right_by_row = [0.,0.]
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
        row_index = 0 if index < split else 1
        t = instance(cell, x, y)
        actual = raw.transformed(t)
        assert actual.left >= previous_right_by_row[row_index] + 30 - 1e-8 and actual.top < y+50
        previous_right_by_row[row_index] = actual.right
        if row["kind"] == "hbt":
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
    mos_rows = [r for r in records if r["kind"] == "nmos"]
    assert len(mos_rows) == 9
    for index, row in enumerate(mos_rows, start=TAPS-9):
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
    for index in range(TAPS - 9):
        x, y = safe_tap_x(22 + index * 60.0, min_x=20, search_steps=80), 4.0
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
    columns = [(net,x) for net,points in terminals.items() for x,_ in points]
    for i,(net,x) in enumerate(columns):
        for other,ox in columns[i+1:]:
            assert abs(x-ox) < 1e-8 or abs(x-ox) >= 5.0-1e-8, ("Distinct M4 routing columns overlap",net,other,x,ox)
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
            rect(4, x - .6, start - .2, x + .6, y + .2)
            via(4, 5, x, y, net, 8)
            assert start < y
            top.shapes(layout.layer(126,0)).insert(pya.DBox(x-.82,start-.82,x+.82,y+.82))
            for vy in (start,y):
                cell=pc("via_stack",dict(b_layer="Metal4",t_layer="TopMetal1",
                        vn_columns=8,vn_rows=1,vt1_columns=2,vt1_rows=1))
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
            cell = pc("via_stack", dict(b_layer="Metal5", t_layer="TopMetal2",
                      vn_columns=8, vn_rows=1, vt1_columns=2, vt1_rows=1,
                      vt2_columns=1, vt2_rows=1))
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
    if any(sha(path) != expected for path, expected in pins.items()):
        raise ValueError("Generation input changed")
    result = dict(status="GENERATED_REQUIRES_NATIVE_DRC_LVS_AND_PEX", input_sha256=pins,
                  output_sha256={p.name: sha(p) for p in out.iterdir()}, source_circuit_sha256=sha(circuit),
                  instances=records, routes=routes, vias=vias, output_shunts=output_shunts, placement_plan=placement_plan,
                  output_pin_edge="left", origin_translation_um=[dx, dy],
                  ports={n: dict(layer=metal, rect_um=[b.left,b.bottom,b.right,b.top])
                         for n, (metal,b) in ports.items()}, bbox_um=[0,0,box.right,box.top],
                  primitive_counts=dict(hbt=16,nmos=9,rppd=12,physical_tap=TAPS), klayout_version=pya.__version__,
                  phy_complete=False, main_chip_integrated=False, qualified_pex=False, manufacturing_approval=False,
                  scope="Parallel-drive external-clock sampler with separate36um tail MOS and actual local body contacts. Explicit SUB taps, external 2.5 V rail and current reference. "
                        "No clock recovery, post-layout timing/current/RF qualification or complete PHY.")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
