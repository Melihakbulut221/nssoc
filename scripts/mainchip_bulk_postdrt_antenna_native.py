#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native phases for one bulk diode cycle. Future owned runner only."""
import hashlib,json,os,sys
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna as p
import mainchip_original_clock_restoration as c
import mainchip_original_clock_restoration_native as n
import mainchip_two_signal_ownership_native as own
import mainchip_original_clock_drc as drc
import mainchip_full_antenna_report as ant
import mainchip_net459_connectivity as graph
import mainchip_fixed_clock_signal_repair as router
CATEGORY="NSSOC_ONE_BULK_POSTDRT_ANTENNA_DRC"
drc.CATEGORY=CATEGORY

def q(value):
    value=str(value)
    p.require(value.startswith("/work/")and not any(x in value for x in "{}[]$\n\r\\"),"owned Tcl path")
    return "{"+value+"}"

def fp(path):return p.pin(c.regular(path).read_bytes())
def save(path,value):path.write_bytes(p.encode(value))
def point(value):return list(value)if isinstance(value,(tuple,list))else[value.x(),value.y()]

def pin_row(t):
    net=t.getNet();m=t.getMTerm()
    return dict(net=None if net is None else net.getName(),sigtype=str(m.getSigType()),io=str(m.getIoType()))

def snapshot(path,out,protected=None):
    db,b=n.load(path)
    try:
        p.require(not list(b.getChildren()),"no hidden child blocks")
        p.require(len(list(b.getNets()))==143820,"complete net census")
        if protected is None:
            protected=sorted(n.selected(b));p.require(len(protected)==1691,"original1691 census")
        nets={};instances={};masters={}
        for net in sorted(b.getNets(),key=lambda x:x.getName()):
            wire=net.getWire()
            raw=None if wire is None else[[wire.getOpcode(i),wire.getData(i)]for i in range(wire.length())]
            nets[net.getName()]=dict(identity=n.identity(db,net),encoded=n.encoded(net),
              wire=dict(pin=p.pin(p.encode(raw)),opcode_count=0 if raw is None else len(raw)))
        for inst in sorted(b.getInsts(),key=lambda x:x.getName()):
            m=inst.getMaster();key=m.getLib().getName()+"/"+m.getName()
            instances[inst.getName()]=dict(master=[m.getLib().getName(),m.getName()],master_type=str(m.getType()),
              location=list(inst.getLocation()),origin=list(inst.getOrigin()),orientation=str(inst.getOrient()),
              status=str(inst.getPlacementStatus()),pins={t.getMTerm().getName():pin_row(t)for t in inst.getITerms()})
            if key not in masters:
                masters[key]=dict(width=m.getWidth(),height=m.getHeight(),type=str(m.getType()),
                  pins={t.getName():dict(io=str(t.getIoType()),sigtype=str(t.getSigType()),
                    boxes=[drc.master_pin_boxes(x)for x in t.getMPins()])for t in m.getMTerms()})
        template=instances.get("ANTENNA_1573")
        p.require(template is not None and template["master"][1]==p.DIODE,"existing qualified diode template")
        rows=[dict(name=r.getName(),box=own.box(r.getBBox()),origin=point(r.getOrigin()),orientation=str(r.getOrient()),
          direction=str(r.getDirection()),count=r.getSiteCount(),spacing=r.getSpacing(),
          site=[r.getSite().getLib().getName(),r.getSite().getName()],
          width=r.getSite().getWidth(),height=r.getSite().getHeight())for r in b.getRows()]
        result=dict(nets=nets,instances=instances,masters=masters,protected=protected,
          block=dict(name=b.getName(),dbu=b.getDbUnitsPerMicron(),tech_dbu=db.getTech().getDbUnitsPerMicron(),rows=rows),
          immutable=own.immutable_material(db,b),diode_template=template)
        odb.write_def(b,str(out));result["def_pin"]=fp(out)
        parsed=c.parse_def(out.read_bytes())
        result["clock_record_pins"]={name:p.pin(parsed["records"][name])for name in protected}
        return result
    finally:odb.dbDatabase.destroy(db)

