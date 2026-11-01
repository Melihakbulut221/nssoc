"""Classify actual completed transient gates on GitHub; never rewrite native data or thresholds."""
import ast,copy,hashlib,io,json,math,os,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"wire-device-audit"
CFG="scripts/cdr-wire-shortcuts-device-audit-inputs.json"
MANIFEST="scripts/cdr-wire-shortcuts-device-audit-pins.json"
BRANCH="codex/cdr-wire-shortcuts-device-audit"
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def digest(b):return hashlib.sha256(b).hexdigest()
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb")as f:f.write((json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
def api(path):return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path],timeout=180))
def gate():
    e=os.environ
    need(e.get("GITHUB_ACTIONS")=="true"and e["GITHUB_REF"]=="refs/heads/"+BRANCH and e["GITHUB_RUN_ATTEMPT"]=="1","hosted first current branch")
    need(e["GITHUB_REPOSITORY"]=="Melihakbulut221/nssoc"and e["GITHUB_EVENT_NAME"]=="workflow_dispatch","current explicit repository dispatch")
    need(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==e["GITHUB_SHA"],"exact current source")
    m=json.loads((ROOT/MANIFEST).read_bytes())
    for n,p in m["files"].items():
        b=(ROOT/n).read_bytes();need(dict(bytes=len(b),sha256=digest(b))==p,"protected source "+n)
    c=json.loads((ROOT/CFG).read_bytes());f=c["measurement_block"]
    lines=(ROOT/f["file"]).read_text().splitlines(True);b="".join(lines[f["start"]-1:f["end"]]).encode()
    need(len(b)==f["bytes"]and digest(b)==f["sha256"],"unchanged original complete measurement block")
    return c
def number(v):
    need(type(v)in(int,float)and math.isfinite(v),"finite native measurement")
    return v
def hbt(x):
    limits=[("minimum_active_vce_v",lambda v:v<.4),("maximum_alltime_abs_vce_v",lambda v:v>1.6),
      ("maximum_alltime_abs_vbe_v",lambda v:v>1),("maximum_alltime_abs_ic_per_emitter_a",lambda v:v>=.003)]
    return [k for k,f in limits if f(number(x[k]))]
def mos(x):
    p=x["peaks_v"];need(set(p)=={"vds","vgs","vgd","vdb","vsb"},"five MOS voltage differences")
    bad=[k for k,v in p.items()if number(v)>1.32]
    if number(x["minimum_active_vds_v"])<0:bad.append("minimum_active_vds_v")
    return bad
def controls():
    gate();good=dict(minimum_active_vce_v=.4,maximum_alltime_abs_vce_v=1.6,maximum_alltime_abs_vbe_v=1,maximum_alltime_abs_ic_per_emitter_a=.002999)
    need(hbt(good)==[],"inclusive voltage and strict current boundaries")
    cases=[]
    for key,value in[("minimum_active_vce_v",.399999),("maximum_alltime_abs_vce_v",1.600001),("maximum_alltime_abs_vbe_v",1.000001),("maximum_alltime_abs_ic_per_emitter_a",.003)]:
        x=dict(good);x[key]=value;need(hbt(x)==[key],"reject exact original boundary "+key);cases.append(key)
    mg=dict(peaks_v={k:1.32 for k in["vds","vgs","vgd","vdb","vsb"]},minimum_active_vds_v=0)
    need(mos(mg)==[],"inclusive MOS boundaries")
    for key in mg["peaks_v"]:
        x=copy.deepcopy(mg);x["peaks_v"][key]=1.320001;need(mos(x)==[key],"MOS terminal boundary");cases.append("mos "+key)
    x=copy.deepcopy(mg);x["minimum_active_vds_v"]=-1e-9;need(mos(x)==["minimum_active_vds_v"],"MOS signed headroom");cases.append("MOS headroom")
    try:number(float("nan"))
    except AssertionError:cases.append("nonfinite")
    else:raise AssertionError("accepted nonfinite")
    save("controls.json",dict(status="PASS_DERIVED_CLASSIFIER_BOUNDARY_CONTROLS",rejected=cases,native_wave_read=False,new_transient_executed=False))
