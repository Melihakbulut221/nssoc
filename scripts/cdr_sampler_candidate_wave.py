#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only complete-wave diagnosis of the rejected coupled sampler candidate."""
import argparse,ast,base64,hashlib,json,math,os,pathlib,resource,subprocess,tarfile,time,traceback,zlib
import numpy as np
import cdr_sampler_transfer as transfer
ROOT=pathlib.Path(__file__).resolve().parents[1]
CONFIG="scripts/cdr-sampler-candidate-wave-inputs.json"
REPO="repos/Melihakbulut221/nssoc/"
START=2e-9;UI=125e-12;STOP=34.25e-9;STEP=.3125e-12
FLAGS=dict(native_simulation_rerun=False,full_phy_accepted=False,final_timing_complete=False,
           physical_acceptance=False,stimulus_changed=False,gates_relaxed=False)
def require(ok,message):
    if not ok:raise ValueError(message)
def encode(v):return(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def filepin(path):
    with pathlib.Path(path).open("rb")as f:return dict(bytes=pathlib.Path(path).stat().st_size,sha256=hashlib.file_digest(f,"sha256").hexdigest())
def close(a,b,label):
    require(type(a)in(int,float)and type(b)in(int,float)and math.isfinite(a)and math.isfinite(b),"finite "+label)
    require(abs(a-b)<=max(1e-15,abs(b)*1e-10),"original metric disagreement "+label)
def reader(source,expected):
    raw=source.read_bytes();require(dict(bytes=len(raw),sha256=sha(raw))==expected,"exact original reader source")
    tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in("digest","read_streamed_wave")]
    require(len(nodes)==2 and {n.name for n in nodes}=={"digest","read_streamed_wave"}and not any(n.decorator_list for n in nodes),"unique frozen reader definitions")
    ns=dict(Path=pathlib.Path,np=np,hashlib=hashlib)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source)+":frozen-reader","exec"),ns)
    return ns["read_streamed_wave"]
def restore(archive,inventory,wanted,directory,prefix="cloud-cdr-via2-m3-loaded"):
    """Hash every member; materialize only explicitly requested native members."""
    require(set(wanted)<=set(inventory)and not directory.exists(),"exclusive selected native output")
    directory.mkdir();seen=set();dirs=set();receipt={}
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            path=pathlib.PurePosixPath(member.name.rstrip("/"))
            require(not path.is_absolute()and ".."not in path.parts and str(path)==member.name.rstrip("/")and path.parts[0]==prefix,"owned archive path")
            if member.isdir():
                require(str(path)not in dirs,"duplicate archive directory");dirs.add(str(path));continue
            require(member.isreg()and len(path.parts)>1,"regular archive member only")
            name="/".join(path.parts[1:]);require(name in inventory and name not in seen,"complete unique archive member")
            expected=inventory[name];require(member.size==expected["bytes"],"member declared byte count")
            stream=tar.extractfile(member);require(stream is not None,"regular member stream")
            destination=(directory/("selected-"+str(len(receipt))))if name in wanted else None
            output=destination.open("xb")if destination else None
            h=hashlib.sha256();count=0
            try:
                while block:=stream.read(4*1024**2):
                    count+=len(block);require(count<=expected["bytes"],"bounded member stream");h.update(block)
                    if output:output.write(block)
            finally:
                stream.close()
                if output:output.close()
            require(dict(bytes=count,sha256=h.hexdigest())==expected,"complete member digest")
            seen.add(name)
            if destination:receipt[name]=dict(path=str(destination),**expected)
    require(seen==set(inventory)and set(receipt)==set(wanted),"all indexed members and requested files")
    return dict(verified_members=len(seen),all_members_verified=True,selected=receipt)