def setting_prefix(source,environment,original):
    p.require(fp(environment)["sha256"]==router.GLOBAL_INPUTS[router.GLOBAL_PREFIX+"_env.tcl"],"original environment")
    router.exact_setup(c.regular(original).read_bytes())
    guards="".join('if {![info exists ::env('+k+')] || $::env('+k+') ne "'+v+'"} {error "Original setting '+k+' differs"}\n'
      for k,v in router.SETTINGS.items())
    return "source "+q(environment)+"\n"+guards+"read_db "+q(source)+"\n"+router.LAYERS+"\nset_thread_count 2\n"

def repair_tcl(source,environment,original,work):
    """Metadata shim does not change dbWire path classes or run detailed_route."""
    text=setting_prefix(source,environment,original)
    text+=r'''
set block [ord::get_db_block]
set metadata_restore {}
set instance_restore {}
foreach net [$block getNets] {
  if {[$net getWireType] eq "FIXED" && [$net getWire] ne "NULL"} {
    lappend metadata_restore [list $net [$net getWire]]
  }
}
foreach inst [$block getInsts] {
  lappend instance_restore [list $inst [$inst getPlacementStatus]]
}
set primary_code [catch {
  foreach pair $metadata_restore { [lindex $pair 0] setWireType ROUTED }
  puts NSSOC_BULK_REPAIR_BEGIN
  set inserted [repair_antennas sg13g2_antennanp -iterations 1 -ratio_margin 10 -diode_only]
  puts "NSSOC_BULK_REPAIR_RETURNED $inserted"
} primary_result primary_options]
set cleanup_errors {}
foreach pair $metadata_restore {
  set net [lindex $pair 0]
  if {[catch {
    $net setWireType FIXED
    if {[$net getWire] ne [lindex $pair 1]} {error "fixed wire object replaced"}
    if {[$net getWireType] ne "FIXED"} {error "fixed metadata not restored"}
  } cleanup]} {lappend cleanup_errors $cleanup}
}
foreach pair $instance_restore {
  if {[catch {[lindex $pair 0] setPlacementStatus [lindex $pair 1]} cleanup]} {
    lappend cleanup_errors $cleanup
  }
}
'''
    for command,path in (("write_def",work/"insertion-after-shim.def"),("write_db",work/"insertion-after-shim.odb")):
        text+="if {[catch {"+command+" "+q(path)+"} cleanup]} {lappend cleanup_errors $cleanup}\n"
    text+='puts "NSSOC_BULK_ANTENNA_METADATA_RESTORE_ERRORS $cleanup_errors"\n'
    text+='if {$primary_code} {return -options $primary_options $primary_result}\n'
    text+='if {[llength $cleanup_errors]} {error "antenna cleanup failed: $cleanup_errors"}\n'
    return text

def check_tcl(source,label,work):
    p.require(label in("baseline","final"),"check label")
    text="read_db "+q(source)+"\nset_thread_count 2\nwrite_def "+q(work/(label+"-check-before.def"))+"\n"
    text+="drt::check_drc -output_file "+q(work/(label+"-drc.rpt"))+" -marker_name "+CATEGORY+"\n"
    text+="check_antennas -verbose -report_file "+q(work/(label+"-full-antenna.rpt"))+"\n"
    text+="set count [ant::antenna_violation_count]\nset routed [design_is_routed]\n"
    text+="set out [open "+q(work/(label+"-counts.json"))+" w]\n"
    text+='puts $out [format {{"full_count":%d,"design_is_routed":%d}} $count $routed]\nclose $out\n'
    text+="write_def "+q(work/(label+"-check-after.def"))+"\nwrite_db "+q(work/(label+"-measured.odb"))+"\n"
    return text

