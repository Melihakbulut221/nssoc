#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Standalone divider v7 power v2: parallel upper-metal power straps only."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

TOP = "nssoc_clock_div4_v7_power_v2_layout"
PORTS = ("CLKP", "CLKN", "QP", "QN", "DIV_AVDD", "AVSS", "SUB")
TAPS = 18
SOURCES = {
    "hw/soc/analog/pcie/rx_sampler_hbt_v2.spice": "2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f",
    "hw/soc/analog/pcie/clock_div2_hbt.spice": "1b18a732c7736ad8c9805131c77fe1d5e467364ae8d6a2b7eb07061131cea4d7",
    "hw/soc/analog/pcie/clock_div2_conditioned_hbt_v3.spice": "158720385252c1dde2d11d4920baeb4a062674894620aa0ffbefe979f101135c",
    "hw/soc/analog/pcie/clock_div4_hbt_v7.spice": "49226d5b3a40fc4f8faafbaee3adb5580d8346222a825b79daaddc0358b2c65c",
}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_texts(root):
    texts = {}
    for path, pin in SOURCES.items():
        p = Path(root) / path
        if sha(p) != pin:
            raise ValueError("Frozen source differs: " + path)
        texts[path] = p.read_text()
    return texts


def flatten(texts):
    """Only reachable native primitives; exact per-instance formal-to-actual mapping."""
    definitions = {}
    current = None
    for text in texts.values():
        for line in text.splitlines():
            words = line.upper().split()
            if not words or words[0].startswith("*"):
                continue
            if words[0] == ".SUBCKT":
                if current is not None or words[1] in definitions:
                    raise ValueError("Duplicate/nested subcircuit")
                current = words[1]
                definitions[current] = (words[2:], [])
            elif words[0] == ".ENDS":
                if current is None or words != [".ENDS", current]:
                    raise ValueError("Exact subcircuit end")
                current = None
            elif current is not None:
                definitions[current][1].append(words)
            else:
                raise ValueError("Statement outside subcircuit")
        if current is not None:
            raise ValueError("Unclosed subcircuit")
    rows = []

    def walk(name, prefix, actual, stack):
        if name in stack:
            raise ValueError("Recursive circuit")
        ports, statements = definitions[name]
        if len(ports) != len(actual) or len(set(ports)) != len(ports):
            raise ValueError("Exact port arity")
        binding = dict(zip(ports, actual))

        def node(n):
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", n) or "__" in n:
                raise ValueError("Unambiguous literal node")
            return binding.get(n, prefix + "__" + n)

        names = set()
        for w in statements:
            if not re.fullmatch(r"X[A-Z0-9_]+", w[0]) or "__" in w[0] or w[0] in names:
                raise ValueError("Unique native instance")
            names.add(w[0])
            ident = prefix + "__" + w[0]
            if w[-1] in definitions:
                walk(w[-1], ident, [node(n) for n in w[1:-1]], stack + (name,))
                continue
            kinds = {
                "NPN13G2": ("hbt", 4),
                "RPPD": ("resistor", 3),
                "CAP_CMIM": ("capacitor", 2),
            }
            found = [
                (model, kind, n)
                for model, (kind, n) in kinds.items()
                if len(w) > n + 1 and w[n + 1] == model
            ]
            if len(found) != 1:
                raise ValueError("Only exact native primitive models")
            model, kind, n = found[0]
            params = {}
            for value in w[n + 2 :]:
                k, v = value.split("=")
                if k in params:
                    raise ValueError("Duplicate parameter")
                params[k] = v
            row = dict(
                kind=kind,
                name=ident,
                nets=[node(v) for v in w[1 : n + 1]],
                source_subcircuit=name,
                source_instance=w[0],
            )

            def um(k):
                if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?U", params[k]):
                    raise ValueError("Literal micron geometry")
                return float(params[k][:-1])

            if kind == "hbt":
                if set(params) != {"NX"} or not params["NX"].isdigit():
                    raise ValueError("Exact HBT geometry")
                row["nx"] = int(params["NX"])
                if row["nx"] not in (1, 2, 4):
                    raise ValueError("Supported native Nx")
            elif kind == "resistor":
                if (
                    set(params) != {"W", "L", "B", "SW_ET"}
                    or params["B"] != "0"
                    or params["SW_ET"] != "1"
                ):
                    raise ValueError("Exact self-heated straight resistor")
                row.update(width_um=um("W"), length_um=um("L"))
            elif kind == "capacitor":
                if set(params) != {"W", "L"}:
                    raise ValueError("Exact native capacitor geometry")
                row.update(width_um=um("W"), length_um=um("L"))
            rows.append(row)

    walk(
        "NSSOC_CLOCK_DIV4_HBT_V7",
        "DIV",
        ["CLKP", "CLKN", "QP", "QN", "DIV_AVDD", "AVSS", "SUB"],
        (),
    )
    if Counter(r["kind"] for r in rows) != dict(hbt=34, resistor=33, capacitor=6):
        raise ValueError("Exact reached primitive census")
    if len({r["name"] for r in rows}) != len(rows):
        raise ValueError("Unique flattened device identity")
    return rows