def sample_metrics(t,p,n,expected,edges,phases,ui,step,limit):
    require(len(expected)==len(edges)and expected,"all expected bits and edges")
    delta=p-n;signed=[];delays=[];failures=[]
    for i,(bit,edge)in enumerate(zip(expected,edges,strict=True)):
        require(bit in(0,1)and edge>=t[0]and edge+.95*ui<=t[-1],"original bit and full timing window")
        sign=2*bit-1
        for phase in phases:
            when=edge+phase*ui;pv=float(np.interp(when,t,p));nv=float(np.interp(when,t,n));margin=float(np.interp(when,t,delta))*sign
            signed.append(margin)
            if margin<.1:failures.append(dict(bit_index=i+1,expected=bit,edge_s=edge,phase_ui=phase,time_s=when,positive_v=pv,negative_v=nv,signed_margin_v=margin,wrong_sign=margin<=0))
        ids=np.flatnonzero((t>=edge)&(t<=edge+.95*ui));bad=ids[delta[ids]*sign<.1]
        delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+step))
    return dict(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),
      below_100mv_samples=sum(x<.1 for x in signed),maximum_clock_to_valid_s=max(delays),clock_to_valid_by_bit_s=delays,
      passed=min(signed)>=.1 and max(delays)<=limit*ui),failures
def hbt_metrics(t,vc,vb,ve,ic,nx,start=START):
    active=t>=start;require(np.any(active)and type(nx)is int and nx>0,"active original device interval/emitter count")
    vce=vc-ve
    metrics=dict(minimum_active_vce_v=float(vce[active].min()),maximum_alltime_abs_vce_v=float(abs(vce).max()),
      maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/nx))
    indices=np.flatnonzero(active);worst=int(indices[int(np.argmin(vce[active]))])
    invalid=np.flatnonzero(active&(vce<.4))
    intervals=[]
    if len(invalid):
        for segment in np.split(invalid,np.flatnonzero(np.diff(invalid)>1)+1):
            k=int(segment[int(np.argmin(vce[segment]))])
            intervals.append(dict(first_row=int(segment[0]),last_row=int(segment[-1]),first_time_s=float(t[segment[0]]),last_time_s=float(t[segment[-1]]),
              samples=len(segment),minimum_row=k,minimum_time_s=float(t[k]),minimum_vce_v=float(vce[k])))
    return metrics,worst,intervals
def violation_events(t,vc,vb,ve,ic,nx):
    arrays=(t,vc,vb,ve,ic)
    require(all(x.ndim==1 and len(x)==len(t) and np.isfinite(x).all() for x in arrays) and len(t)>1,"complete finite event vectors")
    require(np.all(np.diff(t)>0) and type(nx)is int and nx>0 and np.any(t>=START),"event time/emitter identity")
    metrics=[
      ("minimum_active_vce_v",vc-ve,t>=START,.4,"minimum"),
      ("maximum_alltime_abs_vce_v",abs(vc-ve),np.ones(len(t),dtype=bool),1.6,"maximum"),
      ("maximum_alltime_abs_vbe_v",abs(vb-ve),np.ones(len(t),dtype=bool),1.0,"maximum"),
      ("maximum_alltime_abs_ic_per_emitter_a",abs(ic)/nx,np.ones(len(t),dtype=bool),.003,"maximum")]
    events=[]
    for name,values,mask,limit,kind in metrics:
        ids=np.flatnonzero(mask);i=int(ids[np.argmin(values[ids])if kind=="minimum"else np.argmax(values[ids])])
        bad=mask & ((values<limit)if kind=="minimum"else ((values>=limit)if name=="maximum_alltime_abs_ic_per_emitter_a"else(values>limit)))
        if not np.any(bad):continue
        intervals=[]
        invalid=np.flatnonzero(bad)
        for segment in np.split(invalid,np.flatnonzero(np.diff(invalid)>1)+1):
            intervals.append(dict(first_row=int(segment[0]),last_row=int(segment[-1]),samples=len(segment),
                first_time_s=float(t[segment[0]]),last_time_s=float(t[segment[-1]])))
        events.append(dict(metric=name,limit=limit,extremum=kind,value=float(values[i]),worst_row=i,time_s=float(t[i]),
            before_active_interval=bool(t[i]<START),all_violating_intervals=intervals))
    return events
