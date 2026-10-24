#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physically join the frozen stronger-output VCO v3 and four fixed RX/sampler lanes; no speed claim."""

import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import make_pcie_analog_bank_v2 as bank
import make_pcie_clock_vco_v3 as vco
from make_pcie_sampler_cell import sha

TOP = "nssoc_pcie_clocked_bank4_v4"
WIDTH, HEIGHT = 2130.0, 3000.0
SUPPLIES = (*bank.SUPPLIES, "AVDD2V3")
CLOCK_PORTS = tuple(f"L{i}_SAMPLER_CLK{p}" for i in range(4) for p in "PN")
PORTS = tuple(p for p in bank.PORTS if p not in CLOCK_PORTS) + ("AVDD2V3", "VCTRL")
PARENTS = {
    "BANK": dict(top=bank.TOP, gds="786b125128c3619d9b0cbf7153c9c273d29219319ac9915c3182646364819017",
                 result="20dcc3309215cfed1a781a8b026dc6db7114a1ec4476c420155799408e693172",
                 schematic="e86389e48f0fd4800f31e1d3496ca409f69a80434ef1ab85288c429c597d977c",
                 offset=(100.0,20.0), ports=bank.PORTS),
    "VCO": dict(top=vco.TOP, gds="cda633d6e7bb3f6e983fabe5d8849b48a5929ebe9feaa3a9a5f58d2c500a3c51",
                result="09063e0703eded75450e72b9b61c13da25c6988b212777b5e483533422945420",
                schematic="d5cae2be7f93ff1587999f21bbdc995dccfc8dc4a5ebe96c9d7409a58126cdbe",
                offset=(100.0,2700.0), ports=vco.PORTS),
}
COUNTS = dict(hbt=122, resistor=81, mim=6, pmos=1, physical_ptap=108, physical_ntap=1)


def mapped_net(kind, net):
    if kind == "BANK":
        if net in CLOCK_PORTS:
            return "CLOCK" + net[-1]
        return net
    if kind != "VCO":
        raise ValueError("Unknown native parent")
    if net in ("AVSS", "SUB", "BULK", "VCTRL"):
        return net
    if net == "AVDD":
        return "AVDD2V3"
    if net in ("CLKP", "CLKN"):
        return "CLOCK" + net[-1]
    return "VCO_" + net


def reference(texts):
    lines = ["* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
             "* SPDX-License-Identifier: CERN-OHL-W-2.0", ".subckt " + TOP + " " + " ".join(PORTS)]
    counts = dict.fromkeys(COUNTS, 0)
    for kind in PARENTS:
        fields = [x.split() for x in texts[kind].splitlines() if x.strip() and not x.startswith("*")]
        if fields[0] != [".subckt", PARENTS[kind]["top"], *PARENTS[kind]["ports"]] or fields[-1] != [".ends", PARENTS[kind]["top"]]:
            raise ValueError("Exact source parent port contract required")
        for f in fields[1:-1]:
            letter = f[0][0].upper()
            if letter == "Q":
                n, typ = 4, "hbt"
            elif letter == "M":
                n, typ = 4, "pmos"
            elif letter == "C":
                n, typ = 2, "mim"
            elif letter == "R":
                if f[3].lower() in ("ptap1", "ntap1"):
                    n, typ = 2, "physical_" + ("ptap" if f[3].lower() == "ptap1" else "ntap")
                else:
                    n, typ = 3, "resistor"
            else:
                raise ValueError("Unexpected parent primitive")
            counts[typ] += 1
            lines += [" ".join([letter + kind + "_" + f[0][1:]] +
                                [mapped_net(kind, node) for node in f[1:1+n]] + f[1+n:])]
    if counts != COUNTS:
        raise ValueError("Clocked bank complete primitive census differs")
    return "\n".join(lines + [".ends " + TOP, ""])


def use_direction(name):
    if name == "AVDD2V3":
        return "POWER", "INOUT"
    return bank.use_direction(name)


