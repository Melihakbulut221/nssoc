"""Actual iteration20 narrow47 preparation, reversible protection and route audits."""
import gc,json,os,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna_native as native
import mainchip_snapshot_reload_native as reload
import mainchip_saved_diode_routing_native as saved
from mainchip_route47_contract import need,select,same_sections,wire_delta
from mainchip_route47_import import import_program
n,p,c=native.n,native.p,native.c
ROOT=reload.ROOT;WORK=reload.WORK;DATA=reload.DATA;INPUT=reload.CANDIDATE
PLAN=Path("/work/tail-source/scripts/mainchip-route47-selected.json")
def read(path):return json.loads(path.read_bytes())
def save(name,value):native.save(DATA/name,value)
def snap(path,stem):
    value=native.snapshot(path,WORK/(stem+".def"),read(ROOT/"bulk-postdrt-antenna/targeted-routing-scope.json")["protected_nets"])
    save(stem+".json",value);del value;gc.collect()
    return read(DATA/(stem+".json"))
def original():
    plan=read(PLAN);need(native.fp(INPUT)==plan["snapshot"],"exact report20 snapshot")
    return plan,read(ROOT/"bulk-postdrt-antenna/targeted-routing-scope.json")
def prepare():
    reload.main()
    plan,scope=original();before=read(DATA/"snapshot-before.json")
    selected,names=select(plan,scope,before)
    need(len(selected)==47 and len(plan["records"])==140 and len(scope["routing_nets"])==828,"actual full report scope")
    db,block=n.load(INPUT)
    try:
        need(len(list(block.getNets()))==143820 and len(list(block.getInsts()))==154480,"actual complete native census")
        for name in names:
            net=block.findNet(name)
            need(net is not None and n.identity(db,net)==before["nets"][name]["identity"],"literal report source native identity "+name)
        for name in selected:
            net=block.findNet(name)
            need(str(net.getSigType())=="SIGNAL"and not net.isSpecial()and not list(net.getSWires())and not list(net.getBTerms()),"ordinary selected ITerm-only net")
            need(net.getWire()is not None and n.encoded(net)["metadata"]=="ROUTED"and set(n.encoded(net)["paths"])=={"ROUTED"},"selected real route")
    finally:odb.dbDatabase.destroy(db)
    save("narrow47-native-selection.json",dict(selected=selected,all_report_sources=names,violations=140,all_names_resolved=True,protected=1691,original_scope=828,input=native.fp(INPUT),plan=native.fp(PLAN),**p.FLAGS))
    del before;gc.collect()
    raw=(WORK/"snapshot-before.def").read_bytes()
    expected,classes=p.fixed_plan(raw,selected)
    (WORK/"narrow47-fixed-expected.def").write_bytes(expected);save("narrow47-original-classes.json",classes)
    records=c.parse_def(expected)["records"]
    patch,_=c.patch_def(raw,{name:records[name]for name,kind in classes.items()if kind is not None})
    (WORK/"narrow47-fixed-patch.def").write_bytes(patch)
    native.metadata_only(INPUT,WORK/"narrow47-fixed-base.odb",{name:"FIXED"for name,kind in classes.items()if kind is not None})
    (WORK/"narrow47-freeze.tcl").write_text(import_program(n.import_tcl,WORK/"narrow47-fixed-base.odb",WORK/"narrow47-fixed-patch.def",WORK,"narrow47-fixed"))
    save("narrow47-prepare.json",dict(status="ACTUAL47_IDENTITIES_RESOLVED_AND_REVERSIBLE_OVERLAY_PREPARED",selected=47,route_executed=False,**p.FLAGS))