def simultaneous_hbt(t,when,devices,voltage,current):
    require(t.ndim==1 and len(t)>1 and np.isfinite(t).all() and np.all(np.diff(t)>0),"strict finite operating-point time axis")
    require(math.isfinite(when) and t[0]<=when<=t[-1],"operating point inside actual capture")
    def value(x):
        require(x.shape==t.shape and np.isfinite(x).all(),"complete finite operating-point vector")
        return float(np.interp(when,t,x))
    result={}
    for name,dev in devices.items():
        require(len(dev["nodes"])==4 and type(dev["nx"])is int and dev["nx"]>0,"operating-point native HBT identity")
        vals={role:value(voltage(node))for role,node in zip(("C","B","E","S"),dev["nodes"],strict=True)}
        amps=value(current(name))
        result[name]=dict(native_id=dev["native_id"],nodes=dev["nodes"],nx=dev["nx"],terminal_v=vals,
            vce_v=vals["C"]-vals["E"],vbe_v=vals["B"]-vals["E"],collector_current_a=amps,collector_current_per_emitter_a=amps/dev["nx"])
    return result
def diagnose(report,t,data):
    require(report["case"]=="nominal_late"and report["corner"]=="nominal"and report["returncode"]==0 and report["diagnostics"]==[]and report["sources_unchanged"]is True,"complete original case")
    require(report["current_context"]==dict(attempt=1,run_id=41277054717,source="e85179e6900c2be9d931a8b30549c99f47c7617d"),"actual case identity")
    require(len(report["devices"])==124 and len(report["vectors"])==1151,"all original devices/vectors")
    aliases=report["binding"]["aliases"]
    def v(name):
        name=aliases.get(name,name)
        return np.zeros(len(t))if name=="0"else data["v("+name+")"]
    controls={};events=[];all_hbt=[]
    for name,dev in report["devices"].items():
        vc,vb,ve,_=map(v,dev["nodes"]);ic=data["@q."+name+".qnpn13g2[ic]"]
        metrics,index,intervals=hbt_metrics(t,vc,vb,ve,ic,dev["nx"])
        require(set(metrics)==set(report["device_checks"][name]),"all original HBT metric fields")
        for key,value in metrics.items():close(value,report["device_checks"][name][key],name+":"+key)
        all_hbt.append(dict(name=name,native_id=dev["native_id"],metrics=metrics,original_metrics_reproduced=True))
        for event in violation_events(t,vc,vb,ve,ic,dev["nx"]):
            index=event["worst_row"]
            snapshot={n:float(v(n)[index])for n in("avdd","cp","cn","dp","dn","ira","irb","irc","ird","irx","iry","ibda","ibdc","ibs0","ibs1","xp","xn","yp","yn","vip","vin")}
            for n in aliases:snapshot[n]=float(v(n)[index])
            # All HBT terminal voltages and collector currents at the SAME row.
            simultaneous={}
            for other,device in report["devices"].items():
                nodes={role:float(v(node)[index]) for role,node in zip(("C","B","E","S"),device["nodes"],strict=True)}
                simultaneous[other]=dict(native_id=device["native_id"],nodes=device["nodes"],terminal_v=nodes,
                    collector_current_a=float(data["@q."+other+".qnpn13g2[ic]"][index]),nx=device["nx"])
            events.append(dict(name=name,native_id=dev["native_id"],nodes=dev["nodes"],nx=dev["nx"],**event,
                collector_v=float(vc[index]),base_v=float(vb[index]),emitter_v=float(ve[index]),collector_current_a=float(ic[index]),
                simultaneous_observed_nodes_v=snapshot,all124_simultaneous_hbt=simultaneous))
    indices=range(1,256);rising=[START+(i+.5)*UI for i in indices];falling=[START+i*UI for i in indices]
    stages={}
    for tag in"abcdxy":
        sampler=tag in"abcd";group="sampler_checks"if sampler else"comparisons"
        expected=report["expected_samples"if sampler else"expected_comparisons"][tag]
        positive,negative=("xpd."+tag+"qp","xpd."+tag+"qn")if sampler else(tag+"p",tag+"n")
        actual,failures=sample_metrics(t,v(positive),v(negative),expected,falling if tag=="b"else rising,(.3,.6,.9)if sampler else(.6,.75,.9),UI,STEP,.3 if sampler else.6)
        original=report[group][tag]
        for k in("samples","wrong_sign_samples","below_100mv_samples","passed"):require(actual[k]==original[k],"original stage "+tag+":"+k)
        for k in("minimum_signed_margin_v","maximum_clock_to_valid_s"):close(actual[k],original[k],"stage "+tag+":"+k)
        require(len(actual["clock_to_valid_by_bit_s"])==len(original["clock_to_valid_by_bit_s"])==255,"complete per-bit delays")
        for x,y in zip(actual["clock_to_valid_by_bit_s"],original["clock_to_valid_by_bit_s"],strict=True):close(x,y,"per-bit delay "+tag)
        stages[tag]=dict(metrics=actual,original_metrics_reproduced=True,all_below_margin_samples=failures)
    operating_points={}
    for tag,stage in stages.items():
        sampler=tag in "abcd";edges=falling if tag=="b"else rising
        expected=report["expected_samples"if sampler else"expected_comparisons"][tag]
        worst_bit=int(np.argmax(stage["metrics"]["clock_to_valid_by_bit_s"]))
        stage_events=[dict(kind="maximum_delay_bit_at_original_deadline",bit_index=worst_bit+1,
            expected=expected[worst_bit],time_s=edges[worst_bit]+(.3 if sampler else .6)*UI)]
        if stage["all_below_margin_samples"]:
            worst=min(stage["all_below_margin_samples"],key=lambda x:x["signed_margin_v"])
            stage_events.append(dict(kind="worst_original_sample_margin",**worst))
        captured=[]
        for event in stage_events:
            when=event["time_s"]
            observed={name:float(np.interp(when,t,v(name)))for name in sorted(set(aliases)|{"avdd","cp","cn","dp","dn","xp","xn","yp","yn","vip","vin"})}
            snapshot=simultaneous_hbt(t,when,report["devices"],v,lambda name:data["@q."+name+".qnpn13g2[ic]"])
            require(len(snapshot)==124,"all124 simultaneous HBT operating points")
            positive,negative=("xpd."+tag+"qp","xpd."+tag+"qn")if sampler else(tag+"p",tag+"n")
            signed=float(np.interp(when,t,v(positive)-v(negative)))*(2*event["expected"]-1)
            if event["kind"]=="worst_original_sample_margin":close(signed,event["signed_margin_v"],"operating-point original margin")
            captured.append(dict(event=event,observed_nodes_v=observed,signed_margin_v=signed,all124_hbt=snapshot))
        operating_points[tag]=captured
    window=(t>=START+8*UI)&(t<=START+255*UI)
    def mean(x):return float(np.trapezoid(x[window],t[window])/(t[window][-1]-t[window][0]))
    phase=mean((v("xp")-v("xn"))-(v("yp")-v("yn")))
    def ic(tag):return data["@q."+report["binding"]["vi_names"][tag]+".qnpn13g2[ic]"]
    current=mean((ic("xxp")+ic("xyn"))-(ic("xxn")+ic("xyp")));voltage=mean(v("vip")-v("vin"))
    close(phase,report["phase_average_v"],"phase average");close(current,report["vi"]["mean_signed_current_a"],"VI current");close(voltage,report["vi"]["mean_output_difference_v"],"VI voltage")
    return dict(status="COMPLETE_CANDIDATE_WAVE_HEADROOM_DIAGNOSIS",all124HBT_metrics_reproduced=True,all6stage_and1530_bit_delays_reproduced=True,
      original_phase_and_VI_reproduced=True,active_mask="t >= 2e-9",phase_window_s=[START+8*UI,START+255*UI],
      phase_average_v=phase,vi_mean_current_a=current,vi_mean_voltage_v=voltage,
      failing_hbt_events=events,hbt=all_hbt,stages=stages,stage_operating_points=operating_points,
      interpretation="Simultaneous original native voltages/currents and complete under-margin samples. Correlation is diagnostic evidence, not proof that a particular edit fixes the circuit.",
      **FLAGS)