def devices(root):
    return flatten(source_texts(root))


def physical_reference(root):
    lines = [
        "* SPDX" + "-FileCopyrightText: 2026 Hasan Melih Akbulut",
        "* SPDX" + "-License-Identifier: CERN-OHL-W-2.0",
        ".subckt " + TOP + " " + " ".join(PORTS),
    ]
    for row in devices(root):
        ns = ["BULK" if n == "SUB" else n for n in row["nets"]]
        if row["kind"] == "hbt":
            lines.append(
                f"Q{row['name']} {' '.join(ns)} npn13G2 Nx={row['nx']} we=0.07u le=0.9u m=1"
            )
        elif row["kind"] == "resistor":
            lines.append(
                f"R{row['name']} {' '.join(ns)} rppd w={row['width_um']:g}u l={row['length_um']:g}u b=0 m=1"
            )
        elif row["kind"] == "capacitor":
            lines.append(
                f"C{row['name']} {' '.join(ns)} cap_cmim w={row['width_um']:g}u l={row['length_um']:g}u m=1"
            )
    lines += [f"RTAP{i} SUB BULK ptap1 A=4p P=8u" for i in range(TAPS)]
    lines += [".ends " + TOP, ""]
    return "\n".join(lines)


def use_direction(name):
    if name == "DIV_AVDD":
        return "POWER", "INOUT"
    if name in ("AVSS", "SUB"):
        return "GROUND", "INOUT"
    return "SIGNAL", "OUTPUT" if name in ("QP", "QN") else "INPUT"


def lef(pya, dbu, box, ports):
    if set(ports) != set(PORTS):
        raise ValueError("Divider physical pin inventory differs")
    result = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "MACRO " + TOP,
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        f"  SIZE {box.width():.3f} BY {box.height():.3f} ;",
    ]
    for name in PORTS:
        metal, b = ports[name]
        use, direction = use_direction(name)
        result += [
            "  PIN " + name,
            "    DIRECTION " + direction + " ;",
            "    USE " + use + " ;",
            "    PORT",
            "      LAYER " + metal + " ;",
            f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;",
            "    END",
            "  END " + name,
        ]
    result += ["  OBS"]
    for metal in (
        "Metal1",
        "Metal2",
        "Metal3",
        "Metal4",
        "Metal5",
        "TopMetal1",
        "TopMetal2",
    ):
        region = pya.Region(box.to_itype(dbu))
        for layer, b in ports.values():
            if layer == metal:
                region -= pya.Region(b.to_itype(dbu))
        result += ["    LAYER " + metal + " ;"]
        for polygon in region.decompose_trapezoids_to_region().each():
            if polygon.area() != polygon.bbox().area():
                raise ValueError("Nonrectangular obstruction")
            b = polygon.bbox().to_dtype(dbu)
            result += [
                f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;"
            ]
    return "\n".join(result + ["  END", "END " + TOP, "END LIBRARY", ""])


