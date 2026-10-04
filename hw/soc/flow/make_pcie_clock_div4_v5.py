#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual native VCOv3/div4v5 composite; preserves all prior layouts and circuits."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

TOP = "nssoc_clock_div4_v5_layout"
PORTS = ("CLKP", "CLKN", "QP", "QN", "VCTRL", "VCO_AVDD", "DIV_AVDD", "AVSS", "SUB")
TAPS = 30
SOURCES = {
    "hw/soc/analog/pcie/clock_vco_hbt_v3.spice": "0d578a1392a13a9d61013eb5f0592515fccb112eddcee24f643f816b020f10f4",
    "hw/soc/analog/pcie/rx_sampler_hbt_v2.spice": "2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f",
    "hw/soc/analog/pcie/clock_div2_hbt.spice": "1b18a732c7736ad8c9805131c77fe1d5e467364ae8d6a2b7eb07061131cea4d7",
    "hw/soc/analog/pcie/clock_div2_conditioned_hbt.spice": "6986c012843f603f7ab7769e951ae01314acdbc0c8e8fc62ce8b5c7a9af25ec3",
    "hw/soc/analog/pcie/clock_div4_hbt_v5.spice": "e68db6846dbfee30afa526a988ff1d585e1f74e10aab06ed65a10de300c944fc",
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
                "SG13_HV_PMOS": ("pmos", 4),
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
            else:
                if set(params) != {"W", "L", "NG", "M"} or params["M"] != "1":
                    raise ValueError("Exact native PMOS geometry")
                row.update(width_um=um("W"), length_um=um("L"), ng=int(params["NG"]))
            rows.append(row)

    walk(
        "NSSOC_CLOCK_VCO_HBT_V3",
        "OSC",
        ["CLKP", "CLKN", "VCTRL", "VCO_AVDD", "AVSS", "SUB"],
        (),
    )
    walk(
        "NSSOC_CLOCK_DIV4_HBT_V5",
        "DIV",
        ["CLKP", "CLKN", "QP", "QN", "DIV_AVDD", "AVSS", "SUB"],
        (),
    )
    if Counter(r["kind"] for r in rows) != dict(
        hbt=64, resistor=42, capacitor=12, pmos=1
    ):
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
        else:
            if ns[-1] != "VCO_AVDD":
                raise ValueError("Exact PMOS well supply")
            ns[-1] = "NWELL"
            lines.append(
                f"M{row['name']} {' '.join(ns)} sg13_hv_pmos w={row['width_um']:g}u l={row['length_um']:g}u ng={row['ng']} m=1"
            )
    lines += [f"RTAP{i} SUB BULK ptap1 A=4p P=8u" for i in range(TAPS)]
    lines += ["RNTAP VCO_AVDD NWELL ntap1 A=4p P=8u", ".ends " + TOP, ""]
    return "\n".join(lines)


def use_direction(name):
    if name in ("VCO_AVDD", "DIV_AVDD"):
        return "POWER", "INOUT"
    if name in ("AVSS", "SUB"):
        return "GROUND", "INOUT"
    return "SIGNAL", "OUTPUT" if name in ("CLKP", "CLKN", "QP", "QN") else "INPUT"


def lef(pya, dbu, box, ports):
    if set(ports) != set(PORTS):
        raise ValueError("VCO physical pin inventory differs")
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
        parser.error("Use a fresh project or /dev/shm/nssoc-vco- directory")
    rows = devices(root)
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
        terminals.setdefault(net, []).append((lane, y))
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

    for index, row in enumerate(rows):
        x, y = 20.0 + index * 40, 20.0
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
        elif row["kind"] == "pmos":
            cell = pc(
                "pmosHV",
                {
                    "w": f"{row['width_um']:g}u",
                    "l": f"{row['length_um']:g}u",
                    "ng": row["ng"],
                },
            )
            t = instance(cell, x, y)
            mp = sorted(
                [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().x,
            )
            gp = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(5, 2))]
            nw = [
                s.dbbox().transformed(t)
                for s in cell.each_shape(layout.layer(31, 0))
                if not s.is_text()
            ]
            if len(mp) != 2 or len(gp) != 1 or len(nw) != 1:
                raise ValueError("Native PMOS pin/well inventory differs")
            source_pin, drain_pin = mp
            # Native source/drain pins are long vertical strips. Separate
            # contact positions prevent two same-height horizontal escapes.
            for p, net, lane, py in [
                (source_pin, row["nets"][2], x - 9, y + 4),
                (drain_pin, row["nets"][0], x - 6, y + 26),
            ]:
                tiny = pya.DBox(p.left, py - 0.1, p.right, py + 0.1)
                if not (
                    p.contains(pya.DPoint(tiny.left, tiny.bottom))
                    and p.contains(pya.DPoint(tiny.right, tiny.top))
                ):
                    raise ValueError("MOS contact lies outside native pin")
                escape(tiny, 1, net, lane, row["name"], 1)
            gate = gp[0]
            gx = round(gate.center().x / 0.005) * 0.005
            gy = y + 35
            # Draw an actual legal poly-contact landing outside the active
            # transistor. Cnt_a=.16, poly enclosure .07; larger .6 pad used.
            top.shapes(layout.layer(5, 0)).insert(
                pya.DBox(gate.left, gate.top - 0.1, gate.right, gy + 0.3)
            )
            top.shapes(layout.layer(5, 0)).insert(
                pya.DBox(gx - 0.3, gy - 0.3, gx + 0.3, gy + 0.3)
            )
            top.shapes(layout.layer(6, 0)).insert(
                pya.DBox(gx - 0.08, gy - 0.08, gx + 0.08, gy + 0.08)
            )
            gate_metal = rect(1, gx - 0.25, gy - 0.25, gx + 0.25, gy + 0.25)
            escape(gate_metal, 1, row["nets"][1], x - 3, row["name"], 1)
            ntap = pc("ntap1", {"w": "2u", "l": "2u"})
            nt = instance(ntap, x + 8, y + 34)
            # Join the genuine NWell bodies geometrically and contact its
            # native n+ active. SUB/AVSS remain separate conductors.
            nb = ntap.dbbox().transformed(nt)
            top.shapes(layout.layer(31, 0)).insert(
                pya.DBox(nw[0].left, nw[0].bottom, nb.right, nb.top)
            )
            via(1, 4, x + 9, y + 35, "VCO_AVDD", 3)
            terminals.setdefault("VCO_AVDD", []).append((x + 9, y + 35))
            records.append(
                dict(
                    kind="well_tap",
                    name="NTAP",
                    nets=["VCO_AVDD", "NWELL"],
                    area_um2=4,
                    perimeter_um=8,
                    placement_um=[x + 8, y + 34],
                    body_connection_geometry_um=str(
                        pya.DBox(nw[0].left, nw[0].bottom, nb.right, nb.top)
                    ),
                )
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
            terminals.setdefault(row["nets"][0], []).append((px, py))
            mx = x - 5
            rect(5, mx - 0.6, py - 0.6, minus.center().x, py + 0.6)
            via(4, 5, mx, py, row["nets"][1], 2)
            terminals.setdefault(row["nets"][1], []).append((mx, py))
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
            dict(**row, placement_um=[x, y], bbox_um=str(cell.dbbox().transformed(t)))
        )
    # Independent square taps: SUB is a real conductor, BULK is the extracted substrate.
    for index in range(TAPS):
        x, y = 40 + index * 160.0, 4.0
        cell = pc("ptap1", {"w": "2u", "l": "2u"})
        t = instance(cell, x, y)
        ps = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))]
        if len(ps) != 1:
            raise ValueError("Native substrate contact pin differs")
        pin = ps[0]
        via(1, 4, pin.center().x, pin.center().y, "SUB", 3)
        terminals.setdefault("SUB", []).append((pin.center().x, pin.center().y))
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
    width = 40.0 * len(rows) + 40.0
    nets = list(PORTS) + sorted(set(terminals) - set(PORTS))
    for index, net in enumerate(nets):
        if net not in terminals:
            raise ValueError("Missing connected net: " + net)
        y = 90.0 + index * 10
        xs = []
        for x, start in terminals[net]:
            rect(4, x - 0.6, start - 0.2, x + 0.6, y + 0.2)
            via(4, 5, x, y, net, 2)
            xs.append(x)
        left, right = min(xs) - 1, max(xs) + 1
        if net in PORTS:
            if net in ("CLKP", "CLKN", "QP", "QN"):
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
        routes=routes,
        vias=vias,
        origin_translation_um=[dx, dy],
        ports={
            n: dict(layer=metal, rect_um=[b.left, b.bottom, b.right, b.top])
            for n, (metal, b) in ports.items()
        },
        bbox_um=[0, 0, box.right, box.top],
        primitive_counts=dict(
            hbt=64, pmos=1, rppd=42, cmim=12, physical_ptap=TAPS, physical_ntap=1
        ),
        klayout_version=pya.__version__,
        phy_complete=False,
        main_chip_integrated=False,
        qualified_pex=False,
        manufacturing_approval=False,
        scope="Exact VCO v3 plus divider v5 composite, explicit finite body contacts and independent VCO/DIV rails. "
        "No PLL/clock recovery, post-layout oscillation/fanout/current/RF qualification or complete PHY.",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
