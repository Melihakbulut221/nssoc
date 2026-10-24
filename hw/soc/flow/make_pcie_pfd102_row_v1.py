#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""SG13G2 phase-detector component:102 core MOS devices and153 finite contacts.

This compact development placement exposes REF/FB/reset/UP/DOWN, supply, ground and
substrate. Ground and substrate remain separate. All51 PMOS wells have real
local contacts. Generation is not DRC/LVS, extracted timing or PLL acceptance.
"""

import argparse
from pathlib import Path
import sys
import json
import hashlib
import xml.etree.ElementTree as ET

TOP = "nssoc_pfd102_layout_v1"
PORTS = ["ref", "fb", "reset", "up", "down", "vdd", "vss", "sub"]
MODELS = {"sg13_hv_nmos": 4, "sg13_hv_pmos": 4, "rppd": 3, "cap_cmim": 2}
SOURCES = {
    "pll_pfd_charge_pump_hv_v1.spice": "194a50048f88614b3f3c0bbbac88cdf8be7f71a8cd62eac3f14914b652d865fc",
}


def pin(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def definitions(texts):
    result = {}
    for text in texts.values():
        active = None
        for line in text.lower().splitlines():
            words = line.split()
            if not words or words[0].startswith("*"):
                continue
            if words[0] == ".subckt":
                assert active is None and words[1] not in result
                active = words[1]
                assert len(words[2:]) == len(set(words[2:]))
                result[active] = (words[2:], [])
            elif words[0] == ".ends":
                assert active and (len(words) == 1 or words == [".ends", active])
                active = None
            else:
                assert active
                result[active][1].append(words)
        assert active is None
    return result


def expand(defs, root):
    rows, wires = [], []

    def walk(model, path, nets, stack=()):
        assert model not in stack
        ports, body = defs[model]
        assert len(ports) == len(nets)
        mapping, seen = dict(zip(ports, nets)), set()

        def node(name):
            return mapping.get(name, path + "." + name)

        for words in body:
            assert words[0] not in seen
            seen.add(words[0])
            here = path + "." + words[0]
            if words[0][0] in ("r", "c"):
                assert len(words) == 4
                wires.append(
                    dict(
                        path=here,
                        kind=words[0][0],
                        nets=[node(x) for x in words[1:3]],
                        value=words[3],
                    )
                )
                continue
            assert words[0].startswith("x")
            if words[-1] in defs:
                walk(words[-1], here, [node(x) for x in words[1:-1]], stack + (model,))
                continue
            matches = [
                (m, n)
                for m, n in MODELS.items()
                if len(words) > n + 1 and words[n + 1] == m
            ]
            assert len(matches) == 1, words
            model_name, count = matches[0]
            params = dict(x.split("=") for x in words[count + 2 :])
            assert len(params) == len(words[count + 2 :])
            rows.append(
                dict(
                    path=here,
                    model=model_name,
                    nets=[node(x) for x in words[1 : count + 1]],
                    params=params,
                )
            )

    model, path, nets = root
    walk(model, path, nets)
    assert len(rows) == len({x["path"] for x in rows})
    assert len(wires) == len({x["path"] for x in wires})
    return rows, wires


def devices(texts):
    if set(texts) != set(SOURCES) or any(
        hashlib.sha256(texts[name].encode()).hexdigest() != digest
        for name, digest in SOURCES.items()
    ):
        raise ValueError("Frozen PFD source changed")
    rows, wires = expand(definitions(texts), ["nssoc_pll_pfd_hv_v1", "xloop", PORTS])
    if len(rows) != 102 or wires:
        raise ValueError("Unexpected PFD core")
    return rows


def use_direction(name):
    if name == "vdd":
        return "POWER", "INOUT"
    if name in ("sub", "vss"):
        return "GROUND", "INOUT"
    return "SIGNAL", "OUTPUT" if name in ("up", "down") else "INPUT"


def lef(pya, dbu, box, ports):
    if set(ports) != set(PORTS):
        raise ValueError("PFD physical pin inventory differs")
    result = [
        "VERSION 5.8 ;",
        'BUSBITCHARS "[]" ;',
        'DIVIDERCHAR "/" ;',
        "MACRO " + TOP,
        "  CLASS BLOCK ;",
        "  ORIGIN 0 0 ;",
        f"  SIZE {box.width():.3f} BY {box.height():.3f} ;",
    ]
    for name in PORTS:
        metal, b = ports[name]
        use, direction = use_direction(name)
        result += [
            "  PIN " + name,
            "    DIRECTION " + direction + " ;",
            "    USE " + use + " ;",
            "    PORT",
            "      LAYER " + metal + " ;",
            f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;",
            "    END",
            "  END " + name,
        ]
    result += ["  OBS"]
    for metal in (
        "Metal1",
        "Metal2",
        "Metal3",
        "Metal4",
        "Metal5",
        "TopMetal1",
        "TopMetal2",
    ):
        region = pya.Region(box.to_itype(dbu))
        for layer, b in ports.values():
            if layer == metal:
                region -= pya.Region(b.to_itype(dbu))
        result += ["    LAYER " + metal + " ;"]
        for polygon in region.decompose_trapezoids_to_region().each():
            if polygon.area() != polygon.bbox().area():
                raise ValueError("Nonrectangular obstruction")
            b = polygon.bbox().to_dtype(dbu)
            result += [
                f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;"
            ]
    return "\n".join(result + ["  END", "END " + TOP, "END LIBRARY", ""])


def build(pdk, out):
    root = Path(__file__).resolve().parents[3]
    out = out.resolve()
    if out.exists() or not out.is_relative_to(root / "hw/soc/out"):
        raise ValueError("Use a fresh project output directory")
    circuits = [root / "hw/soc/analog/pcie" / name for name in SOURCES]
    rows = devices({p.name: p.read_text() for p in circuits})
    if any(row["model"] not in ("sg13_hv_nmos", "sg13_hv_pmos") for row in rows):
        raise ValueError("Compact row routing requires the frozen 102 MOS PFD")
    source = pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    inputs = [
        *circuits,
        Path(__file__).resolve(),
        *source.rglob("*.py"),
        *source.rglob("*.json"),
        lyp,
    ]
    pins = {str(p): pin(p) for p in inputs}
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
    records = []
    terminals = {}
    routes = []
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
            dict(
                b_layer=metal(lo),
                t_layer=metal(hi),
                vn_columns=1,
                vn_rows=1,
                vt1_columns=2,
                vt1_rows=1,
                vt2_columns=1,
                vt2_rows=1,
            ),
        )
        b = cell.dbbox()
        place(cell, x - b.center().x, y - b.center().y)

    def escape(pin, net, lane, label):
        x = round(pin.center().x / 0.005) * 0.005
        y = round(pin.center().y / 0.005) * 0.005
        via(1, 3, x, y)
        box(3, x - 0.2, y - 0.2, lane + 0.2, y + 0.2)
        via(3, 4, lane, y)
        terminals.setdefault(net, []).append((row_index, lane, y))
        routes.append(
            dict(device=label, net=net, native_pin=str(pin), escape=[lane, y])
        )

    for i, row in enumerate(rows):
        row_index = i // 12
        x = 350 + (i % 12) * 40
        y = 30 + row_index * 260
        lane = x + 17
        n = row["nets"]
        p = row["params"]
        name = "D" + str(i)
        model = row["model"]
        params = {k: p[k] for k in ("w", "l")}
        params.update({"ng": int(p["ng"])} if "ng" in p else {})
        if model in ("sg13_hv_pmos", "sg13_hv_nmos"):
            cell = pc("pmosHV" if model.endswith("pmos") else "nmosHV", params)
            t = place(cell, x, y)
            mp = sorted(
                [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().x,
            )
            gp = [s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(5, 2))]
            assert len(mp) == 2 and len(gp) == 1
            for k, (pinn, net) in enumerate(zip(mp, [n[2], n[0]])):
                py = (
                    round((pinn.bottom + 0.4 if k == 0 else pinn.top - 0.4) / 0.005)
                    * 0.005
                )
                tiny = pya.DBox(pinn.left, py - 0.1, pinn.right, py + 0.1)
                assert pinn.contains(
                    pya.DPoint(tiny.left, tiny.bottom)
                ) and pinn.contains(pya.DPoint(tiny.right, tiny.top))
                escape(tiny, net, lane + k * 4, name)
            gate = gp[0]
            gx = round(gate.center().x / 0.005) * 0.005
            gy = round((gate.top + 1) / 0.005) * 0.005
            top.shapes(layout.layer(5, 0)).insert(
                pya.DBox(gate.left, gate.top - 0.1, gate.right, gy + 0.3)
            )
            top.shapes(layout.layer(5, 0)).insert(
                pya.DBox(gx - 0.3, gy - 0.3, gx + 0.3, gy + 0.3)
            )
            top.shapes(layout.layer(6, 0)).insert(
                pya.DBox(gx - 0.08, gy - 0.08, gx + 0.08, gy + 0.08)
            )
            escape(
                box(1, gx - 0.25, gy - 0.25, gx + 0.25, gy + 0.25), n[1], lane + 8, name
            )
            body = "BULK"
            if model.endswith("pmos"):
                well = [
                    s.dbbox().transformed(t)
                    for s in cell.each_shape(layout.layer(31, 0))
                    if not s.is_text()
                ]
                assert len(well) == 1
                tap = pc("ntap1", {"w": "2u", "l": "2u"})
                nt = place(tap, x + 10, y - 5)
                nb = tap.dbbox().transformed(nt)
                bridge = pya.DBox(
                    min(well[0].left, nb.left),
                    min(well[0].bottom, nb.bottom),
                    max(well[0].right, nb.right),
                    max(well[0].top, nb.top),
                )
                top.shapes(layout.layer(31, 0)).insert(bridge)
                pinboxes = [
                    s.dbbox().transformed(nt)
                    for s in tap.each_shape(layout.layer(8, 2))
                ]
                assert (
                    len(pinboxes) == 2 and pinboxes[0].center() == pinboxes[1].center()
                )
                escape(
                    min(pinboxes, key=lambda b: b.area()),
                    n[3],
                    lane + 12,
                    name + "_ntap",
                )
                body = "NWELL" + str(i)
                reference.append(f"RNTAP{i} {n[3]} {body} ntap1 A=4p P=8u")
            reference.append(
                f"M{name} "
                + " ".join(n[:3] + [body])
                + f" {model} w={p['w']} l={p['l']} ng=1 m=1"
            )
        elif model == "rppd":
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
                f"R{name} "
                + " ".join(n[:2] + ["BULK"])
                + f" rppd w={p['w']} l={p['l']} b=0 m=1"
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
            py = round(plates[6].center().y / 0.005) * 0.005
            px = lane + 8
            mx = lane + 4
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
        records.append(
            dict(
                row,
                instance=name,
                placement_um=[x, y],
                bbox_um=str(cell.dbbox().transformed(t)),
            )
        )
        tap = pc("ptap1", {"w": "2u", "l": "2u"})
        tt = place(tap, x + 10, y - 8 if model == "sg13_hv_nmos" else y - 20)
        tp = [s.dbbox().transformed(tt) for s in tap.each_shape(layout.layer(8, 2))]
        assert len(tp) == 1
        escape(tp[0], "sub", lane + 16, name + "_ptap")
        reference.append(f"RPTAP{i} sub BULK ptap1 A=4p P=8u")
    # Isolated local row buses feed per-net global trunks. Different rows
    # reuse local escape x coordinates only within disjoint vertical bands.
    # Power widths are actual geometry; no extracted resistance is scaled.
    ports = {}
    global_lanes = {}
    cursor = 20.0
    for net in sorted(terminals):
        width = 8.0 if net in ("vdd", "vss", "sub") else 1.2
        global_lanes[net] = (cursor + width / 2, width)
        cursor += width + 2.0
    assert cursor < 300
    joins = {}
    for row_index in range((len(rows) + 11) // 12):
        cursor = row_index * 260 + 70.0
        nets = sorted(net for net, points in terminals.items()
                      if any(r == row_index for r, _, _ in points))
        for net in nets:
            points = [(x, sy) for r, x, sy in terminals[net] if r == row_index]
            gx, width = global_lanes[net]
            y = cursor + width / 2
            cursor += width + 2.0
            for x, sy in points:
                box(4, x - .6, min(sy, y) - .2, x + .6, max(sy, y) + .2)
                via(4, 5, x, y)
            left = 0 if net in PORTS and net not in ports else gx - width / 2
            box(5, left, y - width / 2, max(x for x, _ in points) + 1, y + width / 2)
            via(4, 5, gx, y)
            joins.setdefault(net, []).append(y)
            if net in PORTS and net not in ports:
                pinbox = pya.DBox(0, y - width / 2, 2, y + width / 2)
                ports[net] = ("Metal5", pinbox)
                top.shapes(layout.layer(layers["Metal5"], 2)).insert(pinbox)
                top.shapes(layout.layer(layers["Metal5"], 25)).insert(pya.DText(net, 0, y))
        assert cursor < row_index * 260 + 245, "Local buses exceed row corridor"
    for net, ys in joins.items():
        gx, width = global_lanes[net]
        box(4, gx - width / 2, min(ys) - width / 2, gx + width / 2, max(ys) + width / 2)
    assert set(ports) == set(PORTS)
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
    (out / (TOP + ".lef")).write_text(lef(pya, layout.dbu, bbox, ports))
    (out / "schematic.cir").write_text("\n".join(reference + [".ends " + TOP, ""]))
    assert all(pin(Path(p)) == h for p, h in pins.items())
    (out / "result.json").write_text(
        json.dumps(
            dict(
                status="GENERATED_UNVERIFIED_DEVELOPMENT_LAYOUT",
                inputs=pins,
                outputs={p.name: pin(p) for p in out.iterdir()},
                core_devices=records,
                substrate_contacts=102,
                well_contacts=51,
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.pdk, args.out)


if __name__ == "__main__":
    main()
