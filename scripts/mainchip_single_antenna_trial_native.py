#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One existing signal net, one new diode, additive Metal1 branch, full delta audit."""
import hashlib,json,os,sys,traceback
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_single_antenna_trial as p
import mainchip_net459_connectivity as graph
import mainchip_two_signal_ownership_native as own
import mainchip_original_clock_restoration_native as n
import mainchip_original_clock_drc as drc
import mainchip_original_clock_restoration as c
import mainchip_full_antenna_report as ant
D=Path("/work/out/single-antenna-trial")
W=Path("/work/out/work/single-antenna-trial")
SOURCE=Path("/work/current-input.odb")
CATEGORY="NSSOC_SINGLE_ANTENNA_TRIAL_DRC"
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
def snapshot(db,b,defpath,removed_pins,present):
    assert len(list(b.getNets()))==143820 and len(list(b.getInsts()))==(153129 if present else 153128)
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
        if net.getName()==p.NET:
            assert encoded["wire_present"]and encoded["metadata"]=="ROUTED"
            assert encoded["paths"]and set(encoded["paths"])=={"ROUTED"}
            encoded=dict(wire_present=True,metadata="ROUTED",only_target_path_list_excluded=True)
        feed("nets",[ident,encoded])
        w=net.getWire()
        if net.getName()!=p.NET:
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
      raw_def=filepin(defpath),actual_instances=153129 if present else 153128,net_count=143820)
def equal_snapshot(actual,base):
    for k in("counts","digests","normalized_def_sha256","immutable_material","clock_names","net_count"):
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
    if with_drc:
        text+="check_antennas -verbose -report_file "+q(W/"candidate-full-antenna.rpt")+"\nset full_count [ant::antenna_violation_count]\n"
    else:text+="set full_count -1\n"
    text+="set out [open "+q(out)+" w]\n"
    text+='puts $out [format {{"target_count":%d,"target_violation":%d,"full_count":%d}} $target_count $target_violation $full_count]\nclose $out\n'
    text+="write_def "+q(W/(label+"-after.def"))+"\n"
    if with_drc:text+="write_db "+q(W/"candidate-measured.odb")+"\n"
    return text
