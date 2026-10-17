#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native SG13G2 layout of the bias-return-local four-PMOS voltage-controlled HBT ring v4."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

TOP = "nssoc_clock_vco_hbt_v4_local_v3_layout"
PORTS = ("CLKP", "CLKN", "VCTRL", "AVDD", "AVSS", "SUB")
CIRCUIT = "hw/soc/analog/pcie/clock_vco_hbt_v4.spice"
CIRCUIT_SHA256 = "0f6eaecc4b5ff7eddf992fecfa7d6015ab6a93807ffc56f2c99d4fbb84a0a8e7"
TAPS = 12
# Each column groups actual connected devices; rows have distinct escape lanes.
COLUMNS = (
    ("P0", "N0", "T0", "RP0", "RN0", "CP0", "CN0"),
    ("P1", "N1", "T1", "RP1", "RN1", "CP1", "CN1"),
    ("P2", "N2", "T2", "RP2", "RN2", "CP2", "CN2"),
    ("CTRL0", "CTRL1", "CTRL2", "CTRL3", "REF", "RB", "BREF"),
    ("BP", "BN", "BT", "BRP", "BRN", "FP", "FN"),
    ("FPD1", "FPD2", "FPD3", "FND1", "FND2", "FND3", "FTP"),
    ("FTN", "FTPD1", "FTPD2", "FTPD3", "FTND1", "FTND2", "FTND3"),
)


def placement(rows):
    names = [n for column in COLUMNS for n in column]
    if (
        len(names) != 49
        or len(set(names)) != 49
        or set(names) != {r["name"] for r in rows}
    ):
        raise ValueError("Exact compact device placement census differs")
    positions = {
        name: (100.0 + col * 100, 20.0 + row * 30, 120.0 + col * 100 + row * 9)
        for col, column in enumerate(COLUMNS)
        for row, name in enumerate(column)
    }
    for stage in range(3):
        x = 40.0 + stage * 120
        for prefix, dx, y, lane in (
            ("P", 0, 20, 20),
            ("N", 0, 50, 29),
            ("T", 0, 80, 38),
            ("RP", 60, 20, 76),
            ("RN", 60, 50, 85),
            ("CP", 60, 80, 94),
            ("CN", 60, 110, 103),
        ):
            positions[prefix + str(stage)] = (x + dx, y, x + lane)
    # Bring the real limiter next to stage 0 and four output branches below
    # the three ring clusters. Only native placement/routing changes; the
    # exact frozen circuit and thirteen finite contacts stay literal.
    positions.update(
        {
            "BP": (78.0, 20.0, 87.0),
            "BN": (78.0, 50.0, 96.0),
            "BT": (78.0, 95.0, 105.0),
            "BRP": (120.0, 80.0, 153.0),
            "BRN": (120.0, 110.0, 162.0),
        }
    )
    # Reserve nonoverlapping 3-um escape lanes around unchanged ring and
    # control columns. This avoids reusing the long finite substrate/power
    # conductors even where the transistor bodies occupy different rows.
    output_lanes = (
        (171.0, 207.0, 216.0, 225.0),
        (272.0, 281.0, 290.0, 327.0),
        (336.0, 345.0, 392.0, 489.0),
        (498.0, 507.0, 516.0, 525.0),
    )
    for branch, lanes in enumerate(output_lanes):
        suffix = "" if branch == 0 else "D" + str(branch)
        for prefix, y, lane in zip(
            ("FP", "FN", "FTP", "FTN"), (150.0, 180.0, 210.0, 220.0), lanes
        ):
            positions[prefix + suffix] = (lane - 15, y, lane)
    return positions


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def devices(text):
    """Literal native geometry and pin order from the exact compact VCO v4."""
    if hashlib.sha256(text.encode()).hexdigest() != CIRCUIT_SHA256:
        raise ValueError("VCO circuit differs from the frozen source")
    rows = []
    for line in text.splitlines():
        f = line.upper().split()
        if not f or not f[0].startswith("X"):
            continue
        name = f[0][1:]
        if len(f) > 5 and f[5] == "NPN13G2":
            rows.append(
                dict(
                    kind="hbt", name=name, nets=f[1:5], nx=int(f[6].removeprefix("NX="))
                )
            )
        elif len(f) > 5 and f[5] == "SG13_HV_PMOS":
            rows.append(
                dict(
                    kind="pmos",
                    name=name,
                    nets=f[1:5],
                    width_um=float(f[6][2:-1]),
                    length_um=float(f[7][2:-1]),
                    ng=int(f[8].removeprefix("NG=")),
                )
            )
        elif len(f) > 4 and f[4] == "RPPD":
            rows.append(
                dict(
                    kind="resistor",
                    name=name,
                    nets=f[1:4],
                    width_um=float(f[5][2:-1]),
                    length_um=float(f[6][2:-1]),
                )
            )
        elif len(f) > 3 and f[3] == "CAP_CMIM":
            rows.append(
                dict(
                    kind="capacitor",
                    name=name,
                    nets=f[1:3],
                    width_um=float(f[4][2:-1]),
                    length_um=float(f[5][2:-1]),
                )
            )
        else:
            raise ValueError("Unknown VCO primitive")
    if {
        kind: sum(r["kind"] == kind for r in rows)
        for kind in ("hbt", "pmos", "resistor", "capacitor")
    } != dict(hbt=30, pmos=4, resistor=9, capacitor=6):
        raise ValueError("VCO native primitive census differs")
    return rows


