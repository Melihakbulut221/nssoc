#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate v50 upper-metal routing for the unchanged v49 native active circuit.

The substrate and signal-return ports remain distinct. Generation does not
establish DRC/LVS, extracted electrical performance, PVT or full PHY acceptance.
"""

import argparse
from pathlib import Path
import sys
import json
import hashlib
import xml.etree.ElementTree as ET

PORTS = ["ip", "inn", "op", "on", "avdd", "avss", "sub", "iref"]
TOP = None
CIRCUIT = "hw/soc/analog/pcie/cdr_active_levelshift_v49.spice"
CIRCUIT_SHA256 = "f50f4a9f65530c0f9b1371b0958624edb77cc6b63496f82058e33b2f6205fb7e"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def devices(text, kind):
    assert kind == 'levelshift'
    assert hashlib.sha256(text.encode()).hexdigest() == CIRCUIT_SHA256
    raw=[s.lower().split() for s in text.splitlines() if s.strip() and not s.lstrip().startswith('*')]
    assert raw[0]==['.subckt','nssoc_cdr_active_levelshift_v49',*PORTS]
    assert raw[-1]==['.ends','nssoc_cdr_active_levelshift_v49']
    expected=[
        ('xp','npn13g2',['on','ip','tail','sub'],dict(nx='4')),
        ('xn','npn13g2',['op','inn','tail','sub'],dict(nx='4')),
        ('xt0','sg13_lv_nmos',['tail','iref','avss','sub'],dict(w='36u',l='.3u',ng='1')),
        ('xt1','sg13_lv_nmos',['tail','iref','avss','sub'],dict(w='36u',l='.3u',ng='1')),
        ('xref','sg13_lv_nmos',['iref','iref','avss','sub'],dict(w='8u',l='.3u',ng='1')),
        ('xup','rppd',['avdd','op','sub'],dict(w='8u',l='2.8u',b='0',sw_et='1')),
        ('xun','rppd',['avdd','on','sub'],dict(w='8u',l='2.8u',b='0',sw_et='1')),
        ('xdp','rppd',['op','avss','sub'],dict(w='4u',l='9.6u',b='0',sw_et='1')),
        ('xdn','rppd',['on','avss','sub'],dict(w='4u',l='9.6u',b='0',sw_et='1'))]
    assert len(raw[1:-1])==len(expected)==9
    rows=[]
    for f,(name,model,nets,params) in zip(raw[1:-1],expected,strict=True):
        assert f[:len(nets)+2]==[name,*nets,model]
        values=f[len(nets)+2:]
        assert dict(v.split('=') for v in values)==params and len(values)==len(params)
        rows.append(dict(path=name,model=model,nets=nets,params=params))
    return rows


def main():
    global TOP
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--kind", choices=("levelshift",), required=True)
    args = parser.parse_args()
    TOP = "nssoc_cdr_active_levelshift_layout_v50"
    R = Path(__file__).resolve().parents[3]
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(R / "hw/soc/out"):
        parser.error("Use a fresh project output directory")
    source = R / CIRCUIT
    rows = devices(source.read_text(), args.kind)
    pdk = args.pdk.resolve()
    src = pdk / "libs.tech/klayout/python"
    lyp = src.parent / "tech/sg13g2.lyp"
    inputs = [
        R / "hw/soc/flow/make_pcie_sampler_parallel_drive_v8.py",
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
        via(3, 6, lane, y)
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
                (collector, 1, n[0], x - 18, 0.04),
                (base, 1, n[1], x - 12, -0.04),
                (m2[0], 2, n[2], x - 6, 0),
            ]:
                escape(pin, met, net, lane, name, 4, off)
            reference.append(
                f"Q{name} "
                + " ".join(n[:3] + ["BULK"])
                + f" npn13G2 Nx={p['nx']} we=0.07u le=0.9u m=1"
            )
        elif row["model"] == "sg13_lv_nmos":
            c = pc("nmos", {"w": p["w"], "l": p["l"], "ng": 1})
            t = place(c, x, y)
            mp = sorted([s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
                        key=lambda b: b.center().x)
            gp = [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(5, 2))]
            assert len(mp) == 2 and len(gp) == 1 and n[3] == "sub"
            for k, (pin, net) in enumerate(zip(mp, [n[2], n[0]], strict=True)):
                py = round((pin.bottom + .4 if k == 0 else pin.top - .4) / .005) * .005
                tiny = pya.DBox(pin.left, py-.1, pin.right, py+.1)
                assert pin.contains(pya.DPoint(tiny.left,tiny.bottom)) and pin.contains(pya.DPoint(tiny.right,tiny.top))
                escape(tiny, 1, net, x-18+6*k, name, 1)
            gate=gp[0]
            gx=round(gate.center().x/.005)*.005
            gy=round((gate.top+1)/.005)*.005
            top.shapes(layout.layer(5,0)).insert(pya.DBox(gate.left,gate.top-.1,gate.right,gy+.3))
            top.shapes(layout.layer(5,0)).insert(pya.DBox(gx-.3,gy-.3,gx+.3,gy+.3))
            top.shapes(layout.layer(6,0)).insert(pya.DBox(gx-.08,gy-.08,gx+.08,gy+.08))
            pin=box(1,gx-.25,gy-.25,gx+.25,gy+.25)
            escape(pin,1,n[1],x-6,name,1)
            reference.append(f"M{name} " + " ".join(n[:3]+["BULK"]) +
                             f" sg13_lv_nmos w={p['w']} l={p['l']} ng=1 m=1")
        elif row["model"] == "rppd":
            c = pc("rppd", {"w": p["w"], "l": p["l"]})
            t = place(c, x, y)
            ps = sorted(
                [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().y,
            )
            assert len(ps) == 2
            for k, pin in enumerate(ps):
                escape(pin, 1, n[k], x - 12 + 6 * k, name)
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
            plus, minus = x - 18, x - 12
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
        # MOS needs a local body contact beside the middle of the long active strip.
        tx,ty=(x+4,y+float(p["w"][:-1])/2-1) if row["model"]=="sg13_lv_nmos" else (x+10,10)
        tt = place(tap, tx, ty)
        tb=tap.dbbox().transformed(tt)
        cb=c.dbbox().transformed(t)
        assert tb.left>=cb.right+1-1e-8 or tb.right<=cb.left-1+1e-8 or tb.bottom>=cb.top+1-1e-8 or tb.top<=cb.bottom-1+1e-8
        assert cb.right < x+40 and cb.top < 140
        ps = [s.dbbox().transformed(tt) for s in tap.each_shape(layout.layer(8, 2))]
        assert len(ps) == 1
        escape(ps[0], 1, "sub", x + 15, name + "_tap", 3)
        reference.append(f"RPTAP{i} sub BULK ptap1 A=4p P=8u")
    columns=[(net,x) for net,points in terminals.items() for x,_ in points]
    for i,(net,x) in enumerate(columns):
        for other,ox in columns[i+1:]:
            assert net==other or abs(x-ox)>=2-1e-8,("Cross-net routing-column overlap",net,other,x,ox)
    ports = {}
    routing_geometry=[]
    for i, net in enumerate(["avss", "inn", "ip", "on", "op", "sub", "avdd", "iref", "tail"]):
        y = 110 + i * 12
        vertical_width = 4.0  # Enclose the actual via landing without sub-minimum edge slivers.
        horizontal_width = 8.0 if net in ("avdd","avss") else 4.0 if net in ("on","op","tail") else 2.0
        xs = []
        for x, sy in terminals[net]:
            box(6, x-vertical_width/2, min(sy,y)-vertical_width/2,
                x+vertical_width/2, max(sy,y)+vertical_width/2)
            via(6,7,x,y)
            xs.append(x)
        box(7,0,y-horizontal_width/2,max(xs)+2,y+horizontal_width/2)
        routing_geometry.append(dict(net=net,vertical_layer="TopMetal1",vertical_width_um=vertical_width,
                                     horizontal_layer="TopMetal2",horizontal_width_um=horizontal_width,bus_y_um=y))
        if net in PORTS:
            pin=pya.DBox(0,y-horizontal_width/2,4,y+horizontal_width/2)
            ports[net]=("TopMetal2",pin)
            top.shapes(layout.layer(layers["TopMetal2"],2)).insert(pin)
            top.shapes(layout.layer(layers["TopMetal2"],25)).insert(pya.DText(net,0,y))
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
                substrate_contacts=len(rows),
                kind=args.kind,
                routes=routes,
                routing_geometry=routing_geometry,
                port_layer_number=layers["TopMetal2"],
                schematic_unchanged_from_v49=True,
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