def prepare():
    assert filepin(SOURCE)==p.INPUT
    db,b=n.load(SOURCE)
    try:
        assert b.findInst(p.NEW)is None and b.findMarkerCategory(CATEGORY)is None
        actual=target(db,b);assert len(actual["projection"]["shapes"])==40
        assert not list(b.findNet(p.NET).getBTerms()),"unexpected target block terminals"
        assert not any(str(t.getInst().getMaster().getType())=="CORE_ANTENNACELL"for t in b.findNet(p.NET).getITerms())
        save("baseline-target.json",actual);save("baseline-connectivity.json",connection_checks(actual))
        base=snapshot(db,b,W/"before.def",[],False);save("baseline-snapshot.json",base)
        sink=b.findInst(p.SINK[0]);assert sink and sink.getMaster().getName()=="sg13g2_buf_1"
        st=sink.findITerm(p.SINK[1]);assert st and st.getNet().getName()==p.NET
        bbox=own.box(sink.getBBox());sgeom=[own.box(r)for l,r in st.getGeometries()if l.getName()=="Metal1"]
        assert sgeom,"sink has no actual Metal1 pin"
        template=b.findInst("ANTENNA_1573");assert template is not None
        master=template.getMaster();assert master.getName()=="sg13g2_antennanp"and str(master.getType())=="CORE_ANTENNACELL"
        size=[master.getWidth(),master.getHeight()]
        rows=[]
        for r in b.getRows():
            rb=own.box(r.getBBox())
            if rb[1]!=bbox[1]:continue
            site=r.getSite()
            rows.append(dict(name=r.getName(),box=rb,origin=point(r.getOrigin()),orientation=str(r.getOrient()),
              direction=str(r.getDirection()),count=r.getSiteCount(),spacing=r.getSpacing(),
              site=[site.getLib().getName(),site.getName()],site_width=site.getWidth(),site_height=site.getHeight()))
        occupied=[dict(name=i.getName(),box=own.box(i.getBBox()))for i in b.getInsts()]
        nearby=[v for v in occupied if v["box"][0]<bbox[2]+40000 and v["box"][2]>bbox[0]-40000 and v["box"][1]<bbox[3]and v["box"][3]>bbox[1]]
        sites=p.legal_sites(rows,occupied,size,bbox)
        save("placement-context.json",dict(sink_box=bbox,sink_Metal1=sgeom,diode_size=size,rows=rows,all_nearby_occupied_instances=nearby,legal_sites=sites,
          selection="Nearest nonoverlapping complete-site same-row location within40um; other instances never moved. Native DRC remains mandatory."))
        assert sites,"no legal untouched same-row site in40um"
        site=sites[0];inst=odb.dbInst.create(b,master,p.NEW);assert inst is not None
        inst.setOrient(site["orientation"]);inst.setLocation(*site["location"]);inst.setPlacementStatus("PLACED")
        assert own.box(inst.getBBox())==site["box"]
        pins=[]
        for t in inst.getITerms():
            mt=t.getMTerm();name=mt.getName();sig=str(mt.getSigType())
            if name=="A":assert sig=="SIGNAL";net=b.findNet(p.NET)
            else:
                assert sig in("POWER","GROUND"),("unexpected diode terminal",name,sig)
                original=template.findITerm(name);assert original is not None
                net=original.getNet();assert net is not None and str(net.getSigType())==sig
            t.connect(net);pins.append([p.NEW,name,net.getName(),sig])
        pins.sort();assert sum(q[1]=="A"for q in pins)==1
        mt=master.findMTerm("A");areas=mt.getDiffArea()
        assert areas and max(float(q[0])for q in areas)==2.0154
        dgeom=[own.box(r)for l,r in inst.findITerm("A").getGeometries()if l.getName()=="Metal1"];assert dgeom
        width=db.getTech().findLayer("Metal1").getWidth();assert width==160
        choices=[]
        for sg in sgeom:
            for dg in dgeom:
                points=p.branch(sg,dg,width);distance=sum(abs(x[0]-y[0])+abs(x[1]-y[1])for x,y in zip(points,points[1:]))
                choices.append((distance,points,sg,dg))
        distance,points,sg,dg=min(choices)
        plan=dict(site=site,connected_pins=pins,points=points,width=width,expected_branch_boxes=p.branch_boxes(points,width),distance=distance,
          sink_Metal1=sg,diode_Metal1=dg,only_added_instance=p.NEW,only_changed_signal_net=p.NET,
          original_shape_count=40,diode_diffusion_area=2.0154,patch_connected_terminals=len(actual["pins"])+1)
        save("plan.json",plan)
        candidate=snapshot(db,b,W/"inserted.def",pins,True);equal_snapshot(candidate,base)
        assert target(db,b)["projection"]==actual["projection"],"instance insertion altered existing route"
        odb.write_db(db,str(W/"inserted.odb"))
    finally:odb.dbDatabase.destroy(db)
    raw=(W/"inserted.def").read_bytes();record=c.parse_def(raw)["records"][p.NET]
    patched=p.append_branch(record,plan["points"]);patch,removed=c.patch_def(raw,{p.NET:patched});assert removed==plan["patch_connected_terminals"]
    (W/"target-patch.def").write_bytes(patch)
    text="read_db "+q(W/"inserted.odb")+"\n"
    for suffix in("single","double"):text+="read_def -floorplan_initialize "+q(W/"target-patch.def")+"\nwrite_def "+q(W/("candidate-"+suffix+".def"))+"\n"
    text+="write_db "+q(W/"candidate.odb")+"\n"
    (W/"import.tcl").write_text(text)
    (W/"baseline-ant.tcl").write_text(antenna_tcl(SOURCE,"baseline"))
    (W/"candidate-check.tcl").write_text(antenna_tcl(W/"candidate.odb","candidate",True))
    save("prepare-result.json",dict(status="PREPARED_ONE_DIODE_AND_M1_BRANCH",plan=plan,source_input_unchanged=True,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
def audit(measured):
    plan=json.loads((D/"plan.json").read_bytes());base=json.loads((D/"baseline-snapshot.json").read_bytes())
    old=json.loads((D/"baseline-target.json").read_bytes());name="candidate-measured.odb"if measured else"candidate.odb"
    db,b=n.load(W/name)
    try:
        snap=snapshot(db,b,W/("audit-"+name+".def"),plan["connected_pins"],True);equal_snapshot(snap,base)
        inst=b.findInst(p.NEW);assert own.box(inst.getBBox())==plan["site"]["box"]and str(inst.getOrient())==plan["site"]["orientation"]
        actual=target(db,b);oldshape=old["projection"]["shapes"];shapes=actual["projection"]["shapes"]
        material=lambda seq:[{k:v for k,v in x.items()if k!="opcode_index"}for x in seq]
        assert material(shapes[:40])==material(oldshape),"preexisting target route changed"
        extra=shapes[40:];assert len(extra)==len(plan["expected_branch_boxes"])
        assert all(x["kind"]=="wire"and x["layer"]=="Metal1"for x in extra)
        assert [x["box"]for x in extra]==plan["expected_branch_boxes"],"undeclared added route"
        origpins=[x for x in actual["pins"]if x["instance"]!=p.NEW];key=lambda x:tuple(x["scoped_identity"])
        assert sorted(origpins,key=key)==sorted(old["pins"],key=key),"original target pins changed"
        newpins=[x for x in actual["pins"]if x["instance"]==p.NEW];assert len(newpins)==1 and newpins[0]["terminal"]=="A"
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
        assert counts["baseline"]==dict(target_count=1,target_violation=1,full_count=-1),"baseline target violation changed"
        authentic=json.loads((p.ROOT/p.VIOLATIONS).read_bytes());expected=[ant.semantics(x)for x in authentic if x["net"]!=p.NET]
        with (W/"baseline-target-antenna.rpt").open()as f:bs,bn,bv=ant.parse(f,1)
        assert [ant.semantics(x)for x in bv]==[ant.semantics(x)for x in authentic if x["net"]==p.NET]
        with (W/"candidate-full-antenna.rpt").open()as f:summary,nets,violations=ant.parse(f,counts["candidate"]["full_count"])
        save("candidate-antenna-summary.json",summary);save("candidate-antenna-violations.json",violations);save("candidate-antenna-net-census.json",nets)
        other=[ant.semantics(x)for x in violations if x["net"]!=p.NET];assert other==expected,"other antenna violations changed"
        target_rows=[x for x in violations if x["net"]==p.NET]
        passed=measurement["marker_count"]==0 and counts["candidate"]["target_count"]==counts["candidate"]["target_violation"]==0 and not target_rows
        save("result.json",dict(status="COMPLETE_SINGLE_ANTENNA_TRIAL_CHECKS",bounded_trial_passed=passed,candidate_rejected=not passed,
          input=p.INPUT,candidate=filepin(W/name),measurement=measurement,antenna=counts,candidate_antenna_summary=summary,
          exact_remaining_chip_preserved=True,all_1691_original_clocks_preserved=True,original_target_wire_shapes_preserved=40,
          new_instances=1,new_signal_connections=1,added_branch_boxes=plan["expected_branch_boxes"],other_violation_semantics_unchanged=True,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
          scope="Single physical repair trial only; current full-chip LVS/foundryDRC/RC and original setup/hold remain required."))
    finally:odb.dbDatabase.destroy(db)
def main():
    assert not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN"))
    p.source_guard();D.mkdir(exist_ok=True);W.mkdir(parents=True,exist_ok=True);error=None
    phase=os.environ["NSSOC_SINGLE_ANTENNA_PHASE"];assert phase in("prepare","audit-import","audit-measured")
    try:
        if phase=="prepare":prepare()
        else:audit(phase=="audit-measured")
    except BaseException as exc:error=exc;save(phase+"-failure.json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
    finally:
        assert filepin(SOURCE)==p.INPUT
        save(phase+"-terminal.json",dict(phase=phase,complete=error is None,error=None if error is None else repr(error),input_unchanged=True,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
if __name__=="__main__":main()
