#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only real candidate antenna data/route/pin census; native runner only."""
import hashlib,json,math,os,sys,traceback
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_antenna_ownership as p
import mainchip_two_signal_ownership_native as own
import mainchip_original_clock_restoration_native as n
D=Path("/work/out/antenna-ownership");W=Path("/work/out/work/antenna-ownership")
SOURCE=Path("/work/current-input.odb");ROOT=Path("/work/tail-source")
def save(name,value):(D/name).write_bytes(p.encoded(value))
def fp(path):
    h=hashlib.sha256();size=0
    with path.open("rb")as f:
        for b in iter(lambda:f.read(1024**2),b""):h.update(b);size+=len(b)
    return dict(bytes=size,sha256=h.hexdigest())
def area_rows(values):
    assert isinstance(values,(list,tuple))
    result=[]
    for value in values:
        assert isinstance(value,(list,tuple))and len(value)==2
        area,layer=value;assert isinstance(area,(int,float))and math.isfinite(area)and area>=0
        result.append(dict(area=float(area),layer=None if layer is None else layer.getName()))
    return result
def master_term(mt):
    model=mt.getDefaultAntennaModel()if mt.hasDefaultAntennaModel()else None
    ga=[]if model is None else area_rows(model.getGateArea())
    da=area_rows(mt.getDiffArea())
    return dict(default_antenna_model=model is not None,gate_areas=ga,diffusion_areas=da,
      gate_area_max=max([0.0]+[x["area"]for x in ga]),diffusion_area_max=max([0.0]+[x["area"]for x in da]),
      io=str(mt.getIoType()),sigtype=str(mt.getSigType()))
