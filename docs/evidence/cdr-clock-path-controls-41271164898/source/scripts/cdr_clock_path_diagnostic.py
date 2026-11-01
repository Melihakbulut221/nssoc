#!/usr/bin/env python3
"""Existing complete-wave clock arrival and sampler settling decomposition.
No simulator, no geometry mutation and no changed acceptance predicate.
"""
import itertools,json,os,pathlib,resource,traceback
import numpy as np
import cdr_via2_m3_wave_diagnostic as d
def axes(t,values):
    d.require(t.ndim==values.ndim==1 and len(t)==len(values) and len(t)>1,"complete one-dimensional axes")
    d.require(np.isfinite(t).all() and np.isfinite(values).all() and np.all(np.diff(t)>0),"finite strictly increasing native time")
def crossings(t,x,low,high,direction):
    d.require(direction in (-1,1) and np.isfinite(low) and np.isfinite(high) and t[0]<=low<high<=t[-1],"owned crossing window")
    lo=max(0,int(np.searchsorted(t,low))-1);hi=min(len(t),int(np.searchsorted(t,high,side="right"))+1)
    y=x[lo:hi]*direction;tt=t[lo:hi]
    ids=np.flatnonzero((y[:-1]<=0)&(y[1:]>0));answer=[]
    for i in ids:
        when=float(tt[i]+(-y[i])*(tt[i+1]-tt[i])/(y[i+1]-y[i]))
        if low<=when<=high:answer.append(when)
    return answer
def clock_groups(records):
    groups={}
    for row in records:
        if row["model"]!="npn13g2":continue
        terminals={x["terminal"]:x for x in row["terminals"]}
        if terminals["B"]["native_net"] not in ("cp","cn"):continue
        tail=terminals["E"]["native_net"];group=groups.setdefault(tail,{"cp":[],"cn":[]})
        group[terminals["B"]["native_net"]].append(row)
    for tail,g in groups.items():
        d.require(g["cp"] and g["cn"],"both clock polarities for shared physical tail "+tail)
        ids=[x["native_id"] for v in g.values()for x in v]
        d.require(len(ids)==len(set(ids)),"unique clock transistor identity")
    return groups
def terminal(row,role):
    matches=[t for t in row["terminals"] if t["terminal"]==role]
    d.require(len(matches)==1,"unique native terminal")
    return matches[0]
def summary(values):
    a=np.asarray(values,dtype=float)
    return dict(count=len(a),minimum=float(a.min()),median=float(np.median(a)),maximum=float(a.max()))if len(a)else dict(count=0)
