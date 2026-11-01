#!/usr/bin/env python3
"""Real isolated MOS units for the PD650 physical implementation.
No full sampler, fresh interconnect PEX or serial PHY acceptance is implied.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
from decimal import Decimal
import xml.etree.ElementTree as ET
WIDTHS=("8","9","8.890","8.885")
PORTS=("S","D","G","SUB")
def top_name(w): return "nssoc_cdr_mos_unit_w"+w.replace(".","p")
def number(s):
    s=str(s).lower()
    return Decimal(s[:-1])*Decimal("1e-6") if s.endswith("u") else Decimal(s)
def parameters(w):
    if w not in WIDTHS: raise ValueError("Unqualified unit width")
    return {"w":w+"u","l":".3u","ng":1}
def reference(w,wrong_width=False):
    # Independent requested circuit. Never generated from extracted devices.
    width="7" if wrong_width else w
    return "\n".join(["* Isolated unit and finite substrate contact",
      ".subckt "+top_name(w)+" "+" ".join(PORTS),
      "MUNIT D G S BULK sg13_lv_nmos w="+width+"u l=.3u ng=1 m=1",
      "RTAP SUB BULK ptap1 A=4p P=8u",".ends "+top_name(w),""])
def verify_parameters(request,actual):
    for k,v in request.items():
        if k not in actual:raise ValueError("Missing PCell parameter "+k)
        if (number(actual[k])!=number(v)) if k in ("w","l") else Decimal(str(actual[k]))!=Decimal(str(v)):
            raise ValueError("Changed PCell parameter "+k)
def controls():
    rejected=[]
    for w in WIDTHS:
        req=parameters(w);verify_parameters(req,dict(w=str(number(w+"u")),l="3e-7",ng=1))
        for k,v in (("w","36u"),("l",".31u"),("ng",2),("missing",None)):
            bad=dict(req)
            if k=="missing":del bad["w"]
            else:bad[k]=v
            try:verify_parameters(req,bad)
            except ValueError:rejected.append(w+":"+k)
            else:raise AssertionError("Accepted changed native geometry parameter")
    for w in ("36","54","8.887","NaN"):
        try:parameters(w)
        except ValueError:rejected.append("unsupported:"+w)
        else:raise AssertionError("Accepted unsupported geometry")
    assert len(rejected)==20
    return dict(widths=list(WIDTHS),refused=rejected,reference_independent_of_extraction=True)
def generate(pdk,out):
    source=pdk.resolve()/"libs.tech/klayout/python"
    sys.dont_write_bytecode=True
    sys.path[:0]=[str(source),str(source/"pycell4klayout-api/source/python")]
    import pya
    import sg13g2_pycell_lib
    lyp=pdk/"libs.tech/klayout/tech/sg13g2.lyp"
    if not lyp.exists():
        choices=list(pdk.rglob("sg13g2.lyp"));assert len(choices)==1
        lyp=choices[0]
    layers={prop.findtext("name")[:-8]:int(prop.findtext("source").split("/")[0])
            for prop in ET.parse(lyp).getroot().iter("properties")
            if prop.findtext("name","").endswith(".drawing")}
    out.mkdir(exist_ok=False);records=[]
    for w in WIDTHS:
        layout=pya.Layout();top=layout.create_cell(top_name(w))
        def pc(name,params):
            cell=layout.create_cell(name,"SG13_dev",params)
            assert cell is not None and not cell.is_empty()
            return cell
        def place(cell,x,y):
            t=pya.DTrans(round(x/.005)*.005,round(y/.005)*.005)
            top.insert(pya.DCellInstArray(cell.cell_index(),t));return t
        def rect(m,x1,y1,x2,y2):
            b=pya.DBox(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2))
            top.shapes(layout.layer(layers["Metal"+str(m)],0)).insert(b);return b
        def via(lo,hi,x,y,cols=2):
            cell=pc("via_stack",dict(b_layer="Metal"+str(lo),t_layer="Metal"+str(hi),vn_columns=cols,vn_rows=1))
            b=cell.dbbox();place(cell,x-b.center().x,y-b.center().y)
        terminals={}
        def escape(pin,net,lane):
            x=round(pin.center().x/.005)*.005;y=round(pin.center().y/.005)*.005
            via(1,3,x,y,1);rect(3,lane-.2,y-.2,x+.2,y+.2);via(3,4,lane,y)
            terminals[net]=(lane,y)
        cell=pc("nmos",parameters(w));verify_parameters(parameters(w),cell.pcell_parameters_by_name())
        t=place(cell,15,10)
        mp=sorted([s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(8,2))],key=lambda b:b.center().x)
        gp=[s.dbbox().transformed(t) for s in cell.each_shape(layout.layer(5,2))]
        assert len(mp)==2 and len(gp)==1
        for k,(pin,net) in enumerate(zip(mp,("S","D"))):
            y=round((pin.bottom+.4 if k==0 else pin.top-.4)/.005)*.005
            tiny=pya.DBox(pin.left,y-.1,pin.right,y+.1)
            assert pin.contains(pya.DPoint(tiny.left,tiny.bottom)) and pin.contains(pya.DPoint(tiny.right,tiny.top))
            escape(tiny,net,6+3*k)
        gate=gp[0];gx=round(gate.center().x/.005)*.005;gy=round((gate.top+1)/.005)*.005
        top.shapes(layout.layer(5,0)).insert(pya.DBox(gate.left,gate.top-.1,gate.right,gy+.3))
        top.shapes(layout.layer(5,0)).insert(pya.DBox(gx-.3,gy-.3,gx+.3,gy+.3))
        top.shapes(layout.layer(6,0)).insert(pya.DBox(gx-.08,gy-.08,gx+.08,gy+.08))
        escape(rect(1,gx-.25,gy-.25,gx+.25,gy+.25),"G",12)
        tap=pc("ptap1",dict(w="2u",l="2u"))
        tt=place(tap,18,10+float(w)/2-1)
        pins=[s.dbbox().transformed(tt) for s in tap.each_shape(layout.layer(8,2))]
        assert len(pins)==1
        x=round(pins[0].center().x/.005)*.005;y=round(pins[0].center().y/.005)*.005
        via(1,4,x,y,3);terminals["SUB"]=(x,y)
        assert set(terminals)==set(PORTS)
        assert all(abs(a[0]-b[0])>=2 for i,a in enumerate(terminals.values()) for b in list(terminals.values())[i+1:])
        buses={}
        for i,net in enumerate(PORTS):
            x,y=terminals[net];bus=28+4*i
            rect(4,x-.6,y-.2,x+.6,bus+.2);via(4,5,x,bus)
            rect(5,0,bus-1,x+1,bus+1)
            pin=pya.DBox(0,bus-1,2,bus+1)
            top.shapes(layout.layer(layers["Metal5"],2)).insert(pin)
            top.shapes(layout.layer(layers["Metal5"],25)).insert(pya.DText(net,1,bus))
            buses[net]=bus
        case=out/top.name;case.mkdir()
        layout.write(str(case/"unit.gds"))
        (case/"reference.cir").write_text(reference(w))
        (case/"wrong-width.cir").write_text(reference(w,True))
        # Physical short is genuine geometry, separate from reference mutation.
        rect(5,.5,buses["S"],1.5,buses["D"])
        layout.write(str(case/"short-sd.gds"))
        box=cell.dbbox()
        records.append(dict(width_um=w,top=top.name,parameters=parameters(w),
            native_parameter_readback={k:cell.pcell_parameters_by_name()[k] for k in parameters(w)},
            native_bbox_um=[box.left,box.bottom,box.right,box.top],
            ports=list(PORTS),primitive_count=2,ng=1,
            gate_contact_source="make_pcie_sampler_hybrid_tail_v1.py:212-230",
            source_drain_extension_um_proposed=.34,
            expected_as_ad_um2=float(Decimal(w)*Decimal(".34")),
            expected_ps_pd_um=2*float(Decimal(w)+Decimal(".34"))))
    (out/"geometry.json").write_text(json.dumps(dict(controls=controls(),units=records,
        full_phy_accepted=False,full_pd650_generated=False,qualified_pex=False),indent=2)+"\n")
def inspect_lvs(report,top,out):
    import klayout.db as db
    lvs=db.LayoutVsSchematic();lvs.read(str(report))
    circuit=lvs.netlist().circuit_by_name(top);assert circuit is not None
    devices=[]
    for dev in circuit.each_device():
        dc=dev.device_class()
        devices.append(dict(name=dev.name,model=dc.name,
            parameters={p.name:dev.parameter(p.id) for p in dc.parameter_definitions()},
            terminals={t.name:dev.net_for_terminal(t.id).name for t in dc.terminal_definitions()}))
    Path(out).write_text(json.dumps(dict(top=top,devices=devices),indent=2)+"\n")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");p.add_argument("--pdk",type=Path);p.add_argument("--out",type=Path)
    p.add_argument("--inspect",type=Path);p.add_argument("--top")
    a=p.parse_args()
    if a.controls:print(json.dumps(controls()))
    elif a.inspect:inspect_lvs(a.inspect,a.top,a.out)
    else:generate(a.pdk,a.out)
