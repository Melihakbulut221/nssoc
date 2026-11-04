"""Hosted synthetic boundary controls; no native routing performed."""
import copy,json,os,sys,tempfile,time,types
from pathlib import Path
from mainchip_route47_memory import budget,checker,configure,CONTAINER_BYTES,ROUTE_RSS_KIB,MIN_AVAILABLE_KIB,FRESH_WINDOWS,WINDOW_RETRIES,WINDOW_ERROR
ROOT=Path(__file__).resolve().parents[1]
class Stalled:
    """First clock read is real; every later read is one second later."""
    def __init__(self):self.began=None
    def __getattr__(self,name):return getattr(time,name)
    def monotonic(self):
        if self.began is None:self.began=time.monotonic();return self.began
        return self.began+1.0
def window_controls(cases):
    sys.path.insert(0,str(ROOT/"original/scripts"))
    import mainchip_exit_checked_supervision as supervision
    sup=supervision.supervisor();trace=Path(tempfile.mkdtemp());sup.TRACE=trace;sup.OUT=trace
    real=sup.memory_snapshot;plan=[]
    def staged(pgid,meminfo_path="/proc/meminfo"):
        sup.time=Stalled()if plan and plan.pop(0)else time
        try:return real(pgid,meminfo_path)
        finally:sup.time=time
    staged.exit_checked_adapter=True;sup.memory_snapshot=staged
    proof=configure(sup,CONTAINER_BYTES)
    assert proof["snapshot_window"]["fresh_windows_per_sample"]==FRESH_WINDOWS and sup.supervised.__globals__["memory_snapshot"]is sup.memory_snapshot
    def retries():
        path=trace/"events.jsonl"
        return [json.loads(x)for x in path.read_text().splitlines()if json.loads(x)["event"]=="memory_window_retry"]if path.exists()else[]
    def refuse(name,meminfo_path="/proc/meminfo",cause=None):
        before=len(retries())
        try:sup.memory_snapshot(os.getpgrp(),meminfo_path)
        except sup.SupervisionFailure as error:
            if cause is not None:assert str(error.__cause__)==cause,(name,error.__cause__)
        else:raise AssertionError(name)
        return len(retries())-before
    plan[:]=[True];value=sup.memory_snapshot(os.getpgrp())
    assert value["sampling_attempts"]==1 and value["group_rss_kib"]>0 and value["members"]and len(retries())==1
    cases.append("one overrun window retaken as complete fresh snapshot")
    plan[:]=[True]*FRESH_WINDOWS
    assert refuse("persistent overrun",cause=WINDOW_ERROR)==FRESH_WINDOWS-1 and not plan
    cases.append("refuse window overrun on every fresh window")
    missing=Path(tempfile.mkdtemp())/"absent-meminfo"
    assert refuse("unreadable meminfo",str(missing))==0
    cases.append("refuse unreadable counter without retry")
    malformed=missing.with_name("malformed-meminfo");malformed.write_text("MemTotal: 1 kB\n")
    assert refuse("malformed meminfo",str(malformed),"Malformed MemAvailable counter or units")==0
    cases.append("refuse malformed counter without retry")
    plan[:]=[True];state=sup.memory_snapshot.window_retry_state;state["retried"]=WINDOW_RETRIES
    assert refuse("retry budget spent",cause=WINDOW_ERROR)==0
    cases.append("refuse overrun after supervisor retry budget")
    try:configure(sup,CONTAINER_BYTES)
    except ValueError:cases.append("refuse second sampler adapter")
    else:raise AssertionError("second sampler adapter")
    return dict(proof["snapshot_window"],retry_events=len(retries()))
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
    sup=types.ModuleType("synthetic_owned_supervisor")
    sup.SECONDS=1200;sup.MIN_AVAILABLE_KIB=MIN_AVAILABLE_KIB;sup.MAX_GROUP_RSS_KIB=10485760
    for name in ("supervised","heartbeat","stop_process","event","sample","wrap","interrupted"):
        exec("def "+name+"(): return MAX_GROUP_RSS_KIB",sup.__dict__)
    exec("def supervised(*,max_group_rss_kib=10485760): return max_group_rss_kib",sup.__dict__)
    exec("class SupervisionFailure(RuntimeError): pass",sup.__dict__)
    sup._memory_counter=types.SimpleNamespace(RESAMPLE_WINDOW=.10,CounterError=type("CounterError",(RuntimeError,),{}))
    sup.memory_snapshot=lambda pgid,meminfo_path="/proc/meminfo":{};sup.memory_snapshot.exit_checked_adapter=True
    configure(sup,CONTAINER_BYTES)
    assert sup.supervised()==ROUTE_RSS_KIB
    cases.append("owned globals use new bound")
    reject("double application not original policy",lambda:configure(sup,CONTAINER_BYTES))
    windows=window_controls(cases)
    assert len(cases)==25,len(cases)
    out=ROOT/"route47-memory-controls";out.mkdir()
    (out/"result.json").write_text(json.dumps(dict(status="PASS_ROUTE47_11GIB_MEMORY_POLICY_CONTROLS",
      cases=cases,count=len(cases),budget=proof,derivation=derivation,snapshot_windows=windows,source_controls_only=True,
      native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