def physical_reference(text):
    lines = [
        "* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
        "* SPDX-License-Identifier: CERN-OHL-W-2.0",
        ".subckt " + TOP + " " + " ".join(PORTS),
    ]
    for row in devices(text):
        ns = ["BULK" if n == "SUB" else n for n in row["nets"]]
        if row["kind"] == "hbt":
            lines.append(
                f"Q{row['name']} {' '.join(ns)} npn13G2 Nx={row['nx']} we=0.07u le=0.9u m=1"
            )
        elif row["kind"] == "resistor":
            lines.append(
                f"R{row['name']} {' '.join(ns)} rppd w={row['width_um']:g}u l={row['length_um']:g}u b=0 m=1"
            )
        elif row["kind"] == "pmos":
            # Native well contact is explicit, not a virtual AVDD/body join.
            ns[-1] = "NWELL"
            lines.append(
                f"M{row['name']} {' '.join(ns)} sg13_hv_pmos w={row['width_um']:g}u l={row['length_um']:g}u ng={row['ng']} m=1"
            )
        else:
            lines.append(
                f"C{row['name']} {' '.join(ns)} cap_cmim w={row['width_um']:g}u l={row['length_um']:g}u m=1"
            )
    lines += [f"RTAP{i} SUB BULK ptap1 A=4p P=8u" for i in range(TAPS)]
    lines += ["RNTAP AVDD NWELL ntap1 A=4p P=8u"]
    return "\n".join(lines + [".ends " + TOP, ""])


