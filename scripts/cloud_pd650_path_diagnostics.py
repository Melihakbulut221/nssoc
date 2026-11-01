#!/usr/bin/env python3
"""Cloud-only physical path and supply diagnostics on three already completed raw waves."""
import copy,gc,hashlib,json,os,platform,re,shutil,subprocess,sys,traceback,types
from pathlib import Path
import numpy as np
import cloud_pd650_wave_analysis as reader
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"pd650-path-diagnostics"
MANIFEST="scripts/pd650-path-diagnostics-pins.json"
INPUTS="scripts/pd650-path-diagnostics-inputs.json"
CASES={
 "width2":(41306148937,"2a62d651d415fba8db3c5b758d1b66c05cde3a38",430565351),
 "width8":(41310192873,"66fb47bb12eff45c83b3d2819d281f99960ac4cc",430594515),
 "buffer_drive":(41325168813,"43fd3f71a289fef004aeb41cd2d0972d81f76f41",430697288)}
def require(ok,message):
    if not ok:raise AssertionError(message)
def pin(path):
    return dict(bytes=path.stat().st_size,sha256=reader.sha(path))
def gate():
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ["GITHUB_RUN_ATTEMPT"]=="1","hosted first attempt")
    require(os.environ["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch","exact repo dispatch")
    require(os.environ["GITHUB_REF"]=="refs/heads/codex/cdr-path-diagnostics","exact diagnostic branch")
    require(platform.python_version_tuple()[:2]==("3","12")and np.__version__=="2.3.3","qualified runtime")
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==os.environ["GITHUB_SHA"],"exact source")
    pins=json.loads((ROOT/MANIFEST).read_bytes())
    require(pins["reader_source"]=="9c5843a973b5a0175d137af0780ae1b5aca46968","original62-control reader")
    for name,expected in pins["files"].items():
        p=ROOT/name;require(p.is_file()and not p.is_symlink()and pin(p)==expected,"exact source "+name)
    cfg=json.loads((ROOT/INPUTS).read_bytes())
    require(set(cfg)==set(CASES),"exact three observed cases")
    for name,(run,source,release)in CASES.items():
        row=cfg[name]
        require((row["run"],row["source"],row["release"])==(run,source,release),"exact case identity")
        require(row["producer_conclusion"]=="failure","preserve all three original rejected outcomes")
        require(set(row["assets"])>={"parts.json","complete-output-index.json"},"complete archive metadata")
        for name,p in row["assets"].items():
            require(name in("parts.json","complete-output-index.json")or re.fullmatch(r"native\.tar\.gz\.part[0-9]{4}",name),"canonical asset")
            require(type(p["bytes"])is int and 0<p["bytes"]<=268435456 and re.fullmatch("[0-9a-f]{64}",p["sha256"]),"complete asset pin")
    return cfg
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x")as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write("\n")
def context(case,work):
    cfg=gate()[case];source=work/"source";(source/"scripts").mkdir(parents=True)
    for name in("cloud_tx_stream.py","cloud_cdr_current_eight_drain_loaded.py"):
        shutil.copyfile(ROOT/"scripts"/name,source/"scripts"/name)
    save(source/"scripts/pd650-wave-analysis-inputs.json",dict(assets=cfg["assets"],producer_conclusion=cfg["producer_conclusion"]))
    ns=dict(reader.__dict__)
    for name,value in reader.__dict__.items():
        if isinstance(value,types.FunctionType)and value.__globals__ is reader.__dict__:
            fn=types.FunctionType(value.__code__,ns,value.__name__,value.__defaults__,value.__closure__)
            fn.__kwdefaults__=value.__kwdefaults__;ns[name]=fn
            require(fn.__code__is value.__code__,"unchanged original function body")
    ns.update(ROOT=source,OUT=OUT/case,SOURCE=cfg["source"],PRODUCER_RUN=cfg["run"],RELEASE=cfg["release"],source_gate=gate)
    return ns