def collect_checks(label,work,out):
    p.require((work/(label+"-check-before.def")).read_bytes()==(work/(label+"-check-after.def")).read_bytes(),"read-only checker DEF")
    counts=json.loads(c.regular(work/(label+"-counts.json")).read_bytes())
    p.require(type(counts["full_count"])is int and counts["full_count"]>=0,"native full count")
    p.require(counts["design_is_routed"]in(0,1),"native routed result")
    with c.regular(work/(label+"-full-antenna.rpt")).open()as f:
        summary,nets,violations=ant.parse(f,counts["full_count"])
    save(out/(label+"-antenna-summary.json"),summary);save(out/(label+"-antenna-nets.json"),nets)
    save(out/(label+"-antenna-violations.json"),violations)
    db,b=n.load(work/(label+"-measured.odb"))
    try:
        category=b.findMarkerCategory(CATEGORY);p.require(category is not None,"DRT category")
        markers=out/(label+"-drc-markers.json");category.writeJSON(str(markers))
        measurement=drc.measure_report(category,work/(label+"-drc.rpt"),work/(label+"-drc-reread.rpt"),markers)
    finally:odb.dbDatabase.destroy(db)
    save(out/(label+"-drc.json"),measurement)
    return dict(net_count=counts["full_count"],violations=violations,design_is_routed=counts["design_is_routed"]),measurement

def connect_new_pg(source,destination,before):
    db,b=n.load(source)
    try:
        added=sorted(set(i.getName()for i in b.getInsts())-set(before["instances"]))
        p.require(added,"no inserted diode")
        template=b.findInst("ANTENNA_1573");p.require(template is not None,"PG template")
        proof=[]
        for name in added:
            inst=b.findInst(name)
            p.require(inst.getMaster()==template.getMaster(),"only exact existing diode master")
            for term in inst.getITerms():
                mt=term.getMTerm();terminal=mt.getName()
                if terminal=="A":
                    net=term.getNet();p.require(net is not None and net.getName()not in before["protected"],"protected diode")
                    continue
                p.require(str(mt.getSigType())in("POWER","GROUND"),"unexpected diode pin")
                ref=template.findITerm(terminal);p.require(ref is not None and ref.getNet()is not None,"PG template net")
                p.require(term.getNet()is None or term.getNet()==ref.getNet(),"wrong existing new PG")
                term.connect(ref.getNet());proof.append([name,terminal,ref.getNet().getName(),str(mt.getSigType())])
        odb.write_db(db,str(destination));return proof
    finally:odb.dbDatabase.destroy(db)

def metadata_only(source,destination,targets):
    db,b=n.load(source)
    try:
        before={n0.getName():n.encoded(n0)for n0 in b.getNets()}
        raw={n0.getName():None if n0.getWire()is None else
          [[n0.getWire().getOpcode(i),n0.getWire().getData(i)]for i in range(n0.getWire().length())]for n0 in b.getNets()}
        p.require(set(targets)<=set(before),"metadata target ownership")
        for name,kind in targets.items():b.findNet(name).setWireType(kind)
        after={n0.getName():n.encoded(n0)for n0 in b.getNets()}
        wanted={name:targets.get(name,row["metadata"])for name,row in before.items()}
        c.validate_metadata_transition(after,before,wanted)
        for net in b.getNets():
            w=net.getWire();actual=None if w is None else[[w.getOpcode(i),w.getData(i)]for i in range(w.length())]
            p.exact(actual,raw[net.getName()],"metadata setter changed wire opcodes")
        odb.write_db(db,str(destination))
    finally:odb.dbDatabase.destroy(db)

def make_overlay(work,out):
    raw=c.regular(work/"insertion.def").read_bytes();plan=json.loads(c.regular(out/"insertion-plan.json").read_bytes())
    expected,classes=p.fixed_plan(raw,plan["mutable_nets"])
    (work/"fixed-expected.def").write_bytes(expected);save(out/"drt-original-classes.json",classes)
    records=c.parse_def(expected)["records"]
    patch,_=c.patch_def(raw,{name:records[name]for name,kind in classes.items()if kind is not None})
    (work/"fixed-patch.def").write_bytes(patch)
    metadata_only(work/"insertion-connected.odb",work/"fixed-base.odb",{name:"FIXED"for name,kind in classes.items()if kind is not None})
    (work/"fixed-import.tcl").write_text(n.import_tcl(work/"fixed-base.odb",work/"fixed-patch.def",work,"fixed"))