def run():
    assert not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN"))
    assert fp(SOURCE)==p.INPUT
    D.mkdir();W.mkdir(parents=True);db=None;error=None
    try:
        rows=p.load_violations(ROOT);net_names=p.validate(rows,(609,697,916))
        db,b=n.load(SOURCE);tech=db.getTech()
        assert b.getDbUnitsPerMicron()==tech.getDbUnitsPerMicron()==1000
        assert len(list(b.getNets()))==143820 and len(list(b.getInsts()))==153128 and not list(b.getChildren())
        clocks=sorted(n.selected(b));assert len(clocks)==1691
        odb.write_def(b,str(W/"before.def"));before=fp(W/"before.def")
        proof=own.api_evidence();layers=own.named_layers(tech,proof)
        assert hasattr(odb,"write_tech_lef")and hasattr(odb,"write_macro_lef")
        odb.write_tech_lef(tech,str(D/"technology.lef"));assert (D/"technology.lef").is_file()
        clauses=p.antenna_statements((D/"technology.lef").read_text(),[x.getName()for x in tech.getLayers()])
        rules={}
        methods=("isValid","hasAreaFactor","hasSideAreaFactor","getAreaFactor","getSideAreaFactor",
          "isAreaFactorDiffUseOnly","isSideAreaFactorDiffUseOnly","hasAntennaCumRoutingPlusCut",
          "getPAR","getCAR","getPSR","getCSR","getGatePlusDiffFactor","getAreaMinusDiffFactor")
        for l in tech.getLayers():
            rule=l.getDefaultAntennaRule()if l.hasDefaultAntennaRule()else None
            rules[l.getName()]=dict(type=str(l.getType()),routing_level=l.getRoutingLevel(),antenna_clauses=clauses[l.getName()],
              default_antenna_rule=None if rule is None else {k:getattr(rule,k)()for k in methods})
        save("technology-antenna-data.json",rules)
        native={};terms={};libs={};all_diodes={}
        retained=b.findInst("ANTENNA_1573");assert retained is not None and retained.getMaster().getName()=="sg13g2_antennanp"
        assert str(retained.getMaster().getType())=="CORE_ANTENNACELL"
        assert b.findInst("ANTENNA_1574")is None and b.findInst("ANTENNA_1575")is None
        for i in b.getInsts():
            m=i.getMaster()
            if str(m.getType())=="CORE_ANTENNACELL":
                all_diodes[i.getName()]=dict(master=[m.getLib().getName(),m.getName()],location=list(i.getLocation()),
                  orientation=str(i.getOrient()),placement=str(i.getPlacementStatus()),
                  terminals=[dict(name=t.getMTerm().getName(),net=None if t.getNet()is None else t.getNet().getName())for t in i.getITerms()])
        for name in net_names:
            net=b.findNet(name);assert net is not None and not net.isSpecial()and net.getWire()is not None and not list(net.getSWires())
            pins=[]
            for t in net.getITerms():
                i=t.getInst();m=i.getMaster();mt=t.getMTerm();key=(m.getLib().getName(),m.getName(),mt.getName())
                if key not in terms:terms[key]=master_term(mt)
                libs[m.getLib().getName()]=m.getLib()
                pins.append(dict(scoped_identity=[i.getName(),mt.getName()],display_name=i.getName()+"/"+mt.getName(),
                  instance=i.getName(),master=list(key[:2]),terminal=key[2],master_type=str(m.getType()),
                  location=list(i.getLocation()),orientation=str(i.getOrient()),placement=str(i.getPlacementStatus()),
                  geometries=[[l.getName(),own.box(r)]for l,r in t.getGeometries()],**terms[key]))
            pins.sort(key=lambda x:x["scoped_identity"])
            native[name]=dict(name=name,sigtype=str(net.getSigType()),wire_type=str(net.getWireType()),
              special=net.isSpecial(),wire_present=True,pins=pins,block_terminals=[t.getName()for t in net.getBTerms()],
              wire_projection=own.native_wire(db,b,net.getWire(),layers,proof))
        save("all-violating-net-native-data.json",native)
        save("all-diode-instances.json",all_diodes)
        save("master-terminal-data.json",[dict(master=list(k[:2]),terminal=k[2],**v)for k,v in sorted(terms.items())])
        exports={}
        for index,(name,lib)in enumerate(sorted(libs.items())):
            path=D/("library-%03d.lef"%index);odb.write_macro_lef(lib,str(path));assert path.is_file()
            exports[name]=dict(path=path.name,**fp(path))
        save("complete-native-lef-index.json",dict(technology=fp(D/"technology.lef"),libraries=exports,native_LEF_remains_in_capsule=True))
        result=p.join(rows,native);odb.write_def(b,str(W/"after.def"))
        assert fp(W/"after.def")==before and sorted(n.selected(b))==clocks,"read-only native drift"
        summary=[]
        for name,net in native.items():
            vv=[r for r in rows if r["net"]==name];pins=net["pins"]
            diodes=[p for p in pins if p["master_type"]=="CORE_ANTENNACELL"]
            summary.append(dict(net=name,violating_checks=len(vv),violating_pins=sorted({r["pin"]for r in vv}),
              violated_layers=sorted({r["layer"]for r in vv}),diode_instances=[p["instance"]for p in diodes],
              connected_diode_diffusion_area=sum(p["diffusion_area_max"]for p in diodes),
              connected_pin_gate_area=sum(p["gate_area_max"]for p in pins),
              connected_pin_diffusion_area=sum(p["diffusion_area_max"]for p in pins),wire_shapes=len(net["wire_projection"]["shapes"])))
        save("all-609-net-summary.json",summary)
        result.update(input=p.INPUT,reported_input=dict(violation_pin=p.VIOLATION_PIN),
          all_chip_diodes=len(all_diodes),violating_nets_with_diode=sum(bool(r["diode_instances"])for r in summary),
          violating_nets_without_diode=sum(not r["diode_instances"]for r in summary),native_def_unchanged=True,
          before_after_def=before,all_1691_original_clocks_unchanged=True,
          geometry_connectivity_or_cumulative_formula_not_recomputed=True,
          no_gate_area_or_diffusion_inferred_from_name=True,per_layer_physical_diode_reachability_unproved=True)
        save("result.json",result)
    except BaseException as exc:
        error=exc;save("failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
    finally:
        if db is not None:odb.dbDatabase.destroy(db)
        assert fp(SOURCE)==p.INPUT
        save("terminal.json",dict(complete=error is None,error=None if error is None else repr(error),input_unchanged=True,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
if __name__=="__main__":run()