def source_guard(config):
    for path,pin in config["source_files"].items():require(filepin(ROOT/path)==pin,"exact source "+path)
def api(path,binary=False,timeout=90):
    cmd=["gh","api",REPO+path]+(["-H","Accept: application/octet-stream"]if binary else[])
    r=subprocess.run(cmd,capture_output=True,timeout=timeout)
    require(r.returncode==0,"GitHub API "+path+": "+r.stderr.decode(errors="replace")[:2000])
    return r.stdout if binary else json.loads(r.stdout)
def remote(rule):
    meta=api("contents/"+rule["path"]+"?ref="+rule["source"]);blob=meta if meta.get("content")else api("git/blobs/"+meta["sha"])
    raw=base64.b64decode(blob["content"])
    require(len(raw)==rule["bytes"]and sha(raw)==rule["sha256"],"exact derived input")
    require(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==meta["sha"],"derived Git blob")
    return raw
def acquire(config,out,work):
    rules=config["derived"];values={}
    for name,rule in rules.items():
        raw=remote(rule);(out/name).write_bytes(raw);values[name]=json.loads(raw)
    report=values["measurement.json"];index=values["index.json"];parts=values["parts.json"]
    run=api("actions/runs/41277054717");release=api("releases/430382305");ref=api("git/ref/tags/"+config["release_tag"])
    require(run["status"]=="completed"and run["conclusion"]=="failure"and run["head_sha"]==config["producer_source"]and run["run_attempt"]==1,"original rejected run identity")
    require(release["id"]==430382305 and release["tag_name"]==config["release_tag"]and release["target_commitish"]==config["producer_source"]and release["draft"]is False and release["prerelease"]is True,"original publication identity")
    require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==config["producer_source"],"exact source release tag")
    (out/"producer.json").write_bytes(encode(dict(run=run,release=release,ref=ref)))
    assets={a["name"]:a for a in release["assets"]};require(len(assets)==len(release["assets"])==6,"complete original release assets")
    require(parts["archive"]==dict(bytes=1053409153,sha256="85589cfeef80154768dc83db199d73c50a106050fcec727bd193e6bc16ace72e") and parts["context"]==report["current_context"] and index["context"]==report["current_context"] and parts["source_directory"]=="cloud-sampler-load","original ordered archive")
    require(len(index["files"])==config["inventory_members"] and len(parts["parts"])==4,"full original inventory")
    combined=work/"complete-native.tar.gz";observations=[];start=time.monotonic()
    with combined.open("xb")as archive:
        for i,row in enumerate(parts["parts"]):
            require(time.monotonic()-start<1200 and row["index"]==i,"bounded ordered acquisition")
            asset=assets[row["name"]];require(asset["state"]=="uploaded"and asset["size"]==row["bytes"]and asset["digest"]=="sha256:"+row["sha256"],"live part metadata")
            path=work/("part-"+str(i))
            with path.open("xb")as stream:
                r=subprocess.run(["gh","api",REPO+"releases/assets/"+str(asset["id"]),"-H","Accept: application/octet-stream"],stdout=stream,stderr=subprocess.PIPE,timeout=min(600,1200-(time.monotonic()-start)))
            (out/("part-"+str(i)+".stderr")).write_bytes(r.stderr)
            observed=filepin(path);observations.append(dict(index=i,asset=asset["id"],returncode=r.returncode,pin=observed))
            (out/"acquisition.json").write_bytes(encode(observations))
            require(r.returncode==0 and observed=={k:row[k]for k in("bytes","sha256")},"complete acquired part")
            with path.open("rb")as stream:
                while block:=stream.read(4*1024**2):archive.write(block)
    require(filepin(combined)==parts["archive"],"whole original archive")
    receipt=restore(combined,index["files"],{config["wave_member"],"native/candidate/composition.json"},work/"selected",prefix="cloud-sampler-load")
    composition=pathlib.Path(receipt["selected"]["native/candidate/composition.json"]["path"]).read_bytes()
    (out/"candidate-composition.json").write_bytes(composition)
    (out/"restore.json").write_bytes(encode(receipt))
    wave=pathlib.Path(receipt["selected"][config["wave_member"]]["path"])
    require(filepin(wave)==dict(bytes=report["raw_capture"]["raw_bytes"],sha256=report["raw_capture"]["raw_sha256"]),"complete original raw")
    return report,wave
