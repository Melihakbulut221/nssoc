#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate the versioned 100-ohm-load native HBT RX preamplifier; requires independent DRC/LVS/PEX."""

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TOP = "nssoc_rx_hbt_v2_layout"
PORTS = ("INP", "INN", "OUTP", "OUTN", "AVDD", "AVSS", "SUB", "IREF", "VCM")
CIRCUIT_SHA256 = "d02827087e0cb43f447fc46fda05dbd23dcee13ad68755fd31ba738404332a4e"


def validate_circuit(text):
    """Accept only the independently simulated, fixed analog source."""
    if hashlib.sha256(text.encode()).hexdigest() != CIRCUIT_SHA256:
        raise ValueError("RX analog source differs from the geometry contract")
    lines = [line for line in text.splitlines() if line and not line.startswith("*")]
    expected = [
        ".subckt nssoc_rx_hbt_rsil_v2 inp inn outp outn avdd avss sub iref vcm",
        "XREF iref iref avss sub npn13G2 Nx=1",
        "XTAIL tail iref avss sub npn13G2 Nx=4",
        "XP outn inp tail sub npn13G2 Nx=4",
        "XN outp inn tail sub npn13G2 Nx=4",
        "XRTP inp vcm sub rsil w=10u l=70.215u b=0 sw_et=1",
        "XRTN inn vcm sub rsil w=10u l=70.215u b=0 sw_et=1",
        "XRP avdd outp sub rsil w=2u l=27.5u b=0 sw_et=1",
        "XRN avdd outn sub rsil w=2u l=27.5u b=0 sw_et=1",
        ".ends nssoc_rx_hbt_rsil_v2",
    ]
    if lines != expected:
        raise ValueError("RX device inventory or port contract differs")
    return lines


def physical_reference(text):
    """Literal device dimensions plus actual square taps, never fitted extraction."""
    source = validate_circuit(text)
    result = ["* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
              "* SPDX-License-Identifier: CERN-OHL-W-2.0",
              ".subckt " + TOP + " " + " ".join(PORTS)]
    for line in source[1:-1]:
        fields = line.upper().split()
        fields[0] = ("Q" if fields[5] == "NPN13G2" else "R") + fields[0][1:]
        fields = ["BULK" if v == "SUB" else v for v in fields]
        if fields[5] == "NPN13G2":
            result.append(" ".join(fields) + " we=0.07u le=0.9u m=1")
        else:
            # sw_et selects compact-model self heating, not LVS geometry.
            result.append(" ".join(v for v in fields if v != "SW_ET=1") + " m=1")
    result += [f"RTAP{i} SUB BULK ptap1 A=4p P=8u" for i in range(8)]
    result += [".ends " + TOP]
    return "\n".join(result) + "\n"


