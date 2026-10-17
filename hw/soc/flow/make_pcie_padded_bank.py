#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual four-lane bank plus sixteen bondpads, with explicit physical substrate return."""

import argparse
import json
from pathlib import Path
import sys
from make_pcie_analog_bank import sha, PORTS, use_direction
from make_pcie_pad_boundary import reference as pad_reference

TOP = "nssoc_pcie_padded_bank4"
WIDTH, HEIGHT = 860.0, 1520.0
BANK_GDS_SHA = "93d88e657b034065605d5bdb65e45d20c05903ef3c5d32b8df4509c07514b6da"


def serial_net(lane, kind, polarity):
    if lane not in range(4) or kind not in ("TX", "RX") or polarity not in ("P", "N"):
        raise ValueError("Unknown serial branch")
    return (
        f"L{lane}_{kind}_"
        + ("OUT" if kind == "TX" else "IN")
        + ("P" if polarity == "P" else "N")
    )


def reference(bank):
    lines = bank.splitlines()
    header = [x for x in lines if x.lower().startswith(".subckt ")]
    if len(header) != 1 or tuple(header[0].split()[2:]) != PORTS:
        raise ValueError("Frozen bank reference port contract differs")
    body = [x.split() for x in lines if x.strip() and x[0].upper() in ("Q", "R")]
    if len(body) != 120 or sum(x[0][0] == "Q" for x in body) != 32:
        raise ValueError("Literal bank device census differs")
    result = [
        "* " + "SPDX" + "-FileCopyrightText: 2026 Hasan Melih Akbulut",
        "* " + "SPDX" + "-License-Identifier: CERN-OHL-W-2.0",
        "* New candidate: real ESD substrate electrodes connect original BULK to AVSS; SUB tap access remains distinct.",
        ".subckt " + TOP + " " + " ".join(PORTS),
    ]
    for row in body:
        # Explicit new parent substrate contract, not by-name virtual joining.
        result.append(" ".join("AVSS" if v == "BULK" else v for v in row))
    padlines = [x.split() for x in pad_reference().splitlines() if x.startswith("D")]
    if len(padlines) != 4:
        raise ValueError("Literal four-diode pad reference changed")
    for lane in range(4):
        for kind in ("TX", "RX"):
            for row in padlines:
                row = list(row)
                row[0] = f"D{lane}{kind}_{row[0][1:]}"
                row[2] = serial_net(lane, kind, row[2][-1])
                result.append(" ".join(row))
    return "\n".join(result + [".ends " + TOP, ""])


