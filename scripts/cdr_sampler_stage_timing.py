"""Read-only sampler stage and local clock observations from complete frozen native wave."""
import json
import numpy as np
TARGETS="scripts/cdr-sampler-stage-timing-map.json"
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def crossings(t,x):
    need(t.ndim==x.ndim==1 and len(t)==len(x)and len(t)>1,"matching one-dimensional native vectors")
    need(np.isfinite(t).all()and np.isfinite(x).all()and np.all(np.diff(t)>0),"finite monotonic native samples")
    result={}
    for label,mask in [("rising",(x[:-1]<=0)&(x[1:]>0)),("falling",(x[:-1]>=0)&(x[1:]<0))]:
        result[label]=[dict(before_index=int(i),after_index=int(i+1),lo_s=float(t[i]),hi_s=float(t[i+1]),before_v=float(x[i]),after_v=float(x[i+1]))for i in np.flatnonzero(mask)]
    return result
def associate(reference,local,window):
    need(type(window)is float and np.isfinite(window)and window>0,"positive diagnostic association window")
    rows=[];used=set()
    for i,r in enumerate(reference):
        center=(r["lo_s"]+r["hi_s"])/2
        hits=[j for j,l in enumerate(local)if abs((l["lo_s"]+l["hi_s"])/2-center)<=window]
        row=dict(reference_index=i,reference=r,candidate_indices=hits)
        if len(hits)==1:
            j=hits[0];need(j not in used,"clock match reused")
            used.add(j);l=local[j]
            row.update(local=l,delay_lower_s=l["lo_s"]-r["hi_s"],delay_upper_s=l["hi_s"]-r["lo_s"])
        rows.append(row)
    matched=[r for r in rows if "local"in r]
    return dict(rows=rows,reference_edges=len(reference),local_edges=len(local),uniquely_matched=len(matched),
      ambiguous=sum(len(r["candidate_indices"])>1 for r in rows),unmatched_reference=sum(not r["candidate_indices"]for r in rows),
      unused_local_indices=sorted(set(range(len(local)))-used),
      minimum_delay_lower_s=min((r["delay_lower_s"]for r in matched),default=None),
      maximum_delay_upper_s=max((r["delay_upper_s"]for r in matched),default=None))
def source_controls():
    t=np.array([0.,1.,2.,3.,4.]);x=np.array([-1.,0.,1.,0.,-1.])
    c=crossings(t,x)
    need([(r["before_index"],r["after_index"])for r in c["rising"]]==[(1,2)]and [(r["before_index"],r["after_index"])for r in c["falling"]]==[(3,4)],"zero plateau bracket orientation")
    ref=[dict(lo_s=1.,hi_s=1.1)];loc=[dict(lo_s=1.2,hi_s=1.3)]
    good=associate(ref,loc,.25)
    need(good["uniquely_matched"]==1 and abs(good["minimum_delay_lower_s"]-.1)<1e-12 and abs(good["maximum_delay_upper_s"]-.3)<1e-12,"bracket delay bounds")
    need(associate(ref,loc*2,.25)["ambiguous"]==1,"duplicate crossings retained as ambiguity")
    need(associate(ref,[],.25)["unmatched_reference"]==1,"missing local crossing retained")
    rejected=[]
    for label,a,b in [("nonmonotonic",t[::-1],x),("nonfinite",t,x*np.nan),("shape",t,x[:-1])]:
        try:crossings(a,b)
        except AssertionError:rejected.append(label)
        else:raise AssertionError("accepted "+label)
    return dict(status="PASS_STAGE_TIMING_DIAGNOSTIC_CONTROLS",brackets_no_interpolation=True,ambiguity_and_missing_edges_preserved=True,rejected=rejected,physical_acceptance=False)