def settling(t,signed,start,stop):
    """Sampled sign-settling time in the original0.95UI window; never a new gate."""
    require(t.ndim==signed.ndim==1 and len(t)==len(signed)and start<stop,"finite window and vector shape")
    left=int(np.searchsorted(t,start));right=int(np.searchsorted(t,stop,side="right"))
    tt=t[left:right];ss=signed[left:right]
    require(len(tt)>=2 and np.all(np.isfinite(tt))and np.all(np.isfinite(ss))and np.all(np.diff(tt)>0),"finite strictly increasing sampled window")
    bad=np.flatnonzero(ss<=0)
    if not len(bad):return dict(settled=True,first_sample_after_last_nonpositive_s=0.,last_nonpositive_s=None)
    last=int(bad[-1]);relative=float(tt[last]-start)
    if last==len(tt)-1:return dict(settled=False,first_sample_after_last_nonpositive_s=None,last_nonpositive_s=relative)
    return dict(settled=True,first_sample_after_last_nonpositive_s=float(tt[last+1]-start),last_nonpositive_s=relative)
def pure_controls():
    checks=[];t=np.arange(11,dtype=float)/10
    def test(name,values,settled,delay):
        r=settling(t,np.array(values,dtype=float),0.,1.)
        require(r["settled"]is settled and r["first_sample_after_last_nonpositive_s"]==delay,name);checks.append(name)
    test("already correct",[1]*11,True,0.)
    test("first change",[-1,-1]+[1]*9,True,.2)
    test("multiple crossings uses last",[-1,1,-1,1,-1,1,-1,1,1,1,1],True,.7)
    test("not settled is censored",[1]*10+[-1],False,None)
    test("zero is not positive",[-1,0,1,1,1,1,1,1,1,1,1],True,.2)
    for name,tt,ss in[
      ("nonfinite",t,np.array([1]*5+[float("nan")]+[1]*5)),
      ("nonmonotonic",np.array([0,.1,.2,.3,.4,.4,.6,.7,.8,.9,1.]),np.ones(11)),
      ("length mismatch",t,np.ones(10)),
      ("empty window",np.array([0.,2.]),np.ones(2))]:
        try:settling(tt,ss,0.,1.)
        except AssertionError:checks.append("reject "+name)
        else:raise AssertionError("accepted "+name)
    require(len(checks)==9,"nine diagnostic controls")
    return checks