def restore_program(source,stem,require_original=False):
    classes=read(DATA/"narrow47-original-classes.json")
    db,block=n.load(source)
    try:odb.write_def(block,str(WORK/(stem+"-source.def")))
    finally:odb.dbDatabase.destroy(db)
    raw=(WORK/(stem+"-source.def")).read_bytes();expected=c.restore_classes(raw,classes)
    if require_original:need(expected==(WORK/"snapshot-before.def").read_bytes(),"exact original full DEF after reversing all extra FIXED classes")
    records=c.parse_def(expected)["records"]
    patch,_=c.patch_def(raw,{name:records[name]for name,kind in classes.items()if kind is not None})
    (WORK/(stem+"-expected.def")).write_bytes(expected);(WORK/(stem+"-patch.def")).write_bytes(patch)
    native.metadata_only(source,WORK/(stem+"-base.odb"),{name:kind for name,kind in classes.items()if kind is not None})
    (WORK/(stem+".tcl")).write_text(import_program(n.import_tcl,WORK/(stem+"-base.odb"),WORK/(stem+"-patch.def"),WORK,stem))
def freeze_audit():
    before=read(DATA/"snapshot-before.json");fixed=snap(WORK/"narrow47-fixed.odb","narrow47-fixed-observed")
    need((WORK/"narrow47-fixed-observed.def").read_bytes()==(WORK/"narrow47-fixed-expected.def").read_bytes(),"exact full serialized FIXED overlay")
    same_sections(before,fixed)
    selected=set(read(DATA/"narrow47-native-selection.json")["selected"]);classes=read(DATA/"narrow47-original-classes.json")
    for name,row in fixed["nets"].items():
        need(row["identity"]==before["nets"][name]["identity"],"FIXED identity and all terminals")
        if name in selected or classes[name]is None:need(row==before["nets"][name],"unmodified selected or wireless net")
        else:c.validate_encoded({name:row["encoded"]},{name:"FIXED"})
    del before,fixed;gc.collect()
    restore_program(WORK/"narrow47-fixed.odb","narrow47-reversed",True)
    save("narrow47-freeze-audit.json",dict(exact_full_DEF=True,unchanged_native_sections=True,selected47_unchanged=True,reverse_import_prepared=True,**p.FLAGS))
def reverse_and_clear():
    before=read(DATA/"snapshot-before.json");restored=snap(WORK/"narrow47-reversed.odb","narrow47-reversed-observed")
    need(before==restored,"complete native roundtrip of temporary protection including all wire opcodes")
    del before,restored;gc.collect()
    save("narrow47-reversal-proof.json",dict(full_snapshot_pin=native.fp(DATA/"snapshot-before.json"),reversed_snapshot_pin=native.fp(DATA/"narrow47-reversed-observed.json"),all_fields_equal=True,**p.FLAGS))
    selected=read(DATA/"narrow47-native-selection.json")["selected"];source=WORK/"narrow47-fixed.odb";target=WORK/"narrow47-cleared.odb"
    guides=saved.read_guides(source);db,block=n.load(source)
    try:
        for name in selected:
            net=block.findNet(name)
            need(net is not None and net.getWire()is not None and str(net.getSigType())=="SIGNAL"and n.encoded(net)["metadata"]=="ROUTED"and set(n.encoded(net)["paths"])=={"ROUTED"},"exact clear owner")
        for name in selected:
            net=block.findNet(name);odb.dbWire.destroy(net.getWire());net.setWireType("ROUTED")
            need(net.getWire()is None,"actual wire removal")
        need(saved.guides(block)==guides,"all in-memory guides unchanged")
        odb.write_db(db,str(target))
    finally:odb.dbDatabase.destroy(db)
    need(saved.read_guides(target)==guides,"all serialized guides unchanged");del guides;gc.collect()
    fixed=read(DATA/"narrow47-fixed-observed.json");after=snap(target,"narrow47-cleared-observed")
    delta=wire_delta(fixed,after,selected,"clear",p.pin(p.encode(None)));save("narrow47-clear-delta.json",delta)
    del fixed,after;gc.collect()
    route=native.route_tcl(WORK,Path(os.environ["NSSOC_BULK_ENVIRONMENT"]),Path(os.environ["NSSOC_BULK_ORIGINAL_TCL"]))
    old="read_db "+native.q(WORK/"fixed.odb")
    need(route.count(old)==1 and route.count("detailed_route {*}$drt_args")==1,"single original router input and call")
    changed=route.replace(old,"read_db "+native.q(target),1)
    marker="puts NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN"
    need(changed.count(marker)==1,"single native route stage")
    debug="set_debug_level DRT snapshot 1\ndetailed_route_debug -snapshot_dir "+native.q(WORK)+"\n"
    changed=changed.replace(marker,debug+marker,1)
    need(changed.replace(debug,"",1).replace("read_db "+native.q(target),old,1)==route,"only input binding and output preservation differ from original route program")
    (WORK/"route.tcl").write_text(changed);(DATA/"narrow47-route-original.tcl").write_text(route);(DATA/"narrow47-route-actual.tcl").write_text(changed)
    save("narrow47-seed.json",dict(status="PASS_NATIVE47_IDENTITY_REVERSIBLE_FIXED_AND_SCOPED_CLEAR",input=native.fp(INPUT),seed=native.fp(target),selected=47,protected_clocks=1691,route_tcl=native.fp(WORK/"route.tcl"),route_executed=False,**p.FLAGS))
