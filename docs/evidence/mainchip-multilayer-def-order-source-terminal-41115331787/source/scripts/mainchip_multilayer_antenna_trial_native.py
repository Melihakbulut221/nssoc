#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Existing diode, exact three-metal additive branch and complete chip delta audit."""
import hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_multilayer_antenna_trial as p
import mainchip_net459_connectivity as graph
import mainchip_two_signal_ownership_native as own
import mainchip_original_clock_restoration_native as n
import mainchip_original_clock_drc as drc
import mainchip_original_clock_restoration as c
import mainchip_full_antenna_report as ant
D=Path("/work/out/multilayer-antenna-trial")
W=Path("/work/out/work/multilayer-antenna-trial")
SOURCE=Path("/work/current-input.odb")
CATEGORY="NSSOC_MULTILAYER_ANTENNA_TRIAL_DRC"
drc.CATEGORY=CATEGORY
def save(name,v):(D/name).write_bytes(p.encode(v))
def filepin(path):return p.pin(path.read_bytes())
def q(path):
    v=str(path);assert v.startswith("/work/")and not any(x in v for x in("{}[]$\n\r\\"));return "{"+v+"}"
def point(v):
    if isinstance(v,(tuple,list)):assert len(v)==2;return list(v)
    return [v.x(),v.y()]
def target(db,b):
    proof=own.api_evidence();layers=own.named_layers(db.getTech(),proof);net=b.findNet(p.NET)
    assert net and not net.isSpecial()and not list(net.getSWires())
    projection=own.native_wire(db,b,net.getWire(),layers,proof)
    pins=[]
    for t in net.getITerms():
        i=t.getInst();m=i.getMaster()
        pins.append(dict(kind="iterm",scoped_identity=["iterm",i.getName(),t.getMTerm().getName()],
          instance=i.getName(),master=[m.getLib().getName(),m.getName()],terminal=t.getMTerm().getName(),
          geometries=[[l.getName(),own.box(r)]for l,r in t.getGeometries()]))
    return dict(scoped_identity=["net",p.NET],wire_identity=["net",p.NET,"wire"],
       metadata_class=str(net.getWireType()),sigtype=str(net.getSigType()),projection=projection,pins=pins)
def existing_diode(db,b):
    i=b.findInst(p.NEW);assert i is not None
    m=i.getMaster()
    row=dict(name=i.getName(),master=[m.getLib().getName(),m.getName()],
      type=str(m.getType()),size=[m.getWidth(),m.getHeight()],
      location=list(i.getLocation()),origin=list(i.getOrigin()),orientation=str(i.getOrient()),
      placement=str(i.getPlacementStatus()),box=own.box(i.getBBox()),terminals=[])
    assert row["name"]==p.NEW and row["master"][1]=="sg13g2_antennanp"
    assert row["type"]=="CORE_ANTENNACELL"and row["size"]==[1440,3780]
    assert row["location"]==[98880,502740]and row["orientation"]=="MX"and row["placement"]=="PLACED"
    assert row["box"]==[98880,502740,100320,506520]
    for t in sorted(i.getITerms(),key=lambda t:t.getMTerm().getName()):
        mt=t.getMTerm();net=t.getNet();assert net is not None
        row["terminals"].append(dict(name=mt.getName(),io=str(mt.getIoType()),sigtype=str(mt.getSigType()),
          net=net.getName(),geometries=[[l.getName(),own.box(r)]for l,r in t.getGeometries()]))
    assert [(t["name"],t["net"],t["sigtype"])for t in row["terminals"]]==[
      ("A",p.NET,"SIGNAL"),("VDD","VPWR","POWER"),("VSS","VGND","GROUND")]
    areas=m.findMTerm("A").getDiffArea();assert areas and max(float(x[0])for x in areas)==2.0154
    row["diffusion_areas"]=[[float(a),None if l is None else l.getName()]for a,l in areas]
    return row

