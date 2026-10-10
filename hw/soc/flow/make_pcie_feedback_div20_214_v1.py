#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate a physical IHP /2-/2-/5 feedback parent with 214 MOS fingers.

Child generators produce pinned standard-cell macros. Parent metal uses their
actual LEF pin regions; short output stubs and a low Q1 track reduce wire load.
Generation alone does not establish electrical timing, PVT, PLL lock or PHY
acceptance. Native extraction and loaded simulation are separate checks.
"""

from pathlib import Path
import argparse, pya, json, hashlib, re
import make_pcie_feedback_toggle36_v1 as toggle
import make_pcie_feedback_mod5_142_v1 as counter


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normalize_and_abstract(layout, top, out, tracks, width_um, port_names, left_edges):
    original = top.bbox()
    assert original == pya.Box(2000, 10000, 131920, 42150)
    shift = pya.Trans(-2000, -10000)
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
    assert top.bbox() == pya.Box(0, 0, 129920, 32150)
    ports = {}
    for name in port_names:
        if name in tracks:
            y = round(tracks[name] * 1000) - 10000
            ports[name] = dict(
                layer="Metal4",
                rect=[left_edges[name], y - 150, left_edges[name] + 500, y + 150],
                direction="INPUT" if name in ["CLK", "RESET_B"] else "OUTPUT",
                use="SIGNAL",
            )
        else:
            y = 4000 if name == "VDD" else 220
            ports[name] = dict(
                layer="Metal1",
                rect=[8240, y - 150, 129680, y + 150],
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
        "MACRO nssoc_feedback_div20_std214_v1",
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        "  SIZE 129.920 BY 32.150 ;",
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
    lines += ["  END", "END nssoc_feedback_div20_std214_v1", "END LIBRARY"]
    (out / "nssoc_feedback_div20_std214_v1.lef").write_text("\n".join(lines) + "\n")
    return ports


def build(pdk, out):
    O = out.resolve()
    O.mkdir()
    C = O / "children"
    C.mkdir()
    T = C / "toggle"
    M = C / "counter"
    toggle.build(pdk, T)
    counter.build(pdk, M)
    TOP = "nssoc_feedback_div20_std214_v1"
    PORTS = ["CLK", "RESET_B", "Q0", "Q1", "Q2", "Q2B", "VDD", "VSS"]
    files = [Path(__file__).resolve()]
    for d in [T, M]:
        r = json.loads((d / "result.json").read_text())
        assert all(sha(Path(p)) == h for p, h in r["inputs"].items())
        assert all(sha(d / p) == h for p, h in r["outputs"].items())
        files.extend([d / "result.json", *[d / p for p in r["outputs"]]])
    L = pya.Layout()
    L.read(str(T / "nssoc_std_toggle2_v1.gds"))
    L.read(str(M / "nssoc_mod5_std_v1.gds"))
    assert L.dbu == 0.001
    children = [
        ("fast0", "nssoc_std_toggle2_v1", 10000, 10000),
        ("fast1", "nssoc_std_toggle2_v1", 40000, 10000),
        ("count", "nssoc_mod5_std_v1", 70000, 10000),
    ]
    top = L.create_cell(TOP)
    for _, name, x, y in children:
        top.insert(pya.CellInstArray(L.cell(name).cell_index(), pya.Trans(x, y)))
    top.flatten(-1, False)
    for li in L.layer_indices():
        for sh in list(top.each_shape(li)):
            if sh.is_text():
                sh.delete()

    def wire(layer, points):
        top.shapes(L.layer(layer, 0)).insert(
            pya.Path([pya.Point(*p) for p in points], 300)
        )

    def via(n, x, y):
        a, b, c = {3: (30, 50, 49), 4: (50, 67, 66)}[n]
        for layer in [a, b]:
            top.shapes(L.layer(layer, 0)).insert(
                pya.Box(x - 150, y - 150, x + 150, y + 150)
            )
        top.shapes(L.layer(c, 0)).insert(pya.Box(x - 95, y - 95, x + 95, y + 95))

    # Every parent connection starts inside an independently verified child LEF pin.
    # Mod5 tracks are physically continuous; only the declared LEF pins may be used.
    # Extend each declared left-edge pin outwards on its own Metal4 track before
    # climbing separate Metal5 trunks, avoiding internal macro metal crossings.
    ports_t = json.loads((T / "result.json").read_text())["ports"]
    ports_m = json.loads((M / "result.json").read_text())["ports"]
    taps = {}
    for instance, name, x, y in children:
        ports = ports_t if instance != "count" else ports_m
        for port, entry in ports.items():
            x0, y0, x1, y1 = entry["rect"]
            px = x + (x0 + x1) // 2
            py = y + (y0 + y1) // 2
            if entry["layer"] == "Metal1" or (instance != "count" and port == "QB"):
                continue
            actual = pya.Region(
                top.begin_shapes_rec(
                    L.layer({"Metal3": 30, "Metal4": 50}[entry["layer"]], 0)
                )
            )
            assert (
                pya.Region(pya.Box(px - 100, py - 100, px + 100, py + 100)) - actual
            ).is_empty()
            if instance == "count":
                # Four staggered outside trunks; child left boundary is x=70um.
                target = {"CLK": 60000, "RESET_B": 62000, "Q2": 64000, "Q2B": 66000}[
                    port
                ]
                wire(50, [(px, py), (target, py)])
                px = target
            elif entry["layer"] == "Metal3":
                via(3, px, py)
            via(4, px, py)
            taps[(instance, port)] = (px, py)
    connections = {
        "CLK": [("fast0", "CLK")],
        "RESET_B": [(i, "RESET_B") for i, _, _, _ in children],
        "Q0": [("fast0", "Q"), ("fast1", "CLK")],
        "Q1": [("fast1", "Q"), ("count", "CLK")],
        "Q2": [("count", "Q2")],
        "Q2B": [("count", "Q2B")],
    }
    route = []
    for j, (net, terms) in enumerate(connections.items()):
        y = 17200 if net == "Q1" else 32000 + j * 2000
        points = [taps[t] for t in terms]
        left = 2000 if net in ["CLK", "RESET_B"] else min(x for x, _ in points) - 500
        wire(50, [(left, y), (max(x for x, _ in points), y)])
        for x, py in points:
            wire(67, [(x, py), (x, y)])
            via(4, x, y)
        top.shapes(L.layer(50, 25)).insert(pya.Text(net, pya.Trans(left + 100, y)))
        route.append(dict(net=net, terms=terms, points=points, track_y=y))
    for net, y in [("VSS", 10220), ("VDD", 14000)]:
        wire(8, [(10240, y), (131680, y)])
        top.shapes(L.layer(8, 25)).insert(pya.Text(net, pya.Trans(10500, y)))
    # QB pins of the fast toggles remain local feedback nets, with no parent label.
    port_geometry = normalize_and_abstract(
        L,
        top,
        O,
        {row["net"]: row["track_y"] / 1000 for row in route},
        0,
        PORTS,
        {
            row["net"]: (
                0
                if row["net"] in ["CLK", "RESET_B"]
                else min(x for x, y in row["points"]) - 2500
            )
            for row in route
        },
    )
    opt = pya.SaveLayoutOptions()
    opt.select_cell(top.cell_index())
    L.write(str(O / (TOP + ".gds")), opt)
    for fname in ["schematic.cir", "source.spice"]:
        defs = {}
        for d in [T, M]:
            for block in re.findall(
                r"(?ms)^\.subckt\s+.*?^\.ends[^\n]*",
                (
                    d
                    / ("schematic.cir" if d == T and fname == "source.spice" else fname)
                ).read_text(),
            ):
                name = block.splitlines()[0].split()[1]
                if (
                    d == T
                    and fname == "source.spice"
                    and name != "nssoc_std_toggle2_v1"
                ):
                    continue
                if name in defs:
                    assert (
                        re.sub(r"\s+", " ", defs[name]).strip()
                        == re.sub(r"\s+", " ", block).strip()
                    ), name
                defs[name] = block
        parent = (
            f".subckt {TOP} "
            + " ".join(PORTS)
            + "\nXfast0 CLK RESET_B Q0 Q0B VDD VSS nssoc_std_toggle2_v1\nXfast1 Q0 RESET_B Q1 Q1B VDD VSS nssoc_std_toggle2_v1\nXcount Q1 RESET_B Q2 Q2B VDD VSS nssoc_mod5_std_v1\n.ends "
            + TOP
            + "\n"
        )
        (O / fname).write_text("\n".join(defs.values()) + "\n" + parent)
    (O / "IHP-source-notice.txt").write_bytes(
        (M / "IHP-source-notice.txt").read_bytes()
    )
    r = dict(
        status="GENERATED_UNVERIFIED_214_MOS_DIV20_PARENT_SHORT_Q1",
        top=TOP,
        ports=port_geometry,
        physical_mos_fingers=214,
        children=children,
        routes=route,
        bbox_dbu=str(top.bbox()),
        inputs={str(p): sha(p) for p in files},
        outputs={p.name: sha(p) for p in O.iterdir() if p.is_file()},
        serial_phy_complete=False,
        main_chip_integrated=False,
        qualified_pex=False,
    )
    (O / "result.json").write_text(json.dumps(r, indent=2) + "\n")
    print(r["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.pdk, args.out)


if __name__ == "__main__":
    main()