def lef(pya, dbu, ports):
    if set(ports) != set(PORTS):
        raise ValueError("Clocked bank port census differs")
    lines = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "MACRO " + TOP,
             "  CLASS BLOCK ;", "  ORIGIN 0 0 ;", f"  SIZE {WIDTH:.3f} BY {HEIGHT:.3f} ;"]
    for name in PORTS:
        layer, b = ports[name]
        use, direction = use_direction(name)
        lines += ["  PIN " + name, "    DIRECTION " + direction + " ;", "    USE " + use + " ;",
                  "    PORT", "      LAYER " + layer + " ;",
                  f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;", "    END", "  END " + name]
    lines += ["  OBS"]
    for layer in ("Metal1", "Metal2", "Metal3", "Metal4", "Metal5", "TopMetal1", "TopMetal2"):
        region = pya.Region(pya.DBox(0, 0, WIDTH, HEIGHT).to_itype(dbu))
        for metal, b in ports.values():
            if metal == layer:
                region -= pya.Region(b.to_itype(dbu))
        lines += ["    LAYER " + layer + " ;"]
        for polygon in region.decompose_trapezoids_to_region().each():
            if polygon.area() != polygon.bbox().area():
                raise ValueError("Nonrectangular obstruction")
            b = polygon.bbox().to_dtype(dbu)
            lines += [f"      RECT {b.left:.3f} {b.bottom:.3f} {b.right:.3f} {b.top:.3f} ;"]
    return "\n".join(lines + ["  END", "END " + TOP, "END LIBRARY", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "bank", "vco", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not (out.is_relative_to(root / "hw/soc/out") or
                           out.is_relative_to(Path("/dev/shm")) and out.name.startswith("nssoc-clocked-")):
        parser.error("Use a fresh project or /dev/shm/nssoc-clocked- directory")
    folders = {"BANK": args.bank.resolve(), "VCO": args.vco.resolve()}
    pins, texts, receipts = {}, {}, {}
    for kind, folder in folders.items():
        for filename, expected in ((PARENTS[kind]["top"] + ".gds", PARENTS[kind]["gds"]),
                                   ("result.json", PARENTS[kind]["result"]), ("schematic.cir", PARENTS[kind]["schematic"])):
            if sha(folder / filename) != expected:
                raise ValueError("Exact frozen native parent changed: " + kind + "/" + filename)
            pins[str(folder / filename)] = expected
        receipt = json.loads((folder / "result.json").read_text())
        receipts[kind] = receipt
        for path, expected in receipt["input_sha256"].items():
            if sha(path) != expected:
                raise ValueError("Frozen parent method/model changed")
            pins[path] = expected
        for name, expected in receipt["output_sha256"].items():
            if sha(folder / name) != expected:
                raise ValueError("Frozen parent output changed")
            pins[str(folder / name)] = expected
        texts[kind] = (folder / "schematic.cir").read_text()
    netlist = reference(texts)
    for path in (Path(__file__).resolve(), Path(bank.__file__).resolve(), Path(vco.__file__).resolve()):
        pins[str(path)] = sha(path)
    source = args.pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    for path in [*source.rglob("*.py"), *source.rglob("*.json"), lyp]:
        pins[str(path)] = sha(path)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- native via PCells
    layout = pya.Layout()
    top = layout.create_cell(TOP)
    layers = {prop.findtext("name")[:-8]: int(prop.findtext("source").split("/")[0])
              for prop in ET.parse(lyp).getroot().iter("properties")
              if prop.findtext("name", "").endswith(".drawing")}
    native_layouts, measurements, endpoints = [], {}, {}
    for kind, folder in folders.items():
        native = pya.Layout()
        native.read(str(folder / (PARENTS[kind]["top"] + ".gds")))
        cell = native.cell(PARENTS[kind]["top"])
        if cell is None:
            raise ValueError("Missing fixed parent top")
        labels = {}
        for metal in ("Metal5", "TopMetal1", "TopMetal2"):
            boxes = [s.dbbox() for s in cell.each_shape(native.layer(layers[metal], 2))]
            for shape in cell.each_shape(native.layer(layers[metal], 25)):
                if not shape.is_text():
                    raise ValueError("Unexpected parent pin metadata")
                name, point = shape.dtext.string, shape.dtext.trans.disp
                matches = [b for b in boxes if b.contains(pya.DPoint(point.x, point.y))]
                if len(matches) != 1 or name in labels:
                    raise ValueError("Ambiguous parent pin")
                labels[name] = (metal, matches[0])
        if set(labels) != set(PARENTS[kind]["ports"]):
            raise ValueError("Complete parent pin census differs")
        if kind == "VCO" and not pya.Region(cell.begin_shapes_rec(native.layer(layers["TopMetal2"], 0))).is_empty():
            raise ValueError("VCO changed to occupy parent clock routing layer")
        copied = layout.create_cell("v4_" + kind)
        copied.copy_tree(cell)
        removed, geometry = {}, []
        for li in native.layer_infos():
            if li.datatype in (2, 25):
                removed[str(li)] = sum(1 for _ in copied.each_shape(layout.layer(li)))
                copied.shapes(layout.layer(li)).clear()
            else:
                before = pya.Region(cell.begin_shapes_rec(native.layer(li)))
                after = pya.Region(copied.begin_shapes_rec(layout.layer(li)))
                if not (before ^ after).is_empty():
                    raise ValueError("Copied parent conductive/device geometry changed")
                if not before.is_empty():
                    geometry.append(str(li))
        t = pya.DTrans(*PARENTS[kind]["offset"])
        top.insert(pya.DCellInstArray(copied.cell_index(), t))
        endpoints[kind] = {n: (m, b.transformed(t)) for n, (m, b) in labels.items()}
        measurements[kind] = dict(unchanged_geometry_layers=geometry, removed_top_pin_metadata=removed,
                                  offset_um=list(PARENTS[kind]["offset"]), bbox_um=str(cell.dbbox().transformed(t)),
                                  ports={n:dict(layer=m,rect_um=[b.left,b.bottom,b.right,b.top]) for n,(m,b) in endpoints[kind].items()})
        native_layouts.append(native)
    ports, routes, vias, clock_connections = {}, [], [], []

    def rect(metal, box):
        top.shapes(layout.layer(layers[metal], 0)).insert(box)

    def via(bottom, upper, x, y, net):
        cell = layout.create_cell("via_stack", "SG13_dev", dict(b_layer=bottom, t_layer=upper,
                                  vt1_columns=2, vt1_rows=1, vt2_columns=1, vt2_rows=1))
        if cell is None or cell.is_empty():
            raise ValueError("Native parent via failed")
        b = cell.dbbox()
        t = pya.DTrans(x - b.center().x, y - b.center().y)
        top.insert(pya.DCellInstArray(cell.cell_index(), t))
        rect("TopMetal1", pya.DBox(x-1.2, y-1.2, x+1.2, y+1.2))
        vias.append(dict(net=net, bottom=bottom, top=upper, center_um=[x,y], bbox_um=str(b.transformed(t))))

    def pin(name, metal, box):
        if name in ports:
            raise ValueError("Duplicate clocked bank port")
        ports[name] = (metal, box)
        rect(metal, box)
        top.shapes(layout.layer(layers[metal], 2)).insert(box)
        top.shapes(layout.layer(layers[metal], 25)).insert(pya.DText(name, pya.DTrans(box.center().x, box.center().y)))

    def horizontal(x1, x2, y, net, terminal=None):
        box = pya.DBox(min(x1,x2), y-1, max(x1,x2), y+1)
        rect("TopMetal1", box)
        row = dict(net=net, layer="TopMetal1", rect_um=[box.left,box.bottom,box.right,box.top])
        if terminal:
            row["terminal"] = terminal
        routes.append(row)
        return row

    trunks = {"AVDD1V8":1090.0,"AVDD2V5":1110.0,"AVSS":1130.0,"SUB":1150.0,"AVDD2V3":2100.0}
    for net, x in trunks.items():
        rect("TopMetal2", pya.DBox(x-2,0,x+2,HEIGHT if net == "AVDD2V3" else 20))
        pin(net,"TopMetal2",pya.DBox(x-2,0,x+2,4))
    for name, (metal,b) in endpoints["BANK"].items():
        x,y = b.center().x,b.center().y
        if name in bank.SUPPLIES:
            if metal != "TopMetal2" or x != trunks[name]:
                raise ValueError("Original supply trunk binding differs")
            continue
        if metal != "TopMetal1":
            raise ValueError("Original bank signal must use TopMetal1")
        if name in CLOCK_PORTS:
            channel = 30.0 if name.endswith("P") else 50.0
            net = mapped_net("BANK",name)
            row = horizontal(channel,x,y,net,name)
            via("TopMetal1","TopMetal2",channel,y,net)
            clock_connections.append(dict(source="VCO_CLK"+name[-1], sink=name,net=net,branch=row))
        else:
            edge = 0 if b.left == 100 else WIDTH
            if b.left != 100 and b.right != 1170:
                raise ValueError("Parent signal is not on expected boundary")
            horizontal(x,edge,y,name)
            pin(name,"TopMetal1",pya.DBox(0,y-1,2,y+1) if edge == 0 else pya.DBox(WIDTH-2,y-1,WIDTH,y+1))
    clock_tops = {}
    for name,(metal,b) in endpoints["VCO"].items():
        if metal != "Metal5":
            raise ValueError("VCO public pin layer differs")
        x,y = b.center().x,b.center().y
        net = mapped_net("VCO",name)
        via("Metal5","TopMetal1",x,y,net)
        if name in ("CLKP","CLKN"):
            edge = 30.0 if name == "CLKP" else 50.0
            clock_tops[net] = y
            via("TopMetal1","TopMetal2",edge,y,net)
        elif name == "VCTRL":
            edge = 0
            pin(name,"TopMetal1",pya.DBox(0,y-1,2,y+1))
        else:
            edge = trunks[net]
            via("TopMetal1","TopMetal2",edge,y,net)
            if name in ("AVSS","SUB"):
                rect("TopMetal2",pya.DBox(edge-2,2660,edge+2,y+2))
        horizontal(x,edge,y,net,"VCO_"+name)
    for net,x in (("CLOCKP",30.0),("CLOCKN",50.0)):
        ys = [(c["branch"]["rect_um"][1]+c["branch"]["rect_um"][3])/2 for c in clock_connections if c["net"] == net]
        box = pya.DBox(x-2,min(ys)-2,x+2,clock_tops[net]+2)
        rect("TopMetal2",box)
        routes.append(dict(net=net,layer="TopMetal2",rect_um=[box.left,box.bottom,box.right,box.top]))
    if len(clock_connections) != 8 or set(ports) != set(PORTS) or top.dbbox() != pya.DBox(0,0,WIDTH,HEIGHT):
        raise ValueError("Exact eight clock branches/boundary/port census differs")
    out.mkdir(parents=True)
    (out/"schematic.cir").write_text(netlist)
    layout.write(str(out/(TOP+".gds")))
    (out/(TOP+".lef")).write_text(lef(pya,layout.dbu,ports))
    if any(sha(path) != expected for path,expected in pins.items()):
        raise ValueError("Clocked bank input changed")
    record = dict(status="GENERATED_REQUIRES_CLOCKED_BANK_DRC_LVS_PEX",input_sha256=pins,
                  output_sha256={p.name:sha(p) for p in out.iterdir()}, parent_geometry=measurements,
                  routes=routes,vias=vias,clock_connections=clock_connections,bbox_um=[0,0,WIDTH,HEIGHT],
                  ports={n:dict(layer=m,rect_um=[b.left,b.bottom,b.right,b.top]) for n,(m,b) in ports.items()},
                  primitive_counts=COUNTS, phy_complete=False,main_chip_integrated=False,qualified_pex=False,
                  clock_fanout_qualified=False,post_layout_8ghz_qualified=False,manufacturing_approval=False,
                  scope="Fixed four TX/RX/sampler lanes and stronger-output VCO v3 joined by eight real clock branches. "
                        "Separate 1.8/2.5/2.3 V rails and explicit external VCTRL/bias. No CDR/PLL locking, "
                        "clock-fanout/load, RF/EM/PEX or post-layout speed qualification; not the main chip.")
    (out/"result.json").write_text(json.dumps(record,indent=2)+"\n")


if __name__ == "__main__":
    main()