def exact_current_vias(db):
    proof=own.api_evidence();layers=own.named_layers(db.getTech(),proof);vias={}
    for key in p.VIA_DEFINITIONS:
        via=odb.dbTechVia.getTechVia(db.getTech(),int(key.split(":")[1]))
        assert via is not None
        value=own.via_record(via,layers)
        p.exact(value,p.VIA_DEFINITIONS[key],"exact current native via definition")
        p.exact(value,own.expected_via(proof["raw_operand_native_lookups"]["vias"][key]),"qualified native via OID")
        vias[key]=value
    catalog=dict(layers=layers,path_layers={},rules={},vias=vias)
    p.expected_added_shapes(catalog)
    return catalog

def snapshot(db,b,defpath):
    assert len(list(b.getNets()))==143820 and len(list(b.getInsts()))==153129
    diode=existing_diode(db,b)
    assert not list(b.getChildren())
    assert b.getDbUnitsPerMicron()==db.getTech().getDbUnitsPerMicron()==1000
    odb.write_def(b,str(defpath));raw=defpath.read_bytes();parsed=c.parse_def(raw)
    clocks=n.selected(b);assert len(clocks)==1691
    digests={k:hashlib.sha256()for k in("nets","raw-other-wires","instances","master-pins","clocks")}
    counts={}
    def feed(kind,row):
        encoded=c.canonical(row);digests[kind].update(len(encoded).to_bytes(8,"big"));digests[kind].update(encoded)
        counts[kind]=counts.get(kind,0)+1
    for net in sorted(b.getNets(),key=lambda x:x.getName()):
        ident=n.identity(db,net)
        encoded=n.encoded(net)
        if net.getName()==p.NET:
            assert encoded["wire_present"]and encoded["metadata"]=="ROUTED"
            assert encoded["paths"]and set(encoded["paths"])=={"ROUTED"}
            encoded=dict(wire_present=True,metadata="ROUTED",only_target_path_list_excluded=True)
        feed("nets",[ident,encoded])
        w=net.getWire()
        if net.getName()!=p.NET:
            feed("raw-other-wires",[net.getName(),None if w is None else [[w.getOpcode(i),w.getData(i)]for i in range(w.length())]])
    masters={}
    for i in sorted(b.getInsts(),key=lambda x:x.getName()):
        m=i.getMaster();mk=(m.getLib().getName(),m.getName());masters[mk]=m
        feed("instances",[i.getName(),list(mk),list(i.getLocation()),list(i.getOrigin()),str(i.getOrient()),str(i.getPlacementStatus())])
    for key,m in sorted(masters.items()):
        for t in sorted(m.getMTerms(),key=lambda x:x.getName()):
            feed("master-pins",[list(key),t.getName(),str(t.getIoType()),str(t.getSigType()),[drc.master_pin_boxes(x)for x in t.getMPins()]])
    for name in sorted(clocks):feed("clocks",[name,parsed["records"][name].decode("ascii")])
    del parsed
    normalized=p.normalized_def(raw)
    return dict(counts=counts,digests={k:v.hexdigest()for k,v in digests.items()},
      normalized_def_sha256=normalized["sha256"],normalized_def_delta=normalized,
      immutable_material=own.immutable_material(db,b),clock_names=sorted(clocks),
      raw_def=filepin(defpath),actual_instances=153129,net_count=143820,existing_diode=diode)
def equal_snapshot(actual,base):
    for k in("counts","digests","normalized_def_sha256","immutable_material","clock_names","net_count","actual_instances","existing_diode"):
        assert actual[k]==base[k],("full remaining-chip invariant",k)

def connection_checks(actual):
    obs={}
    for mode in("positive_area","closed_boundary"):
        r=graph.observe(actual["projection"]["shapes"],actual["pins"],mode)
        assert r["all_pins_share_one_wire_component"]and r["all_wire_material_one_component"],("physical target connectivity",mode)
        assert all(len(v["wire_components"])==1 for v in r["pins"])
        obs[mode]=r
    return obs
