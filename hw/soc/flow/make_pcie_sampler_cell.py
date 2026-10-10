#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native SG13G2 layout of the fixed external-clock HBT sampler v2."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

TOP = "nssoc_rx_sampler_hbt_v2_layout"
PORTS = ("DP", "DN", "QP", "QN", "CLKP", "CLKN", "AVDD", "AVSS", "SUB", "IREF")
CIRCUIT = "hw/soc/analog/pcie/rx_sampler_hbt_v2.spice"
CIRCUIT_SHA256 = "2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f"
TAPS = 8


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def devices(text):
    """Flatten only the exact two fixed subcircuits, preserving terminal order."""
    if hashlib.sha256(text.encode()).hexdigest() != CIRCUIT_SHA256:
        raise ValueError("Sampler circuit differs from the frozen v2 source")
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
            elif len(fields) > 4 and fields[4] == "RPPD":
                rows.append(dict(kind="resistor", name=name, nets=[net(v) for v in fields[1:4]],
                                 width_um=float(fields[5][2:-1]), length_um=float(fields[6][2:-1])))
            else:
                expand(fields[-1], [net(v) for v in fields[1:-1]], name + "_")
    expand("NSSOC_RX_SAMPLER_HBT", list(PORTS), "")
    if len(rows) != 27 or sum(row["kind"] == "hbt" for row in rows) != 15:
        raise ValueError("Sampler primitive census differs")
    return rows


def physical_reference(text):
    lines = ["* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
             "* SPDX-License-Identifier: CERN-OHL-W-2.0",
             ".subckt " + TOP + " " + " ".join(PORTS)]
    for row in devices(text):
        nets = " ".join("BULK" if n == "SUB" else n for n in row["nets"])
        if row["kind"] == "hbt":
            lines.append(f"Q{row['name']} {nets} npn13G2 Nx={row['nx']} we=0.07u le=0.9u m=1")
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
    inputs = [*source.rglob("*.py"), *source.rglob("*.json"), lyp, circuit, Path(__file__).resolve()]
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

    def escape(pin, metal, net, lane, label, cols, offset=0):
        y = round((pin.center().y + offset) / .005) * .005
        x = round(pin.center().x / .005) * .005
        via(metal, 3, x, y, net, cols)
        rect(3, lane - .2, y - .2, x + .2, y + .2)
        via(3, 4, lane, y, net)
        terminals.setdefault(net, []).append((lane, y))
        routes.append(dict(device=label, net=net, source_layer=metal, actual_pin_um=str(pin),
                           escape_lane_um=lane, escape_y_um=y))

    for index, row in enumerate(rows):
        x, y = 20.0 + index * 32, 20.0
        if row["kind"] == "hbt":
            cell = pc("npn13G2", {"Nx": row["nx"]})
            t = instance(cell, x, y)
            m1 = sorted([s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                        key=lambda b: b.center().y)
            m2 = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(10, 2))]
            if len(m1) != 2 or len(m2) != 1:
                raise ValueError("Native HBT pin inventory differs")
            base, collector = m1
            for pin, metal, net, lane, offset in [(collector, 1, row["nets"][0], x - 9, .04),
                                                  (base, 1, row["nets"][1], x - 6, -.04),
                                                  (m2[0], 2, row["nets"][2], x - 3, 0)]:
                escape(pin, metal, net, lane, row["name"], 4, offset)
        else:
            cell = pc("rppd", {"w": f"{row['width_um']:g}u", "l": f"{row['length_um']:g}u"})
            t = instance(cell, x, y)
            ps = sorted([s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                        key=lambda b: b.center().y)
            if len(ps) != 2:
                raise ValueError("Native rppd pin inventory differs")
            for k, pin in enumerate(ps):
                escape(pin, 1, row["nets"][k], x - 6 + 3*k, row["name"],
                       1 if row["width_um"] == 1 else 4)
        records.append(dict(**row, placement_um=[x, y], bbox_um=str(cell.dbbox().transformed(t))))
    # Independent square taps: SUB is a real conductor, BULK is the extracted substrate.
    for index in range(TAPS):
        x, y = 30 + index * 96.0, 4.0
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
    width = 880.0
    nets = list(PORTS) + sorted(set(terminals) - set(PORTS))
    for index, net in enumerate(nets):
        if net not in terminals:
            raise ValueError("Missing connected net: " + net)
        y = 80.0 + index * 10
        xs = []
        for x, start in terminals[net]:
            rect(4, x - .6, start - .2, x + .6, y + .2)
            via(4, 5, x, y, net, 2)
            xs.append(x)
        left, right = min(xs) - 1, max(xs) + 1
        if net in PORTS:
            if net in ("QP", "QN"):
                right = width
                b = pya.DBox(width - 2, y - 1, width, y + 1)
            else:
                left = 0
                b = pya.DBox(0, y - 1, 2, y + 1)
            ports[net] = ("Metal5", b)
            top.shapes(layout.layer(layers["Metal5"], 2)).insert(b)
            top.shapes(layout.layer(layers["Metal5"], 25)).insert(pya.DText(net, pya.DTrans(b.center().x, y)))
        rect(5, left, y - 1, right, y + 1)
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
                  instances=records, routes=routes, vias=vias, origin_translation_um=[dx, dy],
                  ports={n: dict(layer=metal, rect_um=[b.left,b.bottom,b.right,b.top])
                         for n, (metal,b) in ports.items()}, bbox_um=[0,0,box.right,box.top],
                  primitive_counts=dict(hbt=15,rppd=12,physical_tap=TAPS), klayout_version=pya.__version__,
                  phy_complete=False, main_chip_integrated=False, qualified_pex=False, manufacturing_approval=False,
                  scope="Fixed v2 external-clock sampler. Explicit SUB taps, external 2.5 V rail and current reference. "
                        "No clock recovery, post-layout timing/current/RF qualification or complete PHY.")
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