def route_restore():
    need((WORK/"routed-fixed.odb").is_file(),"actual returned router checkpoint")
    restore_program(WORK/"routed-fixed.odb","narrow47-restored")
def route_audit():
    before=read(DATA/"snapshot-before.json");after=snap(WORK/"narrow47-restored.odb","narrow47-restored-observed")
    need((WORK/"narrow47-restored-observed.def").read_bytes()==(WORK/"narrow47-restored-expected.def").read_bytes(),"actual class-restored complete DEF")
    selected=read(DATA/"narrow47-native-selection.json")["selected"]
    delta=wire_delta(before,after,selected,"route",p.pin(p.encode(None)))
    delta["complete_DEF"]=native.router.routing_delta((WORK/"snapshot-before.def").read_bytes(),(WORK/"narrow47-restored-observed.def").read_bytes(),{"mutable":selected,"selected":before["protected"]})
    save("narrow47-route-delta.json",delta);del before,after;gc.collect()
    (WORK/"final-check.tcl").write_text(native.check_tcl(WORK/"narrow47-restored.odb","final",WORK))
def measure():
    antenna,drc=native.collect_checks("final",WORK,DATA)
    after=snap(WORK/"final-measured.odb","narrow47-measured-observed")
    need(after==read(DATA/"narrow47-restored-observed.json"),"read-only full DRC and antenna measurement")
    need(antenna["design_is_routed"]==1,"native design_is_routed result")
    save("narrow47-result.json",dict(status="COMPLETE_ACTUAL47_ROUTE_SCOPE_AND_FULL_DRC_ANTENNA_MEASUREMENT",candidate=native.fp(WORK/"narrow47-restored.odb"),
        selected47_routing_executed=True,all_nonselected_wires_and_clocks_unchanged=True,temporary47_protection_restored=True,
        original_global_route_classes_restored=False,diode_PG_audit_complete=False,full_LVS_accepted=False,
        drc=drc,antenna=antenna,routing_complete=False,**p.FLAGS))
def main():
    need(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
    phase=os.environ["NSSOC_ROUTE47_PHASE"]
    actions={"prepare":prepare,"freeze-audit":freeze_audit,"reverse-audit-clear":reverse_and_clear,"route-restore":route_restore,"route-audit":route_audit,"measure":measure}
    need(phase in actions,"declared native phase")
    p.source_guard();original();actions[phase]()
    for name,pin in read(Path("/work/snapshot-selected-pins.json")).items():need(native.fp(ROOT/name)==pin,"original input unchanged "+name)
if __name__=="__main__":main()
