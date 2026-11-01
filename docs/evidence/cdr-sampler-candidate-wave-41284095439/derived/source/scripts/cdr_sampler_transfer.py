#!/usr/bin/env python3
"""Diagnostic transfer timing on authenticated native waves; never an acceptance gate."""
import math
import numpy as np
def require(ok,msg):
    if not ok:raise ValueError(msg)
def transitions(t,x,hysteresis):
    require(t.ndim==x.ndim==1 and t.shape==x.shape and len(t)>1,"matching one-dimensional axes")
    require(np.isfinite(t).all() and np.isfinite(x).all() and np.all(np.diff(t)>0),"finite strictly increasing capture")
    require(math.isfinite(hysteresis) and hysteresis>0,"positive diagnostic hysteresis")
    strong=np.flatnonzero(abs(x)>=hysteresis)
    if not len(strong):return []
    last=int(strong[0]);state=1 if x[last]>0 else -1;out=[]
    for raw_i in strong[1:]:
        i=int(raw_i);new=1 if x[i]>0 else -1
        if new==state:last=i;continue
        j=i-1
        while j>last and x[j]*new>=0:j-=1
        require(x[j]*new<0 and x[j+1]*new>=0,"bracketed observed crossing")
        fraction=float(-x[j]/(x[j+1]-x[j]))
        when=float(t[j]+fraction*(t[j+1]-t[j]))
        out.append(dict(time_s=when,direction=new,confirmed_at_s=float(t[i]),
            bracket_rows=[j,j+1],bracket_v=[float(x[j]),float(x[j+1])]))
        state=new;last=i
    return out
def match_events(source,target,window):
    require(math.isfinite(window) and window>0,"positive matching window")
    for events in (source,target):
        require(all(math.isfinite(e["time_s"])and e["direction"]in(-1,1)for e in events),"valid events")
        require(all(a["time_s"]<b["time_s"]for a,b in zip(events,events[1:])),"strict event order")
    rows=[]
    for i,e in enumerate(source):
        upper=min(e["time_s"]+window,source[i+1]["time_s"]if i+1<len(source)else math.inf)
        same=[(j,x)for j,x in enumerate(target)if x["direction"]==e["direction"]]
        candidates=[(j,x)for j,x in same if e["time_s"]<=x["time_s"]<upper]
        prior=[(j,x)for j,x in same if x["time_s"]<e["time_s"]]
        future=[(j,x)for j,x in same if x["time_s"]>=upper]
        row=dict(source_index=i,source=e,window_end_s=upper,
            target_candidates=[dict(index=j,event=x)for j,x in candidates],
            preceding_same_direction=dict(index=prior[-1][0],event=prior[-1][1])if prior else None,
            following_same_direction=dict(index=future[0][0],event=future[0][1])if future else None,
            status="matched"if len(candidates)==1 else("missing_in_current_input_state"if not candidates else"ambiguous"))
        if len(candidates)==1:row["delay_s"]=candidates[0][1]["time_s"]-e["time_s"]
        rows.append(row)
    matched=[r["delay_s"]for r in rows if r["status"]=="matched"]
    summary=dict(source_transitions=len(source),target_transitions=len(target),
        matched=len(matched),missing=sum(r["status"]=="missing_in_current_input_state"for r in rows),
        ambiguous=sum(r["status"]=="ambiguous"for r in rows))
    if matched:summary.update(minimum_delay_s=min(matched),median_delay_s=float(np.median(matched)),
        p95_delay_s=float(np.quantile(matched,.95)),maximum_delay_s=max(matched))
    return dict(summary=summary,events=rows)
def terminal(row,name):
    found=[x for x in row["terminals"]if x["terminal"]==name]
    require(len(found)==1,"one native terminal "+name);return found[0]
def passive_branch(records,from_cluster,to_cluster):
    def endpoints(row,model,names):
        if row["model"]!=model:return False
        return {terminal(row,n)["native_cluster"]for n in names}=={from_cluster,to_cluster}
    rs=[r for r in records if endpoints(r,"rppd",("rppd_1","rppd_2"))]
    caps=[r for r in records if endpoints(r,"cap_cmim",("mim_top","mim_btm"))]
    shunts=[r for r in records if r["model"]=="rppd"and
        {terminal(r,n)["native_cluster"]for n in("rppd_1","rppd_2")}=={to_cluster,23}]
    require(len(rs)==len(caps)==len(shunts)==1,"unique series resistor, parallel MIM and ground shunt "+str((from_cluster,to_cluster,len(rs),len(caps),len(shunts))))
    require(any(t["native_net"]=="avss"and t["native_cluster"]==23 for t in shunts[0]["terminals"]),"actual ground shunt")
    return dict(source_cluster=from_cluster,base_cluster=to_cluster,series=rs[0],shunt=shunts[0],feedforward=caps[0])
PATHS=[("A_to_AD","a",123,125,"ad"),("C_to_CD","c",128,130,"cd"),
       ("D_to_S0","d",131,132,"s0"),("D_to_S1","d",149,150,"s1")]