def route_tcl(work,environment,original):
    raw=router.route_tcl(work/"fixed.odb",environment,work,c.regular(original).read_bytes(),q)
    start=raw.index("detailed_route {*}$drt_args");end=raw.index("\nwrite_def ",start);call=raw[start:end]
    p.require(raw.count(call)==1 and raw.count("detailed_route ")==1,"single original router call")
    tail=raw[end:]
    expected='\nwrite_def '+q(work/'routed-fixed.def')+'\nwrite_db '+q(work/'routed-fixed.odb')+'\nputs NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED\nexit\n'
    p.exact(tail,expected,"original route tail")
    replacement="set route_code [catch {"+call+"} route_result route_options]\nset save_errors {}\n"
    for command,path in (("write_def",work/"route-partial.def"),("write_db",work/"route-partial.odb")):
        replacement+="if {[catch {"+command+" "+q(path)+"} save_error]} {lappend save_errors $save_error}\n"
    replacement+='if {$route_code} {puts stderr "NSSOC_BULK_ROUTE_SAVE_ERRORS $save_errors"; return -options $route_options $route_result}\n'
    replacement+='if {[llength $save_errors]} {error "route output preservation: $save_errors"}\n'
    return raw[:start]+replacement+tail

def restore_plan(work,out,failure=False):
    classes=json.loads(c.regular(out/"drt-original-classes.json").read_bytes())
    options=(work/"routed-fixed.odb",work/"route-partial.odb",work/"fixed.odb")
    source=next((x for x in options if x.is_file()),None)
    p.require(source is not None,"no owned state available for class restoration")
    if not failure:p.require(source==options[0],"successful route output required")
    snapshot(source,work/"restore-source.def",json.loads((out/"baseline-snapshot.json").read_bytes())["protected"])
    raw=(work/"restore-source.def").read_bytes();expected=c.restore_classes(raw,classes)
    (work/"restored-expected.def").write_bytes(expected);parsed=c.parse_def(expected)
    patch,_=c.patch_def(raw,{name:parsed["records"][name]for name,kind in classes.items()if kind is not None})
    (work/"restore-patch.def").write_bytes(patch);original=json.loads((out/"insertion-snapshot.json").read_bytes())
    targets={name:original["nets"][name]["encoded"]["metadata"]for name in classes}
    metadata_only(source,work/"restore-base.odb",targets)
    (work/"restore.tcl").write_text(n.import_tcl(work/"restore-base.odb",work/"restore-patch.def",work,"candidate"))
    save(out/"class-restoration-plan.json",dict(source=str(source),source_pin=fp(source),
      failure_cleanup=failure,used_pre_route_fallback=source==options[-1],classes=classes,**p.FLAGS))


def preserve_owned_routes(path,plan,out,label):
    """Complete raw operands, catalogs, shapes and current terminal identities for every changed owner."""
    db,b=n.load(path)
    try:
        proof=own.api_evidence();layers=own.named_layers(db.getTech(),proof);index={}
        for name in plan["mutable_nets"]:
            net=b.findNet(name);p.require(net is not None and net.getWire()is not None,"owned native wire")
            observation=dict(net=name,identity=n.identity(db,net),encoded=n.encoded(net),
              projection=own.native_wire(db,b,net.getWire(),layers,proof))
            filename=label+"-owned-route-"+hashlib.sha256(name.encode()).hexdigest()+".json"
            save(out/filename,observation);index[name]=dict(path=filename,**fp(out/filename))
        save(out/(label+"-owned-route-index.json"),index)
        p.exact(sorted(index),sorted(plan["mutable_nets"]),"full owned-route observation index")
        return index
    finally:odb.dbDatabase.destroy(db)

def connectivity(path,plan,out):
    db,b=n.load(path)
    try:
        proof=own.api_evidence();layers=own.named_layers(db.getTech(),proof);result={}
        for name in plan["mutable_nets"]:
            net=b.findNet(name)
            p.require(net is not None and not net.isSpecial()and not list(net.getSWires()),"ordinary changed signal")
            p.require(not list(net.getBTerms()),"changed-net BTerm graph requires separate qualification")
            projection=own.native_wire(db,b,net.getWire(),layers,proof);pins=[]
            for term in net.getITerms():
                inst=term.getInst()
                pins.append(dict(kind="iterm",scoped_identity=["iterm",inst.getName(),term.getMTerm().getName()],
                  geometries=[[layer.getName(),own.box(rect)]for layer,rect in term.getGeometries()]))
            modes={mode:graph.observe(projection["shapes"],pins,mode)for mode in("positive_area","closed_boundary")}
            save(out/("connectivity-"+hashlib.sha256(name.encode()).hexdigest()+".json"),dict(net=name,projection=projection,modes=modes))
            result[name]=modes
        return p.validate_connectivity(result,plan)
    finally:odb.dbDatabase.destroy(db)