def diagnose():
    c=gate();p=c["parent"];run=api("actions/runs/"+str(p["run"]))
    need(run["status"]=="completed"and run["conclusion"]=="failure"and run["head_sha"]==p["source"]and run["run_attempt"]==1,"actual rejected terminal parent")
    a=api("actions/artifacts/"+str(p["artifact"]["id"]));expected=p["artifact"]
    need(a["size_in_bytes"]==expected["bytes"]and a["digest"]=="sha256:"+expected["sha256"]and not a["expired"],"exact derived artifact")
    raw=subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/"+str(a["id"])+"/zip"],timeout=300)
    need(len(raw)==expected["bytes"]and digest(raw)==expected["sha256"],"complete derived transport")
    z=zipfile.ZipFile(io.BytesIO(raw));need(len(z.namelist())==len(set(z.namelist())),"unique artifact members")
    idx=json.loads(z.read("derived-index.json"));name="derived/measurement-result.json";b=z.read(name)
    need(dict(bytes=len(b),sha256=digest(b))==idx[name]==p["measurement"],"actual unmodified complete measurement")
    m=json.loads(b)
    need(m["current_context"]==dict(source=p["source"],run_id=p["run"],attempt=1),"actual measurement context")
    need(m["status"]=="REJECTED_WHOLE_MIM_PD500_LOADED"and m["sources_unchanged"]and m["transient_executed"],"retain actual electrical rejection")
    wave=m["raw_capture"];need(wave["raw_bytes"]==p["wave"]["bytes"]and wave["raw_sha256"]==p["wave"]["sha256"]and wave["complete_unmodified_rows"],"reference to actual complete native wave")
    need(len(m["device_checks"])==124 and len(m["mos_checks"])==50 and len(m["native_cap_voltage_checks"])==7,"all original physical device checks")
    bind=m["binding"]
    def describe(name,records):
        d=records[name];roles=[]
        for tag,n in bind["vi_names"].items():
            if n==name:roles.append("VI "+tag)
        for net,row in bind["probe_witnesses"].items():
            if name=="xpd."+row["device"]:roles.append("sampler "+net)
        for tag,names in bind["mos_tail_groups"].items():
            if name in names:roles.append("tail "+tag)
        if name in bind["tail_names"]:roles.append("HBT buffer tail")
        return dict(native_id=d["native_id"],nodes=d["nodes"],parameters=d["parameters"],roles=roles)
    hb={}
    for n,x in m["device_checks"].items():
        bad=hbt(x)
        if bad:hb[n]=dict(violations=bad,measurements=x,device=describe(n,m["devices"]))
    mm={}
    for n,x in m["mos_checks"].items():
        bad=mos(x);need(x["passed"]is(not bad),"reproduce actual individual MOS predicate")
        if bad:mm[n]=dict(violations=bad,measurements=x,device=describe(n,m["mos_devices"]))
    tails={n:v for n,v in m["minimum_active_tail_current_a"].items()if number(v)<.0005}
    mos_tails={n:v for n,v in m["minimum_active_mos_tail_current_a"].items()if number(v)<0}
    stage={n:v for n,v in m["minimum_active_stage_tail_current_a"].items()if number(v)<.0005}
    caps={n:x for n,x in m["native_cap_voltage_checks"].items()if number(x["maximum_alltime_abs_v"])>1.6}
    safe=not any([hb,mm,tails,mos_tails,stage,caps]);need(safe is m["devices_passed"],"complete original device predicate reproduced")
    timing={}
    for kind,rows,limit in[("sampler",m["sampler_checks"],.3),("comparison",m["comparisons"],.6)]:
        for n,x in rows.items():
            ok=number(x["minimum_signed_margin_v"])>=.1 and number(x["maximum_clock_to_valid_s"])<=limit*125e-12
            need(ok is x["passed"],"unchanged original margin and clock-to-valid predicate")
            timing[kind+"_"+n]={k:v for k,v in x.items()if k!="clock_to_valid_by_bit_s"}
    need(number(m["data_offset_s"])>0,"this actual nominal_late scenario")
    phase=number(m["phase_average_v"])>=.03;need(phase is m["phase_passed"],"original signed phase predicate")
    data=all(x["passed"]for x in timing.values())and phase;need(data is m["data_passed"],"complete original data predicate")
    vi=m["vi"];vp=number(vi["mean_signed_current_a"])>=50e-6 and number(vi["mean_output_difference_v"])>=.005
    vb=all(number(v)>=.0001 for v in vi["minimum_active_tail_current_a"].values())
    need(vp is vi["phase_passed"]and vb is vi["bias_passed"]and(vp and vb)is vi["passed"],"complete original VI predicate")
    need(not(safe and data and vi["passed"]),"rejection remains rejection")
    save("input-run.json",run);save("input-artifact.json",a);save("input-measurement.json",m)
    result=dict(status="COMPLETE_DERIVED_CLASSIFICATION_OF_REJECTED_TRANSIENT",parent=p,
      source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),reproduced=dict(devices=safe,data=data,phase=phase,vi=vi["passed"]),
      failing_hbt=hb,failing_mos=mm,failing_hbt_tails=tails,failing_mos_tail_polarity=mos_tails,failing_stage_currents=stage,failing_caps=caps,
      timing=timing,phase_average_v=m["phase_average_v"],vi=vi,interface_observations=m["interface_observations"],
      native_wave_read=False,new_transient_executed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False,
      scope="Derived scalar gate reproduction and exact device identities only. New native wave/device diagnosis remains separate.")
    save("result.json",result);gate()
    print(json.dumps(dict(status=result["status"],failed_hbt=len(hb),failed_mos=len(mm),failed_stage_currents=len(stage),failed_caps=len(caps),physical_acceptance=False)),flush=True)
if __name__=="__main__":
    OUT.mkdir(exist_ok=True)
    try:
        if sys.argv[1:]==["--controls"]:controls()
        elif sys.argv[1:]==["--diagnose"]:diagnose()
        else:raise AssertionError("known explicit entry")
    except BaseException as exc:
        import traceback
        save("failure-"+sys.argv[1].lstrip("-")+".json",dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False));raise
