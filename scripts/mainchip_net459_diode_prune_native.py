#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Real candidate mutation and serialized full-chip delta audit; cloud only."""
import copy,hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_net459_diode_prune as p
import mainchip_net459_connectivity as graph
import mainchip_two_signal_ownership_native as own
import mainchip_original_clock_restoration_native as n
import mainchip_original_clock_drc as drc
import mainchip_original_clock_restoration as c
D=Path("/work/out/net459-diode-prune")
W=Path("/work/out/work/net459-diode-prune")
SOURCE=Path("/work/current-input.odb")
CATEGORY="NSSOC_NET459_TWO_DIODE_PRUNE_DRC"
drc.CATEGORY=CATEGORY
def save(name,v):(D/name).write_bytes(p.encode(v))
def filepin(path):return p.pin(path.read_bytes())
def q(path):
    value=str(path)
    assert value.startswith("/work/")and not any(x in value for x in("{}[]$\n\r\\"))
    return "{"+value+"}"
def target(db,b):
    proof=own.api_evidence();layers=own.named_layers(db.getTech(),proof);net=b.findNet("net459")
    assert net and not net.isSpecial()and not list(net.getSWires())
    projection=own.native_wire(db,b,net.getWire(),layers,proof)
    pins=[]
    for t in net.getITerms():
        i=t.getInst();m=i.getMaster()
        pins.append(dict(kind="iterm",scoped_identity=["iterm",i.getName(),t.getMTerm().getName()],
          instance=i.getName(),master=[m.getLib().getName(),m.getName()],terminal=t.getMTerm().getName(),
          geometries=[[l.getName(),own.box(r)]for l,r in t.getGeometries()]))
    return dict(scoped_identity=["net","net459"],wire_identity=["net","net459","wire"],
       metadata_class=str(net.getWireType()),sigtype=str(net.getSigType()),projection=projection,pins=pins)
def deletions(b):
    result=[];pins=[]
    for name in p.REMOVE:
        i=b.findInst(name);assert i is not None
        m=i.getMaster();assert [m.getLib().getName(),m.getName()]==["sg13g2_stdcell","sg13g2_antennanp"]
        terms=[]
        for t in i.getITerms():
            mt=t.getMTerm();net=t.getNet()
            row=dict(terminal=mt.getName(),sigtype=str(mt.getSigType()),io=str(mt.getIoType()),
                net=None if net is None else net.getName(),
                geometries=[[l.getName(),own.box(r)]for l,r in t.getGeometries()])
            assert row["terminal"]=="A"or row["sigtype"]in("POWER","GROUND")
            if row["terminal"]=="A":assert row["net"]=="net459"and row["sigtype"]=="SIGNAL"
            if net is not None:
                assert row["terminal"]=="A"or str(net.getSigType())in("POWER","GROUND")
                pins.append([name,row["terminal"],row["net"],row["sigtype"]])
            terms.append(row)
        assert sum(x["terminal"]=="A"for x in terms)==1
        assert sorted(x["terminal"]for x in terms)==sorted(t.getName()for t in m.getMTerms())
        result.append(dict(instance=name,master=[m.getLib().getName(),m.getName()],location=list(i.getLocation()),
          origin=list(i.getOrigin()),orientation=str(i.getOrient()),placement=str(i.getPlacementStatus()),terms=terms))
    return result,sorted(pins)