def use_direction(name):
    if name == "AVDD":
        return "POWER", "INOUT"
    if name in ("AVSS", "SUB"):
        return "GROUND", "INOUT"
    return "SIGNAL", "OUTPUT" if name in ("CLKP", "CLKN") else "INPUT"


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
        and out.name.startswith("nssoc-vco-")
    ):
        parser.error("Use a fresh project or /dev/shm/nssoc-vco- directory")
    circuit = root / CIRCUIT
    rows = devices(circuit.read_text())
    source = args.pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    inputs = [
        *source.rglob("*.py"),
        *source.rglob("*.json"),
        lyp,
        circuit,
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
    placements = placement(rows)
    wells = []
    power_routes = []
    bias_returns = []
    ref_diode = []

    def pc(name, parameters):
        cell = layout.create_cell(name, "SG13_dev", parameters)
        if cell is None or cell.is_empty():
            raise ValueError("Native PCell failed: " + name)
        return cell

    def instance(cell, x, y):
        trans = pya.DTrans(round(x / 0.005) * 0.005, round(y / 0.005) * 0.005)
        top.insert(pya.DCellInstArray(cell.cell_index(), trans))
        return trans

    def layer_name(number):
        return "Metal" + str(number) if number <= 5 else "TopMetal" + str(number - 5)

    def rect(metal, x1, y1, x2, y2):
        box = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers[layer_name(metal)], 0)).insert(box)
        return box

    def via(bottom, upper, x, y, net, cols=2):
        cell = pc(
            "via_stack",
            dict(
                b_layer=layer_name(bottom),
                t_layer=layer_name(upper),
                vn_columns=cols,
                vn_rows=1,
                vt1_columns=1,
                vt1_rows=1,
                vt2_columns=1,
                vt2_rows=1,
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
        rect(3, min(lane, x) - 0.2, y - 0.2, max(lane, x) + 0.2, y + 0.2)
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

    for row in rows:
        x, y, lane = placements[row["name"]]
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
                (collector, 1, row["nets"][0], lane, 0.04),
                (base, 1, row["nets"][1], lane + 3, -0.04),
                (m2[0], 2, row["nets"][2], lane + 6, 0),
            ]:
                escape(pin, metal, net, lane, row["name"], 4, offset)
            if row["name"] in ("T0", "T1", "T2", "REF"):
                # A real parallel emitter return starts on the native M2 pin,
                # before the old narrow M3 escape. Its native stack and TM2
                # branch reach a common TM1 spine, preserving every old wire.
                emitter = m2[0]
                ex = round(emitter.center().x / 0.005) * 0.005
                ey = round(emitter.center().y / 0.005) * 0.005
                return_x = x + (30 if row["name"] in ("T1", "T2") else -6)
                # Keep the narrow landing within the native emitter; widen
                # only outside its full PCell boundary. The chosen free
                # landing columns avoid original SUB M4 and AVDD power vias.
                edge = cell.dbbox().transformed(t)
                elbow = edge.right + 1 if return_x > ex else edge.left - 1
                rect(2, min(ex, elbow) - 0.4, ey - 0.4, max(ex, elbow) + 0.4, ey + 0.4)
                rect(
                    2,
                    min(elbow, return_x) - 0.5,
                    ey - 1,
                    max(elbow, return_x) + 0.5,
                    ey + 1,
                )
                via(2, 7, return_x, ey, "AVSS", 4)
                rect(7, return_x - 2, ey - 2, return_x + 2, 149)
                via(6, 7, return_x, 145, "AVSS", 4)
                if row["name"] == "REF":
                    # Join the close same-AVSS lower-via TM1 pad to the
                    # common spine with actual metal, avoiding a 0.06um slot.
                    rect(6, return_x - 1, ey - 1, return_x + 1, 146)
                bias_returns.append(
                    dict(
                        device=row["name"],
                        net="AVSS",
                        native_emitter_um=str(emitter),
                        landing_um=[return_x, ey],
                        source_layer="Metal2",
                        parallel_layer="TopMetal2",
                        branch_width_um=4,
                        common_spine_y_um=145,
                    )
                )
            if row["name"] == "REF":
                # The diode is already connected in the source. This true M1
                # U-route joins its two native pin ends outside the PCell,
                # instead of making C and B meet only through the long bus.
                join_x = (
                    round((cell.dbbox().transformed(t).right + 2.5) / 0.005) * 0.005
                )
                by, cy = base.center().y, collector.center().y
                rect(1, base.right - 0.2, by - 0.2, join_x + 0.2, by + 0.2)
                rect(1, collector.right - 0.2, cy - 0.2, join_x + 0.2, cy + 0.2)
                rect(
                    1, join_x - 0.2, min(by, cy) - 0.2, join_x + 0.2, max(by, cy) + 0.2
                )
                ref_diode.append(
                    dict(
                        device="REF",
                        net="REF",
                        layer="Metal1",
                        native_base_um=str(base),
                        native_collector_um=str(collector),
                        join_x_um=join_x,
                        width_um=0.4,
                    )
                )
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
                    lane + 3 * k,
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
            for p, net, pin_lane, py in [
                (source_pin, row["nets"][2], lane, y + 2),
                (drain_pin, row["nets"][0], lane + 3, y + 6),
            ]:
                tiny = pya.DBox(p.left, py - 0.1, p.right, py + 0.1)
                if not (
                    p.contains(pya.DPoint(tiny.left, tiny.bottom))
                    and p.contains(pya.DPoint(tiny.right, tiny.top))
                ):
                    raise ValueError("MOS contact lies outside native pin")
                escape(tiny, 1, net, pin_lane, row["name"], 1)
            gate = gp[0]
            gx = round(gate.center().x / 0.005) * 0.005
            gy = y + 12
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
            escape(gate_metal, 1, row["nets"][1], lane + 6, row["name"], 1)
            wells.append(nw[0])
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
            px = lane + 6
            top.shapes(layout.layer(layers["TopMetal1"], 0)).insert(
                pya.DBox(plus.center().x, py - 1.2, px + 1.2, py + 1.2)
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
            mx = lane + 3
            rect(5, minus.center().x, py - 0.6, mx + 0.6, py + 0.6)
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
    # Four PMOS have separate real source/drain/gate regions in one genuine
    # NWell polygon. A single finite ntap connects that well to AVDD.
    if len(wells) != 4:
        raise ValueError("Four native PMOS well regions required")
    ntap = pc("ntap1", {"w": "2u", "l": "2u"})
    nt = instance(ntap, 408, 23)
    nb = ntap.dbbox().transformed(nt)
    bridge = pya.DBox(
        min(b.left for b in wells),
        min(b.bottom for b in wells),
        nb.right,
        max(b.top for b in wells),
    )
    top.shapes(layout.layer(31, 0)).insert(bridge)
    via(1, 4, 409, 24, "AVDD", 3)
    terminals.setdefault("AVDD", []).append((409, 24))
    records.append(
        dict(
            kind="well_tap",
            name="NTAP",
            nets=["AVDD", "NWELL"],
            area_um2=4,
            perimeter_um=8,
            placement_um=[408, 23],
            body_connection_geometry_um=str(bridge),
        )
    )
    # Independent square taps: SUB is a real conductor, BULK is the extracted substrate.
    for index in range(TAPS):
        x, y = 7 + index * 4, 4.0
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
    width = 560.0
    nets = list(PORTS) + sorted(set(terminals) - set(PORTS))
    signal_index = 0
    local_y = {
        **{f"P{i}": 30.0 + 4 * i for i in range(3)},
        **{f"N{i}": 60.0 + 4 * i for i in range(3)},
        **{f"T{i}": 74.0 for i in range(3)},
        "BT": 74.0,
        "BO_P": 130.0,
        "BO_N": 134.0,
    }
    for net in nets:
        if net not in terminals:
            raise ValueError("Missing connected net: " + net)
        if net in ("AVDD", "AVSS", "SUB"):
            y = {"AVDD": 350.0, "AVSS": 380.0, "SUB": 410.0}[net]
        elif net in local_y:
            y = local_y[net]
        else:
            y = 230.0 + signal_index * 4
            signal_index += 1
            if y >= 330:
                raise ValueError("Signal routing exceeded fixed power-rail clearance")
        xs = []
        for x, start in terminals[net]:
            rect(4, x - 0.6, min(start, y) - 0.2, x + 0.6, max(start, y) + 0.2)
            via(4, 5, x, y, net, 2)
            xs.append(x)
            if net in ("AVDD", "AVSS"):
                # True parallel top-metal path; retain the complete M4 route.
                # Its offset and landing stay outside native transistor/MIM.
                shift = 0.75 if net == "AVDD" else -0.75
                upper_x, lower_y = x + shift, start + 5
                rect(
                    4,
                    min(x, upper_x) - 0.6,
                    lower_y - 0.6,
                    max(x, upper_x) + 0.6,
                    lower_y + 0.6,
                )
                via(4, 7, upper_x, lower_y, net, 1)
                rect(7, upper_x - 1, lower_y - 1, upper_x + 1, y + 1)
                via(5, 7, upper_x, y, net, 1)
                power_routes.append(
                    dict(
                        net=net,
                        native_lane_um=x,
                        start_um=[upper_x, lower_y],
                        end_um=[upper_x, y],
                        top_layer="TopMetal2",
                        width_um=2,
                    )
                )
        left, right = min(xs) - 1, max(xs) + 1
        if net in PORTS:
            if net in ("CLKP", "CLKN"):
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
        if net in ("AVDD", "AVSS"):
            # Boundary pin remains M5 with a native via to a wide TM1 spine.
            rect(6, left, y - 8, right, y + 8)
            via(5, 6, 1, y, net, 1)
    if {r["device"] for r in bias_returns} != {"T0", "T1", "T2", "REF"} or len(
        ref_diode
    ) != 1:
        raise ValueError("Exact physical local bias network missing")
    # Wide actual top-metal connection to the existing public AVSS conductor.
    # It crosses AVDD only on a different layer, with no via at that crossing.
    rect(6, 2, 141, 398, 149)
    via(6, 7, 4, 145, "AVSS", 4)
    rect(7, 0, 141, 8, 384)
    via(5, 7, 4, 380, "AVSS", 4)
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
    (out / "schematic.cir").write_text(physical_reference(circuit.read_text()))
    layout.write(str(out / (TOP + ".gds")))
    (out / (TOP + ".lef")).write_text(lef(pya, layout.dbu, box, ports))
    if any(sha(path) != expected for path, expected in pins.items()):
        raise ValueError("Generation input changed")
    result = dict(
        status="GENERATED_REQUIRES_NATIVE_DRC_LVS_AND_PEX",
        input_sha256=pins,
        output_sha256={p.name: sha(p) for p in out.iterdir()},
        source_circuit_sha256=sha(circuit),
        instances=records,
        routes=routes,
        vias=vias,
        power_routes=power_routes,
        local_bias_returns=bias_returns,
        local_ref_diode=ref_diode,
        origin_translation_um=[dx, dy],
        ports={
            n: dict(layer=metal, rect_um=[b.left, b.bottom, b.right, b.top])
            for n, (metal, b) in ports.items()
        },
        bbox_um=[0, 0, box.right, box.top],
        primitive_counts=dict(
            hbt=30, pmos=4, rppd=9, cmim=6, physical_ptap=TAPS, physical_ntap=1
        ),
        klayout_version=pya.__version__,
        phy_complete=False,
        main_chip_integrated=False,
        qualified_pex=False,
        manufacturing_approval=False,
        scope="Bias-return-local exact-device VCO v4 candidate, explicit SUB and NWell taps, external VCTRL and 2.3 V rail. "
        "No PLL/clock recovery, post-layout oscillation/fanout/current/RF qualification or complete PHY.",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
