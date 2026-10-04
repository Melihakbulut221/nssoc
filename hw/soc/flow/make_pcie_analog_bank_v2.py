#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Connect four native RX preamplifiers to fixed v2 clocked samplers, with TX cells."""

import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from make_pcie_analog_bank import TX_GDS_SHA, TX_RESULT_SHA
from make_pcie_rx_cell_v2 import TOP as RX_TOP, physical_reference as rx_reference
from make_pcie_sampler_cell import TOP as SAMPLER_TOP, physical_reference as sampler_reference, sha

TOP = "nssoc_pcie_analog_bank4_v2"
WIDTH, HEIGHT, PITCH = 1070.0, 2640.0, 660.0
SUPPLIES = ("AVDD1V8", "AVDD2V5", "AVSS", "SUB")
CELL_PORTS = {"TX": ("INP", "INN", "OUTP", "OUTN", "AVDD", "AVSS", "SUB", "IREF"),
              "RX": ("INP", "INN", "OUTP", "OUTN", "AVDD", "AVSS", "SUB", "IREF", "VCM"),
              "SAMPLER": ("DP", "DN", "QP", "QN", "CLKP", "CLKN", "AVDD", "AVSS", "SUB", "IREF")}
SIGNALS = {"TX": ("INP", "INN", "OUTP", "OUTN", "IREF"),
           "RX": ("INP", "INN", "IREF", "VCM"),
           "SAMPLER": ("QP", "QN", "CLKP", "CLKN", "IREF")}
PORTS = tuple(f"L{lane}_{kind}_{pin}" for lane in range(4) for kind in CELL_PORTS
              for pin in SIGNALS[kind]) + SUPPLIES


def mapped_net(lane, kind, net):
    if lane not in range(4) or kind not in CELL_PORTS:
        raise ValueError("Unknown physical lane/cell")
    if net in ("AVSS", "SUB", "BULK"):
        return net
    if net == "AVDD":
        return "AVDD2V5" if kind == "SAMPLER" else "AVDD1V8"
    if kind == "SAMPLER" and net in ("DP", "DN"):
        return f"L{lane}_RX_OUT" + ("P" if net == "DP" else "N")
    return f"L{lane}_{kind}_{net}"


def reference(texts):
    lines = ["* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut",
             "* SPDX-License-Identifier: CERN-OHL-W-2.0", ".subckt " + TOP + " " + " ".join(PORTS)]
    counts = {"hbt": 0, "resistor": 0, "tap": 0}
    for lane in range(4):
        for kind, text in texts.items():
            body = [line.split() for line in text.splitlines() if line.strip() and not line.startswith("*")]
            if (tuple(body[0][2:]) != CELL_PORTS[kind] or body[0][0].lower() != ".subckt" or
                    body[-1][0].lower() != ".ends"):
                raise ValueError("Primitive port contract differs")
            for f in body[1:-1]:
                if f[0][0].upper() == "Q":
                    n, typ = 4, "hbt"
                elif f[0][0].upper() == "R":
                    n, typ = (2, "tap") if f[3].lower() == "ptap1" else (3, "resistor")
                else:
                    raise ValueError("Unexpected primitive reference body")
                counts[typ] += 1
                lines += [" ".join([f[0][0] + f"{lane}{kind}_" + f[0][1:]] +
                                    [mapped_net(lane, kind, v) for v in f[1:1+n]] + f[1+n:])]
    if counts != {"hbt": 92, "resistor": 72, "tap": 96}:
        raise ValueError("Bank v2 primitive census differs")
    return "\n".join(lines + [".ends " + TOP, ""])


def use_direction(name):
    if name in ("AVDD1V8", "AVDD2V5"):
        return "POWER", "INOUT"
    if name in ("AVSS", "SUB"):
        return "GROUND", "INOUT"
    return "SIGNAL", "OUTPUT" if name.endswith(("_OUTP", "_OUTN", "_QP", "_QN")) else "INPUT"


