#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generate an actual hybrid XOR leaf with finite substrate contacts.

All54 source devices are represented:16HBT,3MOS,8rppd and27contacts.
Five additional local MOS contacts make59physical devices. New physical
model/RC must include them; this is not the54device ideal component model.

The substrate and signal-return ports remain distinct. Generation does not
establish DRC/LVS, extracted electrical performance, PVT or full PHY acceptance.
"""

import argparse
from pathlib import Path
import sys
import json
import hashlib
import xml.etree.ElementTree as ET

PORTS = ["dp", "dn", "ep", "en", "qp", "qn", "avdd", "avss", "sub", "iref"]
TOP = None
CIRCUIT = "hw/soc/analog/pcie/cdr_xor_core_hybrid_tail_v2.spice"
CIRCUIT_SHA256 = "47dbcf055d732456f9b5c199e8deedd0a2fc402546c5c464ab315862bd70b660"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def devices(text, kind):
    assert hashlib.sha256(text.encode()).hexdigest() == CIRCUIT_SHA256
    assert kind == 'xor'
    raw=[s.lower().split()for s in text.splitlines()if s and not s.startswith('*')]
    ports=['sub','ap','an','bp','bn','iref','sp','sn','on','op','avss','avdd']
    assert raw[0]==['.subckt','nssoc_cdr_xor_core_hybrid_tail_v2',*ports]
    assert raw[-1]==['.ends','nssoc_cdr_xor_core_hybrid_tail_v2']and len(raw)==56
    # Physically cross both data pairs and preserve XOR output polarity.
    mapping=dict(zip(ports,['sub','dp','dn','dn','dp','iref','ep','en','qp','qn','avss','avdd'],strict=True))
    wrapper=Path(__file__).resolve().parents[3]/'hw/soc/analog/pcie/cdr_xor_hybrid_tail_v2.spice'
    assert sha(wrapper)=='39d055605d72b6aa586b058c5492e17ae5bffe2dffc0942c07258dcb7137cddc'
    wr=[l.lower().split()for l in wrapper.read_text().splitlines()if l and not l.startswith('*')]
    assert wr[0]==['.subckt','nssoc_cdr_xor_hybrid_tail_v2',*PORTS]
    assert wr[2]==['.ends','nssoc_cdr_xor_hybrid_tail_v2']and len(wr)==3
    assert wr[1]==['xcore',*[mapping[p]for p in ports],'nssoc_cdr_xor_core_hybrid_tail_v2'],'Physical XOR cross-connection/polarity differs from native tested wrapper'
    rows=[];taps=[]
    for f in raw[1:-1]:
        if f[3]=='ptap1':
            assert f[1:3]==['sub','n_1']
            p=dict(v.split('=')for v in f[4:]);assert p==dict(r='81.66666666666666666666666668',w='2u',l='2u')
            taps.append(f[0]);continue
        found=[(m,n)for m,n in [('npn13g2',4),('sg13_lv_nmos',4),('rppd',3)]if len(f)>n+1 and f[n+1]==m]
        assert len(found)==1;model,count=found[0];p=dict(v.split('=')for v in f[count+2:])
        assert f[count]=='n_1'and len(p)==len(f[count+2:])
        nets=[mapping.get(n,n)for n in f[1:count]]+['sub']
        rows.append(dict(path='xgate.xcore.'+f[0],model=model,nets=nets,params=p,source_bulk_node='n_1'))
    assert len(rows)==len(taps)==27
    assert sum(r['model']=='npn13g2'for r in rows)==16
    assert sum(r['model']=='sg13_lv_nmos'for r in rows)==3
    assert sum(r['model']=='rppd'for r in rows)==8
    assert sum(int(r['params']['nx'])for r in rows if r['model']=='npn13g2')==72
    assert [r['path']for r in rows if r['model']=='sg13_lv_nmos']==['xgate.xcore.xd0009','xgate.xcore.xd0049','xgate.xcore.xd0053']
    for i,r in enumerate(rows):
        r['source_contact']=taps[i]
        if r['model']=='sg13_lv_nmos':assert r['params']==dict(w='8u'if r['path'].endswith('xd0009')else'64u',l='.3u',ng='1')
    return rows


def main():
    global TOP
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--kind", choices=("xor",), required=True)
    args = parser.parse_args()
    TOP = "nssoc_cdr_xor_hybrid_tail_layout_v3"
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
        Path(__file__).resolve(),
        source,
        R / "hw/soc/analog/pcie/cdr_xor_hybrid_tail_v2.spice",
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
    local_mos_contacts = []
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
        via(3, 4, lane, y)
        terminals.setdefault(net, []).append((lane, y))
        routes.append(
            dict(
                device=label, net=net, native_layer=met, pin=str(pin), escape=[lane, y]
            )
        )

    for i, row in enumerate(rows):
        x = 30 + i * 30
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
                (collector, 1, n[0], x - 9, 0.04),
                (base, 1, n[1], x - 6, -0.04),
                (m2[0], 2, n[2], x - 3, 0),
            ]:
                escape(pin, met, net, lane, name, 4, off)
            reference.append(
                f"Q{name} "
                + " ".join(n[:3] + ["BULK"])
                + f" npn13G2 Nx={p['nx']} we=0.07u le=0.9u m=1"
            )
        elif row["model"] == "sg13_lv_nmos":
            c = pc("nmos", {"w":p["w"],"l":p["l"],"ng":1})
            t = place(c,x,y)
            mp = sorted([s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8,2))],key=lambda b:b.center().x)
            gp = [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(5,2))]
            assert len(mp)==2 and len(gp)==1 and n[3]=='sub'
            # Native nmos left source/right drain; access at separate y levels.
            for k,(pin,net) in enumerate(zip(mp,[n[2],n[0]],strict=True)):
                py=round((pin.bottom+.4 if k==0 else pin.top-.4)/.005)*.005
                tiny=pya.DBox(pin.left,py-.1,pin.right,py+.1)
                assert pin.contains(pya.DPoint(tiny.left,tiny.bottom))and pin.contains(pya.DPoint(tiny.right,tiny.top))
                escape(tiny,1,net,x-9+3*k,name,1)
            gate=gp[0];gx=round(gate.center().x/.005)*.005;gy=round((gate.top+1)/.005)*.005
            top.shapes(layout.layer(5,0)).insert(pya.DBox(gate.left,gate.top-.1,gate.right,gy+.3))
            top.shapes(layout.layer(5,0)).insert(pya.DBox(gx-.3,gy-.3,gx+.3,gy+.3))
            top.shapes(layout.layer(6,0)).insert(pya.DBox(gx-.08,gy-.08,gx+.08,gy+.08))
            pin=box(1,gx-.25,gy-.25,gx+.25,gy+.25)
            escape(pin,1,n[1],x-3,name,1)
            reference.append(f"M{name} "+" ".join(n[:3]+['BULK'])+f" sg13_lv_nmos w={p['w']} l={p['l']} ng=1 m=1")
            # Additional finite local contact beside each MOS active strip; preserve
            # separate substrate and signal-return conductors throughout.
            tapcell=pc('ptap1',{'w':'2u','l':'2u'})
            width=float(p['w'][:-1])
            # LU.b limits distance from every N+ active point to a PWell tie
            # to20um. A central contact leaves a64um stripe end uncovered.
            offsets=[width/4,3*width/4]if width==64 else[width/2]
            for contact_index,offset in enumerate(offsets):
                tt=place(tapcell,x+3,y+offset-1)
                pins_m=[s.dbbox().transformed(tt) for s in tapcell.each_shape(layout.layer(8,2))];assert len(pins_m)==1
                escape(pins_m[0],1,'sub',x+15,name+'_local_body_'+str(contact_index),3)
                reference.append(f"RLOCAL{i}_{contact_index} sub BULK ptap1 A=4p P=8u")
                local_mos_contacts.append(dict(device=name,index=contact_index,offset_along_active_um=offset,bbox_um=str(tapcell.dbbox().transformed(tt))))
        elif row["model"] == "rppd":
            c = pc("rppd", {"w": p["w"], "l": p["l"]})
            t = place(c, x, y)
            ps = sorted(
                [s.dbbox().transformed(t) for s in c.each_shape(layout.layer(8, 2))],
                key=lambda b: b.center().y,
            )
            assert len(ps) == 2
            for k, pin in enumerate(ps):
                escape(pin, 1, n[k], x - 6 + 3 * k, name)
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
            plus, minus = x - 9, x - 6
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
        tt = place(tap, x + 10, 10)
        ps = [s.dbbox().transformed(tt) for s in tap.each_shape(layout.layer(8, 2))]
        assert len(ps) == 1
        escape(ps[0], 1, "sub", x + 15, name + "_tap", 3)
        reference.append(f"RPTAP{i} sub BULK ptap1 A=4p P=8u")
    ports = {}
    for i, net in enumerate(sorted(terminals)):
        y = 150 + i * 6
        xs = []
        for x, sy in terminals[net]:
            box(4, x - 0.6, min(sy, y) - 0.2, x + 0.6, max(sy, y) + 0.2)
            via(4, 5, x, y)
            xs.append(x)
        box(5, 0, y - 0.6, max(xs) + 1, y + 0.6)
        if net in PORTS:
            pin = pya.DBox(0, y - 0.6, 2, y + 0.6)
            ports[net] = ("Metal5", pin)
            top.shapes(layout.layer(layers["Metal5"], 2)).insert(pin)
            top.shapes(layout.layer(layers["Metal5"], 25)).insert(pya.DText(net, 0, y))
    assert set(ports) == set(PORTS)
    assert len(rows)==27 and len(local_mos_contacts)==5
    sys.path.insert(0, str(R / "hw/soc/flow"))
    import make_pcie_clock_vco_v6_local_v1 as writer

    writer.TOP = TOP
    writer.PORTS = PORTS
    writer.use_direction = lambda n: (
        ("POWER", "INOUT")
        if n == "avdd"
        else ("GROUND", "INOUT")
        if n in ["avss", "sub"]
        else ("SIGNAL", "OUTPUT" if n in ["qp", "qn"] else "INPUT")
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
                substrate_contacts=len(rows)+len(local_mos_contacts),
                original_finite_contact_count=27,
                additional_local_mos_contact_count=5,
                expected_native_devices=59,
                column_pitch_um=30,
                local_mos_contacts=local_mos_contacts,
                kind=args.kind,
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


if __name__ == "__main__":
    main()