def emit(out):
    for p in sorted(out.glob("*")):
        if not p.is_file()or p.suffix not in(".json",".stderr"):continue
        raw=p.read_bytes();packed=zlib.compress(raw,9);parts=[packed[i:i+24000]for i in range(0,len(packed),24000)]
        print("WAVE_DIAG_INDEX "+json.dumps(dict(name=p.name,bytes=len(raw),sha256=sha(raw),chunks=len(parts))),flush=True)
        for i,data in enumerate(parts):print("WAVE_DIAG_CHUNK "+json.dumps(dict(name=p.name,index=i,data=base64.b64encode(data).decode())),flush=True)
def main():
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1","single cloud execution")
    c=json.loads((ROOT/CONFIG).read_bytes());source_guard(c)
    out=ROOT/"cloud-sampler-candidate-wave";out.mkdir(exist_ok=False)
    for name in [*c["source_files"],CONFIG]:
        target=out/"source"/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    work=pathlib.Path(os.environ["RUNNER_TEMP"])/("nssoc-sampler-candidate-wave-"+os.environ["GITHUB_RUN_ID"]);work.mkdir(exist_ok=False)
    result=dict(status="INCOMPLETE_WAVE_DIAGNOSIS",source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),**FLAGS)
    try:
        resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
        report,wave=acquire(c,out,work)
        read=reader(ROOT/c["reader_path"],c["source_files"][c["reader_path"]])
        t,data,capture=read(wave,report["vectors"],STOP,STEP)
        require(capture==report["raw_capture"],"complete original parser result reproduced")
        result.update(diagnose(report,t,data),capture=capture)
        composition=json.loads((out/"candidate-composition.json").read_bytes())
        require(composition==json.loads((out/"topology-candidate.json").read_bytes()),"native composition equals authenticated preflight input")
        require(len(composition["device_records"])==500,"all500 candidate devices")
        for row in composition["device_records"]:
            if row["model"]!="npn13g2":continue
            dev=report["devices"]["xpd."+row["instance"].lower()]
            require(dev["nodes"]==["xpd."+x["node"].lower() for x in row["terminals"]] and dev["nx"]==int(row["parameters"]["nx"]),"native candidate HBT terminal identity")
        result["transfer_paths"]=transfer.analyze(report,composition,t,data)
        transfer_summary={k:v["summary"]for k,v in result["transfer_paths"]["paths"].items()}
        (out/"transfer-summary.json").write_bytes(encode(transfer_summary))
        summary={k:v for k,v in result.items()if k not in ("hbt","stages","capture","failing_hbt_events","stage_operating_points","transfer_paths")}
        summary["transfer_paths"]=transfer_summary
        summary["retimer_observations"]={k:{n:v[n]for n in("summary","expected_sequence_lags")}for k,v in result["transfer_paths"]["retimer_observations"].items()}
        summary["failing_hbt_events"]=[{k:v for k,v in e.items()if k not in ("all124_simultaneous_hbt","simultaneous_observed_nodes_v","all_violating_intervals")}for e in result["failing_hbt_events"]]
        summary["stage_operating_points"]={tag:[dict(event=x["event"],signed_margin_v=x["signed_margin_v"],observed_nodes_v=x["observed_nodes_v"])for x in rows]for tag,rows in result["stage_operating_points"].items()}
        summary["stages"]={k:{n:v for n,v in s["metrics"].items()if n!="clock_to_valid_by_bit_s"}for k,s in result["stages"].items()}
        (out/"summary.json").write_bytes(encode(summary))
        source_guard(c)
    except BaseException as e:
        result.update(error=repr(e),traceback=traceback.format_exc());raise
    finally:
        (out/"result.json").write_bytes(encode(result));emit(out)
if __name__=="__main__":main()
