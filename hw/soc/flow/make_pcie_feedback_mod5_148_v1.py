#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate the native-cell modulo-five macro with a drive-four Q2B inverter and six-pin abstract.

Native DRC/LVS, terminal binding, wire extraction and finite loaded simulation
are separate gates. This generator does not establish a qualified PLL or PHY.
"""

import argparse
import hashlib
import json
import re
import sys
from decimal import Decimal
from pathlib import Path
import pya


def normalize_and_abstract(layout, top, out, tracks, width_um, port_names):
    original = top.bbox()
    assert original == pya.Box(-240, -220, 63120, 18450)
    shift = pya.Trans(240, 220)
    before = {
        i: pya.Region(top.begin_shapes_rec(i)).merged() for i in layout.layer_indices()
    }
    top.transform(shift)
    for index, region in before.items():
        restored = (
            pya.Region(top.begin_shapes_rec(index))
            .merged()
            .transformed(shift.inverted())
        )
        assert (region ^ restored).is_empty(), layout.get_info(index)
    assert top.bbox() == pya.Box(0, 0, 63360, 18670)
    ports = {}
    for name in port_names:
        if name in tracks:
            y = round(tracks[name] * 1000) + 220
            ports[name] = dict(
                layer="Metal4",
                rect=[240, y - 150, 740, y + 150],
                direction="INPUT" if name in ["CLK", "RESET_B"] else "OUTPUT",
                use="SIGNAL",
            )
        else:
            y = 4000 if name == "VDD" else 220
            ports[name] = dict(
                layer="Metal1",
                rect=[240, y - 150, round(width_um * 1000) + 240, y + 150],
                direction="INOUT",
                use="POWER" if name == "VDD" else "GROUND",
            )
    layers = {
        "Metal1": (8, 0),
        "Metal2": (10, 0),
        "Metal3": (30, 0),
        "Metal4": (50, 0),
        "Metal5": (67, 0),
        "TopMetal1": (126, 0),
        "TopMetal2": (134, 0),
    }

    def rectangle(box):
        return " ".join(
            f"{x / 1000:.3f}" for x in [box.left, box.bottom, box.right, box.top]
        )

    lines = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "MACRO nssoc_mod5_strong_q2b148_v1",
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        "  SIZE 63.360 BY 18.670 ;",
    ]
    for name, port in ports.items():
        box = pya.Box(*port["rect"])
        metal = pya.Region(
            top.begin_shapes_rec(layout.layer(*layers[port["layer"]]))
        ).merged()
        assert (pya.Region(box) - metal).is_empty(), name
        lines += [
            f"  PIN {name}",
            f"    DIRECTION {port['direction']} ;",
            f"    USE {port['use']} ;",
            "    PORT",
            f"      LAYER {port['layer']} ;",
            f"        RECT {rectangle(box)} ;",
            "    END",
            f"  END {name}",
        ]
    lines += ["  OBS"]
    for name in layers:
        region = pya.Region(top.bbox())
        for port in ports.values():
            if port["layer"] == name:
                region -= pya.Region(pya.Box(*port["rect"]))
        lines.append(f"    LAYER {name} ;")
        for polygon in region.decompose_trapezoids_to_region().each():
            assert polygon.is_box()
            lines.append("      RECT " + rectangle(polygon.bbox()) + " ;")
    lines += ["  END", "END nssoc_mod5_strong_q2b148_v1", "END LIBRARY"]
    (out / "nssoc_mod5_strong_q2b148_v1.lef").write_text("\n".join(lines) + "\n")
    return ports


def build(pdk, out):
    R = Path.cwd()
    out = out.resolve()
    out.mkdir(parents=True)
    P = pdk.resolve() / "libs.ref/sg13g2_stdcell"
    sys.path.insert(0, str(R / "hw/soc/flow"))
    from make_pcie_feedback_toggle36_v1 import PDK_INPUTS

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    for n, h in PDK_INPUTS.items():
        assert sha(P / n) == h
    TOP = "nssoc_mod5_strong_q2b148_v1"
    # Q2 gates every next-state bit, including all invalid-state recovery.
    rows = [
        ("FF0", "dfrbpq_2", ["q0", "CLK", "d0", "RESET_B", "VDD", "VSS"]),
        ("FF1", "dfrbpq_2", ["q1", "CLK", "d1", "RESET_B", "VDD", "VSS"]),
        ("FF2", "dfrbpq_2", ["Q2", "CLK", "d2", "RESET_B", "VDD", "VSS"]),
        ("Q0B", "inv_1", ["q0b", "q0", "VDD", "VSS"]),
        ("Q2B", "inv_4", ["Q2B", "Q2", "VDD", "VSS"]),
        ("D0N", "nand2_1", ["d0b", "Q2B", "q0b", "VDD", "VSS"]),
        ("D0I", "inv_1", ["d0", "d0b", "VDD", "VSS"]),
        ("XX0", "nand2_1", ["xn0", "q1", "q0", "VDD", "VSS"]),
        ("XX1", "nand2_1", ["xn1", "q1", "xn0", "VDD", "VSS"]),
        ("XX2", "nand2_1", ["xn2", "q0", "xn0", "VDD", "VSS"]),
        ("XX3", "nand2_1", ["xq", "xn1", "xn2", "VDD", "VSS"]),
        ("D1N", "nand2_1", ["d1b", "Q2B", "xq", "VDD", "VSS"]),
        ("D1I", "inv_1", ["d1", "d1b", "VDD", "VSS"]),
        ("D2N", "nand3_1", ["d2b", "Q2B", "q1", "q0", "VDD", "VSS"]),
        ("D2I", "inv_1", ["d2", "d2b", "VDD", "VSS"]),
    ]
    ports = ["CLK", "RESET_B", "Q2", "Q2B", "VDD", "VSS"]
    full = (P / "spice/sg13g2_stdcell.spice").read_text()
    lef = (P / "lef/sg13g2_stdcell.lef").read_text()
    cells = {}
    subs = []
    reference = []
    fingers = []
    for short in dict.fromkeys(c for _, c, _ in rows):
        name = "sg13g2_" + short
        block = re.search(r"(?im)^\.subckt " + name + r" .*?^\.ends.*?$", full, re.S)[0]
        subs.append(block)
        pin_names = block.splitlines()[0].split()[2:]
        lefb = re.search(r"(?ms)^MACRO " + name + r"\n.*?^END " + name + r"\b", lef)[0]
        w = float(re.search(r"SIZE (\S+) BY", lefb)[1])
        cells[short] = dict(name=name, ports=pin_names, width=w)
        for line in block.splitlines():
            v = line.split()
            if (
                v
                and v[0].startswith("X")
                and len(v) > 5
                and v[5] in ["sg13_lv_nmos", "sg13_lv_pmos"]
            ):
                params = dict(x.split("=") for x in v[6:])
                ng = int(params["ng"])
                assert ng in [1, 2, 4] and params["m"] == "1"
                ww = params["w"]
                scale = {"n": Decimal(".001"), "u": Decimal(1)}
                each = Decimal(ww[:-1]) * scale[ww[-1]] / ng
                for k in range(ng):
                    reference.append(
                        " ".join(
                            [
                                "M" + v[0][1:] + "_" + str(k),
                                *v[1:6],
                                f"w={each}u",
                                f"l={params['l']}",
                            ]
                        )
                    )
                fingers.append(
                    dict(
                        cell=name,
                        instance=v[0],
                        fingers=ng,
                        width_um=str(each),
                        nodes=v[1:5],
                    )
                )
            else:
                reference.append(line)
    layout = pya.Layout()
    layout.read(str(P / "gds/sg13g2_stdcell.gds"))
    assert layout.dbu == 0.001
    top = layout.create_cell(TOP)

    def pt(x, y):
        return pya.Point(round(x * 1000), round(y * 1000))

    def box(layer, x0, y0, x1, y1):
        top.shapes(layout.layer(*layer)).insert(pya.Box(pt(x0, y0), pt(x1, y1)))

    def wire(layer, points):
        top.shapes(layout.layer(*layer)).insert(pya.Path([pt(*p) for p in points], 300))

    def via(n, x, y):
        layers = {
            1: ((8, 0), (10, 0), (19, 0)),
            2: ((10, 0), (30, 0), (29, 0)),
            3: ((30, 0), (50, 0), (49, 0)),
        }
        lo, hi, cut = layers[n]
        box(cut, x - 0.095, y - 0.095, x + 0.095, y + 0.095)
        for layer in [lo, hi]:
            box(layer, x - 0.15, y - 0.15, x + 0.15, y + 0.15)

    # Independent access points avoid adjacent vertical-track spacing and cell metal.
    access = {
        "dfrbpq_2": {
            "Q": (12.8, 1.67, 12.8),
            "CLK": (6.67, 1.64, 6.67),
            "D": (0.435, 1.615, 0.435),
            "RESET_B": (2.475, 1.735, 2.475),
        },
        "inv_4": {"Y": (1.925, 2.7, 2.10), "A": (0.700, 1.70, 0.70)},
        "inv_1": {"Y": (0.970, 2.7, 1.0), "A": (0.465, 1.685, 0.46)},
        "nand2_1": {
            "Y": (0.960, 2.7, 1.0),
            "A": (1.435, 1.685, 1.54),
            "B": (0.475, 1.685, 0.46),
        },
        "nand3_1": {
            "Y": (0.900, 2.76, 1.54),
            "A": (1.95, 1.695, 2.10),
            "B": (1.03, 1.695, 1.005),
            "C": (0.475, 1.695, 0.45),
        },
    }
    nets = {}
    x = 0
    placements = []
    calls = []
    for instance, short, nodes in rows:
        c = cells[short]
        assert len(nodes) == len(c["ports"])
        cell = layout.cell(c["name"])
        top.insert(pya.CellInstArray(cell.cell_index(), pya.Trans(pt(x, 0))))
        placements.append(dict(instance=instance, cell=c["name"], x_um=x))
        calls.append(" ".join(["X" + instance, *nodes, c["name"]]))
        for name, net in zip(c["ports"], nodes, strict=True):
            if name in ["VDD", "VSS"]:
                continue
            px, y, tx = access[short][name]
            px += x
            tx += x
            via(1, px, y)
            wire((10, 0), [(px, y), (tx, y)])
            via(2, tx, y)
            nets.setdefault(net, []).append((tx, y))
        if short == "dfrbpq_2":
            via(1, x + 4.985, 3.215)
            via(2, x + 4.985, 3.215)
            wire((30, 0), [(x + 2.475, 3.215), (x + 4.985, 3.215)])
        x = round(x + c["width"], 3)
    assert len(rows) == 15 and x == 62.88
    tracks = {net: round(5.5 + 0.8 * i, 3) for i, net in enumerate(nets)}
    for net, points in nets.items():
        y = tracks[net]
        for xx, yy in points:
            wire((30, 0), [(xx, yy), (xx, y)])
            via(3, xx, y)
        lo = min(xx for xx, _ in points)
        hi = max(xx for xx, _ in points)
        if net in ports:
            lo = 0
        wire((50, 0), [(lo, y), (max(hi, lo + 0.5), y)])
        if net in ports:
            box((50, 2), 0, y - 0.15, 0.5, y + 0.15)
            top.shapes(layout.layer(50, 25)).insert(
                pya.Text(net, pya.Trans(pt(0.25, y)))
            )
    for name, y in [("VDD", 3.78), ("VSS", 0)]:
        box((8, 2), 0, y - 0.15, x, y + 0.15)
        top.shapes(layout.layer(8, 25)).insert(pya.Text(name, pya.Trans(pt(x / 2, y))))
    # Strip child text without altering any geometry.
    top.flatten(-1, False)
    for li in layout.layer_indices():
        if layout.get_info(li).datatype == 25:
            for shape in list(top.each_shape(li)):
                if shape.is_text():
                    shape.delete()
    for net in ports:
        if net in tracks:
            top.shapes(layout.layer(50, 25)).insert(
                pya.Text(net, pya.Trans(pt(0.25, tracks[net])))
            )
    for name, y in [("VDD", 3.78), ("VSS", 0)]:
        top.shapes(layout.layer(8, 25)).insert(pya.Text(name, pya.Trans(pt(x / 2, y))))
    port_geometry = normalize_and_abstract(layout, top, out, tracks, x, ports)
    opt = pya.SaveLayoutOptions()
    opt.select_cell(top.cell_index())
    layout.write(str(out / (TOP + ".gds")), opt)
    toptext = (
        "\n.subckt "
        + TOP
        + " "
        + " ".join(ports)
        + "\n"
        + "\n".join(calls)
        + "\n.ends "
        + TOP
        + "\n"
    )
    (out / "schematic.cir").write_text("\n".join(reference) + toptext)
    (out / "source.spice").write_text("\n".join(subs) + toptext)
    (out / "IHP-source-notice.txt").write_text(full.split(".subckt", 1)[0])
    (out / "finger-reference.json").write_text(json.dumps(fingers, indent=2) + "\n")
    census = sum(
        sum(f["fingers"] for f in fingers if f["cell"] == "sg13g2_" + short)
        for _, short, _ in rows
    )
    r = dict(
        status="GENERATED_UNVERIFIED_MOD5_STANDARD_CELL_MACRO",
        top=TOP,
        ports=port_geometry,
        physical_mos_fingers=census,
        placements=placements,
        nets=nets,
        tracks=tracks,
        bbox=str(top.bbox()),
        inputs={
            str(p): sha(p)
            for p in [
                Path(__file__),
                P / "gds/sg13g2_stdcell.gds",
                P / "spice/sg13g2_stdcell.spice",
                P / "lef/sg13g2_stdcell.lef",
            ]
        },
        outputs={p.name: sha(p) for p in out.iterdir() if p.is_file()},
        drc_pass=False,
        lvs_pass=False,
        serial_phy_complete=False,
    )
    (out / "result.json").write_text(json.dumps(r, indent=2) + "\n")
    print(r["status"], census)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.pdk, args.out)


if __name__ == "__main__":
    main()
