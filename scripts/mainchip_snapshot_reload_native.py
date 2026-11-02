"""Actual pinned OpenROAD partial-ODB load/write/reload and full native scope audit."""
import gc, json, sys
from pathlib import Path
sys.path.insert(0, "/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna_native as native
from mainchip_bulk_postdrt_antenna_native import n, p
from mainchip_snapshot_reload_contract import compare_scope, need
ROOT=Path("/work/reload-inputs")
DATA=Path("/work/out/bulk-postdrt-antenna")
WORK=Path("/work/out/work/bulk-postdrt-antenna")
CANDIDATE=ROOT/"work/bulk-postdrt-antenna/drt_iter20.odb"
def read(path): return json.loads(path.read_bytes())
def main():
    proof=read(Path("/work/snapshot-selected-pins.json"))
    for name, pin in proof.items(): need(native.fp(ROOT/name)==pin, "authenticated input "+name)
    stage=read(ROOT/"bulk-postdrt-antenna/full-route-stage.json")
    need(not stage["route_returned"] and not stage["snapshot_reload_qualified"], "partial route only")
    need({v["iteration"]for v in stage["snapshot_inventory"].values()}==set(range(26)), "complete retained iteration census")
    need(native.fp(CANDIDATE)=={k:stage["snapshot_inventory"]["drt_iter20.odb"][k] for k in ("bytes","sha256")}, "actual selected retained iteration20")
    original_path=ROOT/"bulk-postdrt-antenna/stale-wire-cleared-snapshot.json"
    original=read(original_path)
    protected=original["protected"]
    need(len(original["instances"])==154480 and len(original["nets"])==143820, "full actual source census")
    need(len(protected)==1691, "original protected clock census")
    del original;gc.collect()
    first=native.snapshot(CANDIDATE, WORK/"snapshot-before.def", protected)
    need(len(first["instances"])==154480 and len(first["nets"])==143820, "full actual loaded census")
    native.save(DATA/"snapshot-before.json", first)
    del first;gc.collect()
    db, block=n.load(CANDIDATE)
    try:
        need(not list(block.getChildren()), "no hidden child blocks")
        odb.write_db(db, str(WORK/"snapshot-reloaded.odb"))
    finally: odb.dbDatabase.destroy(db)
    second=native.snapshot(WORK/"snapshot-reloaded.odb", WORK/"snapshot-after.def", protected)
    native.save(DATA/"snapshot-after.json", second)
    del second;gc.collect()
    before_pin=native.fp(DATA/"snapshot-before.json")
    after_pin=native.fp(DATA/"snapshot-after.json")
    need(before_pin==after_pin, "complete native snapshots and exported DEF unchanged by write/reload")
    native.save(DATA/"snapshot-roundtrip.json", dict(
        status="PASS_COMPLETE_PARTIAL_ODB_LOAD_WRITE_RELOAD",
        candidate=native.fp(CANDIDATE), rewritten=native.fp(WORK/"snapshot-reloaded.odb"),
        complete_native_snapshot=before_pin, instances=154480,nets=143820,
        protected_clock_records=1691,routing_complete=False,**p.FLAGS))
    scope=read(ROOT/"bulk-postdrt-antenna/targeted-routing-scope.json")
    need(len(scope["routing_nets"])==828, "original exact targeted route scope")
    original=read(original_path);current=read(DATA/"snapshot-before.json")
    result=compare_scope(original,current,scope)
    native.save(DATA/"snapshot-scoped-delta.json",result)
    del original,current;gc.collect()
    for name,pin in proof.items():need(native.fp(ROOT/name)==pin,"original inputs unchanged "+name)
    native.save(DATA/"snapshot-reload-result.json",dict(
        status="PASS_PARTIAL_SNAPSHOT_ROUNDTRIP_AND_ORIGINAL_SCOPED_DELTA",
        candidate=native.fp(CANDIDATE),scope=result,roundtrip=read(DATA/"snapshot-roundtrip.json"),
        snapshot_reload_qualified=True,routing_complete=False,diode_PG_audit_complete=False,
        original_class_restoration_complete=False,**p.FLAGS))
if __name__=="__main__":main()