def lef(pya, dbu, ports):
    if set(ports) != set(PORTS):
        raise ValueError("Padded bank must preserve exact 47-port contract")
    out = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "MACRO " + TOP,
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        f"  SIZE {WIDTH:.3f} BY {HEIGHT:.3f} ;",
    ]
    for n in PORTS:
        metal, b = ports[n]
        use = "POWER" if n == "AVDD" else "GROUND" if n in ("AVSS", "SUB") else "SIGNAL"
        out += [
            "  PIN " + n,
            "    DIRECTION " + use_direction(n)[1] + " ;",
            "    USE " + use + " ;",
            "    PORT",
            "      LAYER " + metal + " ;",
            f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;",
            "    END",
            "  END " + n,
        ]
    out += ["  OBS"]
    for metal in (
        "Metal1",
        "Metal2",
        "Metal3",
        "Metal4",
        "Metal5",
        "TopMetal1",
        "TopMetal2",
    ):
        region = pya.Region(pya.DBox(0, 0, WIDTH, HEIGHT).to_itype(dbu))
        openings = pya.Region()
        for m, b in ports.values():
            if m == metal:
                openings.insert(b.to_itype(dbu))
        out += ["    LAYER " + metal + " ;"]
        for poly in (region - openings).decompose_trapezoids_to_region().each():
            if poly.area() != poly.bbox().area():
                raise ValueError("Nonrectangular abstract obstruction")
            b = poly.bbox().to_dtype(dbu)
            out += [
                f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;"
            ]
    return "\n".join(out + ["  END", "END " + TOP, "END LIBRARY", ""])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ("pdk", "bank", "bank-check", "pad", "pad-check", "out"):
        ap.add_argument("--" + n, type=Path, required=True)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = a.out.resolve()
    pdk = a.pdk.resolve()
    bank = a.bank.resolve()
    pad = a.pad.resolve()
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-padded-")
    ):
        ap.error("Fresh project or /dev/shm/nssoc-padded- output required")
    bg = bank / "nssoc_pcie_analog_bank4.gds"
    pg = pad / "nssoc_pcie_pad_boundary.gds"
    if sha(bg) != BANK_GDS_SHA:
        raise ValueError("Exact source bank geometry differs")
    pins = {str(Path(__file__).resolve()): sha(__file__)}
    for n in ("make_pcie_analog_bank.py", "make_pcie_pad_boundary.py"):
        p = root / "hw/soc/flow" / n
        pins[str(p)] = sha(p)
    records = {}
    for label, folder in [
        ("bank", bank),
        ("bank_check", a.bank_check.resolve()),
        ("pad", pad),
        ("pad_check", a.pad_check.resolve()),
    ]:
        rec = json.loads((folder / "result.json").read_text())
        records[label] = rec
        pins[str(folder / "result.json")] = sha(folder / "result.json")
        if (
            label == "bank_check"
            and rec["status"]
            != "PASS_NATIVE_BANK4_MAIN_DRC_STRICT_LVS_LEF_AND_NEGATIVE_CONTROLS_ONLY"
        ):
            raise ValueError("Completed original bank check required")
        if (
            label == "pad_check"
            and rec["status"]
            != "PASS_PAD_BOUNDARY_MAIN_DRC_STRICT_LVS_AND_SEVEN_NEGATIVES_NO_ESD_RF_APPROVAL"
        ):
            raise ValueError("Completed original pad check required")
        for n, h in rec[
            "outputs" if label == "bank_check" else "output_sha256"
        ].items():
            pins[str(folder / n)] = h
        for source_path, source_hash in rec.get(
            "input_sha256", rec.get("inputs", {})
        ).items():
            if source_path in pins and pins[source_path] != source_hash:
                raise ValueError("Conflicting preserved input identity")
            pins[source_path] = source_hash
    source = pdk / "libs.tech/klayout/python"
    for p in [*source.rglob("*.py"), *source.rglob("*.json")]:
        pins[str(p)] = sha(p)
    if any(sha(p) != h for p, h in pins.items()):
        raise ValueError("Verified primitive/method source changed")
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa:F401

    l = pya.Layout()
    top = l.create_cell(TOP)
    sources = []
    cells = {}
    placements = []
    routes = []
    vias = []
    ports = {}
    layers = {
        "Metal1": 8,
        "Metal2": 10,
        "Metal3": 30,
        "Metal4": 50,
        "Metal5": 67,
        "TopMetal1": 126,
        "TopMetal2": 134,
    }
    for label, path, name in [
        ("bank", bg, "nssoc_pcie_analog_bank4"),
        ("pad", pg, "nssoc_pcie_pad_boundary"),
    ]:
        native = pya.Layout()
        native.read(str(path))
        c = l.create_cell("padded_" + label)
        c.copy_tree(native.cell(name))
        for info in l.layer_infos():
            if info.datatype in (2, 25):
                c.shapes(l.layer(info)).clear()
        sources.append(native)
        cells[label] = c

    def rect(m, b):
        top.shapes(l.layer(layers[m], 0)).insert(b)

    def wire(m, x1, y1, x2, y2, w, net):
        if x1 != x2 and y1 != y2:
            raise ValueError("Only explicit Manhattan parent routes")
        b = pya.DBox(
            min(x1, x2) - w / 2 if x1 == x2 else min(x1, x2),
            min(y1, y2) - w / 2 if y1 == y2 else min(y1, y2),
            max(x1, x2) + w / 2 if x1 == x2 else max(x1, x2),
            max(y1, y2) + w / 2 if y1 == y2 else max(y1, y2),
        )
        rect(m, b)
        routes.append(
            dict(net=net, layer=m, rect_um=[b.left, b.bottom, b.right, b.top])
        )

    def via(bottom, upper, x, y, net):
        c = l.create_cell(
            "via_stack",
            "SG13_dev",
            dict(
                b_layer=bottom,
                t_layer=upper,
                vn_columns=1,
                vn_rows=2,
                vt1_columns=1,
                vt1_rows=1,
                vt2_columns=1,
                vt2_rows=1,
            ),
        )
        if c is None or c.is_empty():
            raise ValueError("Native via failed")
        b = c.dbbox()
        t = pya.DTrans(x - b.center().x, y - b.center().y)
        top.insert(pya.DCellInstArray(c.cell_index(), t))
        if upper in ("TopMetal1", "TopMetal2"):
            rect("TopMetal1", pya.DBox(x - 1.2, y - 1.2, x + 1.2, y + 1.2))
        vias.append(
            dict(
                net=net,
                bottom=bottom,
                top=upper,
                center_um=[x, y],
                bbox_um=str(b.transformed(t)),
            )
        )

    def pin(n, m, b):
        if n in ports:
            raise ValueError("Repeated parent pin")
        ports[n] = (m, b)
        rect(m, b)
        top.shapes(l.layer(layers[m], 2)).insert(b)
        top.shapes(l.layer(layers[m], 25)).insert(
            pya.DText(n, pya.DTrans(b.center().x, b.center().y))
        )

    bt = pya.DTrans(300.0, 60.0)
    top.insert(pya.DCellInstArray(cells["bank"].cell_index(), bt))
    placements.append(dict(kind="bank", transform=str(bt)))
    serial = {
        serial_net(i, k, p) for i in range(4) for k in ("TX", "RX") for p in ("P", "N")
    }
    bp = {
        n: pya.DBox(*v["rect_um"]).transformed(bt)
        for n, v in records["bank"]["ports"].items()
    }
    for n, v in records["bank"]["ports"].items():
        if n not in serial and n not in ("AVDD", "AVSS"):
            pin(n, v["layer"], bp[n])
    for n, x, y in [("AVDD", 240.0, 20.0), ("AVSS", 252.0, 40.0)]:
        wire("Metal1", x, y, x, 1510.0, 2.0, n)
        wire("Metal2", 0.0, y, WIDTH, y, 2.0, n)
        via("Metal1", "Metal2", x, y, n)
        pin(n, "Metal2", pya.DBox(0, y - 1, 4, y + 1))
        b = bp[n]
        sx, sy = b.center().x, b.center().y
        via("Metal3", "TopMetal2", sx, sy, n)
        wire("Metal3", sx, y, sx, sy, 1.0, n)
        via("Metal2", "Metal3", sx, y, n)
    for lane in range(4):
        base = lane * 360.0 + 60.0
        for kind in ("TX", "RX"):
            pt = (
                pya.DTrans(3, False, 0.0, base + 220.0)
                if kind == "TX"
                else pya.DTrans(1, False, 860.0, base + 140.0)
            )
            top.insert(pya.DCellInstArray(cells["pad"].cell_index(), pt))
            placements.append(
                dict(
                    kind="pad",
                    lane=lane,
                    role=kind,
                    transform=str(pt),
                    bbox_um=str(cells["pad"].dbbox().transformed(pt)),
                )
            )
            for pol in ("P", "N"):
                n = serial_net(lane, kind, pol)
                row = records["pad"]["ports"]["PAD" + pol]
                bond = pya.DBox(*row["rectangles_um"][0]).transformed(pt)
                core = pya.DBox(*row["rectangles_um"][1]).transformed(pt)
                pin(n, "TopMetal2", bond)
                # Signals cross the bank only in actual empty inter-cell gaps on Metal4.
                pside = pol == "P"
                bridge = (
                    base + (174.0 if pside else 180.0)
                    if kind == "TX"
                    else base + (354.0 if pside else 360.0)
                )
                padcol = (
                    (230.0 if pside else 242.0)
                    if kind == "TX"
                    else (608.0 if pside else 620.0)
                )
                bankcol = (
                    (580.0 if pside else 280.0)
                    if kind == "TX"
                    else (280.0 if pside else 580.0)
                )
                b = bp[n]
                bx, by = b.center().x, b.center().y
                cx, cy = core.center().x, core.center().y
                wire("TopMetal1", bx, by, bankcol, by, 2.4, n)
                via("TopMetal1", "TopMetal2", bankcol, by, n)
                wire("TopMetal2", bankcol, by, bankcol, bridge, 4.0, n)
                via("Metal4", "TopMetal2", bankcol, bridge, n)
                wire("Metal4", padcol, bridge, bankcol, bridge, 1.2, n)
                via("Metal4", "TopMetal2", padcol, bridge, n)
                wire("TopMetal2", padcol, cy, padcol, bridge, 4.0, n)
                wire("TopMetal2", cx, cy, padcol, cy, 4.0, n)
            for n, trunk in [("AVDD", 240.0), ("AVSS", 252.0)]:
                b = pya.DBox(
                    *records["pad"]["ports"][n]["rectangles_um"][0]
                ).transformed(pt)
                x, y = b.center().x, b.center().y
                via("Metal3", "Metal5", x, y, n)
                if kind == "TX":
                    yy = base + (230.0 if n == "AVDD" else 238.0)
                    wire("Metal3", x, y, x, yy, 1.0, n)
                    via("Metal2", "Metal3", x, yy, n)
                    wire("Metal2", x, yy, trunk, yy, 1.0, n)
                else:
                    yy = base + (174.0 if n == "AVDD" else 180.0)
                    yy0 = base + (122.0 if n == "AVDD" else 130.0)
                    xx = 608.0 if n == "AVDD" else 620.0
                    wire("Metal3", x, yy0, x, y, 1.0, n)
                    wire("Metal3", xx, yy0, x, yy0, 1.0, n)
                    wire("Metal3", xx, yy0, xx, yy, 1.0, n)
                    via("Metal2", "Metal3", xx, yy, n)
                    wire("Metal2", trunk, yy, xx, yy, 1.0, n)
                via("Metal1", "Metal2", trunk, yy, n)
    if set(ports) != set(PORTS):
        raise ValueError("Parent port census differs")
    if (
        top.dbbox().left < 0
        or top.dbbox().bottom < 0
        or top.dbbox().right > WIDTH
        or top.dbbox().top > HEIGHT
    ):
        raise ValueError("Parent geometry outside explicit outline " + str(top.dbbox()))
    out.mkdir(parents=True)
    l.write(str(out / (TOP + ".gds")))
    (out / (TOP + ".lef")).write_text(lef(pya, l.dbu, ports))
    (out / "schematic.cir").write_text(reference((bank / "schematic.cir").read_text()))
    if any(sha(p) != h for p, h in pins.items()):
        raise ValueError("Physical source changed during parent generation")
    rec = dict(
        status="GENERATED_REQUIRES_INDEPENDENT_NATIVE_PARENT_DRC_LVS",
        input_sha256=pins,
        output_sha256={p.name: sha(p) for p in out.iterdir()},
        ports={
            n: dict(layer=m, rect_um=[b.left, b.bottom, b.right, b.top])
            for n, (m, b) in ports.items()
        },
        placements=placements,
        routes=routes,
        vias=vias,
        bbox_um=[0, 0, WIDTH, HEIGHT],
        primitive_counts=dict(
            bank=1,
            pad_pairs=8,
            bondpads=16,
            ESD_diodes=32,
            npn13G2=32,
            rsil=24,
            literal_ptap1=64,
        ),
        substrate_contract="Actual fixed ESD AVSS substrate electrodes physically join common bank BULK to AVSS. Literal bank tap geometries/parameters retained between external SUB and AVSS; no virtual-name join or acceptance inherited.",
        main_chip_integrated=False,
        phy_complete=False,
        qualified_pex=False,
        esd_qualified=False,
    )
    (out / "result.json").write_text(json.dumps(rec, indent=2) + "\n")


if __name__ == "__main__":
    main()