def lef(pya, dbu, ports):
    if set(ports) != set(PORTS):
        raise ValueError("Incomplete bank v2 ports")
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
    for name in ("pdk", "tx", "rx", "sampler", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not (out.is_relative_to(root / "hw/soc/out") or
                           out.is_relative_to(Path("/dev/shm")) and out.name.startswith("nssoc-sampler-")):
        parser.error("Use a fresh project or /dev/shm/nssoc-sampler- directory")
    folders = {kind: getattr(args, kind.lower()).resolve() for kind in CELL_PORTS}
    tops = {"TX": "nssoc_tx_cml_layout", "RX": RX_TOP, "SAMPLER": SAMPLER_TOP}
    if (sha(folders["TX"] / (tops["TX"] + ".gds")) != TX_GDS_SHA or
            sha(folders["TX"] / "result.json") != TX_RESULT_SHA):
        raise ValueError("Original native TX differs")
    texts = {kind: (folder / "schematic.cir").read_text() for kind, folder in folders.items()}
    if texts["RX"] != rx_reference((root / "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice").read_text()):
        raise ValueError("RX circuit differs")
    if texts["SAMPLER"] != sampler_reference((root / "hw/soc/analog/pcie/rx_sampler_hbt_v2.spice").read_text()):
        raise ValueError("Sampler circuit differs")
    netlist = reference(texts)
    methods = [Path(__file__).resolve(), *(root / "hw/soc/flow" / name for name in
                                         ("make_pcie_analog_bank.py", "make_pcie_rx_cell_v2.py", "make_pcie_sampler_cell.py"))]
    pins = {str(p): sha(p) for p in methods}
    for folder in folders.values():
        generated = json.loads((folder / "result.json").read_text())
        pins[str(folder / "result.json")] = sha(folder / "result.json")
        for name, expected in generated["output_sha256"].items():
            if sha(folder / name) != expected:
                raise ValueError("Primitive view changed")
            pins[str(folder / name)] = expected
        for path, expected in generated["input_sha256"].items():
            if sha(path) != expected:
                raise ValueError("Primitive method/source changed")
            pins[path] = expected
    source = args.pdk.resolve() / "libs.tech/klayout/python"
    lyp = source.parent / "tech/sg13g2.lyp"
    for path in [*source.rglob("*.py"), *source.rglob("*.json"), lyp]:
        pins[str(path)] = sha(path)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source), str(source / "pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib  # noqa: F401 -- real native via PCells
    layout = pya.Layout()
    top = layout.create_cell(TOP)
    layers = {prop.findtext("name")[:-8]: int(prop.findtext("source").split("/")[0])
              for prop in ET.parse(lyp).getroot().iter("properties")
              if prop.findtext("name", "").endswith(".drawing")}
    cells, measurements, native_layouts = {}, {}, []
    for kind, folder in folders.items():
        native = pya.Layout()
        native.read(str(folder / (tops[kind] + ".gds")))
        cell = native.cell(tops[kind])
        if cell is None:
            raise ValueError("Missing source top")
        for metal in ("TopMetal1", "TopMetal2"):
            if not pya.Region(cell.begin_shapes_rec(native.layer(layers[metal], 0))).is_empty():
                raise ValueError("Primitive occupies parent routing metals")
        boxes = [s.dbbox() for s in cell.each_shape(native.layer(layers["Metal5"], 2))]
        labels = {}
        for shape in cell.each_shape(native.layer(layers["Metal5"], 25)):
            if not shape.is_text():
                raise ValueError("Unexpected pin metadata")
            name = shape.dtext.string
            point = shape.dtext.trans.disp
            matches = [b for b in boxes if b.contains(pya.DPoint(point.x, point.y))]
            if len(matches) != 1 or name in labels:
                raise ValueError("Ambiguous native pin")
            labels[name] = matches[0]
        if set(labels) != set(CELL_PORTS[kind]):
            raise ValueError("Primitive physical pin census differs")
        copied = layout.create_cell("v2_" + kind)
        copied.copy_tree(cell)
        removed = {}
        geometry = []
        for li in native.layer_infos():
            if li.datatype in (2, 25):
                removed[str(li)] = sum(1 for _ in copied.each_shape(layout.layer(li)))
                copied.shapes(layout.layer(li)).clear()
            else:
                before = pya.Region(cell.begin_shapes_rec(native.layer(li)))
                after = pya.Region(copied.begin_shapes_rec(layout.layer(li)))
                if not (before ^ after).is_empty():
                    raise ValueError("Copied primitive geometry changed")
                if not before.is_empty():
                    geometry.append(str(li))
        measurements[kind] = dict(unchanged_geometry_layers=geometry, removed_top_pin_metadata=removed,
                                  ports={n: [b.left,b.bottom,b.right,b.top] for n,b in labels.items()},
                                  bbox_um=str(cell.dbbox()))
        cells[kind] = (copied, labels)
        native_layouts.append(native)
    ports, routes, vias, placements = {}, [], [], []

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
            raise ValueError("Duplicate bank port")
        ports[name] = (metal, box)
        rect(metal, box)
        top.shapes(layout.layer(layers[metal], 2)).insert(box)
        top.shapes(layout.layer(layers[metal], 25)).insert(pya.DText(name, pya.DTrans(box.center().x, box.center().y)))

    def horizontal(x1, x2, y, net):
        box = pya.DBox(min(x1,x2), y-1, max(x1,x2), y+1)
        rect("TopMetal1", box)
        routes.append(dict(net=net, layer="TopMetal1", rect_um=[box.left,box.bottom,box.right,box.top]))

    trunks = dict(zip(SUPPLIES, (990.0, 1010.0, 1030.0, 1050.0), strict=True))
    for net, x in trunks.items():
        rect("TopMetal2", pya.DBox(x-2,0,x+2,HEIGHT))
        pin(net, "TopMetal2", pya.DBox(x-2,0,x+2,4))
    for lane in range(4):
        positions = {}
        for kind, offset in (("TX",10), ("RX",190), ("SAMPLER",370)):
            cell, local_pins = cells[kind]
            dx, dy = 40 - cell.dbbox().left, lane * PITCH + offset - cell.dbbox().bottom
            t = pya.DTrans(dx, dy)
            top.insert(pya.DCellInstArray(cell.cell_index(), t))
            placements.append(dict(lane=lane, kind=kind, translation_um=[dx,dy],
                                   bbox_um=str(cell.dbbox().transformed(t))))
            for name, local in local_pins.items():
                b = local.transformed(t)
                x, y = b.center().x, b.center().y
                net = mapped_net(lane, kind, name)
                positions[(kind, name)] = (x,y)
                via("Metal5", "TopMetal1", x, y, net)
                if (kind == "RX" and name in ("OUTP","OUTN")) or (kind == "SAMPLER" and name in ("DP","DN")):
                    continue
                if net in SUPPLIES:
                    edge = trunks[net]
                    via("TopMetal1", "TopMetal2", edge, y, net)
                else:
                    edge = 0 if name in ("INP","OUTN","IREF","CLKP","CLKN") else WIDTH
                    pin(net, "TopMetal1", pya.DBox(0,y-1,2,y+1) if edge == 0 else pya.DBox(WIDTH-2,y-1,WIDTH,y+1))
                horizontal(x, edge, y, net)
        for suffix, channel in (("P",940.0),("N",20.0)):
            start = positions[("RX","OUT"+suffix)]
            end = positions[("SAMPLER","D"+suffix)]
            net = mapped_net(lane,"RX","OUT"+suffix)
            for x,y in (start,end):
                horizontal(x,channel,y,net)
                via("TopMetal1","TopMetal2",channel,y,net)
            box = pya.DBox(channel-2,min(start[1],end[1]),channel+2,max(start[1],end[1]))
            rect("TopMetal2",box)
            routes.append(dict(net=net,layer="TopMetal2",rect_um=[box.left,box.bottom,box.right,box.top],
                               connected_terminals=[f"L{lane}_RX_OUT{suffix}",f"L{lane}_SAMPLER_D{suffix}"]))
    if set(ports) != set(PORTS) or top.dbbox() != pya.DBox(0,0,WIDTH,HEIGHT):
        raise ValueError(f"Bank v2 boundary/port census differs: {top.dbbox()}, {set(ports) ^ set(PORTS)}")
    out.mkdir(parents=True)
    (out/"schematic.cir").write_text(netlist)
    layout.write(str(out/(TOP+".gds")))
    (out/(TOP+".lef")).write_text(lef(pya,layout.dbu,ports))
    if any(sha(path) != value for path,value in pins.items()):
        raise ValueError("Bank generation input changed")
    record = dict(status="GENERATED_REQUIRES_BANK_DRC_LVS_PEX", input_sha256=pins,
                  output_sha256={p.name:sha(p) for p in out.iterdir()}, primitive_source_measurements=measurements,
                  placements=placements,routes=routes,vias=vias,bbox_um=[0,0,WIDTH,HEIGHT],
                  ports={n:dict(layer=metal,rect_um=[b.left,b.bottom,b.right,b.top]) for n,(metal,b) in ports.items()},
                  primitive_counts=dict(hbt=92,resistor=72,physical_tap=96),
                  phy_complete=False,main_chip_integrated=False,qualified_pex=False,manufacturing_approval=False,
                  scope="Four actual TX/RX/sampler lanes and eight physical RX-to-sampler connections. "
                        "Separate 1.8 V TX/RX and 2.5 V sampler rails, external clock/bias. "
                        "No pads, CDR/PLL, RF/EM/PEX or post-layout speed qualification; not the main chip.")
    (out/"result.json").write_text(json.dumps(record,indent=2)+"\n")


if __name__ == "__main__":
    main()
