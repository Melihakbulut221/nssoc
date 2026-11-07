#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native SG13G2 layout of the c5r3k vctrl series-RC integrator macro.

Two core devices from pll_vctrl_integrator_c5r3k_v1.spice: XRINT (rppd W2
L23, about 3.0 kOhm) from vctrl to the internal node and XCINT (cmim
57.7 x 57.7 um, about 5.0 pF) from the internal node to avss. The conventions
are those of make_pcie_pump_filter13_v1.py: one finite substrate contact per
core device on the SUB port, M1->M3 escapes to private M4 lanes, one M5 bus
per net, and Metal5 ports on the left edge (x=0) for direct parent landing.
The cmim escape lanes sit to the right of the plate because the plate is far
wider than the pump's 40 um device pitch. Generation alone does not establish
DRC/LVS, PEX or loop behaviour.

Intended parent placement (not performed here): lower-left corner at
PARENT_ORIGIN_UM inside the free PLL area (1022,1495)-(2162,1760) um, between
the AVSS TopMetal2 strap (x 940-1020) and the unused area to its right.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_pcie_pump_filter13_v1 as pump  # noqa: E402

TOP = "nssoc_pll_vctrl_integrator_c5r3k_v1"
SUBCKT = "nssoc_pll_vctrl_integrator_c5r3k_v1"
PORTS = ["vctrl", "avss", "sub"]
SOURCE = "pll_vctrl_integrator_c5r3k_v1.spice"
SOURCE_SHA256 = "c2e30198888c9c6cd87229155f7a141b5487305cb0e794fbdbc831cc6fa87f19"
CORE = {
    "xint.xrint": dict(model="rppd", nets=["vctrl", "xint.mid", "sub"],
                       params={"w": "2u", "l": "23u", "b": "0", "sw_et": "1"}),
    "xint.xcint": dict(model="cap_cmim", nets=["xint.mid", "avss"],
                       params={"w": "57.7u", "l": "57.7u"}),
}
# Free-area placement proposal for the parent integration step (um).
PARENT_ORIGIN_UM = (1100.0, 1550.0)
BUS_Y0 = 110.0  # first M5 bus; above the 57.7 um plate placed at y=30.
# Device origins: rppd lanes at x+17/x+21 and its tap lane at x+33 stay
# well left of the cmim bottom plate (x=80-0.6).
ORIGIN_X = {"rppd": 30.0, "cap_cmim": 80.0}


