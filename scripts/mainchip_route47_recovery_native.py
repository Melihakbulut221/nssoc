"""Authenticate and recover actual iteration19 without rerouting or changing route acceptance."""
import gc,json,shutil,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import mainchip_route47_native as n
from mainchip_route47_contract import need,select
ROOT=Path("/work/recovery-inputs")
DATA=n.DATA
WORK=n.WORK
CANDIDATE="work/bulk-postdrt-antenna/drt_iter19.odb"
COPIES={
 "bulk-postdrt-antenna/snapshot-before.json":"bulk-postdrt-antenna/snapshot-before.json",
 "bulk-postdrt-antenna/narrow47-original-classes.json":"bulk-postdrt-antenna/narrow47-original-classes.json",
 "bulk-postdrt-antenna/narrow47-native-selection.json":"bulk-postdrt-antenna/narrow47-native-selection.json",
 "work/bulk-postdrt-antenna/snapshot-before.def":"work/bulk-postdrt-antenna/snapshot-before.def",
 CANDIDATE:"work/bulk-postdrt-antenna/routed-fixed.odb",
}
def main():
    pins=n.read(Path("/work/recovery-selected-pins.json"))
    for name,pin in pins.items():need(n.native.fp(ROOT/name)==pin,"authenticated recovery input "+name)
    need(n.native.fp(ROOT/CANDIDATE)==dict(bytes=214392179,sha256="a93e921ccd7abb164dbe2ff3f6a1a1c26777d707399cea7580d7c5d08ea11017"),"actual iteration19 saved ODB")
    before=n.read(ROOT/"bulk-postdrt-antenna/snapshot-before.json")
    plan,scope=n.original();selected,names=select(plan,scope,before)
    declaration=n.read(ROOT/"bulk-postdrt-antenna/narrow47-native-selection.json")
    need(declaration["selected"]==selected and len(selected)==47 and declaration["protected"]==1691,"independent original47 scope")
    need(len(before["nets"])==143820 and len(before["instances"])==154480 and len(before["protected"])==1691,"complete original native snapshot census")
    reversal=n.read(ROOT/"bulk-postdrt-antenna/narrow47-reversal-proof.json")
    need(reversal["all_fields_equal"]is True and reversal["full_snapshot_pin"]==reversal["reversed_snapshot_pin"]==n.native.fp(ROOT/"bulk-postdrt-antenna/snapshot-before.json"),"authenticated full original reversal")
    del before;gc.collect()
    command=n.read(ROOT/"bulk-postdrt-supervision/narrow47-actual-original64-route.command.json")
    need(command["supervision_failure"]=="maximum_group_rss"and command["returncode"]==-15,"actual failed route retained, never reclassified successful")
    for source,destination in COPIES.items():
        target=Path("/work/out")/destination
        need(not target.exists(),"exclusive recovery destination")
        target.parent.mkdir(parents=True,exist_ok=True)
        with (ROOT/source).open("rb")as r,target.open("xb")as w:shutil.copyfileobj(r,w,4*1024**2)
        need(n.native.fp(target)==pins[source],"byte-identical recovered native input")
    for name,pin in pins.items():need(n.native.fp(ROOT/name)==pin,"recovery inputs unchanged")
    n.save("narrow47-recovery.json",dict(status="AUTHENTICATED_ITERATION19_FOR_ORIGINAL_RESTORATION_AND_AUDIT",
        source_run=41415994457,candidate=n.native.fp(WORK/"routed-fixed.odb"),selected=47,protected_clocks=1691,
        current_route_calls=0,router_internal_state_resume_claimed=False,original_route_failed=True,
        routing_complete=False,**n.p.FLAGS))
if __name__=="__main__":main()
