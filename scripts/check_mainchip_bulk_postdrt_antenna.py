#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls. Synthetic native I/O is never an actual repair."""
import argparse,ast,copy,json,subprocess,sys,tempfile,traceback
from pathlib import Path
from types import SimpleNamespace
import mainchip_bulk_postdrt_antenna as p

def fixture():
    protected=["clock"+str(i)for i in range(1691)]
    def term(inst,pin):return[inst,pin,"master","INPUT",[0,0],"R0",[0,0],"PLACED",[0,0],"SIGNAL"]
    def net(name,sig="SIGNAL",terms=None):
        return dict(identity=dict(name=name,sigtype=sig,terminals=terms or[],bterms=[],rule=None),
          encoded=dict(wire_present=True,metadata="ROUTED",paths=["ROUTED"]),
          wire=dict(pin={"bytes":4,"sha256":"a"*64},opcode_count=1))
    pins=dict(A=dict(net="data",sigtype="SIGNAL",io="INPUT"),VSS=dict(net="VSS",sigtype="GROUND",io="INOUT"))
    template=dict(master=["lib",p.DIODE],master_type="CORE_ANTENNACELL",location=[0,0],origin=[0,0],
      orientation="R0",status="PLACED",pins=pins)
    before=dict(nets={name:net(name)for name in protected},instances={"ANTENNA_1573":template},
      masters={"lib/"+p.DIODE:{"qualified":"synthetic"}},block={"rows":["row"]},immutable={"sha256":"f"*64},
      diode_template=template,protected=protected)
    before["nets"]["data"]=net("data",terms=[term("ANTENNA_1573","A")])
    before["nets"]["other"]=net("other")
    before["nets"]["VSS"]=net("VSS","GROUND",[term("ANTENNA_1573","VSS")])
    after=copy.deepcopy(before);after["instances"]["ANTENNA_NEW"]=copy.deepcopy(template)
    after["instances"]["ANTENNA_NEW"]["location"]=[10,0]
    after["nets"]["data"]["identity"]["terminals"].append(term("ANTENNA_NEW","A"))
    after["nets"]["VSS"]["identity"]["terminals"].append(term("ANTENNA_NEW","VSS"))
    return before,after,protected

def native_functions():
    """Only selected source renderers, with explicit non-native I/O boundaries."""
    path=Path(__file__).with_name("mainchip_bulk_postdrt_antenna_native.py")
    tree=ast.parse(path.read_bytes());names=("q","repair_tcl","route_tcl")
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
    p.require(len(nodes)==3,"three actual renderer bodies")
    def prior_route(source,environment,work,original,q):
        return "read_db "+q(source)+"\n"+p.router.SETUP+p.router.ARGUMENTS+"\n"+\
          "puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN\n"+\
          "detailed_route {*}$drt_args -output_drc "+q(work/"fixed-routing.drc")+"\n"+\
          "write_def "+q(work/"routed-fixed.def")+"\nwrite_db "+q(work/"routed-fixed.odb")+"\n"+\
          "puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED\nexit\n"
    ns=dict(p=p,Path=Path,setting_prefix=lambda *a:"",
      c=SimpleNamespace(regular=lambda path:SimpleNamespace(read_bytes=lambda:b"explicit synthetic original Tcl input")),
      router=SimpleNamespace(route_tcl=prior_route))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),ns)
    return ns