def snapshot(db,b,defpath,removed_pins,present):
    assert len(list(b.getNets()))==143820 and len(list(b.getInsts()))==(153130 if present else 153128)
    assert {x for x in p.REMOVE if b.findInst(x)is not None}==set(p.REMOVE if present else ())
    assert not list(b.getChildren())
    assert b.getDbUnitsPerMicron()==db.getTech().getDbUnitsPerMicron()==1000
    odb.write_def(b,str(defpath));raw=defpath.read_bytes();parsed=c.parse_def(raw)
    clocks=n.selected(b);assert len(clocks)==1691
    digests={k:hashlib.sha256()for k in("nets","raw-other-wires","instances","master-pins","clocks")}
    counts={}
    def feed(kind,row):
        encoded=c.canonical(row);digests[kind].update(len(encoded).to_bytes(8,"big"));digests[kind].update(encoded)
        counts[kind]=counts.get(kind,0)+1
    actual_removed=[]
    for net in sorted(b.getNets(),key=lambda x:x.getName()):
        ident=n.identity(db,net)
        for t in ident["terminals"]:
            if t[0]in p.REMOVE:actual_removed.append([t[0],t[1],net.getName(),t[-1]])
        ident["terminals"]=[t for t in ident["terminals"]if t[0]not in p.REMOVE]
        encoded=n.encoded(net)
        if net.getName()=="net459":
            assert encoded["wire_present"]and encoded["metadata"]=="ROUTED"
            assert len(encoded["paths"])==(71 if present else 43)and set(encoded["paths"])=={"ROUTED"}
            encoded=dict(wire_present=True,metadata="ROUTED",only_target_path_list_excluded=True)
        feed("nets",[ident,encoded])
        w=net.getWire()
        if net.getName()!="net459":
            feed("raw-other-wires",[net.getName(),None if w is None else [[w.getOpcode(i),w.getData(i)]for i in range(w.length())]])
    assert sorted(actual_removed)==(removed_pins if present else []),"exact connected terminal delta"
    masters={}
    for i in sorted(b.getInsts(),key=lambda x:x.getName()):
        m=i.getMaster();mk=(m.getLib().getName(),m.getName());masters[mk]=m
        if i.getName()not in p.REMOVE:
            feed("instances",[i.getName(),list(mk),list(i.getLocation()),list(i.getOrigin()),str(i.getOrient()),str(i.getPlacementStatus())])
    for key,m in sorted(masters.items()):
        for t in sorted(m.getMTerms(),key=lambda x:x.getName()):
            feed("master-pins",[list(key),t.getName(),str(t.getIoType()),str(t.getSigType()),[drc.master_pin_boxes(x)for x in t.getMPins()]])
    for name in sorted(clocks):feed("clocks",[name,parsed["records"][name].decode("ascii")])
    del parsed
    normalized=p.normalized_def(raw,removed_pins,p.REMOVE if present else ())
    return dict(counts=counts,digests={k:v.hexdigest()for k,v in digests.items()},
      normalized_def_sha256=normalized["sha256"],normalized_def_delta=normalized,
      immutable_material=own.immutable_material(db,b),clock_names=sorted(clocks),
      raw_def=filepin(defpath),actual_instances=153130 if present else 153128,net_count=143820)
def equal_snapshot(actual,base):
    for k in("counts","digests","normalized_def_sha256","immutable_material","clock_names","net_count"):
        assert actual[k]==base[k],("full remaining-chip invariant",k)
def check_target(actual,plan):
    projected=actual["projection"]
    assert actual["sigtype"]=="SIGNAL"and actual["metadata_class"]=="ROUTED"
    assert p.material(projected["shapes"])==p.material(plan["retained_shapes"]),"complete retained geometry"
    assert len(projected["shapes"])==85
    key=lambda x:tuple(x["scoped_identity"])
    assert sorted(actual["pins"],key=key)==sorted(plan["retained_pins"],key=key),"three exact retained pins"
    observations={}
    for mode in("positive_area","closed_boundary"):
        r=graph.observe(projected["shapes"],actual["pins"],mode)
        assert r["all_pins_share_one_wire_component"]and r["all_wire_material_one_component"]
        assert all(len(x["wire_components"])==1 for x in r["pins"])
        observations[mode]=r
    return observations
def antenna_tcl(source,label,with_drc=False):
    out=W/(label+"-ant-counts.json")
    text="read_db "+q(source)+"\nset_thread_count 2\nwrite_def "+q(W/(label+"-before.def"))+"\n"
    if with_drc:
        text+="drt::check_drc -output_file "+q(W/"initial-drc.rpt")+" -marker_name "+CATEGORY+"\n"
    text+="check_antennas -verbose -report_file "+q(W/(label+"-net459-antenna.rpt"))+" -net net459\n"
    text+="set net_count [ant::antenna_violation_count]\nset net_violation [ant::check_net_violation net459]\n"
    text+="check_antennas -verbose -report_file "+q(W/(label+"-full-antenna.rpt"))+"\n"
    text+="set full_count [ant::antenna_violation_count]\n"
    text+="set out [open "+q(out)+" w]\n"
    text+='puts $out [format {{"net459_count":%d,"net459_violation":%d,"full_count":%d}} $net_count $net_violation $full_count]\nclose $out\n'
    text+="write_def "+q(W/(label+"-after.def"))+"\n"
    if with_drc:text+="write_db "+q(W/"candidate-measured.odb")+"\n"
    return text
