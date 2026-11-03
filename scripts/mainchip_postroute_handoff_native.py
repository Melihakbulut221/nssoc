"""Restore original global classes and verify actual physical-netlist export in cloud."""
import copy, gc, json, os, sys
from pathlib import Path
sys.path.insert(0, "/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna_native as native
from mainchip_bulk_postdrt_antenna_native import n,p,c
from mainchip_postroute_handoff_contract import need, restoration, topology, pg
WORK=Path("/work/out/work/bulk-postdrt-antenna")
DATA=Path("/work/out/bulk-postdrt-antenna")
CANDIDATE=Path("/work/route-candidate/work/bulk-postdrt-antenna/narrow47-restored.odb")
BASELINE=Path(os.environ["NSSOC_BULK_INPUT"])
def read(path): return json.loads(path.read_bytes())
def save(name, value): native.save(DATA/name, value)
def snap(path, stem):
    # Candidate FIXED includes the temporary router overlay, not just the
    # original clock/fixed scope. Derive ownership only from the exact baseline.
    need(native.fp(BASELINE)==p.INPUT, "exact original protected-scope input")
    db,block=n.load(BASELINE)
    try:
        protected=sorted(n.selected(block))
        need(len(protected)==len(set(protected))==1691, "original protected1691 census")
    finally: odb.dbDatabase.destroy(db)
    value=native.snapshot(path, WORK/(stem+".def"), protected)
    save(stem+".json",value)
    return value
def capture(path):
    db, block=n.load(path)
    try:
        need(not list(block.getChildren()), "flat complete physical design")
        instances={}
        for inst in block.getInsts():
            name=inst.getName()
            need(name not in instances,"unique instance")
            instances[name]=dict(master=inst.getMaster().getName(),
                pins={t.getMTerm().getName():t.getNet().getName() if t.getNet() else None for t in inst.getITerms()})
        ports={t.getName():dict(net=t.getNet().getName() if t.getNet() else None,io=str(t.getIoType())) for t in block.getBTerms()}
        nets={net.getName():dict(iterms=sorted([t.getInst().getName(),t.getMTerm().getName()] for t in net.getITerms()),
                bterms=sorted(t.getName() for t in net.getBTerms())) for net in block.getNets()}
        return dict(top=block.getName(),instances=instances,ports=ports,nets=nets)
    finally: odb.dbDatabase.destroy(db)
def prepare():
    config=read(Path("/work/tail-source/scripts/mainchip-handoff-route-inputs.json"))
    for name, pin in read(Path("/work/route-candidate-pins.json")).items():
        need(native.fp(Path("/work/route-candidate")/name)==pin,"authenticated route candidate")
    result=read(Path("/work/route-candidate/bulk-postdrt-antenna/narrow47-result.json"))
    need(result["status"]=="COMPLETE_ACTUAL47_ROUTE_SCOPE_AND_FULL_DRC_ANTENNA_MEASUREMENT","returned native route observation")
    need(result["candidate"]==native.fp(CANDIDATE),"exact observed candidate ODB")
    need(result["selected47_routing_executed"] is True and result["temporary47_protection_restored"] is True,"completed local restoration")
    before=snap(CANDIDATE,"handoff-before")
    baseline=snap(BASELINE,"handoff-baseline")
    need(len(before["instances"])==154480 and len(baseline["instances"])==153129,"actual before/after cell census")
    need(len(before["nets"])==len(baseline["nets"])==143820,"actual net census")
    need(before["protected"]==baseline["protected"] and len(before["protected"])==1691,"original protected nets")
    for name,row in baseline["instances"].items():
        need(before["instances"][name]==row,"unchanged original instance "+name)
    supplies=pg(before["instances"],baseline["diode_template"],baseline["instances"])
    need(len(supplies["added_diodes"])==1351,"actual added diode count")
    save("handoff-logical-diode-pg.json",supplies)
    raw=(WORK/"handoff-before.def").read_bytes()
    records=c.parse_def(raw)["records"]
    original=c.parse_def((WORK/"handoff-baseline.def").read_bytes())["records"]
    need(set(records)==set(original),"exact full DEF net census")
    changes={}
    for name,record in records.items():
        target=c.classes(original[name])
        current=c.classes(record)
        if target is None:
            need(current is None,"no new route on originally wireless net "+name)
        elif current!=target:
            need(current in ("ROUTED","FIXED","COVER"),"known current path class")
            changes[name]=c.route_class(record,target)
    need(changes,"global temporary route classes must be restored")
    expected=c.replace_records(raw,changes)
    (WORK/"handoff-expected.def").write_bytes(expected)
    patch,_=c.patch_def(raw,changes)
    (WORK/"handoff-patch.def").write_bytes(patch)
    targets={name:row["encoded"]["metadata"] for name,row in baseline["nets"].items()}
    native.metadata_only(CANDIDATE,WORK/"handoff-base.odb",targets)
    q=native.q
    tcl="read_db "+q(WORK/"handoff-base.odb")+"\n"
    tcl+="read_def -floorplan_initialize "+q(WORK/"handoff-patch.def")+"\nwrite_def "+q(WORK/"handoff-single.def")+"\n"
    tcl+="read_def -floorplan_initialize "+q(WORK/"handoff-patch.def")+"\nwrite_def "+q(WORK/"handoff-restored.def")+"\nwrite_db "+q(WORK/"handoff-restored.odb")+"\n"
    (WORK/"handoff-restore.tcl").write_text(tcl)
    save("handoff-prepare.json",dict(candidate=native.fp(CANDIDATE),producer=config["producer"],changed_classes=len(changes),logical_diode_pg=supplies,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
def restored():
    before=read(DATA/"handoff-before.json")
    baseline=read(DATA/"handoff-baseline.json")
    after=snap(WORK/"handoff-restored.odb","handoff-restored-observed")
    need((WORK/"handoff-restored-observed.def").read_bytes()==(WORK/"handoff-expected.def").read_bytes(),"complete restored DEF byte equality")
    result=restoration(before,after,baseline,native.fp(WORK/"handoff-expected.def"))
    need(after["clock_record_pins"]==baseline["clock_record_pins"],"original complete1691 clock records")
    result["original_clock_gate"]=n.original_gate(Path(os.environ["NSSOC_BULK_DONOR"]),WORK/"handoff-restored.odb",DATA,"handoff-original-clock")
    save("handoff-restoration.json",result)
    del before,baseline,after;gc.collect()
    save("handoff-topology-before.json",capture(WORK/"handoff-restored.odb"))
    db, block=n.load(WORK/"handoff-restored.odb")
    try:
        top=block.getName()
        need(top=="soc_top","exact admitted mainchip top")
        odb.dbChip.destroy(db.getChip())
        need(db.getChip() is None,"library-only fresh import database")
        odb.write_db(db,str(WORK/"handoff-libraries.odb"))
    finally: odb.dbDatabase.destroy(db)
    q=native.q
    (WORK/"handoff-export.tcl").write_text("read_db "+q(WORK/"handoff-restored.odb")+"\nwrite_verilog -include_pwr_gnd "+q(WORK/"handoff-candidate.v")+"\nwrite_def "+q(WORK/"handoff-export-after.def")+"\n")
    (WORK/"handoff-relink.tcl").write_text("read_db "+q(WORK/"handoff-libraries.odb")+"\nread_verilog "+q(WORK/"handoff-candidate.v")+"\nlink_design "+top+"\nwrite_db "+q(WORK/"handoff-relinked.odb")+"\n")
    (WORK/"final-check.tcl").write_text(native.check_tcl(WORK/"handoff-restored.odb","final",WORK))
def relinked():
    need((WORK/"handoff-export-after.def").read_bytes()==(WORK/"handoff-restored-observed.def").read_bytes(),"read-only Verilog export")
    before=read(DATA/"handoff-topology-before.json")
    after=capture(WORK/"handoff-relinked.odb")
    save("handoff-topology-after.json",after)
    proof=topology(before,after)
    diode=read(DATA/"handoff-logical-diode-pg.json")["added_diodes"][0]
    faults=[]
    for label in ("missing_diode","diode_master","diode_signal","diode_supply","boundary"):
        wrong=dict(after)
        if label=="boundary":
            wrong["ports"]=dict(after["ports"])
            port=next(iter(wrong["ports"]))
            wrong["ports"][port]=dict(wrong["ports"][port],net=None)
        else:
            wrong["instances"]=dict(after["instances"])
            wrong["instances"][diode]=copy.deepcopy(after["instances"][diode])
            if label=="missing_diode":del wrong["instances"][diode]
            elif label=="diode_master":wrong["instances"][diode]["master"]="CORRUPTED"
            elif label=="diode_signal":wrong["instances"][diode]["pins"]["A"]=None
            else:
                pin=next(p0 for p0 in wrong["instances"][diode]["pins"] if p0!="A")
                wrong["instances"][diode]["pins"][pin]=None
        try:topology(before,wrong)
        except ValueError:faults.append(label)
        else:raise ValueError("accepted actual topology fault "+label)
    proof.update(candidate=native.fp(WORK/"handoff-restored.odb"),netlist=native.fp(WORK/"handoff-candidate.v"),rejected_native_faults=faults)
    save("handoff-netlist-proof.json",proof)
def measure():
    antenna,drc=native.collect_checks("final",WORK,DATA)
    measured=snap(WORK/"final-measured.odb","handoff-measured")
    need(measured==read(DATA/"handoff-restored-observed.json"),"read-only complete physical checking")
    need(antenna["design_is_routed"]==1,"native design routed")
    save("handoff-result.json",dict(status="COMPLETE_NATIVE_GLOBAL_CLASS_RESTORATION_AND_NETLIST_ROUNDTRIP",
        candidate=native.fp(WORK/"handoff-restored.odb"),netlist=native.fp(WORK/"handoff-candidate.v"),
        restoration=read(DATA/"handoff-restoration.json"),netlist_proof=read(DATA/"handoff-netlist-proof.json"),
        logical_pg=read(DATA/"handoff-logical-diode-pg.json"),drc=drc,antenna=antenna,
        physical_supply_connectivity_verified=False,full_LVS_accepted=False,physical_acceptance=False,
        timing_accepted=False,full_phy_accepted=False))
def main():
    need(not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
    p.source_guard()
    phase=os.environ["NSSOC_HANDOFF_PHASE"]
    actions={"prepare":prepare,"restored":restored,"relinked":relinked,"measure":measure}
    need(phase in actions,"declared phase")
    actions[phase]()
    need(native.fp(BASELINE)==p.INPUT,"unchanged original input")
    for name,pin in read(Path("/work/route-candidate-pins.json")).items():
        need(native.fp(Path("/work/route-candidate")/name)==pin,"unchanged candidate source")
if __name__=="__main__":main()
