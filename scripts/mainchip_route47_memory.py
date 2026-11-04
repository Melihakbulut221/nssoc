"""Explicit 11 GiB RSS policy inside the unchanged 12 GiB cloud container.

A memory snapshot that only overran its own 100 ms wall-clock window is retaken
fresh, at most FRESH_WINDOWS times per sample and WINDOW_RETRIES per supervisor.
Every accepted value is a complete fresh snapshot; nothing stale is substituted.
"""
import ast,hashlib,types
ORIGINAL_RSS_KIB=10485760
ROUTE_RSS_KIB=11534336
MIN_AVAILABLE_KIB=2097152
CONTAINER_BYTES=12884901888
RESERVE_BYTES=1073741824
CHECKER_BYTES=14874
CHECKER_SHA256="059e3e4edde4a63997cc841728f02d5b6a2aaf77335cb7d1b8dba70ed7d2e321"
WINDOW_ERROR="Total memory snapshot bounded window exhausted"
WINDOW_SECONDS=.10
FRESH_WINDOWS=5
WINDOW_RETRIES=256
def need(value,message):
    if not value:raise ValueError(message)
def budget(container_bytes,rss_kib,available_kib):
    need(all(type(v)is int for v in (container_bytes,rss_kib,available_kib)),"integer resource policy")
    need(container_bytes==CONTAINER_BYTES,"unchanged 12 GiB cgroup")
    need(rss_kib==ROUTE_RSS_KIB,"exact declared 11 GiB process-group RSS")
    need(available_kib==MIN_AVAILABLE_KIB,"unchanged 2 GiB host available reserve")
    need(container_bytes-rss_kib*1024>=RESERVE_BYTES,"at least 1 GiB non-RSS cgroup reserve")
    return dict(container_bytes=container_bytes,maximum_group_rss_kib=rss_kib,
                minimum_available_kib=available_kib,non_RSS_reserve_bytes=container_bytes-rss_kib*1024,
                original_maximum_group_rss_kib=ORIGINAL_RSS_KIB,
                execution_resource_change_only=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def checker(raw):
    need(len(raw)==CHECKER_BYTES and hashlib.sha256(raw).hexdigest()==CHECKER_SHA256,"frozen evidence checker bytes")
    old=b"MAX_GROUP_RSS_KIB=10485760";new=b"MAX_GROUP_RSS_KIB=11534336"
    need(raw.count(old)==1,"single resource constant")
    changed=raw.replace(old,new,1)
    need(changed.count(new)==1 and changed.replace(new,old,1)==raw,"exact reversible resource-only change")
    before=ast.parse(raw);after=ast.parse(changed)
    funcs=lambda tree:{n.name:ast.dump(n,include_attributes=False)for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    need(funcs(before)==funcs(after),"all checker function bodies unchanged")
    module=types.ModuleType("_route47_11gib_command_evidence")
    exec(compile(changed,"<authenticated-route47-11gib-command-evidence>","exec"),module.__dict__)
    need(module.MAX_GROUP_RSS_KIB==ROUTE_RSS_KIB and module.MIN_AVAILABLE_KIB==MIN_AVAILABLE_KIB,"checker resource binding")
    return module,dict(original_sha256=CHECKER_SHA256,derived_sha256=hashlib.sha256(changed).hexdigest(),
                       all_function_bodies_unchanged=True,only_MAX_GROUP_RSS_KIB_changed=True)
def window_retry(supervisor):
    original=supervisor.memory_snapshot;counter=supervisor._memory_counter
    need(getattr(original,"exit_checked_adapter",False)and not getattr(original,"window_retry_adapter",False),"original exit-checked sampler seam")
    need(counter.RESAMPLE_WINDOW==WINDOW_SECONDS and isinstance(counter.CounterError,type),"original 100 ms snapshot window")
    state=dict(retried=0)
    def measured(pgid,meminfo_path="/proc/meminfo"):
        for window in range(1,FRESH_WINDOWS+1):
            try:return original(pgid,meminfo_path)
            except supervisor.SupervisionFailure as error:
                cause=error.__cause__
                if type(cause)is not counter.CounterError or str(cause)!=WINDOW_ERROR:raise
                if window==FRESH_WINDOWS or state["retried"]>=WINDOW_RETRIES:raise
                state["retried"]+=1
                supervisor.event("memory_window_retry",window=window,fresh_windows=FRESH_WINDOWS,
                    retried=state["retried"],maximum_retries=WINDOW_RETRIES,error=repr(cause))
    measured.exit_checked_adapter=True;measured.window_retry_adapter=True;measured.window_retry_state=state
    supervisor.memory_snapshot=measured
    return dict(window_seconds=WINDOW_SECONDS,fresh_windows_per_sample=FRESH_WINDOWS,maximum_window_retries=WINDOW_RETRIES,
                retried_error=WINDOW_ERROR,other_counter_errors_unchanged=True,stale_values_substituted=False)
def configure(supervisor,container_bytes):
    proof=budget(container_bytes,ROUTE_RSS_KIB,MIN_AVAILABLE_KIB)
    need(supervisor.SECONDS==1200 and supervisor.MAX_GROUP_RSS_KIB==ORIGINAL_RSS_KIB
         and supervisor.MIN_AVAILABLE_KIB==MIN_AVAILABLE_KIB,"original supervisor policy before explicit change")
    for name in ("supervised","heartbeat","stop_process","event","sample","wrap","interrupted"):
        need(getattr(supervisor,name).__globals__ is supervisor.__dict__,"single owned supervisor globals")
    need(supervisor.supervised.__kwdefaults__["max_group_rss_kib"]==ORIGINAL_RSS_KIB,"original supervised default RSS")
    supervisor.supervised.__kwdefaults__=dict(supervisor.supervised.__kwdefaults__,max_group_rss_kib=ROUTE_RSS_KIB)
    supervisor.MAX_GROUP_RSS_KIB=ROUTE_RSS_KIB
    need(supervisor.supervised.__globals__["MAX_GROUP_RSS_KIB"]==ROUTE_RSS_KIB,"actual runtime policy binding")
    proof["snapshot_window"]=window_retry(supervisor)
    need(supervisor.supervised.__globals__["memory_snapshot"]is supervisor.memory_snapshot,"actual runtime sampler binding")
    return proof