def abstract_lef(pya, dbu, box, ports):
    """Boundary access only; conservatively block all routing metals inside."""
    if set(ports) != set(PORTS):
        raise ValueError("LEF pin inventory differs")
    lines = ["VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;",
             "MACRO " + TOP, "  CLASS BLOCK ;", "  ORIGIN 0 0 ;",
             f"  SIZE {box.width():.3f} BY {box.height():.3f} ;"]
    for name in PORTS:
        metal, b = ports[name]
        use = "POWER" if name == "AVDD" else "GROUND" if name in ("AVSS", "SUB") else "SIGNAL"
        direction = "OUTPUT" if name in ("OUTP", "OUTN") else "INOUT" if use != "SIGNAL" else "INPUT"
        lines += ["  PIN " + name, "    DIRECTION " + direction + " ;", "    USE " + use + " ;",
                  "    PORT", f"      LAYER Metal{metal} ;",
                  f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;",
                  "    END", "  END " + name]
    full = pya.Region(box.to_itype(dbu))
    opening = pya.Region()
    for metal, b in ports.values():
        if metal != 5:
            raise ValueError("Unexpected abstract pin metal")
        opening.insert(b.to_itype(dbu))
    lines += ["  OBS"]
    for layer in ("Metal1", "Metal2", "Metal3", "Metal4", "Metal5", "TopMetal1", "TopMetal2"):
        region = full - opening if layer == "Metal5" else full
        lines += ["    LAYER " + layer + " ;"]
        # Rectangular decomposition avoids an OBS polygon with pin holes.
        for piece in region.decompose_trapezoids_to_region().each():
            b = piece.bbox().to_dtype(dbu)
            if piece.area() != piece.bbox().area():
                raise ValueError("Nonrectangular abstract obstruction")
            lines += [f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;"]
    return "\n".join(lines + ["  END", "END " + TOP, "END LIBRARY", ""])


def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdk", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not (out.is_relative_to(root / "hw/soc/out") or
                           out.is_relative_to(Path("/dev/shm")) and out.name.startswith("nssoc-rx-")):
        ap.error("Use a fresh project output directory")
    circuit = root / "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice"
    validate_circuit(circuit.read_text())
    source = args.pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    inputs = [
        p for p in source.rglob("*") if p.is_file() and p.suffix in [".py", ".json"]
    ] + [lyp, Path(__file__).resolve(), root / "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice"]
    pins = {str(p): sha(p) for p in inputs}
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- registers native PCells

    layout = pya.Layout()
    top = layout.create_cell("nssoc_rx_hbt_v2_layout")
    layers = {}
    for prop in ET.parse(lyp).getroot().iter("properties"):
        name = prop.findtext("name", "")
        src = prop.findtext("source", "")
        if name in [f"Metal{i}.drawing" for i in range(1, 6)]:
            layers[int(name[5])] = int(src.split("/")[0])
    records = []
    ports = {}

    def pc(name, params):
        c = layout.create_cell(name, "SG13_dev", params)
        if c is None or c.is_empty():
            raise RuntimeError("Native PCell failed " + name)
        return c

    def inst(c, x, y):
        t = pya.DTrans(round(x / 0.005) * 0.005, round(y / 0.005) * 0.005)
        top.insert(pya.DCellInstArray(c.cell_index(), t))
        return t

    def rect(m, x1, y1, x2, y2):
        b = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers[m], 0)).insert(b)
        return b

    def via(bottom, upper, cols, rows, x, y, net):
        c = pc(
            "via_stack",
            {
                "b_layer": "Metal" + str(bottom),
                "t_layer": "Metal" + str(upper),
                "vn_columns": cols,
                "vn_rows": rows,
            },
        )
        bb = c.dbbox()
        t = inst(c, x - bb.center().x, y - bb.center().y)
        b = bb.transformed(t)
        records.append(
            dict(
                kind="via_stack",
                net=net,
                bottom=bottom,
                top=upper,
                columns=cols,
                rows=rows,
                bbox_um=str(b),
            )
        )
        return b

    def port(net, m, x, y, w=2, h=2):
        if net in ports:
            raise ValueError("Duplicate physical port " + net)
        b = rect(m, x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        ports[net] = (m, b)
        top.shapes(layout.layer(layers[m], 2)).insert(b)
        top.shapes(layout.layer(layers[m], 25)).insert(
            pya.DText(net, pya.DTrans(float(x), float(y)))
        )

    def riser(m, x, width, y1, y2):
        return rect(
            m, x - width / 2, min(y1, y2) - 0.2, x + width / 2, max(y1, y2) + 0.2
        )

    # Multiplicities and emitter geometry match the simulated compact-model cells.
    hbts = [
        ("REF", 1, 10.0, -10.0, "IREF", "IREF", "AVSS", -4.0, -4.0, -22.0),
        ("TAIL", 4, 40.0, -10.0, "TAIL", "IREF", "AVSS", 10.0, -4.0, -22.0),
        ("P", 4, 20.0, 20.0, "OUTN", "INP", "TAIL", 32.0, 24.0, 10.0),
        ("N", 4, 60.0, 20.0, "OUTP", "INN", "TAIL", 32.0, 24.0, 10.0),
    ]
    for name, nx, x, y, cn, bn, en, cy, by, ey in hbts:
        c = pc("npn13G2", {"Nx": nx})
        t = inst(c, x, y)
        m1 = sorted(
            [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
            key=lambda b: b.center().y,
        )
        m2 = [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(10, 2))]
        assert len(m1) == 2 and len(m2) == 1
        bp, cp = m1
        ep = m2[0]
        cols = 16 if nx == 4 else 4
        cx = cp.center().x
        ex = ep.center().x
        # Collector escapes north and emitter south on separate broad Metal4 strips.
        vc = via(
            1,
            4,
            cols,
            2 if name == "TAIL" else 1,
            cx,
            cp.center().y + (0.24 if name == "TAIL" else 0.04),
            cn,
        )
        riser(4, cx, vc.width(), cp.center().y, cy)
        via(4, 5, cols, 5, cx, cy, cn)
        ve = via(2, 4, cols, 3, ex, ep.center().y, en)
        riser(4, ex, ve.width(), ep.center().y, ey)
        via(4, 5, cols, 5, ex, ey, en)
        # Base exits west on Metal3, below the emitter; no base via into the emitter strip.
        bx = x - 5
        via(1, 3, cols, 1, bp.center().x, bp.center().y - 0.04, bn)
        rect(3, bx, bp.center().y - 0.2, bp.right, bp.center().y + 0.2)
        via(3, 4, 2, 1, bx, bp.center().y, bn)
        riser(4, bx, 1.0, bp.center().y, by)
        via(4, 5, 2, 2, bx, by, bn)
        records.append(
            dict(
                kind="hbt",
                name=name,
                nx=nx,
                placement_um=[x, y],
                nets=[cn, bn, en, "BULK"],
                collector_pin=str(cp),
                base_pin=str(bp),
                emitter_pin=str(ep),
            )
        )
    # Four native three-terminal resistors, geometry fixed by the analog source.
    # Each actual pin is measured before escape routing; no guessed terminal box.
    for name, x, y, width, length, bottom_net, top_net, bottom_y, top_y in [
        ("RP", 61.775, 40.0, 2.0, 27.5, "OUTP", "AVDD", 32.0, 94.0),
        ("RN", 21.775, 40.0, 2.0, 27.5, "OUTN", "AVDD", 32.0, 94.0),
        ("RTP", -24.0, 30.0, 10.0, 70.215, "INP", "VCM", 24.0, 112.0),
        ("RTN", 96.0, 30.0, 10.0, 70.215, "INN", "VCM", 24.0, 112.0),
    ]:
        c = pc("rsil", {"w": f"{width:g}u", "l": f"{length:g}u"})
        t = inst(c, x, y)
        ps = sorted([s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
                    key=lambda b: b.center().y)
        if len(ps) != 2:
            raise ValueError("Unexpected native resistor pins")
        cols = 4 if width == 2.0 else 22
        for p, net, target in [(ps[0], bottom_net, bottom_y), (ps[1], top_net, top_y)]:
            v = via(1, 4, cols, 2, p.center().x, p.center().y, net)
            riser(4, p.center().x, v.width(), p.center().y, target)
            via(4, 5, cols, 5, p.center().x, target, net)
        records.append(dict(kind="resistor", name=name, nets=[bottom_net, top_net, "BULK"],
                            width_um=width, length_um=length, placement_um=[x, y],
                            actual_pin_boxes_um=[str(p) for p in ps]))
    # M5 buses terminate at real boundary access rectangles. No pad or ESD is implied.
    for net, x1, x2, y, width in [
        ("AVDD", 20.0, 125.0, 94.0, 8.0),
        ("TAIL", 20.0, 73.0, 10.0, 8.0),
        ("AVSS", 8.0, 53.0, -22.0, 8.0),
        ("IREF", -40.0, 36.0, -4.0, 2.0),
        ("INP", -40.0, 15.0, 24.0, 2.0),
        ("INN", 55.0, 125.0, 24.0, 2.0),
        ("OUTN", -40.0, 30.5, 32.0, 6.0),
        ("OUTP", 58.0, 125.0, 32.0, 6.0),
        ("VCM", -19.0, 125.0, 112.0, 2.0),
    ]:
        rect(5, x1, y-width/2, x2, y+width/2)
    rect(5, 29.5, -30.0, 31.5, -22.0)
    for net, x, y in [("INP", -40.0, 24.0), ("INN", 125.0, 24.0),
                      ("OUTN", -40.0, 32.0), ("OUTP", 125.0, 32.0),
                      ("IREF", -40.0, -4.0), ("AVDD", 125.0, 94.0),
                      ("AVSS", 30.5, -30.0), ("VCM", 125.0, 112.0)]:
        port(net, 5, x, y)
    # Explicit native p-type substrate contacts, routed independently of AVSS.
    for x in [-32.0, 118.0]:
        for y in [-22.0, 20.0, 75.0, 118.0]:
            c = pc("ptap1", {"w": "2u", "l": "2u"})
            t = inst(c, x, y)
            ps = [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))]
            assert len(ps) == 1
            p = ps[0]
            via(1, 4, 3, 3, p.center().x, p.center().y, "SUB")
            records.append(
                dict(
                    kind="substrate_tap",
                    placement_um=[x, y],
                    nets=["SUB", "BULK"],
                    active_area_um2=4.0,
                    active_perimeter_um=8.0,
                )
            )
        riser(4, x + 1, 2.0, -22.0, 126.0)
        via(4, 5, 3, 3, x + 1, 126.0, "SUB")
    rect(5, -32, 125, 125, 127)
    port("SUB", 5, 125, 126)
    # The pre-layout SUB was an ideal compact-model bulk. The physical model
    # retains a separate BULK plus eight real square ptap1 contacts to SUB.
    net = physical_reference(circuit.read_text())
    if set(ports) != set(PORTS):
        raise ValueError("Incomplete physical port inventory")
    box = top.dbbox()
    dx, dy = -box.left, -box.bottom
    transform = pya.Trans(round(dx/layout.dbu), round(dy/layout.dbu))
    top.transform(transform)
    ports = {name: (m, b.transformed(pya.DTrans(dx, dy))) for name, (m, b) in ports.items()}
    box = top.dbbox()
    if box.left != 0 or box.bottom != 0:
        raise ValueError("Nonzero abstract origin")
    for name, (metal, b) in ports.items():
        if not (b.left == 0 or b.bottom == 0 or b.right == box.right or b.top == box.top):
            raise ValueError("Physical port is not boundary accessible: " + name)
    lef = abstract_lef(pya, layout.dbu, box, ports)
    out.mkdir(parents=True)
    (out / "schematic.cir").write_text(net)
    layout.write(str(out / "nssoc_rx_hbt_v2_layout.gds"))
    (out / "nssoc_rx_hbt_v2_layout.lef").write_text(lef)
    if any(sha(Path(p)) != v for p, v in pins.items()):
        raise RuntimeError("Native PCell inputs changed during generation")
    rec = dict(
        status="GENERATED_REQUIRES_DRC_LVS_PEX_AND_CURRENT_QUALIFICATION",
        input_sha256=pins,
        output_sha256={p.name: sha(p) for p in out.iterdir()},
        instances=records,
        source_circuit_sha256=sha(circuit),
        origin_translation_um=[dx, dy],
        ports={n: dict(layer="Metal"+str(m), rect_um=[b.left,b.bottom,b.right,b.top])
               for n, (m,b) in ports.items()},
        abstract_scope="Physical pin rectangles and conservative obstructions on all seven routing metals. No Liberty or package model.",
        bbox_um=str(top.dbbox()),
        klayout_version=pya.__version__,
        manufacturing_approval=False,
        phy_complete=False,
        scope="One continuous-time RX preamplifier, four native HBTs, four native rsil devices and eight real square substrate taps. External VCM/current reference. No CTLE/slicer/CDR, PCIe link, qualified RF layout, EM, interconnect PEX, timing/power Liberty or chip integration.",
    )
    (out / "result.json").write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()