def describe(report,composition):
    records=composition["device_records"];byid={r["native_id"]:r for r in records}
    require(len(byid)==len(records)==500,"complete unique native500")
    aliases=report["binding"]["aliases"];paths={}
    for label,source,positive,negative,output in PATHS:
        p=byid[positive];n=byid[negative]
        require(p["model"]==n["model"]=="npn13g2","exact receiver HBT model")
        pd=report["devices"]["xpd."+p["instance"].lower()];nd=report["devices"]["xpd."+n["instance"].lower()]
        for row,dev in [(p,pd),(n,nd)]:
            require(dev["nodes"]==["xpd."+x["node"].lower()for x in row["terminals"]]and dev["nx"]==int(row["parameters"]["nx"]),"full native receiver identity")
        require(aliases["xpd."+output+"n"]==pd["nodes"][0] and aliases["xpd."+output+"p"]==nd["nodes"][0],"collector polarity of receiver")
        qp=report["binding"]["probe_witnesses"][source+"qp"];qn=report["binding"]["probe_witnesses"][source+"qn"]
        branches=dict(positive=passive_branch(records,qp["native_cluster"],terminal(p,"B")["native_cluster"]),
                      negative=passive_branch(records,qn["native_cluster"],terminal(n,"B")["native_cluster"]))
        paths[label]=dict(source_sampler=source,receiver_ids=[positive,negative],branches=branches,
            sampler_nodes=[qp["probe"],qn["probe"]],base_nodes=[pd["nodes"][1],nd["nodes"][1]],
            buffer_nodes=["xpd."+output+"p","xpd."+output+"n"])
    return paths
def expected_lags(source,target):
    require(len(source)==len(target) and len(source)>4 and all(x in(0,1)for x in source+target),"complete expected binary sequences")
    matches=[]
    for lag in range(-2,3):
        pairs=[(target[i],source[i-lag])for i in range(len(target))if 0<=i-lag<len(source)]
        if all(a==b for a,b in pairs):matches.append(dict(target_index_minus_source_index=lag,compared=len(pairs)))
    return matches
def analyze(report,composition,t,data):
    description=describe(report,composition)
    aliases=report["binding"]["aliases"]
    def v(name):
        name=aliases.get(name,name)
        return np.zeros(len(t))if name=="0"else data["v("+name+")"]
    mask=(t>=3e-9)&(t<=34.25e-9);axis=t[mask];paths={}
    for label,desc in description.items():
        traces={name:v(nodes[0])-v(nodes[1])for name,nodes in[
            ("sampler",desc["sampler_nodes"]),("base",desc["base_nodes"]),("buffer",desc["buffer_nodes"])]}
        levels=dict(sampler=.05,base=.01,buffer=.05)
        events={k:transitions(axis,x[mask],levels[k])for k,x in traces.items()}
        stages={key:match_events(events[a],events[b],125e-12)for key,a,b in[
            ("sampler_to_base","sampler","base"),("base_to_buffer","base","buffer"),("sampler_to_buffer","sampler","buffer")]}
        paths[label]=dict(**desc,hysteresis_v=levels,transitions=events,matches=stages,
            summary={k:v["summary"]for k,v in stages.items()})
    retimers={}
    for source,target in [("a","c"),("b","d")]:
        traces={}
        for tag in (source,target):
            points=report["binding"]["sampler_points"]
            traces[tag]=v(points[tag+"qp"])-v(points[tag+"qn"])
        events={tag:transitions(axis,x[mask],.05)for tag,x in traces.items()}
        result=match_events(events[source],events[target],125e-12)
        retimers[source+"_to_"+target]=dict(source_sampler=source,target_sampler=target,
            expected_sequence_lags=expected_lags(report["expected_samples"][source],report["expected_samples"][target]),
            diagnostic_hysteresis_v=.05,summary=result["summary"],events=result["events"],
            source_transitions=events[source],target_transitions=events[target],
            interpretation="Observed crossing correspondence with pipeline expected-sequence lag recorded; not an acceptance gate.")
    return dict(status="COMPLETE_LOADED_TRANSFER_DIAGNOSIS",window_s=[float(axis[0]),float(axis[-1])],
        matching_rule="one same-direction confirmed crossing before the next source transition and within125ps; missing/ambiguous and outside events retained",
        diagnostic_hysteresis_is_not_an_electrical_acceptance_gate=True,
        all_original_measurements_unchanged=True,physical_acceptance=False,full_phy_accepted=False,
        final_timing_complete=False,paths=paths,retimer_observations=retimers)
def preflight():
    import argparse,json,os,pathlib
    import cdr_sampler_candidate_wave as core
    parser=argparse.ArgumentParser();parser.add_argument("--preflight",action="store_true",required=True);parser.parse_args()
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1","single cloud-only preflight")
    cfg=json.loads((core.ROOT/core.CONFIG).read_bytes());core.source_guard(cfg)
    report=json.loads(core.remote(cfg["derived"]["measurement.json"]))
    baseline=json.loads(core.remote(cfg["derived"]["topology-baseline.json"]))
    index=json.loads(core.remote(cfg["derived"]["index.json"]))
    composition=core.expected_composition(cfg,baseline,index)
    require(report["current_context"]==cfg["producer_context"],"exact preflight native context")
    paths=describe(report,composition)
    result=dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),
        status="COMPLETE_AUTHENTICATED_TRANSFER_TOPOLOGY_PREFLIGHT",native_archive_acquired=False,
        producer_context=cfg["producer_context"],candidate_target_source=cfg["candidate_target_source"],complete_composition_digest_matched=True,input_pins={k:cfg["derived"][k]for k in("measurement.json","topology-baseline.json","index.json")},paths=paths)
    out=pathlib.Path("cloud-sampler-candidate-controls/topology-preflight.json")
    require(not out.exists(),"exclusive preflight output");out.write_bytes(core.encode(result))
    print(json.dumps(dict(status=result["status"],paths=list(paths),native_archive_acquired=False)),flush=True)
if __name__=="__main__":preflight()