def phase(args):
    work=args.work;out=args.out;source=args.input
    def read(name):return json.loads(c.regular(out/name).read_bytes())
    if args.phase=="prepare":
        p.exact(fp(source),p.INPUT,"current input");p.require(fp(args.donor)["sha256"]==c.DONOR_SHA,"original1691 donor")
        base=snapshot(source,work/"baseline.def");p.require(len(base["instances"])==153129,"original instance count")
        save(out/"baseline-snapshot.json",base);(work/"baseline-check.tcl").write_text(check_tcl(source,"baseline",work))
    elif args.phase=="baseline-audit":
        antenna,measurement=collect_checks("baseline",work,out)
        authentic=json.loads(c.regular(p.ROOT/p.PROOF["violations"]).read_bytes())
        p.exact(sorted([ant.semantics(v)for v in antenna["violations"]],key=p.encode),
          sorted([ant.semantics(v)for v in authentic],key=p.encode),"authentic608 baseline")
        p.require(antenna["net_count"]==608 and len(antenna["violations"])==915 and measurement["marker_count"]==0,"current baseline gates")
        p.require(antenna["design_is_routed"]==1,"current baseline routed")
        base=read("baseline-snapshot.json")
        p.require(not(set(base["protected"])&{v["net"]for v in antenna["violations"]}),"protected net already violates")
        (work/"repair.tcl").write_text(repair_tcl(source,args.environment,args.original_tcl,work))
    elif args.phase=="insertion-audit":
        base=read("baseline-snapshot.json")
        raw=snapshot(work/"insertion-after-shim.odb",work/"insertion-before-pg.def",base["protected"])
        save(out/"insertion-before-pg-snapshot.json",raw)
        pg=connect_new_pg(work/"insertion-after-shim.odb",work/"insertion-connected.odb",base);save(out/"new-diode-pg.json",pg)
        inserted=snapshot(work/"insertion-connected.odb",work/"insertion.def",base["protected"]);save(out/"insertion-snapshot.json",inserted)
        p.exact(inserted["clock_record_pins"],base["clock_record_pins"],"original1691 insertion records")
        plan=p.admit_insertions(base,inserted,base["protected"],read("baseline-antenna-violations.json"))
        save(out/"insertion-plan.json",plan)
        save(out/"insertion-def-delta.json",p.insertion_def_delta((work/"baseline.def").read_bytes(),
          (work/"insertion.def").read_bytes(),plan,inserted,len(base["instances"])))
        preserve_owned_routes(work/"insertion-connected.odb",plan,out,"insertion")
        make_overlay(work,out)
    elif args.phase=="fixed-audit":
        base=read("baseline-snapshot.json");inserted=read("insertion-snapshot.json")
        fixed=snapshot(work/"fixed.odb",work/"fixed-actual.def",base["protected"]);save(out/"fixed-snapshot.json",fixed)
        p.require((work/"fixed-actual.def").read_bytes()==(work/"fixed-expected.def").read_bytes(),"exact serialized fixed overlay")
        p.same_base(inserted,fixed);p.exact(inserted["instances"],fixed["instances"],"fixed overlay instances")
        classes=read("drt-original-classes.json");mutable=read("insertion-plan.json")["mutable_nets"]
        for name,row in fixed["nets"].items():
            p.exact(row["identity"],inserted["nets"][name]["identity"],"fixed overlay identity")
            if name in mutable:p.exact(row,inserted["nets"][name],"mutable net frozen or changed")
            elif classes[name]is not None:c.validate_encoded({name:row["encoded"]},{name:"FIXED"})
        (work/"route.tcl").write_text(route_tcl(work,args.environment,args.original_tcl))
    elif args.phase in("restore-plan","failure-restore-plan"):
        restore_plan(work,out,args.phase.startswith("failure"))
    elif args.phase=="restored-audit":
        base=read("baseline-snapshot.json");plan=read("insertion-plan.json")
        current=snapshot(work/"candidate.odb",work/"restored-actual.def",base["protected"])
        p.require((work/"restored-actual.def").read_bytes()==(work/"restored-expected.def").read_bytes(),"restored complete DEF")
        save(out/"restored-snapshot.json",current)
        delta=p.route_delta(read("insertion-snapshot.json"),current,plan)
        delta["full_DEF"]=router.routing_delta((work/"insertion.def").read_bytes(),(work/"restored-actual.def").read_bytes(),
          {"mutable":plan["mutable_nets"],"selected":plan["protected_nets"]})
        save(out/"route-delta.json",delta)
        p.exact(current["clock_record_pins"],base["clock_record_pins"],"original1691 DEF records")
        save(out/"original-clock-gate.json",n.original_gate(args.donor,work/"candidate.odb",out,"original-clock-gate"))
        preserve_owned_routes(work/"candidate.odb",plan,out,"restored")
        save(out/"connectivity-summary.json",connectivity(work/"candidate.odb",plan,out))
        (work/"final-check.tcl").write_text(check_tcl(work/"candidate.odb","final",work))
    elif args.phase=="failure-restored-audit":
        base=read("baseline-snapshot.json")
        current=snapshot(work/"candidate.odb",work/"failure-restored.def",base["protected"])
        p.require((work/"failure-restored.def").read_bytes()==(work/"restored-expected.def").read_bytes(),"failed-route restoration bytes")
        save(out/"failure-restored-snapshot.json",current)
        save(out/"failure-restored-clock-gate.json",n.original_gate(args.donor,work/"candidate.odb",out,"failure-clock-gate"))
    elif args.phase=="antenna-restore-audit":
        base=read("baseline-snapshot.json")
        current=snapshot(work/"insertion-after-shim.odb",work/"antenna-cleanup.def",base["protected"])
        for name,row in base["nets"].items():
            p.exact(current["nets"][name]["wire"],row["wire"],"antenna cleanup wire")
            p.exact(current["nets"][name]["encoded"],row["encoded"],"antenna cleanup metadata")
        save(out/"antenna-cleanup-snapshot.json",current)
    elif args.phase=="final-audit":
        final,measurement=collect_checks("final",work,out);p.require(final["design_is_routed"]==1,"full design routed")
        base=read("baseline-snapshot.json")
        measured=snapshot(work/"final-measured.odb",work/"final-measured.def",base["protected"])
        p.exact(measured,read("restored-snapshot.json"),"measurement unchanged full snapshot")
        baseline=dict(net_count=608,violations=read("baseline-antenna-violations.json"))
        result=p.verdict(baseline,final,measurement,read("route-delta.json"),read("connectivity-summary.json"),read("original-clock-gate.json"))
        result.update(input=p.INPUT,candidate=fp(work/"final-measured.odb"),actual_added_diodes=len(read("insertion-plan.json")["added_instances"]))
        save(out/"result.json",result)
    else:raise AssertionError("unknown native phase")

def main():
    # Match the qualified OpenROAD -python environment interface; no unproved extra argv parsing.
    args=SimpleNamespace(phase=os.environ["NSSOC_BULK_PHASE"])
    for name in("input","donor","environment","original_tcl","work","out"):
        setattr(args,name,Path(os.environ["NSSOC_BULK_"+name.upper()]))
    p.require(args.phase in("prepare","baseline-audit","insertion-audit","fixed-audit","restore-plan",
      "failure-restore-plan","restored-audit","failure-restored-audit","antenna-restore-audit","final-audit"),"native phase")
    p.require(args.work==Path("/work/out/work/bulk-postdrt-antenna")and
      args.out==Path("/work/out/bulk-postdrt-antenna"),"exact owned native output paths")
    p.require(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
    p.source_guard();p.exact(fp(args.input),p.INPUT,"immutable current input")
    args.out.mkdir(parents=True,exist_ok=True);args.work.mkdir(parents=True,exist_ok=True)
    p.run_phase(args.phase,lambda:phase(args),lambda:p.exact(fp(args.input),p.INPUT,"input unchanged"),
      lambda name,value:save(args.out/name,value))
if __name__=="__main__":main()