def diagnose_stages(root,m,contract,t,d,save):
    cfg=json.loads((root/TARGETS).read_bytes())
    need(cfg["mapping_run"]==41450661063 and cfg["mapping_source"]=="22baa225789b8ec1c9ce98437196af1e48fc2918","actual full native mapping provenance")
    need(cfg["full_mapping"]==dict(bytes=796986,sha256="2beff7cbad50618c7a00100db3af5d63276a1476acb1dc56224e1822055ac06f"),"exact complete mapping reference")
    pairs=cfg["pairs"];need(len(pairs)==48,"all48 sampler data and selector devices")
    named={p["schematic"]["name"]:p for p in pairs}
    need(len(named)==48 and set(named)=={f"S{a}_{s}_{r}"for a in "ABCD"for s in "MS"for r in ("DP","DN","CS0","CS1","CH0","CH1")},"complete sampler-stage roles")
    records={int(r["native_id"]):r for r in contract["device_records"]}
    probes={}
    for name,p in named.items():
        need(p["status"]=="Match"and p["layout"]["model"]==p["schematic"]["model"]=="npn13g2","matched native HBT")
        rec=records[p["layout"]["id"]];dev=m["devices"]["xpd."+p["loaded_instance"].lower()]
        need(rec["instance"]==p["loaded_instance"]and rec["parameters"]==p["loaded_parameters"]and dev["native_id"]==rec["native_id"],"actual loaded primitive identity")
        need([x["terminal"]for x in rec["terminals"]]==["C","B","E","S"],"native HBT terminal order")
        need({q["terminal"]:dict(cluster=q["native_cluster"],name=q["native_net"])for q in rec["terminals"]}==
             {k:dict(cluster=v["cluster"],name=v["name"])for k,v in p["layout"]["terminals"].items()},"native terminals match original mapped primitive")
        probes[name]=dict(native_id=rec["native_id"],nodes=dict(zip(["C","B","E","S"],dev["nodes"],strict=True)),schematic_terminals=p["schematic"]["terminals"])
    def v(node):
        return np.zeros(len(t))if node=="0"else d["v("+node+")"]
    def at(name,terminal):return v(probes[name]["nodes"][terminal])
    start=2e-9;end=33.875e-9;ui=125e-12
    stages={};clock_summary={}
    for tag in "ABCD":
        for stage in "MS":
            prefix="S"+tag+"_"+stage+"_";pn=prefix+"DP";nn=prefix+"DN"
            data_in=at(pn,"B")-at(nn,"B")
            data_out=at(nn,"C")-at(pn,"C")
            clocks={}
            for leg in (0,1):
                cs=prefix+"CS"+str(leg);ch=prefix+"CH"+str(leg)
                cs_ref=probes[cs]["schematic_terminals"]["B"]["name"].lower()
                ch_ref=probes[ch]["schematic_terminals"]["B"]["name"].lower()
                need({cs_ref,ch_ref}=={"cp","cn"},"explicit opposite ideal clock terminals")
                actual=crossings(t,at(cs,"B")-at(ch,"B"));reference=crossings(t,v(cs_ref)-v(ch_ref))
                edges={}
                for direction in ("rising","falling"):
                    local=[r for r in actual[direction]if r["lo_s"]>=start and r["hi_s"]<=end]
                    ideal=[r for r in reference[direction]if r["lo_s"]>=start and r["hi_s"]<=end]
                    edges[direction]=associate(ideal,local,float(.25*ui))
                clocks[str(leg)]=dict(sample_selector=cs,hold_selector=ch,ideal_positive=cs_ref,ideal_negative=ch_ref,edges=edges)
                clock_summary[prefix+str(leg)]={direction:{k:v for k,v in row.items()if k not in ("rows","unused_local_indices")}for direction,row in edges.items()}
            stages[prefix]=dict(input_probes=dict(positive=probes[pn]["nodes"]["B"],negative=probes[nn]["nodes"]["B"]),
              output_probes=dict(positive=probes[nn]["nodes"]["C"],negative=probes[pn]["nodes"]["C"]),
              input_crossings={k:[r for r in a if r["lo_s"]>=start and r["hi_s"]<=end]for k,a in crossings(t,data_in).items()},
              output_crossings={k:[r for r in a if r["lo_s"]>=start and r["hi_s"]<=end]for k,a in crossings(t,data_out).items()},clocks=clocks)
    by_sampler={}
    phases=[0.,.1,.2,.3,.4,.5,.6,.75,.9]
    for tag in "abcd":
        master="S"+tag.upper()+"_M_";slave="S"+tag.upper()+"_S_"
        signals=dict(master_input=at(master+"DP","B")-at(master+"DN","B"),
          master_output=at(master+"DN","C")-at(master+"DP","C"),
          slave_input=at(slave+"DP","B")-at(slave+"DN","B"),
          slave_output=at(slave+"DN","C")-at(slave+"DP","C"),
          master_clock=at(master+"CS0","B")-at(master+"CH0","B"),
          slave_clock=at(slave+"CS0","B")-at(slave+"CH0","B"))
        # Independently reproduce the original final-output timing gate from all
        # original samples; upstream stage observations do not replace that gate.
        bits=m["expected_samples"][tag];rows=[];delays=[]
        for bit_index,bit in enumerate(bits,start=1):
            edge=start+(bit_index+(0 if tag=="b"else .5))*ui;sign=2*bit-1
            ids=np.flatnonzero((t>=edge)&(t<=edge+.95*ui));bad=ids[signals["slave_output"][ids]*sign<.1]
            delay=0. if not len(bad)else float(t[bad[-1]]-edge+.3125e-12);delays.append(delay)
            samples=[]
            for phase in phases:
                requested=edge+phase*ui;i=int(np.searchsorted(t,requested,side="left"))
                need(i<len(t)and t[i]>=requested and (i==0 or t[i-1]<requested),"first actual sample at or after requested time")
                samples.append(dict(phase_ui=phase,requested_s=requested,index=i,actual_s=float(t[i]),
                  values_v={name:float(values[i])for name,values in signals.items()}))
            rows.append(dict(bit_index=bit_index,expected=bit,edge_s=edge,original_clock_to_valid_s=delay,samples=samples))
        need(np.allclose(delays,m["sampler_checks"][tag]["clock_to_valid_by_bit_s"],atol=1e-18,rtol=0),"every original per-bit final-output delay reproduced")
        check=m["sampler_checks"][tag]
        by_sampler[tag]=dict(original_check={k:v for k,v in check.items()if not isinstance(v,(list,dict))},rows=rows,worst_bit_indices=[r["bit_index"]for r in rows if abs(r["original_clock_to_valid_s"]-max(delays))<1e-18])
    scope=dict(new_transient_executed=False,new_layout_generated=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
       measurement_limits_changed=False,clock_delay_scope="Native 0V crossing brackets; diagnostic association window +/-0.25UI; ambiguous/missing matches retained; no resampling or clock-recovery claim",
       stage_samples_scope="First existing raw sample at or after each diagnostic time; no interpolation; upstream samples are observations, not substitute acceptance gates")
    save("sampler-stage-timing.json",dict(parent=m["current_context"],mapping=cfg,probes=probes,stages=stages,samplers=by_sampler,scope=scope))
    save("sampler-stage-summary.json",dict(parent=m["current_context"],clock_summary=clock_summary,
      samplers={k:dict(original_check=v["original_check"],worst_bit_indices=v["worst_bit_indices"])for k,v in by_sampler.items()},scope=scope,all_original_per_bit_sampler_delays_reproduced=True))
