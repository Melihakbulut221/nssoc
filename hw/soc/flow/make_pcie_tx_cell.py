#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate one native-PCell experimental CML TX; requires independent DRC/LVS/PEX."""

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


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
    if out.exists() or not out.is_relative_to(root / "hw/soc/out"):
        ap.error("Use a fresh project output directory")
    source = args.pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    inputs = [
        p for p in source.rglob("*") if p.is_file() and p.suffix in [".py", ".json"]
    ] + [lyp, Path(__file__).resolve(), root / "hw/soc/analog/pcie/tx_cml_rsil.spice"]
    pins = {str(p): sha(p) for p in inputs}
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- registers native PCells

    layout = pya.Layout()
    top = layout.create_cell("nssoc_tx_cml_layout")
    layers = {}
    for prop in ET.parse(lyp).getroot().iter("properties"):
        name = prop.findtext("name", "")
        src = prop.findtext("source", "")
        if name in [f"Metal{i}.drawing" for i in range(1, 6)]:
            layers[int(name[5])] = int(src.split("/")[0])
    records = []

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
        b = rect(m, x - w / 2, y - h / 2, x + w / 2, y + h / 2)
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
        ("TAIL", 8, 40.0, -10.0, "TAIL", "IREF", "AVSS", 10.0, -4.0, -22.0),
        ("P", 8, 20.0, 20.0, "OUTN", "INP", "TAIL", 32.0, 24.0, 10.0),
        ("N", 8, 60.0, 20.0, "OUTP", "INN", "TAIL", 32.0, 24.0, 10.0),
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
        cols = 32 if nx == 8 else 4
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
        if bn in ["INP", "INN"]:
            port(bn, 5, bx, by)
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
    for name, x, net in [("RP", 61.475, "OUTP"), ("RN", 21.475, "OUTN")]:
        c = pc("rsil", {"w": "10u", "l": "70.215u"})
        t = inst(c, x, 40)
        ps = sorted(
            [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
            key=lambda b: b.center().y,
        )
        assert len(ps) == 2
        for p, n, target in [(ps[0], net, 32.0), (ps[1], "AVDD", 118.0)]:
            v = via(1, 4, 22, 2, p.center().x, p.center().y, n)
            riser(4, p.center().x, v.width(), p.center().y, target)
            via(4, 5, 22, 5, p.center().x, target, n)
        records.append(
            dict(
                kind="resistor",
                name=name,
                nets=["AVDD", net, "BULK"],
                width_um=10.0,
                length_um=70.215,
                placement_um=[x, 40.0],
            )
        )
    # Horizontal Metal5 buses. Current-density/EM and extracted RF remain separate gates.
    for net, x1, x2, y, w in [
        ("AVDD", 20.0, 73.0, 118.0, 8.0),
        ("TAIL", 20.0, 73.0, 10.0, 8.0),
        ("AVSS", 8.0, 53.0, -22.0, 8.0),
        ("IREF", 4.0, 36.0, -4.0, 2.0),
    ]:
        rect(5, x1, y - w / 2, x2, y + w / 2)
        if net != "TAIL":
            port(net, 5, (x1 + x2) / 2, y, w=3, h=2)
    port("OUTN", 5, 26.475, 32.0, w=16, h=6)
    port("OUTP", 5, 66.475, 32.0, w=16, h=6)
    # Explicit native p-type substrate contacts, routed independently of AVSS.
    for x in [0.0, 85.0]:
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
    rect(5, 0, 125, 87, 127)
    port("SUB", 5, 44, 126)
    # Physical reference removes ideal measurement probes and represents all eight
    # native substrate contacts explicitly. BULK is their internal substrate node.
    net = (
        "* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\n* SPDX-"
        + "License-Identifier: CERN-OHL-W-2.0\n.subckt nssoc_tx_cml_layout INP INN OUTP OUTN AVDD AVSS SUB IREF\n"
    )
    for name, nx, x, y, cn, bn, en, cy, by, ey in hbts:
        net += f"Q{name} {cn} {bn} {en} BULK npn13G2 Nx={nx} we=0.07u le=0.9u m=1\n"
    net += "RP AVDD OUTP BULK rsil w=10u l=70.215u m=1\nRN AVDD OUTN BULK rsil w=10u l=70.215u m=1\n.ends nssoc_tx_cml_layout\n"
    net = net.replace(
        ".ends nssoc_tx_cml_layout",
        "".join(f"RTAP{i} SUB BULK ptap1 A=4p P=8u\n" for i in range(8))
        + ".ends nssoc_tx_cml_layout",
    )
    out.mkdir(parents=True)
    (out / "schematic.cir").write_text(net)
    layout.write(str(out / "nssoc_tx_cml_layout.gds"))
    if any(sha(Path(p)) != v for p, v in pins.items()):
        raise RuntimeError("Native PCell inputs changed during generation")
    rec = dict(
        status="GENERATED_REQUIRES_DRC_LVS_PEX_AND_CURRENT_QUALIFICATION",
        input_sha256=pins,
        output_sha256={p.name: sha(p) for p in out.iterdir()},
        instances=records,
        bbox_um=str(top.dbbox()),
        klayout_version=pya.__version__,
        manufacturing_approval=False,
        phy_complete=False,
        scope="One TX current-steering cell only, four native HBT PCells, two native rsil loads and eight substrate taps. External predriver/current reference; not complete PCIe, qualified RF layout, EM, or extracted characterization.",
    )
    (out / "result.json").write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()
