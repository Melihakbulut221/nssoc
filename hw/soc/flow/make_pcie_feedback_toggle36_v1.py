#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate the IHP standard-cell feedback /2 development macro and physical abstract.

Uses immutable PDK DFF2/INV1 cells with explicit metal feedback and reset straps.
This macro is not a general DFF, a PLL, or a complete PCIe PHY. Native DRC/LVS,
parasitic simulation and loaded parent integration are separate checks.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
import pya

TOP = "nssoc_std_toggle2_v1"
PDK_INPUTS = {
    "gds/sg13g2_stdcell.gds": "6ee92931ad70eeb8f79ca89fe0d4f38892d9e7e14d1a1b21bfb7118e55bf232f",
    "spice/sg13g2_stdcell.spice": "2b6d4e3cb169bdbb1350e01e213ffe7bb4bad261821a51a2fe38a5c92211975a",
}


def pin(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_and_abstract(L, top, out):
    assert L.dbu == 0.001
    box = top.bbox()
    assert (box.left, box.bottom, box.right, box.top) == (-240, -220, 15120, 6150)
    regions = {
        i: pya.Region(top.begin_shapes_rec(i)).merged() for i in L.layer_indices()
    }
    shift = pya.Trans(240, 220)
    top.transform(shift)
    for i, before in regions.items():
        after = (
            pya.Region(top.begin_shapes_rec(i)).merged().transformed(shift.inverted())
        )
        assert (before ^ after).is_empty(), L.get_info(i)
    assert top.bbox() == pya.Box(0, 0, 15360, 6370)
    ports = {
        n: dict(
            layer="Metal3",
            rect=[round(x * 1000) - 150 + 240, 5920, round(x * 1000) + 150 + 240, 6370],
            direction="INPUT" if n in ["CLK", "RESET_B"] else "OUTPUT",
            use="SIGNAL",
        )
        for n, x in [("CLK", 6.67), ("RESET_B", 2.475), ("Q", 12.8), ("QB", 14.410)]
    }
    for n, y in [("VDD", 3780), ("VSS", 0)]:
        ports[n] = dict(
            layer="Metal1",
            rect=[240, y + 70, 15120, y + 370],
            direction="INOUT",
            use="POWER" if n == "VDD" else "GROUND",
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
    for n, p in ports.items():
        rect = pya.Region(pya.Box(*p["rect"]))
        metal = pya.Region(top.begin_shapes_rec(L.layer(*layers[p["layer"]]))).merged()
        assert (rect - metal).is_empty(), n

    def rect(box):
        return " ".join(
            f"{v / 1000:.3f}" for v in [box.left, box.bottom, box.right, box.top]
        )

    lines = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        f"MACRO {TOP}",
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        "  SIZE 15.360 BY 6.370 ;",
    ]
    for n, p in ports.items():
        lines += [
            f"  PIN {n}",
            f"    DIRECTION {p['direction']} ;",
            f"    USE {p['use']} ;",
            "    PORT",
            f"      LAYER {p['layer']} ;",
            f"        RECT {rect(pya.Box(*p['rect']))} ;",
            "    END",
            f"  END {n}",
        ]
    lines += ["  OBS"]
    for name in layers:
        obs = pya.Region(top.bbox())
        for p in ports.values():
            if p["layer"] == name:
                obs -= pya.Region(pya.Box(*p["rect"]))
        lines.append(f"    LAYER {name} ;")
        for polygon in obs.decompose_trapezoids_to_region().each():
            assert polygon.is_box()
            lines.append("      RECT " + rect(polygon.bbox()) + " ;")
    lines += ["  END", f"END {TOP}", "END LIBRARY"]
    (out / (TOP + ".lef")).write_text("\n".join(lines) + "\n")
    return ports


def build(pdk, out):
    P = pdk.resolve() / "libs.ref/sg13g2_stdcell"
    out = out.resolve()
    if out.exists():
        raise ValueError("Use a fresh output directory")
    for name, want in PDK_INPUTS.items():
        if pin(P / name) != want:
            raise ValueError("Frozen PDK source changed: " + name)
    out.mkdir(parents=True)
    L = pya.Layout()
    L.read(str(P / "gds/sg13g2_stdcell.gds"))
    top = L.create_cell(TOP)

    def point(x, y):
        return pya.Point(round(x / L.dbu), round(y / L.dbu))

    def box(layer, x0, y0, x1, y1):
        top.shapes(L.layer(*layer)).insert(pya.Box(point(x0, y0), point(x1, y1)))

    def wire(layer, points, width=0.3):
        top.shapes(L.layer(*layer)).insert(
            pya.Path([point(*p) for p in points], round(width / L.dbu))
        )

    def via1(x, y):
        box((19, 0), x - 0.095, y - 0.095, x + 0.095, y + 0.095)
        for layer in [(8, 0), (10, 0)]:
            box(layer, x - 0.15, y - 0.15, x + 0.15, y + 0.15)

    def via2(x, y):
        box((29, 0), x - 0.095, y - 0.095, x + 0.095, y + 0.095)
        for layer in [(10, 0), (30, 0)]:
            box(layer, x - 0.15, y - 0.15, x + 0.15, y + 0.15)

    for name, x in [("sg13g2_dfrbpq_2", 0), ("sg13g2_inv_1", 13.44)]:
        c = L.cell(name)
        assert c is not None
        top.insert(pya.CellInstArray(c.cell_index(), pya.Trans(point(x, 0))))
    q = (12.80, 1.67)
    a = (13.905, 1.685)
    d = (0.435, 1.615)
    qb = (14.410, 2.7)
    for x, y in [q, a, d, qb]:
        via1(x, y)
    wire((10, 0), [q, (a[0], q[1]), a])
    wire((10, 0), [d, (d[0], qb[1]), qb])
    pins = {"CLK": (6.67, 1.64), "RESET_B": (2.475, 1.735), "Q": q, "QB": qb}
    for name, (x, y) in pins.items():
        if name not in ["Q", "QB"]:
            via1(x, y)
        via2(x, y)
        wire((30, 0), [(x, y), (x, 6.15)])
        box((30, 2), x - 0.15, 5.7, x + 0.15, 6.15)
        top.shapes(L.layer(30, 25)).insert(pya.Text(name, pya.Trans(point(x, 5.9))))
    # Explicit metal strap between the two RESET_B metal islands already joined
    # through native poly. Keeps the original netlist while making the bridge
    # part of the measured metal RC instead of an implicit poly-only connection.
    via1(4.985, 3.215)
    via2(4.985, 3.215)
    wire((30, 0), [(2.475, 3.215), (4.985, 3.215)])
    for name, y in [("VDD", 3.78), ("VSS", 0)]:
        box((8, 2), 0.0, y - 0.15, 14.88, y + 0.15)
        top.shapes(L.layer(8, 25)).insert(pya.Text(name, pya.Trans(point(7.44, y))))
    # Flatten exact cell geometry and retain only macro interface metal labels.
    # Child labels A/D/Y otherwise concatenate to A|Q and D|QB|Y in flat LVS.
    conductors = [(8, 0), (10, 0), (30, 0), (19, 0), (29, 0)]
    before = {
        str(z): pya.Region(top.begin_shapes_rec(L.layer(*z))).merged()
        for z in conductors
    }
    top.flatten(-1, False)
    removed = []
    for li in L.layer_indices():
        info = L.get_info(li)
        if info.datatype == 25:
            for shape in list(top.each_shape(li)):
                if shape.is_text():
                    removed.append({"layer": str(info), "text": shape.text.string})
                    shape.delete()
    for name, (x, y) in pins.items():
        top.shapes(L.layer(30, 25)).insert(pya.Text(name, pya.Trans(point(x, 5.9))))
    for name, y in [("VDD", 3.78), ("VSS", 0)]:
        top.shapes(L.layer(8, 25)).insert(pya.Text(name, pya.Trans(point(7.44, y))))
    assert all(
        (
            before[str(z)] ^ pya.Region(top.begin_shapes_rec(L.layer(*z))).merged()
        ).is_empty()
        for z in conductors
    )
    ports = normalize_and_abstract(L, top, out)
    (out / "label-normalization.json").write_text(
        json.dumps(
            {
                "status": "EXACT_CONDUCTOR_XOR_PRESERVED_AFTER_FLATTEN_AND_MACRO_LABELS",
                "removed_labels": removed,
                "port_names": list(pins) + ["VDD", "VSS"],
                "area_dbu2": {key: region.area() for key, region in before.items()},
            },
            indent=2,
        )
        + "\n"
    )
    opt = pya.SaveLayoutOptions()
    opt.select_cell(top.cell_index())
    L.write(str(out / (TOP + ".gds")), opt)
    full = (P / "spice/sg13g2_stdcell.spice").read_text()
    subs = []
    for name in ["sg13g2_dfrbpq_2", "sg13g2_inv_1"]:
        hit = re.search(r"(?im)^\.subckt " + name + r" .*?^\.ends.*?$", full, re.S)
        assert hit
        subs.append(hit[0])
    # The LVS deck reads primitive M devices; the ngspice source uses X wrappers.
    # Enumerate the two explicit parallel fingers, preserving total W and all nets.
    from decimal import Decimal

    normal = []
    finger_proof = []
    for line in "\n".join(subs).splitlines():
        words = line.split()
        if (
            words
            and words[0].startswith("X")
            and len(words) > 5
            and words[5] in ["sg13_lv_nmos", "sg13_lv_pmos"]
        ):
            params = dict(v.split("=") for v in words[6:])
            ng = int(params["ng"])
            assert ng in [1, 2] and params["m"] == "1"
            w = params["w"]
            scale = {"n": Decimal("0.001"), "u": Decimal(1)}
            total = Decimal(w[:-1]) * scale[w[-1]]
            each = total / ng
            for i in range(ng):
                normal.append(
                    " ".join(
                        [
                            "M" + words[0][1:] + "_" + str(i),
                            *words[1:6],
                            f"w={each}u",
                            f"l={params['l']}",
                        ]
                    )
                )
            finger_proof.append(
                dict(
                    source=words[0],
                    total_width_um=str(total),
                    fingers=ng,
                    per_finger_um=str(each),
                    nodes=words[1:5],
                )
            )
            assert each * ng == total
        else:
            normal.append(line)
    assert len(finger_proof) == 34 and sum(r["fingers"] for r in finger_proof) == 36
    (out / "finger-reference.json").write_text(
        json.dumps(
            {
                "status": "EXACT_PDK_PARALLEL_FINGER_EXPANSION_FOR_LVS",
                "devices": finger_proof,
                "native_spice_source_unchanged": True,
            },
            indent=2,
        )
        + "\n"
    )
    (out / "schematic.cir").write_text(
        "\n".join(normal)
        + f"\n.subckt {TOP} CLK RESET_B Q QB VDD VSS\nXDFF Q CLK QB RESET_B VDD VSS sg13g2_dfrbpq_2\nXINV QB Q VDD VSS sg13g2_inv_1\n.ends {TOP}\n"
    )
    # Preserve the upstream notice alongside the derived native reference.
    notice = full.split(".subckt", 1)[0]
    assert "Copyright 2023 IHP PDK Authors" in notice
    (out / "IHP-source-notice.txt").write_text(notice)
    r = dict(
        status="GENERATED_UNVERIFIED_DEVELOPMENT_LAYOUT",
        top=TOP,
        ports=ports,
        bbox_dbu=[0, 0, 15360, 6370],
        physical_mos_fingers=36,
        inputs={
            str(p): pin(p)
            for p in [P / name for name in PDK_INPUTS] + [Path(__file__).resolve()]
        },
        outputs={p.name: pin(p) for p in out.iterdir() if p.is_file()},
        drc_pass=False,
        lvs_pass=False,
        qualified_pex=False,
        main_chip_integrated=False,
        serial_phy_complete=False,
    )
    assert all(pin(Path(p)) == h for p, h in r["inputs"].items())
    (out / "result.json").write_text(json.dumps(r, indent=2) + "\n")
    print(r["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.pdk, args.out)


if __name__ == "__main__":
    main()
