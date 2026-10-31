"""Clear only saved-plan signal wires; preserve the entire surrounding native DB."""
import gc,json,os,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_stale_wire_routing as a
import mainchip_saved_diode_routing_native as saved
import mainchip_bulk_postdrt_antenna_native as native
from mainchip_bulk_postdrt_antenna_native import p,n
WORK=saved.WORK
DATA=saved.DATA

def read(name):return json.loads((DATA/name).read_bytes())

def clear():
    original=WORK/"fixed.odb";target=WORK/"stale-wire-cleared.odb"
    p.require(original.is_file()and not target.exists(),"owned fresh wire-clear output")
    fixed_pin=native.fp(original);admission=read("insertion-plan.json")
    p.require(len(admission["mutable_nets"])==608 and len(admission["attachments"])==1351
      and len(admission["protected_nets"])==1691,"actual scoped census")
    before=read("fixed-snapshot.json")
    p.require(len(before["instances"])==154480 and len(before["nets"])==143820,"actual complete candidate census")
    guide_before=saved.read_guides(original)
    saved.save("stale-wire-original-guides.json",guide_before)
    db,block=n.load(original)
    report=dict(complete=False,removed=[],input=fixed_pin,**p.FLAGS)
    try:
        for name in sorted(admission["mutable_nets"]):
            net=block.findNet(name)
            p.require(net is not None and str(net.getSigType())=="SIGNAL","owned live signal")
            wire=net.getWire()
            p.require(wire is not None and str(net.getWireType())=="ROUTED","actual initial routing")
            odb.dbWire.destroy(wire)
            p.require(net.getWire()is None,"wire removal readback")
            report["removed"].append(name)
        p.exact(saved.guides(block),guide_before,"every guide unchanged in memory")
        odb.write_db(db,str(target));report["candidate"]=native.fp(target)
    except BaseException as exc:
        report["error"]=repr(exc)
        try:
            partial=WORK/"stale-wire-unadmitted-partial.odb";odb.write_db(db,str(partial))
            report["partial"]=native.fp(partial)
        except BaseException as secondary:report["partial_error"]=repr(secondary)
        raise
    finally:
        odb.dbDatabase.destroy(db)
        saved.save("stale-wire-mutation.json",report)
    p.exact(saved.read_guides(target),guide_before,"every guide unchanged after reload")
    del guide_before;gc.collect()
    after=native.snapshot(target,WORK/"stale-wire-cleared.def",admission["protected_nets"])
    saved.save("stale-wire-cleared-snapshot.json",after)
    report["delta"]=a.clear_delta(before,after,admission)
    p.exact(native.fp(original),fixed_pin,"unchanged fixed input")
    p.require(len(report["removed"])==608,"actual608wire removal")
    # Original fixed-audit generated this exact Tcl. Compare before the single input replacement.
    route=WORK/"route.tcl";raw=route.read_text()
    original_render=native.route_tcl(WORK,Path(os.environ["NSSOC_BULK_ENVIRONMENT"]),Path(os.environ["NSSOC_BULK_ORIGINAL_TCL"]))
    p.exact(raw,original_render,"exact unchanged original route program")
    new=a.route_text(raw,WORK)
    (DATA/"route-before-stale-wire-clear.tcl").write_text(raw)
    (DATA/"route-after-stale-wire-clear.tcl").write_text(new)
    route.write_text(new)
    report.update(complete=True,all_guides_unchanged=True,route_before=p.pin(raw.encode()),route_after=p.pin(new.encode()))
    saved.save("stale-wire-mutation.json",report)

def main():
    a.source_gate()
    phase=os.environ.get("NSSOC_STALE_WIRE_PHASE")
    if phase=="clear":
        p.source_guard();saved.verify_inputs()
        p.run_phase("stale-wire-clear",clear,saved.verify_inputs,lambda name,value:saved.save(name,value))
        return
    p.require(phase=="clock-audit","known scoped adapter phase")
    p.require(os.environ.get("NSSOC_BULK_PHASE")in("restored-audit","failure-restored-audit"),"only two original clock audit callers")
    # Keep phase/main code and every native physical gate intact.
    proxy=SimpleNamespace(**vars(n))
    proxy.original_gate=a.gate_adapter(n.original_gate)
    derived_phase=a.clone(native.phase,n=proxy)
    a.clone(native.main,phase=derived_phase)()

if __name__=="__main__":main()