def antenna_tcl(source,label,with_drc=False):
    out=W/(label+"-ant-counts.json");net="{"+p.NET+"}"
    text="read_db "+q(source)+"\nset_thread_count 2\nwrite_def "+q(W/(label+"-before.def"))+"\n"
    if with_drc:text+="drt::check_drc -output_file "+q(W/"initial-drc.rpt")+" -marker_name "+CATEGORY+"\n"
    text+="check_antennas -verbose -report_file "+q(W/(label+"-target-antenna.rpt"))+" -net "+net+"\n"
    text+="set target_count [ant::antenna_violation_count]\nset target_violation [ant::check_net_violation "+net+"]\n"
    text+="check_antennas -verbose -report_file "+q(W/(label+"-full-antenna.rpt"))+"\nset full_count [ant::antenna_violation_count]\n"
    text+="set out [open "+q(out)+" w]\n"
    text+='puts $out [format {{"target_count":%d,"target_violation":%d,"full_count":%d}} $target_count $target_violation $full_count]\nclose $out\n'
    text+="write_def "+q(W/(label+"-after.def"))+"\n"
    if with_drc:text+="write_db "+q(W/"candidate-measured.odb")+"\n"
    return text
def prepare():
    assert filepin(SOURCE)==p.INPUT
    db,b=n.load(SOURCE)
    try:
        assert b.findMarkerCategory(CATEGORY)is None
        diode=existing_diode(db,b)
        actual=target(db,b);assert len(actual["projection"]["shapes"])==40
        assert not list(b.findNet(p.NET).getBTerms()),"unexpected target block terminals"
        baseline_connectivity={mode:graph.observe(actual["projection"]["shapes"],actual["pins"],mode)
          for mode in("positive_area","closed_boundary")}
        for mode,row in baseline_connectivity.items():
            assert row["all_wire_material_one_component"]and not row["all_pins_share_one_wire_component"],("inserted baseline",mode)
            diode_rows=[r for r in row["pins"]if r["scoped_identity"]==["iterm",p.NEW,"A"]]
            assert len(diode_rows)==1 and diode_rows[0]["wire_components"]==[],("baseline diode physically unconnected",mode)
        save("baseline-target.json",actual);save("baseline-connectivity.json",baseline_connectivity)
        base=snapshot(db,b,W/"before.def");save("baseline-snapshot.json",base)
        catalog=exact_current_vias(db)
        save("actual-branch-via-catalog.json",catalog)
        plan=dict(existing_diode=diode,seed=p.SEED,expected_added_shapes=p.expected_added_shapes(catalog),
          original_shape_count=40,patch_connected_terminals=len(actual["pins"]),
          new_instances=0,new_signal_connections=0,only_changed_signal_net=p.NET)
        save("plan.json",plan)
    finally:odb.dbDatabase.destroy(db)
    raw=(W/"before.def").read_bytes();record=c.parse_def(raw)["records"][p.NET]
    patched=p.append_branch(record);patch,removed=c.patch_def(raw,{p.NET:patched})
    assert removed==plan["patch_connected_terminals"]
    (W/"target-patch.def").write_bytes(patch)
    text="read_db "+q(SOURCE)+"\n"
    for suffix in("single","double"):text+="read_def -floorplan_initialize "+q(W/"target-patch.def")+"\nwrite_def "+q(W/("candidate-"+suffix+".def"))+"\n"
    text+="write_db "+q(W/"candidate.odb")+"\n"
    (W/"import.tcl").write_text(text)
    (W/"baseline-ant.tcl").write_text(antenna_tcl(SOURCE,"baseline"))
    (W/"candidate-check.tcl").write_text(antenna_tcl(W/"candidate.odb","candidate",True))
    save("prepare-result.json",dict(status="PREPARED_EXISTING_DIODE_MULTILAYER_BRANCH",plan=plan,
      source_input_unchanged=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
def audit(measured):
    plan=json.loads((D/"plan.json").read_bytes());base=json.loads((D/"baseline-snapshot.json").read_bytes())
    old=p.restore_target_catalog(json.loads((D/"baseline-target.json").read_bytes()))
    name="candidate-measured.odb"if measured else"candidate.odb"
    db,b=n.load(W/name)
    try:
        snap=snapshot(db,b,W/("audit-"+name+".def"));equal_snapshot(snap,base)
        p.exact(existing_diode(db,b),plan["existing_diode"],"existing diode preserved")
        actual=target(db,b);delta=p.validate_route_delta(old,actual)
        order=p.validate_def_import_order((W/"candidate-single.def").read_bytes(),(W/"candidate-double.def").read_bytes(),old)
        save(("measured"if measured else"imported")+"-def-import-order.json",order)
        save(("measured"if measured else"imported")+"-route-delta.json",delta)
        save(("measured"if measured else"imported")+"-target.json",actual)
        save(("measured"if measured else"imported")+"-snapshot.json",snap)
        save(("measured"if measured else"imported")+"-connectivity.json",connection_checks(actual))
        if not measured:return
        category=b.findMarkerCategory(CATEGORY);assert category is not None
        category.writeJSON(str(D/"drc-markers.json"))
        measurement=drc.measure_report(category,W/"initial-drc.rpt",W/"reread-drc.rpt",D/"drc-markers.json")
        counts={}
        for label in("baseline","candidate"):
            assert (W/(label+"-before.def")).read_bytes()==(W/(label+"-after.def")).read_bytes(),"checker changed DEF"
            counts[label]=json.loads((W/(label+"-ant-counts.json")).read_bytes())
        authentic=json.loads((p.ROOT/p.legacy.VIOLATIONS).read_bytes());reports={}
        for label in("baseline","candidate"):
            with (W/(label+"-full-antenna.rpt")).open()as f:summary,nets,violations=ant.parse(f,counts[label]["full_count"])
            with (W/(label+"-target-antenna.rpt")).open()as f:ts,tn,tv=ant.parse(f,counts[label]["target_count"])
            p.exact(sorted([ant.semantics(v)for v in tv],key=p.encode),
              sorted([ant.semantics(v)for v in violations if v["net"]==p.NET],key=p.encode),"target/full antenna report join")
            save(label+"-antenna-summary.json",summary);save(label+"-antenna-violations.json",violations)
            save(label+"-antenna-net-census.json",nets)
            reports[label]=dict(counts=counts[label],violations=violations)
        verdict=p.validate_antenna(reports["baseline"],reports["candidate"],authentic,measurement["marker_count"])
        save("result.json",dict(status="COMPLETE_MULTILAYER_ANTENNA_TRIAL_CHECKS",**verdict,
          input=p.INPUT,candidate=filepin(W/name),measurement=measurement,antenna=counts,def_import_order=order,
          exact_remaining_chip_preserved=True,all_1691_original_clocks_preserved=True,
          original_target_wire_shapes_preserved=40,new_instances=0,new_signal_connections=0,
          added_wire_count=3,added_via_component_count=9,expected_added_shapes=plan["expected_added_shapes"],
          scope="Existing-diode physical repair trial only; full-chip LVS/foundry DRC/RC and original setup/hold remain required."))
    finally:odb.dbDatabase.destroy(db)
def main():
    assert not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN"))
    p.source_guard();D.mkdir(exist_ok=True);W.mkdir(parents=True,exist_ok=True);error=None
    phase=os.environ["NSSOC_MULTILAYER_ANTENNA_PHASE"];assert phase in("prepare","audit-import","audit-measured")
    def action():
        if phase=="prepare":prepare()
        else:audit(phase=="audit-measured")
    def unchanged():assert filepin(SOURCE)==p.INPUT,"current input changed"
    p.run_phase(phase,action,unchanged,save)
if __name__=="__main__":main()