def diagnose(case,t,d,m,contract):
    require(m["binding"]["interface"]["avdd"]=="avdd"and m["binding"]["interface"]["avss"]=="0","actual supply references")
    rows={r["native_id"]:r for r in contract["device_records"]}
    require(len(rows)==len(contract["device_records"])==650,"complete unique native composition")
    bound=m["binding"];cache={}
    def voltage(n):
        n=bound["aliases"].get(n,n)
        if n not in cache:
            if n=="0":cache[n]=np.zeros(len(t))
            else:
                key="v("+n+")";require(key in d,"actual captured terminal "+key);cache[n]=d[key]
        return cache[n]
    def terminal(ident,label):
        r=rows[ident];require(r["instance"]=="XD"+format(ident,"04d"),"native device identity")
        matches=[p for p in r["terminals"]if p["terminal"]==label];require(len(matches)==1,"unique native terminal")
        return dict(device=r["instance"],model=r["model"],terminal=label,native_cluster=matches[0]["native_cluster"],
                    native_net=matches[0]["native_net"],node="xpd."+matches[0]["node"].lower())
    def pair(a,b):return dict(positive=a,negative=b)
    def diff(p):return voltage(p["positive"]["node"])-voltage(p["negative"]["node"])
    def receiver(port):
        found=[terminal(r["native_id"],"B")for r in contract["device_records"]if r["model"]=="npn13g2"
          and any(q["terminal"]=="B"and q["native_cluster"]==port["native_cluster"]for q in r["terminals"])]
        require(found,"actual physical receiver bases");return found[0],found
    active=t>=reader.START;window=(t>=reader.START+8*reader.UI)&(t<=reader.START+255*reader.UI)
    rail={}
    for r in contract["device_records"]:
        for q in r["terminals"]:
            if q["native_net"]not in("avdd","avss"):continue
            node="xpd."+q["node"].lower()
            rail.setdefault(node,dict(rail=q["native_net"],cluster=q["native_cluster"],users=[]))["users"].append(dict(device=r["instance"],terminal=q["terminal"]))
    supply={}
    for node,info in rail.items():
        value=voltage(node);ref=voltage("avdd")if info["rail"]=="avdd"else voltage("0")
        drop=ref-value if info["rail"]=="avdd"else value-ref
        supply[node]=dict(**info,voltage_active_v=reader.stats(value[active]),drop_active_v=reader.stats(drop[active]),
                         drop_measurement_window_v=reader.stats(drop[window]))
    plans={"A":("a",227,229,228,230,123,125,125,123),
           "C":("c",238,240,239,241,128,130,130,128),
           "D_X":("d",234,236,235,237,131,132,132,131),
           "D_Y":("d",234,236,235,237,149,150,150,149)}
    paths={}
    for label,(tag,rp,rn,sp,sn,bp,bn,op,on)in plans.items():
        witness=[]
        for leg in("p","n"):
            dev=bound["probe_witnesses"][tag+"q"+leg]["device"]
            ids=[i for i,r in rows.items()if r["instance"].lower()==dev.lower()]
            require(len(ids)==1,"exact original sampler probe");ident=ids[0]
            witness.append(terminal(ident,"C"))
        stages={"sampler":pair(*witness),"series_input":pair(terminal(rp,"rppd_1"),terminal(rn,"rppd_1")),
                "series_output":pair(terminal(rp,"rppd_2"),terminal(rn,"rppd_2")),
                "shunt_top":pair(terminal(sp,"rppd_1"),terminal(sn,"rppd_1")),
                "buffer_base":pair(terminal(bp,"B"),terminal(bn,"B")),
                "buffer_collector":pair(terminal(op,"C"),terminal(on,"C"))}
        p,ps=receiver(stages["buffer_collector"]["positive"]);n,ns=receiver(stages["buffer_collector"]["negative"])
        stages["first_receiver_base"]=pair(p,n)
        wire_pairs=[("sampler","series_input"),("series_output","shunt_top"),
                    ("shunt_top","buffer_base"),("buffer_collector","first_receiver_base")]
        wire={}
        for first,last in wire_pairs:
            wire[first+"->"+last]={}
            for leg in("positive","negative"):
                a,b=stages[first][leg],stages[last][leg]
                require(a["native_cluster"]==b["native_cluster"]and a["native_net"]==b["native_net"],"same native extracted conductor")
                delta=voltage(a["node"])-voltage(b["node"])
                wire[first+"->"+last][leg]=dict(from_node=a["node"],to_node=b["node"],difference_active_v=reader.stats(delta[active]))
        values={name:diff(p)for name,p in stages.items()}
        timing={}
        for name,value in values.items():
            events=[];delays=[]
            for i,bit in enumerate(m["expected_samples"][tag],start=1):
                edge=reader.START+(i+.5)*reader.UI;sign=2*bit-1
                settled=settling(t,sign*value,edge,edge+.95*reader.UI)
                margins={str(phase):float(np.interp(edge+phase*reader.UI,t,sign*value))for phase in(.3,.6,.9)}
                source={str(phase):float(np.interp(edge+phase*reader.UI,t,sign*values["sampler"]))for phase in(.3,.6,.9)}
                events.append(dict(bit_index=i,expected=bit,edge_s=edge,sign_settling=settled,
                                   signed_samples_v=margins,source_signed_samples_v=source))
                if settled["settled"]:delays.append(settled["first_sample_after_last_nonpositive_s"])
            conditional={}
            for phase in(".3",".6",".9"):
                key=str(float(phase));eligible=[e for e in events if e["source_signed_samples_v"][key]>=.1]
                conditional[key]=dict(source_valid=len(eligible),wrong_sign=sum(e["signed_samples_v"][key]<=0 for e in eligible))
            timing[name]=dict(events=events,settled_bits=len(delays),censored_bits=255-len(delays),
                              settled_delay_s=reader.stats(np.array(delays))if delays else None,
                              source_conditioned=conditional,differential_active_v=reader.stats(value[active]),
                              commonmode_active_v=reader.stats(((voltage(stages[name]["positive"]["node"])+voltage(stages[name]["negative"]["node"]))/2)[active]))
        paths[label]=dict(nodes=stages,all_physical_receivers=dict(positive=ps,negative=ns),wire_differences=wire,stages=timing,
                          diagnostic_only=True,acceptance_criteria_changed=False)
    return dict(status="COMPLETE_PHYSICAL_PATH_DIAGNOSTICS_ONLY",case=case,producer_run=CASES[case][0],producer_source=CASES[case][1],
      source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),supply_nodes=supply,paths=paths,
      original_device_pass=m["devices_passed"],original_data_pass=m["data_passed"],original_phase_pass=m["phase_passed"],
      electrical_gates_unchanged=True,native_simulation=False,geometry_changed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
      scope="Original sampled waves and actual physical terminals. Sign settling and rail drops are diagnostics, not replacement acceptance gates or proof of causation.")