def decompose(report,composition,t,data,original):
    records=composition["device_records"]
    d.require(len(records)==500 and len({r["native_id"]for r in records})==500,"all500 native devices")
    hbts=[r for r in records if r["model"]=="npn13g2"]
    d.require(len(hbts)==124,"all124 HBT identities")
    for row in hbts:
        name="xpd."+row["instance"].lower();dev=report["devices"][name]
        d.require(dev["native_id"]==row["native_id"] and dev["nx"]==int(row["parameters"]["nx"]),"report/composition device identity")
        d.require(dev["nodes"]==["xpd."+terminal(row,k)["node"].lower() for k in ("C","B","E","S")],"exact terminal probes")
    aliases=report["binding"]["aliases"]
    def v(name):
        return data["v("+aliases.get(name,name)+")"]
    ext=v("cp")-v("cn");axes(t,ext)
    groups=clock_groups(records)
    d.require(len(groups)==8 and sum(len(v)for g in groups.values()for v in g.values())==32,"all8 sampler clock tails and32 native clock devices")
    port_edges={};edge_inputs=[]
    for direction in (1,-1):
        for bit in range(1,256):
            nominal=d.START+(bit+(.5 if direction==1 else 0))*d.UI
            low=nominal-.45*d.UI;high=nominal+.45*d.UI
            observed=crossings(t,ext,low,high,direction)
            d.require(len(observed)==1,"one actual external clock edge in full bounded window")
            port_edges[(direction,bit)]=observed[0]
            edge_inputs.append(dict(direction=direction,bit=bit,nominal_s=nominal,external_s=observed[0]))
    output_pairs={tag:[report["binding"]["sampler_points"][tag+"q"+p]for p in("p","n")]for tag in "abcd"}
    by_probe={"xpd."+x["node"].lower():x["native_net"]for r in records for x in r["terminals"]}
    ownership={}
    for tag,probes in output_pairs.items():
        outputnets={by_probe[p]for p in probes}
        preceding={terminal(r,"B")["native_net"]for r in hbts if terminal(r,"C")["native_net"]in outputnets}-outputnets
        ownership[tag]={}
        for label,nets in (("output",outputnets),("preceding",preceding)):
            emitters={terminal(r,"E")["native_net"]for r in hbts if terminal(r,"C")["native_net"]in nets}
            ownership[tag][label]=sorted(tail for tail,g in groups.items()if emitters&{terminal(r,"C")["native_net"]for a in g.values()for r in a})
        d.require(len(ownership[tag]["output"])==1,"one physical output clock-tail group per sampler")
    clock_results={};clock_lookup={}
    for tail,g in groups.items():
        pairs=[]
        for cp,cn in itertools.product(g["cp"],g["cn"]):
            p="xpd."+terminal(cp,"B")["node"].lower();n="xpd."+terminal(cn,"B")["node"].lower()
            pv=v(p);nv=v(n);delta=pv-nv;axes(t,delta)
            entries=[];delays=[]
            for edge in edge_inputs:
                nominal=edge["nominal_s"];direction=edge["direction"];bit=edge["bit"]
                local=crossings(t,delta,nominal-.45*d.UI,nominal+.45*d.UI,direction)
                unique=len(local)==1
                row=dict(**edge,local_crossings_s=local,unique=unique)
                if unique:
                    row.update(delay_from_external_s=local[0]-edge["external_s"],local_common_mode_v=float(np.interp(local[0],t,(pv+nv)/2)))
                    delays.append(row["delay_from_external_s"])
                entries.append(row);clock_lookup[(tail,cp["native_id"],cn["native_id"],direction,bit)]=row
            pairs.append(dict(cp_device=cp["native_id"],cn_device=cn["native_id"],cp_probe=p,cn_probe=n,
                              delay_summary_s=summary(delays),nonunique_count=sum(not e["unique"]for e in entries),all510_edges=entries))
        clock_results[tail]=dict(cp_devices=[r["native_id"]for r in g["cp"]],cn_devices=[r["native_id"]for r in g["cn"]],pairs=pairs)
    stages={}
    for tag in "abcd":
        direction=-1 if tag=="b"else 1
        expected=report["expected_samples"][tag];delays=original["stages"][tag]["metrics"]["clock_to_valid_by_bit_s"]
        d.require(len(expected)==len(delays)==255,"all sampler data bits")
        p,n=output_pairs[tag];delta=v(p)-v(n);rows=[]
        tail=ownership[tag]["output"][0];g=groups[tail]
        for bit,(value,delay)in enumerate(zip(expected,delays,strict=True),1):
            nominal=d.START+(bit+(.5 if direction==1 else 0))*d.UI;deadline=nominal+.3*d.UI
            clocks=[clock_lookup[(tail,cp["native_id"],cn["native_id"],direction,bit)] for cp,cn in itertools.product(g["cp"],g["cn"])]
            rows.append(dict(bit=bit,expected=value,nominal_s=nominal,original_clock_to_valid_s=delay,
                 deadline_s=deadline,signed_margin_at_original_deadline_v=float(np.interp(deadline,t,delta))*(2*value-1),
                 output_common_mode_at_deadline_v=float(np.interp(deadline,t,(v(p)+v(n))/2)),
                 local_clock_pairs=[dict(unique=c["unique"],local_crossings_s=c["local_crossings_s"],
                   settled_time_minus_local_crossing_s=nominal+delay-c["local_crossings_s"][0]if c["unique"]else None)for c in clocks]))
        stages[tag]=dict(physical_clock_links=ownership[tag],positive_probe=p,negative_probe=n,all255_bits=rows,
                        original_metrics=original["stages"][tag]["metrics"])
    return dict(status="COMPLETE_ORIGINAL_CLOCK_ARRIVAL_AND_SETTLING_DIAGNOSIS",original_electrical_metrics_reproduced=True,
      clock_groups=clock_results,stages=stages,external_edges=edge_inputs,
      all_clock_pairs_preserved=True,all_sampler_bits_preserved=True,
      interpretation="Crossing and settling differences are measured correlation, not isolated cell propagation delays or proof of a fix. No crossings are discarded or selected from ambiguous windows.",**d.FLAGS)
def main():
    d.require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1","single cloud execution")
    config=json.loads((d.ROOT/d.CONFIG).read_bytes());d.source_guard(config)
    out=d.ROOT/"cloud-clock-path-diagnostic";out.mkdir(exist_ok=False)
    work=pathlib.Path(os.environ["RUNNER_TEMP"])/("nssoc-clock-path-"+os.environ["GITHUB_RUN_ID"]);work.mkdir(exist_ok=False)
    result=dict(status="INCOMPLETE_CLOCK_PATH_DIAGNOSIS",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),**d.FLAGS)
    try:
        resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
        report,wave=d.acquire(config,out,work)
        read=d.reader(d.ROOT/config["reader_path"],config["source_files"][config["reader_path"]])
        t,data,capture=read(wave,report["vectors"],d.STOP,d.STEP)
        d.require(capture==report["raw_capture"],"complete original1151-vector waveform")
        original=d.diagnose(report,t,data)
        (out/"original-reproduction.json").write_bytes(d.encode(original))
        result.update(decompose(report,json.loads((out/"composition.json").read_bytes()),t,data,original),capture=capture)
        concise={tail:[{k:p[k]for k in("cp_device","cn_device","delay_summary_s","nonunique_count")}for p in g["pairs"]]for tail,g in result["clock_groups"].items()}
        (out/"summary.json").write_bytes(d.encode(dict(status=result["status"],clock_groups=concise,stage_links={s:r["physical_clock_links"]for s,r in result["stages"].items()},**d.FLAGS)))
        d.source_guard(config)
    except BaseException as exc:
        result.update(error=repr(exc),traceback=traceback.format_exc());raise
    finally:
        (out/"result.json").write_bytes(d.encode(result));d.emit(out)
if __name__=="__main__":main()
