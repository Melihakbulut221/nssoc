#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate the native CDR V/I interface: eight HBTs, four resistors, one MIM and thirteen taps.

The substrate and signal-return ports remain distinct. Generation does not
establish DRC/LVS, extracted electrical performance, PVT or full PHY acceptance.
"""

import argparse
from pathlib import Path
import sys
import json
import hashlib
import xml.etree.ElementTree as ET

PORTS = ["xp", "xn", "yp", "yn", "op", "on", "avdd", "avss", "sub", "irx", "iry"]
TOP = "nssoc_cdr_vi13_layout_v1"
CIRCUIT = "hw/soc/analog/pcie/cdr_vi_hbt_v1.spice"
CIRCUIT_SHA256 = "9f13b4eeca782f34feb3a858937de871f61b2e7ab5a06ffc43ecfdfb5f5268ef"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def devices(text):
    if hashlib.sha256(text.encode()).hexdigest() != CIRCUIT_SHA256:
        raise ValueError("CDR V/I source differs from the frozen native circuit")
    rows = []
    for line in text.lower().splitlines():
        fields = line.split()
        if not fields or not fields[0].startswith("x"):
            continue
        found = [(model, count) for model, count in
                 (("npn13g2", 4), ("rppd", 3), ("cap_cmim", 2))
                 if len(fields) > count + 1 and fields[count + 1] == model]
        assert len(found) == 1, fields
        model, count = found[0]
        params = dict(p.split("=") for p in fields[count + 2:])
        assert len(params) == len(fields[count + 2:])
        rows.append(dict(path="xvi." + fields[0], model=model,
                         nets=fields[1:count + 1], params=params))
    assert [r["path"] for r in rows] == ["xvi." + n for n in
        ("xxp", "xxn", "xtx", "xrx", "xyp", "xyn", "xty", "xry",
         "xrp", "xrn", "xbp", "xbn", "xcf")]
    assert all(r["params"] == {"nx": "1"} for r in rows[:8])
    assert rows[-1]["params"] == {"w": "40u", "l": "40u"}
    assert rows[-1]["nets"] == ["op", "on"]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    R = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(R / "hw/soc/out"):
        parser.error("Use a fresh project output directory")
    source = R / CIRCUIT
    rows = devices(source.read_text())
    pdk = args.pdk.resolve()
    src = pdk / "libs.tech/klayout/python"
    lyp = src.parent / "tech/sg13g2.lyp"
    inputs = [
        Path(__file__).resolve(),
        source,
        R / "hw/soc/flow/make_pcie_clock_vco_v6_local_v1.py",
        *src.rglob("*.py"),
        *src.rglob("*.json"),
        lyp,
    ]
    pins = {str(p): sha(p) for p in inputs}
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(src), str(src / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- native PCell registration

    layout = pya.Layout()
    top = layout.create_cell(TOP)
    layers = {
        p.findtext("name")[:-8]: int(p.findtext("source").split("/")[0])
        for p in ET.parse(lyp).getroot().iter("properties")
        if p.findtext("name", "").endswith(".drawing")
    }
    terminals = {}
    routes = []
    records = []
    reference = [
        "* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
        "* SPDX-License-" "Identifier: CERN-OHL-W-2.0",
        ".subckt " + TOP + " " + " ".join(PORTS),
    ]

    def pc(name, params):
        c = layout.create_cell(name, "SG13_dev", params)
        assert c is not None and not c.is_empty()
        return c

    def place(c, x, y):
        t = pya.DTrans(round(x / 0.005) * 0.005, round(y / 0.005) * 0.005)
        top.insert(pya.DCellInstArray(c.cell_index(), t))
        return t

    def metal(n):
        return "Metal" + str(n) if n <= 5 else "TopMetal" + str(n - 5)

    def box(n, x1, y1, x2, y2):
        b = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers[metal(n)], 0)).insert(b)
        return b

    def via(lo, hi, x, y, cols=2):
        c = pc(
            "via_stack",
            dict(
                b_layer=metal(lo),
                t_layer=metal(hi),
                vt1_columns=2,
                vt1_rows=1,
                vt2_columns=1,
                vt2_rows=1,
                vn_columns=cols,
                vn_rows=1,
            ),
        )
        b = c.dbbox()
        place(c, x - b.center().x, y - b.center().y)

    def escape(pin, met, net, lane, label, cols=4, offset=0):
        x = round(pin.center().x / 0.005) * 0.005
        y = round((pin.center().y + offset) / 0.005) * 0.005
        via(met, 3, x, y, cols)
        box(3, lane - 0.2, y - 0.2, x + 0.2, y + 0.2)
        via(3, 4, lane, y)
        terminals.setdefault(net, []).append((lane, y))
        routes.append(
            dict(
                device=label, net=net, native_layer=met, pin=str(pin), escape=[lane, y]
            )
        )

    for i, row in enumerate(rows):
        x = 30 + i * 60
        y = 30
        n = row["nets"]
        p = row["params"]
        name = "D" + str(i)
        if row["model"] == "npn13g2":
            c = pc("npn13G2", {"Nx": int(p["nx"])})
            t = place(c, x, y)
            m1 = sorted(
                [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().y,
            )
            m2 = [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(10, 2))]
            assert len(m1) == 2 and len(m2) == 1
            base, collector = m1
            for pin, met, net, lane, off in [
                (collector, 1, n[0], x - 9, 0.04),
                (base, 1, n[1], x - 6, -0.04),
                (m2[0], 2, n[2], x - 3, 0),
            ]:
                escape(pin, met, net, lane, name, 4, off)
            reference.append(
                f"Q{name} "
                + " ".join(n[:3] + ["BULK"])
                + f" npn13G2 Nx={p['nx']} we=0.07u le=0.9u m=1"
            )
        elif row["model"] == "rppd":
            c = pc("rppd", {"w": p["w"], "l": p["l"]})
            t = place(c, x, y)
            ps = sorted(
                [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().y,
            )
            assert len(ps) == 2
            for k, pin in enumerate(ps):
                escape(pin, 1, n[k], x - 6 + 3 * k, name)
            reference.append(
                f"R{name} "
                + " ".join(n[:2] + ["BULK"])
                + f" rppd w={p['w']} l={p['l']} b=0 m=1"
            )
        else:
            assert row["model"] == "cap_cmim"
            c = pc("cmim", {"w": p["w"], "l": p["l"]})
            t = place(c, x, y)
            plates = {}
            for met in (5, 6):
                bs = [z.dbbox().transformed(t) for z in
                      c.each_shape(layout.layer(layers[metal(met)], 0)) if z.is_box()]
                assert len(bs) == 1
                plates[met] = bs[0]
            cy = round(plates[6].center().y / 0.005) * 0.005
            plus, minus = x - 9, x - 6
            # Both via stacks are OUTSIDE the native capacitor plates.
            # Only the top plate crosses the other leg, on TopMetal1.
            assert minus + 1.2 < min(b.left for b in plates.values())
            box(6, plus - 1.2, cy - 1.2, plates[6].center().x, cy + 1.2)
            via(5, 6, plus, cy)
            via(4, 5, plus, cy)
            terminals.setdefault(n[0], []).append((plus, cy))
            box(5, minus - 0.6, cy - 0.6, plates[5].center().x, cy + 0.6)
            via(4, 5, minus, cy)
            terminals.setdefault(n[1], []).append((minus, cy))
            routes.extend([dict(device=name, net=n[0], native_layer=6,
                                pin=str(plates[6]), escape=[plus, cy]),
                           dict(device=name, net=n[1], native_layer=5,
                                pin=str(plates[5]), escape=[minus, cy])])
            reference.append(f"C{name} " + " ".join(n)
                             + f" cap_cmim w={p['w']} l={p['l']} m=1")
        records.append(
            dict(
                row,
                instance=name,
                placement_um=[x, y],
                bbox_um=str(c.dbbox().transformed(t)),
            )
        )
        tap = pc("ptap1", {"w": "2u", "l": "2u"})
        tt = place(tap, x + 10, 10)
        ps = [s.dbbox().transformed(tt) for s in tap.each_shape(layout.layer(8, 2))]
        assert len(ps) == 1
        escape(ps[0], 1, "sub", x + 15, name + "_tap", 3)
        reference.append(f"RPTAP{i} sub BULK ptap1 A=4p P=8u")
    ports = {}
    for i, net in enumerate(sorted(terminals)):
        y = 150 + i * 6
        xs = []
        for x, sy in terminals[net]:
            box(4, x - 0.6, min(sy, y) - 0.2, x + 0.6, max(sy, y) + 0.2)
            via(4, 5, x, y)
            xs.append(x)
        box(5, 0, y - 0.6, max(xs) + 1, y + 0.6)
        if net in PORTS:
            pin = pya.DBox(0, y - 0.6, 2, y + 0.6)
            ports[net] = ("Metal5", pin)
            top.shapes(layout.layer(layers["Metal5"], 2)).insert(pin)
            top.shapes(layout.layer(layers["Metal5"], 25)).insert(pya.DText(net, 0, y))
    assert set(ports) == set(PORTS)
    sys.path.insert(0, str(R / "hw/soc/flow"))
    import make_pcie_clock_vco_v6_local_v1 as writer

    writer.TOP = TOP
    writer.PORTS = PORTS
    writer.use_direction = lambda n: (
        ("POWER", "INOUT")
        if n == "avdd"
        else ("GROUND", "INOUT")
        if n in ["avss", "sub"]
        else ("SIGNAL", "OUTPUT" if n in ["op", "on"] else "INPUT")
    )
    bbox = top.dbbox()
    assert bbox.left == 0
    dy = -bbox.bottom
    top.transform(pya.Trans(0, round(dy / layout.dbu)))
    ports = {
        n: (met, b.transformed(pya.DTrans(0, dy))) for n, (met, b) in ports.items()
    }
    bbox = top.dbbox()
    out.mkdir()
    layout.write(str(out / (TOP + ".gds")))
    (out / (TOP + ".lef")).write_text(writer.lef(pya, layout.dbu, bbox, ports))
    (out / "schematic.cir").write_text("\n".join(reference + [".ends " + TOP, ""]))
    assert all(sha(Path(p)) == h for p, h in pins.items())
    (out / "result.json").write_text(
        json.dumps(
            dict(
                status="GENERATED_UNVERIFIED_DEVELOPMENT_LAYOUT",
                inputs=pins,
                outputs={p.name: sha(p) for p in out.iterdir()},
                core_devices=records,
                substrate_contacts=13,
                routes=routes,
                ports={n: str(b) for n, (_, b) in ports.items()},
                bbox_um=str(bbox),
                drc_pass=False,
                lvs_pass=False,
                pex_qualified=False,
                main_chip_integrated=False,
                serial_phy_complete=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("GENERATED", bbox)


if __name__ == "__main__":
    main()