def prepare():
    assert filepin(SOURCE)==p.INPUT
    authentic,proof=graph.source_guard();plan=p.plan(authentic);save("plan.json",plan)
    db,b=n.load(SOURCE)
    try:
        assert b.findMarkerCategory(CATEGORY)is None
        actual=target(db,b)
        assert json.loads(p.encode(actual))==authentic,"actual current native target differs"
        rows,pins=deletions(b);save("deleted-instance-inventory.json",dict(instances=rows,connected_pins=pins))
        base=snapshot(db,b,W/"before.def",pins,True);save("baseline-snapshot.json",base)
        for name in p.REMOVE:odb.dbInst.destroy(b.findInst(name))
        # Instance deletion alone must preserve all original route material.
        after=target(db,b)
        assert after["projection"]==actual["projection"]
        assert {tuple(x["scoped_identity"][1:])for x in after["pins"]}==p.KEEP_PINS
        odb.write_def(b,str(W/"pruned-instances.def"))
        odb.write_db(db,str(W/"pruned-instances.odb"))
    finally:odb.dbDatabase.destroy(db)
    raw=(W/"pruned-instances.def").read_bytes();record=c.parse_def(raw)["records"]["net459"]
    pruned=p.prune_record(record,plan["keep_paths"],71)
    patch,removed=c.patch_def(raw,{"net459":pruned});assert removed==3
    (W/"target-patch.def").write_bytes(patch)
    tcl="read_db "+q(W/"pruned-instances.odb")+"\n"
    for suffix in("single","double"):
        tcl+="read_def -floorplan_initialize "+q(W/"target-patch.def")+"\nwrite_def "+q(W/("candidate-"+suffix+".def"))+"\n"
    tcl+="write_db "+q(W/"candidate.odb")+"\n"
    (W/"import.tcl").write_text(tcl)
    (W/"baseline-ant.tcl").write_text(antenna_tcl(SOURCE,"baseline"))
    (W/"candidate-check.tcl").write_text(antenna_tcl(W/"candidate.odb","candidate",True))
    save("prepare-result.json",dict(status="PREPARED_EXACT_BRANCH_AND_TWO_DIODE_CANDIDATE",
        baseline=base["raw_def"],removed_instances=rows,connected_terminal_delta=pins,
        target_patch=filepin(W/"target-patch.def"),remaining_pins=3,expected_instances=153128,
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
def audit(measured):
    pins=json.loads((D/"deleted-instance-inventory.json").read_bytes())["connected_pins"]
    base=json.loads((D/"baseline-snapshot.json").read_bytes());plan=json.loads((D/"plan.json").read_bytes())
    name="candidate-measured.odb"if measured else"candidate.odb"
    db,b=n.load(W/name)
    try:
        actual=snapshot(db,b,W/("audit-"+name+".def"),pins,False);equal_snapshot(actual,base)
        observations=check_target(target(db,b),plan)
        save("measured-target.json"if measured else"imported-target.json",observations)
        save("measured-snapshot.json"if measured else"imported-snapshot.json",actual)
        if measured:
            category=b.findMarkerCategory(CATEGORY);assert category is not None
            category.writeJSON(str(D/"drc-markers.json"))
            measurement=drc.measure_report(category,W/"initial-drc.rpt",W/"reread-drc.rpt",D/"drc-markers.json")
            antenna={}
            for label in("baseline","candidate"):
                assert (W/(label+"-before.def")).read_bytes()==(W/(label+"-after.def")).read_bytes(),"checker changed DEF"
                a=json.loads((W/(label+"-ant-counts.json")).read_bytes())
                assert set(a)=={"net459_count","net459_violation","full_count"}
                assert all(type(v)is int and v>=0 for v in a.values())
                for kind in("net459","full"):
                    path=W/(label+"-"+kind+"-antenna.rpt");assert path.is_file()
                    (D/path.name).write_bytes(path.read_bytes())
                antenna[label]=a
            passed=measurement["marker_count"]==0 and all(v==0 for v in antenna["candidate"].values())
            save("result.json",dict(status="COMPLETE_BOUNDED_CANDIDATE_CHECKS",
              bounded_candidate_checks_passed=passed,candidate_rejected=not passed,
              input=p.INPUT,candidate=filepin(W/name),measurement=measurement,antenna=antenna,
              exact_remaining_chip_preserved=True,all_1691_original_clocks_preserved=True,
              explicit_two_instance_delta=True,retained_wire_shapes=85,remaining_target_pins=3,
              physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
              scope="DRT plus native antenna/connection checks only; full chip LVS, foundry DRC and final original timing remain required."))
    finally:odb.dbDatabase.destroy(db)
def main():
    assert not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN"))
    p.source_guard();D.mkdir(exist_ok=True);W.mkdir(parents=True,exist_ok=True)
    phase=os.environ["NSSOC_NET459_PRUNE_PHASE"];assert phase in("prepare","audit-import","audit-measured")
    error=None
    try:
        if phase=="prepare":prepare()
        else:audit(phase=="audit-measured")
    except BaseException as exc:
        error=exc;save(phase+"-failure.json",dict(error=repr(exc),physical_acceptance=False));raise
    finally:
        assert filepin(SOURCE)==p.INPUT,"current input modified"
        save(phase+"-terminal.json",dict(phase=phase,complete=error is None,error=None if error is None else repr(error),
          source_input_unchanged=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
if __name__=="__main__":main()
