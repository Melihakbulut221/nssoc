"""Hosted synthetic boundary controls; no native routing performed."""
import copy,json,sys
from pathlib import Path
from mainchip_route47_memory import budget,checker,configure,CONTAINER_BYTES,ROUTE_RSS_KIB,MIN_AVAILABLE_KIB
ROOT=Path(__file__).resolve().parents[1]
def main():
    cases=[]
    def reject(name,fn):
        try:fn()
        except ValueError:cases.append("refuse "+name)
        else:raise AssertionError(name)
    proof=budget(CONTAINER_BYTES,ROUTE_RSS_KIB,MIN_AVAILABLE_KIB);cases.append("exact 11 GiB within 12 GiB")
    for name,args in [
      ("old container changed",(CONTAINER_BYTES+1,ROUTE_RSS_KIB,MIN_AVAILABLE_KIB)),
      ("RSS above new cap",(CONTAINER_BYTES,ROUTE_RSS_KIB+1,MIN_AVAILABLE_KIB)),
      ("old RSS policy mislabeled",(CONTAINER_BYTES,10485760,MIN_AVAILABLE_KIB)),
      ("host reserve lowered",(CONTAINER_BYTES,ROUTE_RSS_KIB,MIN_AVAILABLE_KIB-1)),
      ("boolean RSS",(CONTAINER_BYTES,True,MIN_AVAILABLE_KIB))]:
        reject(name,lambda args=args:budget(*args))
    raw=(ROOT/"original/scripts/mainchip_exit_checked_command_evidence.py").read_bytes()
    module,derivation=checker(raw);cases.append("authenticated unchanged checker bodies")
    reject("checker source mutation",lambda:checker(raw+b"\n"))
    record=dict(returncode=0,supervision_failure=None,pid=100,minimum_available_kib=MIN_AVAILABLE_KIB,
        maximum_group_rss_kib=ROUTE_RSS_KIB,elapsed_seconds=1.0,requested_timeout_seconds=1200,
        process_group_cleanup=dict(signals=[],remaining_live=[],remaining_nonrunning=[]),
        last_memory_sentinel_sample=dict(available_kib=MIN_AVAILABLE_KIB,group_rss_kib=ROUTE_RSS_KIB),
        memory_read_error=None,memory_terminal_resolution=None)
    module.validate(record,1200);cases.append("actual checker accepts exact RSS and host reserve boundary")
    for name,changes in [
      ("RSS boundary exceeded",{"last_memory_sentinel_sample":dict(available_kib=MIN_AVAILABLE_KIB,group_rss_kib=ROUTE_RSS_KIB+1)}),
      ("host reserve violated",{"last_memory_sentinel_sample":dict(available_kib=MIN_AVAILABLE_KIB-1,group_rss_kib=1)}),
      ("failed exit",{"returncode":1}),("signalled exit",{"returncode":-15}),
      ("old limits in record",{"maximum_group_rss_kib":10485760}),
      ("live child",{"process_group_cleanup":dict(signals=[],remaining_live=[100],remaining_nonrunning=[])}),
      ("recorded memory failure",{"supervision_failure":"maximum_group_rss"}),
      ("unresolved missing counter",{"memory_read_error":"missing","memory_terminal_resolution":None})]:
        changed=copy.deepcopy(record);changed.update(changes)
        reject(name,lambda changed=changed:module.validate(changed,1200))
    import types
    sup=types.ModuleType("synthetic_owned_supervisor")
    sup.SECONDS=1200;sup.MIN_AVAILABLE_KIB=MIN_AVAILABLE_KIB;sup.MAX_GROUP_RSS_KIB=10485760
    for name in ("supervised","heartbeat","stop_process","event","sample","wrap","interrupted"):
        exec("def "+name+"(): return MAX_GROUP_RSS_KIB",sup.__dict__)
    exec("def supervised(*,max_group_rss_kib=10485760): return max_group_rss_kib",sup.__dict__)
    configure(sup,CONTAINER_BYTES)
    assert sup.supervised()==ROUTE_RSS_KIB
    cases.append("owned globals use new bound")
    reject("double application not original policy",lambda:configure(sup,CONTAINER_BYTES))
    assert len(cases)==19,len(cases)
    out=ROOT/"route47-memory-controls";out.mkdir()
    (out/"result.json").write_text(json.dumps(dict(status="PASS_ROUTE47_11GIB_MEMORY_POLICY_CONTROLS",
      cases=cases,count=len(cases),budget=proof,derivation=derivation,source_controls_only=True,
      native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