def placement_plan(rows):
    """Fixed topology grouping; every primitive appears once, circuit unchanged."""
    by_name = {r["name"]: r for r in rows}
    if len(rows) != 73 or len(by_name) != len(rows):
        raise ValueError("Exact 73 primitive placement census required")
    first = [n for n in by_name if n.startswith("DIV__XFIRST__")]
    second = [n for n in by_name if n.startswith("DIV__XSECOND__")]
    interstage = [
        n for n in by_name if n.startswith("DIV__") and n not in first + second
    ]
    groups = [first, interstage, second]
    flat = [n for group in groups for n in group]
    if len(flat) != 73 or len(set(flat)) != 73 or set(flat) != set(by_name):
        raise ValueError("Topology grouping omitted/duplicated an exact primitive")
    if [len(group) for group in groups] != [30, 17, 26]:
        raise ValueError("Topology group sizes changed")
    starts, net_rows, plan = {}, {}, {}
    base = 0
    for rid, group in enumerate(groups):
        nets = {"SUB"}
        for name in group:
            row = by_name[name]
            count = {"hbt": 3, "resistor": 2, "capacitor": 2}[row["kind"]]
            nets.update(row["nets"][:count])
        ordered = [n for n in PORTS if n in nets] + sorted(nets - set(PORTS))
        starts[rid], net_rows[rid] = base, ordered
        for index, name in enumerate(group):
            col = len(group) - 1 - index if rid in (0, 2) else index
            plan[name] = (rid, 160.0 + col * 40, base + 20.0)
        base += 90 + len(ordered) * 10 + 40
    return plan, starts, net_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-div4-")
    ):
        parser.error("Use a fresh project or /dev/shm/nssoc-div4- directory")
    rows = devices(root)
    plan, row_starts, row_nets = placement_plan(rows)
    source = args.pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    inputs = [
        *source.rglob("*.py"),
        *source.rglob("*.json"),
        lyp,
        *(root / p for p in SOURCES),
        Path(__file__).resolve(),
    ]
    pins = {str(path): sha(path) for path in inputs}
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- native PCell registration

    layout = pya.Layout()
    top = layout.create_cell(TOP)
    layers = {
        prop.findtext("name")[:-8]: int(prop.findtext("source").split("/")[0])
        for prop in ET.parse(lyp).getroot().iter("properties")
        if prop.findtext("name", "").endswith(".drawing")
    }
    records, routes, vias, terminals, ports = [], [], [], {}, {}

    def pc(name, parameters):
        cell = layout.create_cell(name, "SG13_dev", parameters)
        if cell is None or cell.is_empty():
            raise ValueError("Native PCell failed: " + name)
        return cell

    def instance(cell, x, y):
        trans = pya.DTrans(round(x / 0.005) * 0.005, round(y / 0.005) * 0.005)
        top.insert(pya.DCellInstArray(cell.cell_index(), trans))
        return trans

    def rect(metal, x1, y1, x2, y2):
        box = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers["Metal" + str(metal)], 0)).insert(box)
        return box

    def via(bottom, upper, x, y, net, cols=2):
        cell = pc(
            "via_stack",
            dict(
                b_layer="Metal" + str(bottom),
                t_layer="Metal" + str(upper),
                vn_columns=cols,
                vn_rows=1,
            ),
        )
        b = cell.dbbox()
        t = instance(cell, x - b.center().x, y - b.center().y)
        b = b.transformed(t)
        vias.append(
            dict(net=net, bottom=bottom, top=upper, center_um=[x, y], bbox_um=str(b))
        )
        return b

    def escape(pin, metal, net, lane, label, cols, offset=0):
        y = round((pin.center().y + offset) / 0.005) * 0.005
        x = round(pin.center().x / 0.005) * 0.005
        via(metal, 3, x, y, net, cols)
        rect(3, lane - 0.2, y - 0.2, x + 0.2, y + 0.2)
        via(3, 4, lane, y, net)
        terminals.setdefault(net, []).append((row_id, lane, y))
        routes.append(
            dict(
                device=label,
                net=net,
                source_layer=metal,
                actual_pin_um=str(pin),
                escape_lane_um=lane,
                escape_y_um=y,
            )
        )

    for row in rows:
        row_id, x, y = plan[row["name"]]
        if row["kind"] == "hbt":
            cell = pc("npn13G2", {"Nx": row["nx"]})
            t = instance(cell, x, y)
            m1 = sorted(
                [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().y,
            )
            m2 = [
                s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(10, 2))
            ]
            if len(m1) != 2 or len(m2) != 1:
                raise ValueError("Native HBT pin inventory differs")
            base, collector = m1
            for pin, metal, net, lane, offset in [
                (collector, 1, row["nets"][0], x - 9, 0.04),
                (base, 1, row["nets"][1], x - 6, -0.04),
                (m2[0], 2, row["nets"][2], x - 3, 0),
            ]:
                escape(pin, metal, net, lane, row["name"], 4, offset)
        elif row["kind"] == "resistor":
            cell = pc(
                "rppd", {"w": f"{row['width_um']:g}u", "l": f"{row['length_um']:g}u"}
            )
            t = instance(cell, x, y)
            ps = sorted(
                [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().y,
            )
            if len(ps) != 2:
                raise ValueError("Native rppd pin inventory differs")
            for k, pin in enumerate(ps):
                escape(
                    pin,
                    1,
                    row["nets"][k],
                    x - 6 + 3 * k,
                    row["name"],
                    1 if row["width_um"] == 1 else 4,
                )
        else:
            cell = pc(
                "cmim", {"w": f"{row['width_um']:g}u", "l": f"{row['length_um']:g}u"}
            )
            t = instance(cell, x, y)
            # Native cmim exposes pin objects but no GDS pin-purpose shapes.
            # Its version-pinned code defines PLUS=TopMetal1, MINUS=Metal5;
            # measure each actual plate, rather than infer a contact in MIM.
            plates = {}
            for metal in ("Metal5", "TopMetal1"):
                shapes = [
                    s.dbbox().transformed(t)
                    for s in cell.each_shape(layout.layer(layers[metal], 0))
                    if s.is_box()
                ]
                if len(shapes) != 1:
                    raise ValueError("Native MIM plate inventory differs")
                plates[metal] = shapes[0]
            plus, minus = plates["TopMetal1"], plates["Metal5"]
            py = round(plus.center().y / 0.005) * 0.005
            px = x - 9
            top.shapes(layout.layer(layers["TopMetal1"], 0)).insert(
                pya.DBox(px - 1.2, py - 1.2, plus.right, py + 1.2)
            )
            cv = pc(
                "via_stack",
                dict(b_layer="Metal5", t_layer="TopMetal1", vt1_columns=2, vt1_rows=1),
            )
            cb = cv.dbbox()
            ct = instance(cv, px - cb.center().x, py - cb.center().y)
            top.shapes(layout.layer(layers["TopMetal1"], 0)).insert(
                pya.DBox(px - 1.2, py - 1.2, px + 1.2, py + 1.2)
            )
            via(4, 5, px, py, row["nets"][0], 2)
            terminals.setdefault(row["nets"][0], []).append((row_id, px, py))
            mx = x - 5
            rect(5, mx - 0.6, py - 0.6, minus.center().x, py + 0.6)
            via(4, 5, mx, py, row["nets"][1], 2)
            terminals.setdefault(row["nets"][1], []).append((row_id, mx, py))
            routes.append(
                dict(
                    device=row["name"],
                    plus_net=row["nets"][0],
                    minus_net=row["nets"][1],
                    plus_native_plate_um=str(plus),
                    minus_native_plate_um=str(minus),
                    plus_contact_outside_native_mim=True,
                    plus_escape_um=[px, py],
                    minus_escape_um=[mx, py],
                )
            )
        records.append(
            dict(
                **row,
                placement_row=row_id,
                placement_um=[x, y],
                bbox_um=str(cell.dbbox().transformed(t)),
            )
        )
    # Independent square taps: SUB is a real conductor, BULK is the extracted substrate.
    for index in range(TAPS):
        row_id = index // 6
        x, y = 180 + (index % 6) * 200.0, row_starts[row_id] + 4.0
        cell = pc("ptap1", {"w": "2u", "l": "2u"})
        t = instance(cell, x, y)
        ps = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))]
        if len(ps) != 1:
            raise ValueError("Native substrate contact pin differs")
        pin = ps[0]
        via(1, 4, pin.center().x, pin.center().y, "SUB", 3)
        terminals.setdefault("SUB", []).append((row_id, pin.center().x, pin.center().y))
        records.append(
            dict(
                kind="substrate_tap",
                name=f"TAP{index}",
                nets=["SUB", "BULK"],
                placement_um=[x, y],
                area_um2=4,
                perimeter_um=8,
            )
        )
    width = 1520.0
    actual_by_row = {
        i: {n for n, ts in terminals.items() if any(t[0] == i for t in ts)}
        for i in row_starts
    }
    if actual_by_row != {i: set(v) for i, v in row_nets.items()}:
        raise ValueError("Actual native terminal census differs from placement plan")
    nets = list(PORTS) + sorted(set(terminals) - set(PORTS))
    crossing = [n for n in nets if len({t[0] for t in terminals[n]}) > 1]
    if len(crossing) > 24:
        raise ValueError("Peripheral trunk capacity exceeded")
    trunks, buses = {}, []
    for net in nets:
        ts = terminals[net]
        ids = sorted({t[0] for t in ts})
        side = (
            ("right" if net in ("CLKP", "CLKN") else "left")
            if net in PORTS
            else ("left" if sum(t[1] for t in ts) <= len(ts) * width / 2 else "right")
        )
        tx = None
        if net in crossing:
            idx = crossing.index(net)
            tx = 12 + idx * 4 if side == "left" else width - 12 - idx * 4
        ys = []
        for rid in ids:
            y = row_starts[rid] + 90 + row_nets[rid].index(net) * 10
            xs = []
            for _, x, start in [t for t in ts if t[0] == rid]:
                if not row_starts[rid] <= start < row_starts[rid] + 85:
                    raise ValueError(
                        "Native terminal outside its isolated row escape band"
                    )
                rect(4, x - 0.6, start - 0.2, x + 0.6, y + 0.2)
                via(4, 5, x, y, net, 2)
                xs.append(x)
            left, right = min(xs) - 1, max(xs) + 1
            if tx is not None:
                left, right = min(left, tx - 1), max(right, tx + 1)
                via(4, 5, tx, y, net, 2)
            if net in PORTS and rid == ids[0]:
                if side == "right":
                    right = width
                    b = pya.DBox(width - 2, y - 1, width, y + 1)
                else:
                    left = 0
                    b = pya.DBox(0, y - 1, 2, y + 1)
                ports[net] = ("Metal5", b)
                top.shapes(layout.layer(layers["Metal5"], 2)).insert(b)
                top.shapes(layout.layer(layers["Metal5"], 25)).insert(
                    pya.DText(net, pya.DTrans(b.center().x, y))
                )
            rect(5, left, y - 1, right, y + 1)
            buses.append(dict(net=net, row=rid, y_um=y, left_um=left, right_um=right))
            ys.append(y)
        if tx is not None:
            rect(4, tx - 0.6, min(ys) - 0.2, tx + 0.6, max(ys) + 0.2)
            trunks[net] = dict(
                x_um=tx, lower_y_um=min(ys), upper_y_um=max(ys), side=side, rows=ids
            )
    # Add only supply routing above the original geometry. Long thin M5 buses
    # and M4 cross-row trunks caused measured ground rise in the frozen wire
    # simulation; primitive topology, placements and every old route stay exact.
    # MIM plates are in the isolated device bands, below these row bus tracks.
    power_straps, power_vias = [], []

    def power_rect(layer, net, x1, y1, x2, y2, role):
        b = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers[layer], 0)).insert(b)
        power_straps.append(
            dict(
                net=net,
                layer=layer,
                role=role,
                rect_um=[b.left, b.bottom, b.right, b.top],
            )
        )

    def power_via(bottom, upper, x, y, net, role):
        parameters = dict(
            b_layer=bottom,
            t_layer=upper,
            vn_columns=2,
            vn_rows=3,
            vt1_columns=2,
            vt1_rows=2,
            vt2_columns=2,
            vt2_rows=2,
        )
        cell = pc("via_stack", parameters)
        b = cell.dbbox()
        t = instance(cell, x - b.center().x, y - b.center().y)
        b = b.transformed(t)
        if b.width() > 6 or b.height() > 6:
            raise ValueError("Power native via array outside six-micron corridor")
        power_vias.append(
            dict(
                net=net,
                role=role,
                parameters=parameters,
                center_um=[x, y],
                bbox_um=str(b),
            )
        )

    for net, trunk_x in (("DIV_AVDD", 96.0), ("AVSS", 112.0)):
        selected = [b for b in buses if b["net"] == net]
        if [b["row"] for b in selected] != [0, 1, 2]:
            raise ValueError("All three actual power row buses required")
        power_rect(
            "TopMetal1",
            net,
            trunk_x - 3,
            selected[0]["y_um"] - 3,
            trunk_x + 3,
            selected[-1]["y_um"] + 3,
            "cross_row_trunk",
        )
        for bus in selected:
            rid, y = bus["row"], bus["y_um"]
            left, right = bus["left_um"], bus["right_um"]
            if not (left <= trunk_x - 3 and trunk_x + 3 <= right):
                raise ValueError("Power trunk must overlap existing actual bus extent")
            power_rect("TopMetal2", net, left, y - 3, right, y + 3, "row_bus")
            power_via("TopMetal1", "TopMetal2", trunk_x, y, net, "trunk_join")
            for _, x, start in [t for t in terminals[net] if t[0] == rid]:
                if not row_starts[rid] <= start < row_starts[rid] + 85:
                    raise ValueError("Actual power branch outside original device band")
                power_via("Metal4", "TopMetal2", x, y, net, "actual_branch")
            if rid == 0:
                # Existing M5 pin and old bus remain unchanged; join at x=2 so
                # the entire native upper-via enclosure stays inside the macro.
                power_via("Metal5", "TopMetal2", 2.0, y, net, "public_port")
    if len(power_straps) != 8:
        raise ValueError("Exact six row straps and two cross-row power trunks")
    box = top.dbbox()
    dx, dy = -box.left, -box.bottom
    top.transform(pya.Trans(round(dx / layout.dbu), round(dy / layout.dbu)))
    ports = {
        n: (metal, b.transformed(pya.DTrans(dx, dy))) for n, (metal, b) in ports.items()
    }
    box = top.dbbox()
    if (
        box.left != 0
        or box.bottom != 0
        or any(not (b.left == 0 or b.right == box.right) for _, b in ports.values())
    ):
        raise ValueError("Physical port boundary/origin differs")
    out.mkdir(parents=True)
    (out / "schematic.cir").write_text(physical_reference(root))
    layout.write(str(out / (TOP + ".gds")))
    (out / (TOP + ".lef")).write_text(lef(pya, layout.dbu, box, ports))
    if any(sha(path) != expected for path, expected in pins.items()):
        raise ValueError("Generation input changed")
    result = dict(
        status="GENERATED_REQUIRES_NATIVE_DRC_LVS_AND_PEX",
        input_sha256=pins,
        output_sha256={p.name: sha(p) for p in out.iterdir()},
        source_circuit_sha256={p: sha(root / p) for p in SOURCES},
        instances=records,
        row_starts_um=row_starts,
        local_buses=buses,
        additive_power_straps=power_straps,
        additive_power_vias=power_vias,
        peripheral_trunks=trunks,
        placement_method="Three topology groups with row-local escapes/buses and peripheral cross-row trunks",
        routes=routes,
        vias=vias,
        origin_translation_um=[dx, dy],
        ports={
            n: dict(layer=metal, rect_um=[b.left, b.bottom, b.right, b.top])
            for n, (metal, b) in ports.items()
        },
        bbox_um=[0, 0, box.right, box.top],
        primitive_counts=dict(hbt=34, rppd=33, cmim=6, physical_ptap=TAPS),
        klayout_version=pya.__version__,
        phy_complete=False,
        main_chip_integrated=False,
        qualified_pex=False,
        manufacturing_approval=False,
        scope="Exact standalone divider v7 power v2, L4 first conditioner, 73 primitives and 18 finite substrate contacts. "
        "Original geometry retained with additive TopMetal2 power row straps and TopMetal1 power trunks. "
        "No oscillator, CMOS feedback chain, extracted division, qualified RC, PLL or complete PHY acceptance.",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
