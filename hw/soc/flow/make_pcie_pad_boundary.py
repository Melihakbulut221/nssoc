#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native differential bondpad/ESD boundary candidate, not HBM/RF approval."""

import argparse, json, sys
from pathlib import Path
from make_pcie_analog_bank import sha

TOP = "nssoc_pcie_pad_boundary"
PORTS = ("PADP", "PADN", "AVDD", "AVSS")
PDK_REV = "c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c"


def reference():
    return (
        "* "
        + "SPDX"
        + "-FileCopyrightText: 2026 Hasan Melih Akbulut\n* "
        + "SPDX"
        + "-License-Identifier: CERN-OHL-W-2.0\n.subckt "
        + TOP
        + " "
        + " ".join(PORTS)
        + "\n"
        + "".join(
            f"D{p}{t} AVDD PAD{p} AVSS diodev{t}_2kv m=1\n"
            for p in ("P", "N")
            for t in ("dd", "ss")
        )
        + ".ends "
        + TOP
        + "\n"
    )


def lef(pya, dbu, ports):
    if set(ports) != set(PORTS):
        raise ValueError("Incomplete physical pad ports")
    lines = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "MACRO " + TOP,
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        "  SIZE 220 BY 220 ;",
    ]
    for name in PORTS:
        pin = ports[name]
        use = "POWER" if name == "AVDD" else "GROUND" if name == "AVSS" else "SIGNAL"
        lines += [
            "  PIN " + name,
            "    DIRECTION INOUT ;",
            "    USE " + use + " ;",
            "    PORT",
            "      LAYER " + pin["layer"] + " ;",
        ]
        for b in pin["rectangles_um"]:
            lines += ["      RECT " + " ".join(f"{v:.3f}" for v in b) + " ;"]
        lines += ["    END", "  END " + name]
    lines += ["  OBS"]
    for metal in (
        "Metal1",
        "Metal2",
        "Metal3",
        "Metal4",
        "Metal5",
        "TopMetal1",
        "TopMetal2",
    ):
        region = pya.Region(pya.DBox(0, 0, 220, 220).to_itype(dbu))
        openings = pya.Region()
        for pin in ports.values():
            if pin["layer"] == metal:
                for b in pin["rectangles_um"]:
                    openings.insert(pya.DBox(*b).to_itype(dbu))
        lines += ["    LAYER " + metal + " ;"]
        for p in (region - openings).decompose_trapezoids_to_region().each():
            if p.area() != p.bbox().area():
                raise ValueError("Nonrectangular obstruction")
            b = p.bbox().to_dtype(dbu)
            lines += [
                f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;"
            ]
    return "\n".join(lines + ["  END", "END " + TOP, "END LIBRARY", ""])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ("pdk", "out"):
        ap.add_argument("--" + n, type=Path, required=True)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[3]
    pdk = a.pdk.resolve()
    out = a.out.resolve()
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-pad-")
    ):
        ap.error("Fresh project or /dev/shm/nssoc-pad- output required")
    source = pdk / "libs.tech/klayout/python"
    pr = pdk / "libs.ref/sg13g2_pr/gds/sg13g2_pr.gds"
    inputs = [
        Path(__file__).resolve(),
        root / "hw/soc/flow/make_pcie_analog_bank.py",
        pr,
        pdk / "libs.tech/ngspice/models/sg13g2_esd.lib",
        *source.rglob("*.py"),
        *source.rglob("*.json"),
    ]
    pins = {str(p): sha(p) for p in inputs}
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa:F401 native PCells

    l = pya.Layout()
    native = pya.Layout()
    native.read(str(pr))
    top = l.create_cell(TOP)
    instances = []
    vias = []
    ports = {}

    def rect(layer, b):
        top.shapes(l.layer(layer, 0)).insert(b)

    def inst(c, x, y):
        t = pya.DTrans(float(x), float(y))
        top.insert(pya.DCellInstArray(c.cell_index(), t))
        return t

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
        b = c.dbbox()
        t = inst(c, x - b.center().x, y - b.center().y)
        if upper == "TopMetal1":
            rect(126, pya.DBox(x - 1.2, y - 1.2, x + 1.2, y + 1.2))
        vias.append(
            dict(
                bottom=bottom,
                top=upper,
                net=net,
                center_um=[x, y],
                bbox_um=str(b.transformed(t)),
            )
        )

    def pin(name, layer, boxes):
        ports[name] = dict(
            layer={67: "Metal5", 134: "TopMetal2"}[layer],
            rectangles_um=[[b.left, b.bottom, b.right, b.top] for b in boxes],
        )
        for b in boxes:
            rect(layer, b)
            top.shapes(l.layer(layer, 2)).insert(b)
            top.shapes(l.layer(layer, 25)).insert(
                pya.DText(name, pya.DTrans(b.center().x, b.center().y))
            )

    for net, y in [("AVDD", 180.0), ("AVSS", 200.0)]:
        rect(67, pya.DBox(0, y - 2, 220, y + 2))
        pin(net, 67, [pya.DBox(0, y - 2, 4, y + 2)])
    for index, polarity in enumerate(("P", "N")):
        padnet = "PAD" + polarity
        px = 50 + index * 100
        pad = l.create_cell(
            "bondpad",
            "SG13_dev",
            dict(
                shape="octagon",
                stack="nil",
                fill="nil",
                diameter="70u",
                topMetal="TM2",
                bottomMetal="1",
                padType="bondpad",
                padPin=padnet,
                addFillerEx="t",
            ),
        )
        if pad is None or pad.is_empty():
            raise ValueError("Native bondpad failed")
        bb = pad.dbbox()
        t = inst(pad, px - bb.center().x, 60 - bb.center().y)
        instances.append(
            dict(
                kind="bondpad",
                net=padnet,
                center_um=[px, 60],
                bbox_um=str(bb.transformed(t)),
            )
        )
        rect(134, pya.DBox(px - 2, 60, px + 2, 220))
        # The same physical terminal has one bond access and one core-edge access.
        pin(
            padnet,
            134,
            [pya.DBox(px - 15, 45, px + 15, 75), pya.DBox(px - 2, 216, px + 2, 220)],
        )
        for which, offset in [("dd", 10), ("ss", 40)]:
            name = "diodev" + which + "_2kv"
            original = native.cell(name)
            c = l.create_cell(name)
            c.copy_tree(original)
            t = inst(c, offset + index * 100, 120)
            m1 = [s.dbbox().transformed(t) for s in c.each_shape(l.layer(8, 2))]
            m2 = sorted(
                [s.dbbox().transformed(t) for s in c.each_shape(l.layer(10, 2))],
                key=lambda b: b.center().x,
            )
            if len(m1) != 1 or len(m2) != 2:
                raise ValueError("Unexpected immutable diode pin geometry")
            # Native C/B/E derivations plus reader's diode-specific B,E,C / C,E,B
            # order: both PADs use leftM2; high VSS/low VDD use M1.
            mapping = {
                "PAD": ("Metal2", m2[0]),
                "AVDD": ("Metal2", m2[1]) if which == "dd" else ("Metal1", m1[0]),
                "AVSS": ("Metal1", m1[0]) if which == "dd" else ("Metal2", m2[1]),
            }
            measured = {}
            for terminal, (metal, b) in mapping.items():
                x, y = b.center().x, b.center().y
                net = padnet if terminal == "PAD" else terminal
                if terminal == "PAD":
                    y = 140.0
                    if not b.contains(pya.DPoint(x, y)):
                        raise ValueError("Common PAD route misses diode electrode")
                    via(metal, "TopMetal1", x, y, net)
                    rect(126, pya.DBox(min(x, px), y - 1.2, max(x, px), y + 1.2))
                else:
                    dest = 180 if net == "AVDD" else 200
                    route_metal = "Metal5" if net == "AVDD" else "Metal4"
                    route_layer = 67 if net == "AVDD" else 50
                    via(metal, route_metal, x, y, net)
                    rect(
                        route_layer,
                        pya.DBox(x - 0.5, min(y, dest), x + 0.5, max(y, dest)),
                    )
                    if net == "AVSS":
                        via("Metal4", "Metal5", x, dest, net)
                measured[terminal] = dict(
                    layer=metal, box_um=[b.left, b.bottom, b.right, b.top], net=net
                )
            if (
                t.angle != 0
                or t.is_mirror()
                or t.disp.x != float(offset + index * 100)
                or t.disp.y != 120.0
            ):
                raise ValueError(
                    "Native diode translation changed orientation or offset"
                )
            instances.append(
                dict(
                    kind=name,
                    polarity=polarity,
                    native_transform=str(t),
                    translation_um=[offset + index * 100, 120],
                    model_port_order=["AVDD", padnet, "AVSS"],
                    measured_pins=measured,
                )
            )
        via("TopMetal1", "TopMetal2", px, 140.0, padnet)
    if (
        top.dbbox().left != 0
        or top.dbbox().bottom < 0
        or top.dbbox().right != 220
        or top.dbbox().top != 220
    ):
        raise ValueError(
            "Unexpected pad boundary outline "
            + str(top.dbbox())
            + " "
            + repr(
                [
                    (l.cell(i.cell_index).name, str(i.dbbox()), str(i.dtrans))
                    for i in top.each_inst()
                ]
            )
        )
    out.mkdir(parents=True)
    (out / (TOP + ".lef")).write_text(lef(pya, l.dbu, ports))
    l.write(str(out / (TOP + ".gds")))
    (out / "schematic.cir").write_text(reference())
    (out / "model.spice").write_text(
        reference()
        .replace("DPdd", "XPdd")
        .replace("DPss", "XPss")
        .replace("DNdd", "XNdd")
        .replace("DNss", "XNss")
    )
    if any(sha(p) != v for p, v in pins.items()):
        raise ValueError("Native inputs changed")
    result = dict(
        status="GENERATED_REQUIRES_DRC_LVS_LOADING_AND_ESD_SYSTEM_VALIDATION",
        input_sha256=pins,
        output_sha256={p.name: sha(p) for p in out.iterdir()},
        instances=instances,
        vias=vias,
        ports=ports,
        bbox_um=[0, 0, 220, 220],
        main_chip_integrated=False,
        phy_complete=False,
        esd_qualified=False,
        scope="Two actual70um native topmetal bondpads plus four fixed IHP2kv-named protection diode cells with routed rails. Device name is not a system HBM/CDM guarantee; rail clamp/package/current path and RF extraction remain open. No connection to digital3.3V padcell.",
        substrate_contract="Native ESD well/substrate VSS electrodes are electrically common through substrate. AVSS must be reconciled with analog-bank BULK/SUB during a later combined-layout verification; isolated bank is unchanged.",
        raw_lvs_export_caveat="Pinned IHP custom_writer emits Esd3Term default C,B,E instead of diodevdd B,E,C or diodevss C,E,B reader order. Use source reference or actual LVSDB named terminals; raw exported .cir is not a simulator model.",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