def devices(text):
    if hashlib.sha256(text.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Frozen integrator source changed")
    rows, wires = pump.expand(pump.definitions({SOURCE: text}), [SUBCKT, "xint", PORTS])
    if wires or {r["path"]: {k: r[k] for k in ("model", "nets", "params")} for r in rows} != CORE:
        raise ValueError("Unexpected integrator core")
    return rows


def lef(pya, dbu, box, ports):
    saved = pump.TOP, pump.PORTS
    try:
        pump.TOP, pump.PORTS = TOP, PORTS
        return pump.lef(pya, dbu, box, ports)
    finally:
        pump.TOP, pump.PORTS = saved


def build(pdk, out):
    root = Path(__file__).resolve().parents[3]
    out = out.resolve()
    if out.exists() or not out.is_relative_to(root / "hw/soc/out"):
        raise ValueError("Use a fresh project output directory")
    circuit = root / "hw/soc/analog/pcie" / SOURCE
    rows = devices(circuit.read_text())
    source = pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    inputs = [
        circuit,
        Path(__file__).resolve(),
        Path(pump.__file__).resolve(),
        *source.rglob("*.py"),
        *source.rglob("*.json"),
        lyp,
    ]
    pins = {str(p): pump.pin(p) for p in inputs}
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- registers native PCells

    layout = pya.Layout()
    top = layout.create_cell(TOP)
    layers = {
        p.findtext("name")[:-8]: int(p.findtext("source").split("/")[0])
        for p in ET.parse(lyp).getroot().iter("properties")
        if p.findtext("name", "").endswith(".drawing")
    }
    records, terminals, routes = [], {}, []
    # REUSE-IgnoreStart
    reference = [
        "* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
        "* SPDX-License-Identifier: CERN-OHL-W-2.0",
        ".subckt " + TOP + " " + " ".join(PORTS),
    ]
    # REUSE-IgnoreEnd

    def pc(name, params):
        cell = layout.create_cell(name, "SG13_dev", params)
        assert cell is not None and not cell.is_empty()
        return cell

    def place(cell, x, y):
        t = pya.DTrans(round(x / 0.005) * 0.005, round(y / 0.005) * 0.005)
        top.insert(pya.DCellInstArray(cell.cell_index(), t))
        return t

    def metal(n):
        return "Metal" + str(n) if n <= 5 else "TopMetal" + str(n - 5)

    def box(n, x1, y1, x2, y2):
        b = pya.DBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        top.shapes(layout.layer(layers[metal(n)], 0)).insert(b)
        return b

    def via(lo, hi, x, y):
        cell = pc(
            "via_stack",
            dict(b_layer=metal(lo), t_layer=metal(hi), vn_columns=1, vn_rows=1,
                 vt1_columns=2, vt1_rows=1, vt2_columns=1, vt2_rows=1),
        )
        b = cell.dbbox()
        place(cell, x - b.center().x, y - b.center().y)

    def escape(pin, net, lane, label):
        x = round(pin.center().x / 0.005) * 0.005
        y = round(pin.center().y / 0.005) * 0.005
        via(1, 3, x, y)
        box(3, x - 0.2, y - 0.2, lane + 0.2, y + 0.2)
        via(3, 4, lane, y)
        terminals.setdefault(net, []).append((lane, y))
        routes.append(dict(device=label, net=net, native_pin=str(pin), escape=[lane, y]))

    def grid(v):
        return round(v / 0.005) * 0.005

    for i, row in enumerate(rows):
        n, p, name, model = row["nets"], row["params"], "D" + str(i), row["model"]
        params = {k: p[k] for k in ("w", "l")}
        x, y = ORIGIN_X[model], 30
        if model == "rppd":
            # Same as the pump: lanes 17 and 21 um right of the device origin.
            lane = x + 17
            cell = pc("rppd", params)
            t = place(cell, x, y)
            ps = sorted(
                [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().y,
            )
            assert len(ps) == 2
            for k, pinn in enumerate(ps):
                escape(pinn, n[k], lane + 4 * k, name)
            reference.append(
                f"R{name} " + " ".join(n[:2] + ["BULK"]) + f" rppd w={p['w']} l={p['l']} b=0 m=1"
            )
        else:
            assert model == "cap_cmim"
            cell = pc("cmim", params)
            t = place(cell, x, y)
            plates = {}
            for met in [5, 6]:
                bs = [
                    s.dbbox().transformed(t)
                    for s in cell.each_shape(layout.layer(layers[metal(met)], 0))
                    if s.is_box()
                ]
                assert len(bs) == 1
                plates[met] = bs[0]
            # Pump convention (plus lane+8, minus lane+4), with the lane moved
            # 9 um beyond the actual Metal5 bottom plate instead of x+17.
            lane = grid(plates[5].right + 9)
            py = grid(plates[6].center().y)
            px, mx = lane + 8, lane + 4
            box(6, plates[6].center().x, py - 1.2, px + 1.2, py + 1.2)
            via(5, 6, px, py)
            via(4, 5, px, py)
            terminals.setdefault(n[0], []).append((px, py))
            box(5, plates[5].center().x, py - 0.6, mx + 0.6, py + 0.6)
            via(4, 5, mx, py)
            terminals.setdefault(n[1], []).append((mx, py))
            reference.append(
                f"C{name} " + " ".join(n) + f" cap_cmim w={p['w']} l={p['l']} m=1"
            )
            routes.append(dict(device=name, plus_net=n[0], minus_net=n[1],
                               plus_escape=[px, py], minus_escape=[mx, py],
                               plus_contact_outside_bottom_plate=px - 1.2 > plates[5].right))
            assert px - 1.2 > plates[5].right + 2
        records.append(dict(row, instance=name, placement_um=[x, y],
                            bbox_um=str(cell.dbbox().transformed(t))))
        tap = pc("ptap1", {"w": "2u", "l": "2u"})
        tt = place(tap, x + 10, 10)
        tp = [s.dbbox().transformed(tt) for s in tap.each_shape(layout.layer(8, 2))]
        assert len(tp) == 1
        escape(tp[0], "sub", lane + 16, name + "_ptap")
        reference.append(f"RPTAP{i} sub BULK ptap1 A=4p P=8u")
    ports = {}
    nets = sorted(terminals)
    assert nets == ["avss", "sub", "vctrl", "xint.mid"], nets
    for i, net in enumerate(nets):
        y = BUS_Y0 + i * 6
        xs = []
        for lx, sy in terminals[net]:
            box(4, lx - 0.6, min(sy, y) - 0.2, lx + 0.6, max(sy, y) + 0.2)
            via(4, 5, lx, y)
            xs.append(lx)
        left = 0 if net in PORTS else min(xs) - 1
        box(5, left, y - 0.6, max(xs) + 1, y + 0.6)
        if net in PORTS:
            pinbox = pya.DBox(0, y - 0.6, 2, y + 0.6)
            ports[net] = ("Metal5", pinbox)
            top.shapes(layout.layer(layers["Metal5"], 2)).insert(pinbox)
            top.shapes(layout.layer(layers["Metal5"], 25)).insert(pya.DText(net, 0, y))
    assert set(ports) == set(PORTS)
    bbox = top.dbbox()
    assert bbox.left == 0
    dy = -bbox.bottom
    top.transform(pya.Trans(0, round(dy / layout.dbu)))
    ports = {n: (met, b.transformed(pya.DTrans(0, dy))) for n, (met, b) in ports.items()}
    bbox = top.dbbox()
    out.mkdir()
    layout.write(str(out / (TOP + ".gds")))
    (out / (TOP + ".lef")).write_text(lef(pya, layout.dbu, bbox, ports))
    (out / "schematic.cir").write_text("\n".join(reference + [".ends " + TOP, ""]))
    assert all(pump.pin(Path(p)) == h for p, h in pins.items())
    (out / "result.json").write_text(
        json.dumps(
            dict(
                status="GENERATED_UNVERIFIED_DEVELOPMENT_LAYOUT",
                inputs=pins,
                outputs={p.name: pump.pin(p) for p in out.iterdir()},
                core_devices=records,
                substrate_contacts=2,
                well_contacts=0,
                routes=routes,
                ports={n: str(b) for n, (_, b) in ports.items()},
                bbox_um=str(bbox),
                origin_translation_um=[0, dy],
                parent_origin_proposal_um=list(PARENT_ORIGIN_UM),
                computed_values=dict(
                    rppd_ohm_typical=3016, rppd_ohm_rsh234=2716, rppd_ohm_rsh286=3317,
                    cmim_fF_typical=5003,
                    method="rppd: rsh*L/(W+0.006um) + 2*35ohm*um/W; cmim: 1.5fF/um2*A + 0.04fF/um*P (PDK typical)"),
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.pdk, args.out)


if __name__ == "__main__":
    main()