def main():
    cfg=gate();OUT.mkdir(exist_ok=False)
    case="width2"if sys.argv[1:]==["controls"]else os.environ["PD650_CASE"]
    require(case in cfg and sys.argv[1:]in(["controls"],["analyze"]),"explicit valid mode and case")
    work=Path(os.environ["RUNNER_TEMP"])/("pd650-path-"+os.environ["GITHUB_RUN_ID"]+"-"+case)
    work.mkdir(exist_ok=False);(OUT/case).mkdir()
    ns=context(case,work)
    originals=(reader.SOURCE,reader.PRODUCER_RUN,reader.RELEASE,reader.ROOT,reader.OUT,reader.source_gate)
    if sys.argv[1:]==["controls"]:
        result=ns["controls"]();require(result["count"]==62,"all62 original reader controls")
        extra=pure_controls()
        save(OUT/"controls.json",dict(status="PASS_DIAGNOSTIC_SOURCE_CONTROLS_ONLY",original_controls=result,new_controls=extra,total_controls=71,
              source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),native_simulation=False,physical_acceptance=False))
    else:
        actual=reader.api("actions/runs/"+str(cfg[case]["run"]))
        require(actual["run_attempt"]==1 and actual["event"]=="workflow_dispatch","original producer dispatch")
        raw=work/"native";raw.mkdir()
        base,index=ns["acquire"](raw);captured={}
        parser=ns["parser"]()
        def read(*args,**kwargs):
            result=parser(*args,**kwargs);captured["wave"]=result;return result
        ns["parser"]=lambda:read
        ns["analyze"](base,index)
        require("wave"in captured,"original raw parser actually executed")
        t,d,_=captured["wave"]
        m=json.loads((base/(reader.CASE+"measurement-result.json")).read_bytes())
        contract=json.loads((base/"native/candidate/composition.json").read_bytes())
        result=diagnose(case,t,d,m,contract)
        save(OUT/case/"physical-path-diagnostics.json",result)
        compact=dict(result);compact["paths"]={k:dict(nodes=v["nodes"],wire_differences=v["wire_differences"],
                    stages={n:{q:x for q,x in stage.items()if q!="events"}for n,stage in v["stages"].items()})for k,v in result["paths"].items()}
        save(OUT/case/"physical-path-summary.json",compact)
        print(json.dumps(dict(case=case,status=result["status"],supply_nodes=len(result["supply_nodes"]),paths=list(result["paths"]))))
        captured.clear();del t,d;gc.collect()
    require(originals==(reader.SOURCE,reader.PRODUCER_RUN,reader.RELEASE,reader.ROOT,reader.OUT,reader.source_gate),"original module unchanged")
    gate()
    # Native inputs remain immutable in their original releases; only this owned cloud cache is removed.
    shutil.rmtree(work)
if __name__=="__main__":
    try:main()
    except BaseException as error:
        OUT.mkdir(exist_ok=True)
        save(OUT/"failure.json",dict(error=repr(error),traceback=traceback.format_exc(),native_simulation=False,full_phy_accepted=False))
        raise