TCL_STUB=r'''
set clk FIXED
set data ROUTED
set placement PLACED
set events {}
proc BLOCK {method args} {
  switch -- $method {getNets {return {NCLK NDATA}} getInsts {return {U}} default {error "bad block API"}}
}
namespace eval ord {proc get_db_block {} {return BLOCK}}
proc NCLK {method args} {
  global clk events fail_cleanup
  switch -- $method {
    getWireType {return $clk}
    getWire {return WCLK}
    setWireType {
      set value [lindex $args 0];lappend events "clock:$value"
      if {$value eq "FIXED" && $fail_cleanup} {error cleanup-primary}
      set clk $value
    }
    default {error "bad clock API"}
  }
}
proc NDATA {method args} {
  global data
  switch -- $method {getWireType {return $data} getWire {return WDATA} default {error "bad data API"}}
}
proc U {method args} {
  global placement events
  switch -- $method {
    getPlacementStatus {return $placement}
    setPlacementStatus {set placement [lindex $args 0];lappend events "placement:$placement"}
    default {error "bad instance API"}
  }
}
proc repair_antennas {args} {
  global fail_primary clk placement events
  if {$args ne {sg13g2_antennanp -iterations 1 -ratio_margin 10 -diode_only}} {error "changed repair argv"}
  if {$clk ne "ROUTED"} {error "shim did not precede repair"}
  set placement FIRM;lappend events repair
  if {$fail_primary} {error repair-primary}
  return 2
}
proc write_def {path} {
  global fail_def events;lappend events "def:$path"
  if {$fail_def} {error def-preservation}
}
proc write_db {path} {
  global fail_db events;lappend events "db:$path"
  if {$fail_db} {error db-preservation}
}
proc read_db {path} {}
proc set_thread_count {args} {}
proc detailed_route_debug {args} {}
proc set_debug_level {args} {}
proc detailed_route {args} {
  global fail_primary events;lappend events route
  if {$fail_primary} {error route-primary}
}
# The renderer's exit is replaced with this source-fixture command, never a production replacement.
proc exit {args} {return}
set ::env(DRT_THREADS) 2
set ::env(DRT_SAVE_SNAPSHOTS) 0
set ::env(DRT_SAVE_DRC_REPORT_ITERS) 5
set ::env(DRT_OPT_ITERS) 64
set ::env(STEP_DIR) /work/unit
'''
def tcl_case(body,flags):
    header="\n".join("set "+k+" "+str(int(v))for k,v in flags.items())+"\n"
    script=header+TCL_STUB+"\nset rc [catch {\n"+body+"\n} result options]\n"
    script+='puts "FIXTURE_RC=$rc"\nputs "FIXTURE_RESULT=$result"\nputs "FIXTURE_STATE=$clk|$placement"\nputs "FIXTURE_EVENTS=$events"\n'
    result=subprocess.run(["tclsh"],input=script.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
    p.require(result.returncode==0,"source fixture Tcl interpreter")
    text=result.stdout.decode("utf-8","strict")
    p.require("FIXTURE_RC="in text,"complete Tcl fixture result")
    return dict(returncode=result.returncode,stdout=text,stderr=result.stderr.decode("utf-8","strict"),
      synthetic_native_api=True,native_executed=False)

def controls():
    positives=[];refusals=[];lifecycle=[];rendered=[]
    def refuse(label,fn,needle):
        try:fn()
        except (AssertionError,ValueError,FileNotFoundError)as exc:
            p.require(needle in str(exc),"wrong refusal for "+label+": "+repr(exc))
            refusals.append(dict(label=label,error=repr(exc)));return
        raise AssertionError("accepted "+label)
    source_manifest=p.source_guard();positives.append("actual protected source and proof bytes")
    with tempfile.TemporaryDirectory(prefix="bulk-source-control-")as directory:
        projection=Path(directory)
        for name in list(source_manifest["files"])+[p.MANIFEST]:
            target=projection/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(p.clock.regular(p.ROOT/name).read_bytes())
        p.source_guard(projection)
        name="scripts/mainchip_original_clock_restoration.py";target=projection/name;raw=target.read_bytes()
        target.write_bytes(raw+b"\n# deliberate source-control mutation\n")
        refuse("changed protected source",lambda:p.source_guard(projection),"source or proof")
        target.write_bytes(raw);target.unlink()
        refuse("missing protected source",lambda:p.source_guard(projection),"mainchip_original_clock_restoration.py")
        target.symlink_to(p.ROOT/name)
        refuse("symlink protected source",lambda:p.source_guard(projection),"symlink")
    def load(key):return json.loads((p.ROOT/p.PROOF[key]).read_bytes())
    run,jobs,release,ref,outputs,parts=(load(k)for k in("run","jobs","release","ref","outputs","parts"))
    p.producer(run,jobs,release,ref,outputs,parts);positives.append("actual successful producer69-member metadata")
    for label,index,key,value,needle in(
      ("producer source",0,"head_sha","0"*40,"producer run"),
      ("producer attempt",0,"run_attempt",2,"producer run"),
      ("producer failed",0,"conclusion","failure","producer run"),
      ("release id",2,"id",1,"producer release"),
      ("release tag",2,"tag_name","wrong","producer release"),
    ):
        args=copy.deepcopy([run,jobs,release,ref,outputs,parts]);args[index][key]=value
        refuse(label,lambda args=args:p.producer(*args),needle)
    for label,mutate,needle in(
      ("job omission",lambda a:a[1]["jobs"].pop(),"all original producer jobs"),
      ("asset omitted",lambda a:a[2]["assets"].pop(),"complete producer assets"),
      ("ref source",lambda a:a[3]["object"].__setitem__("sha","0"*40),"producer ref"),
      ("native member omitted",lambda a:a[4]["files"].pop(p.MEMBER),"complete69 outputs"),
      ("native member hash",lambda a:a[4]["files"][p.MEMBER].__setitem__("sha256","0"*64),"complete69 outputs"),
      ("archive hash",lambda a:a[5]["archive"].__setitem__("sha256","0"*64),"archive parts"),
    ):
        args=copy.deepcopy([run,jobs,release,ref,outputs,parts]);mutate(args)
        refuse(label,lambda args=args:p.producer(*args),needle)
    before,after,protected=fixture()
    plan=p.admit_insertions(before,after,protected,[{"net":"data"}])
    p.require(plan["mutable_nets"]==["data"]and plan["attachments"]=={"ANTENNA_NEW":"data"},"measured set")
    positives.append("actual admission on explicit synthetic insertion")
    margin=p.admit_insertions(before,after,protected,[{"net":"other"}])
    p.require(margin["repaired_margin_only_nets"]==["data"],"margin-only repair disclosed")
    positives.append("margin-only repair disclosed")
    mutations=(
      ("original moved",lambda a:a["instances"]["ANTENNA_1573"]["location"].__setitem__(0,1),"original instance"),
      ("original pin moved",lambda a:a["instances"]["ANTENNA_1573"]["pins"]["A"].__setitem__("net","other"),"original instance"),
      ("original removed",lambda a:a["instances"].pop("ANTENNA_1573"),"original instance removed"),
      ("new non diode",lambda a:a["instances"]["ANTENNA_NEW"]["master"].__setitem__(1,"buffer"),"added diode master"),
      ("new diode unknown net",lambda a:a["instances"]["ANTENNA_NEW"]["pins"]["A"].__setitem__("net","absent"),"protected/unknown"),
      ("new diode clock",lambda a:a["instances"]["ANTENNA_NEW"]["pins"]["A"].__setitem__("net",protected[0]),"protected/unknown"),
      ("new diode wrong PG",lambda a:a["instances"]["ANTENNA_NEW"]["pins"]["VSS"].__setitem__("net","data"),"diode PG template"),
      ("new diode missing A",lambda a:a["instances"]["ANTENNA_NEW"]["pins"].pop("A"),"diode terminal census"),
      ("new diode status",lambda a:a["instances"]["ANTENNA_NEW"].__setitem__("status","FIRM"),"new diode placement"),
      ("old wire changed by repair",lambda a:a["nets"]["data"]["wire"]["pin"].__setitem__("sha256","b"*64),"repair changed existing encoded"),
      ("metadata shim unrestored",lambda a:a["nets"]["data"]["encoded"].__setitem__("metadata","FIXED"),"antenna metadata restore"),
      ("new unexplained terminal",lambda a:a["nets"]["other"]["identity"]["terminals"].append(["rogue","A"]),"original terminal identity"),
      ("row changed",lambda a:a["block"].__setitem__("rows",["moved"]),"block/rows"),
      ("special wire changed",lambda a:a["immutable"].__setitem__("sha256","0"*64),"special and obstruction"),
      ("master changed",lambda a:a["masters"].__setitem__("lib/"+p.DIODE,{}),"master definitions"),
    )
    for label,mutate,needle in mutations:
        bad=copy.deepcopy(after);mutate(bad)
        refuse(label,lambda bad=bad:p.admit_insertions(before,bad,protected,[{"net":"data"}]),needle)

    # Component/connection removal is exact; existing wire/property tokens remain owned.
    defraw=b"VERSION 5.8 ;\nCOMPONENTS 1 ;\n- ANTENNA_1573 sg13g2_antennanp + PLACED ( 0 0 ) N ;\nEND COMPONENTS\nNETS 2 ;\n- data ( ANTENNA_1573 A ) + USE SIGNAL\n  + ROUTED Metal1 ( 0 0 ) ( 1 0 ) ;\n- VSS ( ANTENNA_1573 VSS ) + USE GROUND ;\nEND NETS\nEND DESIGN\n"
    addeddef=defraw.replace(b"COMPONENTS 1 ;",b"COMPONENTS 2 ;").replace(b"END COMPONENTS\n",
      b"- ANTENNA_NEW sg13g2_antennanp + PLACED ( 10 0 ) N ;\nEND COMPONENTS\n")
    addeddef=addeddef.replace(b"( ANTENNA_1573 A )",b"( ANTENNA_1573 A ) ( ANTENNA_NEW A )")
    addeddef=addeddef.replace(b"( ANTENNA_1573 VSS )",b"( ANTENNA_1573 VSS ) ( ANTENNA_NEW VSS )")
    p.insertion_def_delta(defraw,addeddef,plan,after,1);positives.append("actual generalized frozen DEF normalizer")
    refuse("insertion DEF wire mutation",lambda:p.insertion_def_delta(defraw,
      addeddef.replace(b"( 1 0 )",b"( 2 0 )"),plan,after,1),"all original DEF tokens")
    refuse("insertion DEF property mutation",lambda:p.insertion_def_delta(defraw,
      addeddef.replace(b"USE SIGNAL",b"USE CLOCK"),plan,after,1),"all original DEF tokens")
    refuse("insertion DEF global mutation",lambda:p.insertion_def_delta(defraw,
      addeddef.replace(b"VERSION 5.8",b"VERSION 5.7"),plan,after,1),"all original DEF tokens")
    routed=copy.deepcopy(after);routed["nets"]["data"]["wire"]["pin"]["sha256"]="b"*64
    delta=p.route_delta(after,routed,plan);positives.append("only measured changed-net route admitted")
    for label,mutate,needle in(
      ("unowned route",lambda a:a["nets"]["other"]["wire"]["pin"].__setitem__("sha256","c"*64),"unowned route delta"),
      ("clock route",lambda a:a["nets"][protected[0]]["wire"]["pin"].__setitem__("sha256","c"*64),"unowned route delta"),
      ("route moved diode",lambda a:a["instances"]["ANTENNA_NEW"]["location"].__setitem__(0,99),"original instance"),
      ("route changed terminal",lambda a:a["nets"]["data"]["identity"].__setitem__("rule","new"),"route changed net identity"),
      ("route metadata remains fixed",lambda a:a["nets"]["data"]["encoded"].__setitem__("metadata","FIXED"),"route metadata"),
      ("route path remains fixed",lambda a:a["nets"]["data"]["encoded"].__setitem__("paths",["FIXED"]),"mutable route classes"),
      ("route unchanged diode net",lambda a:a["nets"]["data"].__setitem__("wire",copy.deepcopy(after["nets"]["data"]["wire"])),"each new diode"),
    ):
        bad=copy.deepcopy(routed);mutate(bad);refuse(label,lambda bad=bad:p.route_delta(after,bad,plan),needle)
    raw=b"VERSION 5.8 ;\nNETS 2 ;\n- data ( U A ) + USE SIGNAL\n  + ROUTED Metal1 ( 0 0 ) ( 1 0 ) ;\n- clock ( C CK ) + USE CLOCK\n  + ROUTED Metal4 ( 2 0 ) ( 3 0 ) ;\nEND NETS\nEND DESIGN\n"
    fixed,classes=p.fixed_plan(raw,["data"]);p.require(classes=={"clock":"ROUTED"},"exact classes")
    p.require(b"+ FIXED Metal4"in fixed and b"+ ROUTED Metal1"in fixed,"only class owner")
    p.require_restored(raw,fixed,classes);positives.append("actual frozen parser class roundtrip")
    refuse("restoration geometry",lambda:p.require_restored(raw.replace(b"( 3 0 )",b"( 4 0 )"),fixed,classes),"complete original-class")
    refuse("restoration missing",lambda:p.require_restored(fixed,fixed,classes),"complete original-class")
    refuse("mutable fixed input",lambda:p.fixed_plan(raw.replace(b"ROUTED Metal1",b"FIXED Metal1"),["data"]),"mutable original ROUTED")
    observations={"data":{m:dict(mode=m,all_pins_share_one_wire_component=True,all_wire_material_one_component=True,
      pins=[{"scoped_identity":["iterm","ANTENNA_NEW","A"]}])for m in("positive_area","closed_boundary")}}
    connection=p.validate_connectivity(observations,plan);positives.append("complete both-mode new-diode connectivity binding")
    for label,mutate,needle in(
      ("missing mode",lambda a:a["data"].pop("positive_area"),"both connectivity modes"),
      ("missing net",lambda a:a.pop("data"),"complete changed-net connectivity"),
      ("disconnected diode",lambda a:a["data"]["positive_area"].__setitem__("all_pins_share_one_wire_component",False),"physical connectivity"),
      ("missing diode pin",lambda a:a["data"]["positive_area"].__setitem__("pins",[]),"added diode physical connection"),
    ):
        bad=copy.deepcopy(observations);mutate(bad);refuse(label,lambda bad=bad:p.validate_connectivity(bad,plan),needle)
    historical=load("violations");baseline={"net_count":608,"violations":historical}
    drc=dict(marker_count=0,all_categories_below_native_cap=True,serialized_markers=dict(complete_native_category_census_equal=True,marker_count=0))
    gate=dict(result=dict(clock_or_fixed_nets=1691,all_source_clock_and_fixed_records_preserved=True))
    residual=p.verdict(baseline,baseline,drc,delta,connection,gate)
    p.require(residual["candidate_rejected"]is True and residual["physical_acceptance"]is False,"remaining608 never pass")
    positives.append("authentic608 remaining is rejected")
    clean=p.verdict(baseline,{"net_count":0,"violations":[]},drc,delta,connection,gate)
    p.require(clean["bounded_cycle_qualified"]is True and clean["full_phy_accepted"]is False,"bounded zero is not signoff")
    positives.append("synthetic zero requires original gates and remains non-PHY")
    refuse("incomplete DRC",lambda:p.verdict(baseline,baseline,{**drc,"all_categories_below_native_cap":False},delta,connection,gate),"complete DRC")
    refuse("wrong clock census",lambda:p.verdict(baseline,baseline,drc,delta,connection,{"result":{**gate["result"],"clock_or_fixed_nets":1690}}),"original1691 gate")
    refuse("antenna count mismatch",lambda:p.verdict(baseline,{"net_count":0,"violations":historical},drc,delta,connection,gate),"antenna report count")

    # Actual production lifecycle with synthetic I/O callbacks, including all phase failures.
    def run_lifecycle(failed=None,final_failed=None,write_failed=False,incomplete=None):
        events=[];writes={};primary=RuntimeError("primary:"+str(failed))
        def action(name):
            events.append(name)
            if name==failed:raise primary
            return {"complete":name!=incomplete,"synthetic":True}
        def finalize(name):
            events.append(name)
            if name==final_failed:raise OSError("cleanup:"+name)
            return {"complete":True}
        def writer(name,value):
            writes[name]=copy.deepcopy(value)
            if write_failed and name=="cycle-terminal.json":raise OSError("terminal write")
        try:
            value=p.run_cycle({n:lambda n=n:action(n)for n in p.PHASES},
              {n:lambda n=n:finalize(n)for n in p.FINALIZERS},writer)
            error=None
        except BaseException as exc:
            value=None;error=exc
        p.require(events[-3:]==list(p.FINALIZERS),"all independent finalizers attempted")
        if failed is not None:
            p.require(error is primary,"original phase error identity")
            p.require(events[:events.index(failed)+1]==list(p.PHASES[:p.PHASES.index(failed)+1]),"no phase continuation")
            p.require(writes["cycle-terminal.json"]["complete"]is False,"failed terminal")
        elif final_failed or write_failed or incomplete:p.require(error is not None,"failure never passes")
        else:p.require(value["complete"]is True and events==list(p.PHASES)+list(p.FINALIZERS),"all phase success")
        lifecycle.append(dict(failed_phase=failed,failed_finalizer=final_failed,write_failed=write_failed,incomplete=incomplete,
          events=events,records=writes,error=None if error is None else repr(error),synthetic_native_io=True))
    run_lifecycle()
    for name in p.PHASES:run_lifecycle(failed=name,final_failed=p.FINALIZERS[0])
    for name in p.FINALIZERS:run_lifecycle(final_failed=name)
    run_lifecycle(failed="route",final_failed="restore-drt-classes",write_failed=True)
    run_lifecycle(write_failed=True);run_lifecycle(incomplete="repair")
    ns=native_functions();work=Path("/work/unit")
    repair=ns["repair_tcl"](work/"input.odb",work/"env.tcl",work/"original.tcl",work)
    route=ns["route_tcl"](work,work/"env.tcl",work/"original.tcl")
    p.require(repair.count("repair_antennas sg13g2_antennanp")==1 and "detailed_route "not in repair,"one repair only")
    p.require(route.count("detailed_route {*}$drt_args")==1 and "repair_antennas "not in route,"one route only")
    for name,primary,cleanup,fail_def,fail_db in(
      ("repair-ok",False,False,False,False),("repair-primary",True,False,False,False),
      ("repair-cleanup",False,True,False,False),("repair-double-failure",True,True,False,False),
      ("repair-def-failure",False,False,True,False),("repair-db-failure",False,False,False,True),
      ("route-ok",False,False,False,False),("route-primary",True,False,False,False),
      ("route-primary-and-save",True,False,True,True),
    ):
        row=tcl_case(repair if name.startswith("repair")else route,
          dict(fail_primary=primary,fail_cleanup=cleanup,fail_def=fail_def,fail_db=fail_db))
        text=row["stdout"];failed=primary or cleanup or fail_def or fail_db
        p.require("FIXTURE_RC="+str(int(failed))in text,"rendered Tcl outcome")
        if primary:p.require("FIXTURE_RESULT="+("repair-primary"if name.startswith("repair")else"route-primary")in text,"Tcl primary preserved")
        if name.startswith("repair"):
            p.require("placement:PLACED"in text,"placement restoration still attempted")
            p.require("def:/work/unit/insertion-after-shim.def"in text and "db:/work/unit/insertion-after-shim.odb"in text,"independent insertion output")
            if not cleanup:p.require("FIXTURE_STATE=FIXED|PLACED"in text,"actual Tcl metadata restored")
        else:p.require("def:/work/unit/route-partial.def"in text and "db:/work/unit/route-partial.odb"in text,"independent partial route output")
        rendered.append(dict(label=name,**row))
    return dict(status="PASS_BULK_POSTDRT_SOURCE_CONTROLS",positive=positives,refusal=refusals,
      lifecycle=lifecycle,rendered_tcl=rendered,counts=dict(positive=len(positives),refusal=len(refusals),
        lifecycle=len(lifecycle),rendered_tcl=len(rendered)),native_executed=False,**p.FLAGS)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    error=None
    try:result=controls()
    except BaseException as exc:
        error=exc;result=dict(status="FAILED_BULK_POSTDRT_SOURCE_CONTROLS",error=repr(exc),traceback=traceback.format_exc(),native_executed=False,**p.FLAGS)
    failures=[]
    try:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(p.encode(result))
    except BaseException as exc:failures.append({"operation":"report-file","error":repr(exc)})
    try:print(p.encode(result).decode(),end="")
    except BaseException as exc:failures.append({"operation":"stdout","error":repr(exc)})
    if failures:
        try:print(p.encode({"preservation_errors":failures,"primary":None if error is None else repr(error)}).decode(),file=sys.stderr)
        except BaseException:pass
    if error is not None:raise error
    if failures:raise RuntimeError("source-report preservation failed: "+repr(failures))
if __name__=="__main__":main()
