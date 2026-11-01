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
    require(len(rs)==len(caps)==len(shunts)==1,"unique series resistor, parallel MIM and ground shunt")
    require(any(t["native_net"]=="avss"and t["native_cluster"]==23 for t in shunts[0]["terminals"]),"actual ground shunt")
    return dict(source_cluster=from_cluster,base_cluster=to_cluster,series=rs[0],shunt=shunts[0],feedforward=caps[0])
def analyze(report,composition,t,data):
    records=composition["device_records"];byid={r["native_id"]:r for r in records}
    require(len(byid)==len(records)==500,"complete unique native500")
    aliases=report["binding"]["aliases"]
    def v(name):
        name=aliases.get(name,name)
        return np.zeros(len(t))if name=="0"else data["v("+name+")"]
    mask=(t>=3e-9)&(t<=34.25e-9);axis=t[mask]
    paths={}
    for label,source,positive,negative,output in [
        ("A_to_AD","a",123,125,"ad"),("C_to_CD","c",128,130,"cd"),
        ("B_to_S0","b",131,132,"s0"),("B_to_S1","b",149,150,"s1")]:
        p=byid[positive];n=byid[negative]
        require(p["model"]==n["model"]=="npn13g2","exact receiver HBT model")
        pd=report["devices"]["xpd."+p["instance"].lower()];nd=report["devices"]["xpd."+n["instance"].lower()]
        for row,dev in [(p,pd),(n,nd)]:
            require(dev["nodes"]==["xpd."+x["node"].lower()for x in row["terminals"]]and dev["nx"]==int(row["parameters"]["nx"]),"full native receiver identity")
        require(aliases["xpd."+output+"n"]==pd["nodes"][0] and aliases["xpd."+output+"p"]==nd["nodes"][0],"collector polarity of receiver")
        qp=report["binding"]["probe_witnesses"][source+"qp"];qn=report["binding"]["probe_witnesses"][source+"qn"]
        branches=dict(positive=passive_branch(records,qp["native_cluster"],terminal(p,"B")["native_cluster"]),
                      negative=passive_branch(records,qn["native_cluster"],terminal(n,"B")["native_cluster"]))
        traces=dict(sampler=v(qp["probe"])-v(qn["probe"]),base=v(pd["nodes"][1])-v(nd["nodes"][1]),
                    buffer=v("xpd."+output+"p")-v("xpd."+output+"n"))
        levels=dict(sampler=.05,base=.01,buffer=.05)
        events={k:transitions(axis,x[mask],levels[k])for k,x in traces.items()}
        stages={key:match_events(events[a],events[b],125e-12)for key,a,b in[
            ("sampler_to_base","sampler","base"),("base_to_buffer","base","buffer"),("sampler_to_buffer","sampler","buffer")]}
        paths[label]=dict(source_sampler=source,receiver_ids=[positive,negative],branches=branches,
            hysteresis_v=levels,transitions=events,matches=stages,
            summary={k:v["summary"]for k,v in stages.items()})
    return dict(status="COMPLETE_LOADED_TRANSFER_DIAGNOSIS",window_s=[float(axis[0]),float(axis[-1])],
        matching_rule="one same-direction confirmed crossing before the next source transition and within125ps; missing/ambiguous and outside events retained",
        diagnostic_hysteresis_is_not_an_electrical_acceptance_gate=True,
        all_original_measurements_unchanged=True,physical_acceptance=False,full_phy_accepted=False,
        final_timing_complete=False,paths=paths)
