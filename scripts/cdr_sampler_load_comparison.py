#!/usr/bin/env python3
"""Compare complete frozen-gate CDR reports; derived JSON only, no native rerun."""
import argparse,base64,copy,hashlib,json,os,pathlib,subprocess,traceback
UI=125e-12
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path("cloud-sampler-load-comparison")
def require(ok,msg):
    if not ok:raise ValueError(msg)
def encode(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def fetch(pin):
    endpoint="repos/Melihakbulut221/nssoc/"
    def api(path):
        p=subprocess.run(["gh","api",endpoint+path],capture_output=True,text=True,timeout=120)
        require(p.returncode==0,p.stderr[:2000]);return json.loads(p.stdout)
    d=api("contents/"+pin["path"]+"?ref="+pin["source"])
    if not d.get("content"):d=api("git/blobs/"+d["sha"])
    raw=base64.b64decode(d["content"])
    require(len(raw)==pin["bytes"] and hashlib.sha256(raw).hexdigest()==pin["sha256"],"authenticated report bytes")
    return raw
def gates(r):
    require(r["case"]=="nominal_late" and r["corner"]=="nominal","same nominal late case")
    require(r["transient_executed"] is True and r["returncode"]==0 and r["diagnostics"]==[] and r["sources_unchanged"] is True,"real clean native measurement")
    require(r["native_flags_verified"]==124,"all original native HBT flags")
    require(len(r["device_checks"])==124 and set(r["device_checks"])==set(r["devices"]),"complete HBT stress checks")
    require(len(r["mos_checks"])==50 and set(r["mos_checks"])==set(r["mos_devices"]),"complete MOS stress checks")
    require(len(r["native_cap_voltage_checks"])==7 and set(r["native_cap_voltage_checks"])==set(r["native_caps"]),"complete native MIM checks")
    require(len(r["minimum_active_stage_tail_current_a"])==16 and len(r["minimum_active_mos_tail_current_a"])==42,"complete physical tail groups")
    require(set(r["minimum_active_tail_current_a"])==set(r["binding"]["tail_names"]),"complete HBT tail identities")
    require(set(r["minimum_active_mos_tail_current_a"])==set(r["binding"]["mos_tail_names"]),"complete MOS tail identities")
    require(set(r["minimum_active_stage_tail_current_a"])==set(r["binding"]["mos_tail_groups"]),"complete stage tail identities")
    require(r["stage_tail_current_gate_a"]==.0005,"original tail gate")
    require(r["phase_gate"]==dict(minimum_signed_v=.03,constant_maximum_abs_v=.01,window_s=[2e-9+8*UI,2e-9+255*UI]),"original phase gate")
    vi=r["vi"]
    require(vi["phase_limits"]==dict(minimum_signed_current_a=50e-6,minimum_signed_voltage_v=.005,constant_maximum_abs_current_a=5e-6,constant_maximum_abs_voltage_v=.002),"original VI gates")
    hbt={}
    for name,x in r["device_checks"].items():
        hbt[name]=dict(min_vce=x["minimum_active_vce_v"]>=.4,max_vce=x["maximum_alltime_abs_vce_v"]<=1.6,
            max_vbe=x["maximum_alltime_abs_vbe_v"]<=1,max_ic=x["maximum_alltime_abs_ic_per_emitter_a"]<.003)
    mos={}
    for name,x in r["mos_checks"].items():
        require(set(x["peaks_v"])=={"vds","vgs","vgd","vdb","vsb"} and x["limit_v"]==1.32,"original complete MOS terminal limits")
        passed=max(x["peaks_v"].values())<=1.32 and x["minimum_active_vds_v"]>=0
        require(x["passed"]==passed,"MOS report/predicate agreement");mos[name]=passed
    cap={}
    for name,x in r["native_cap_voltage_checks"].items():
        require(x["limit_v"]==1.6,"original MIM limit");cap[name]=x["maximum_alltime_abs_v"]<=1.6
    tails=all(x>=.0005 for x in r["minimum_active_tail_current_a"].values())
    mos_tails=all(x>=0 for x in r["minimum_active_mos_tail_current_a"].values())
    stage_tails=all(x>=.0005 for x in r["minimum_active_stage_tail_current_a"].values())
    device=all(all(x.values()) for x in hbt.values()) and all(mos.values()) and all(cap.values()) and tails and mos_tails and stage_tails
    require(r["devices_passed"]==device,"complete device predicate agreement")
    stages={}
    require(set(r["sampler_checks"])==set("abcd") and set(r["comparisons"])=={"x","y"},"all six stages")
    for key,entry in {**r["sampler_checks"],**r["comparisons"]}.items():
        delays=entry["clock_to_valid_by_bit_s"]
        require(len(delays)==255 and entry["samples"]==765,"all original bits and samples")
        require(entry["maximum_clock_to_valid_s"]==max(delays),"complete delay census maximum")
        limit=(.3 if key in "abcd" else .6)*UI
        passed=entry["minimum_signed_margin_v"]>=.1 and max(delays)<=limit
        require(entry["passed"]==passed,"stage predicate agreement")
        stages[key]=dict(passed=passed,delay_limit_s=limit,maximum_clock_to_valid_s=max(delays),
            minimum_signed_margin_v=entry["minimum_signed_margin_v"],wrong_sign_samples=entry["wrong_sign_samples"],below_100mv_samples=entry["below_100mv_samples"])
    phase=r["phase_average_v"]>=.03
    require(r["phase_passed"]==phase,"phase predicate agreement")
    data=all(x["passed"] for x in stages.values()) and phase
    require(r["data_passed"]==data,"complete data predicate agreement")
    require(set(vi["minimum_active_tail_current_a"])=={"xtx","xty"},"both VI tail currents")
    vi_phase=vi["mean_signed_current_a"]>=50e-6 and vi["mean_output_difference_v"]>=.005
    vi_bias=min(vi["minimum_active_tail_current_a"].values())>=.0001
    require(vi["phase_passed"]==vi_phase and vi["bias_passed"]==vi_bias and vi["passed"]==(vi_phase and vi_bias),"VI predicate agreement")
    passed=device and data and vi_phase and vi_bias
    require(r["status"]==("PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF" if passed else "REJECTED_WHOLE_MIM_PD500_LOADED"),"original final status")
    require(all(r[k] is False for k in ("accepted","cdr_accepted","qualified_pex","closed_loop","full_phy_accepted")),"no transferred product acceptance")
    return dict(all_original_screen_gates_passed=passed,devices_passed=device,data_passed=data,vi_passed=vi_phase and vi_bias,
        failing_hbt={n:[k for k,v in checks.items() if not v] for n,checks in hbt.items() if not all(checks.values())},
        failing_mos=[n for n,v in mos.items() if not v],failing_caps=[n for n,v in cap.items() if not v],
        hbt_tails_passed=tails,mos_tails_passed=mos_tails,stage_tails_passed=stage_tails,stages=stages,
        phase_average_v=r["phase_average_v"],vi_mean_current_a=vi["mean_signed_current_a"],vi_mean_voltage_v=vi["mean_output_difference_v"],vi_current_passed=vi["mean_signed_current_a"]>=50e-6,vi_voltage_passed=vi["mean_output_difference_v"]>=.005)
LOADS=(175,176,177,178,191,194,195,196,202,205,207,208,212,214,215,216)
BUFFERS=(182,183,220,221)
SHUNTS=(184,185,222,223)
DECLARED=dict(native_ids=sorted(LOADS+BUFFERS+SHUNTS),sixteen_latch_loads_l_um=[2.6,1.5],four_buffer_loads_l_um=[1.8,1.0],four_shunts_l_um=[5,3.4])
def compare(base,cand):
    original=gates(base);current=gates(cand)
    for key in ("case","corner","data_offset_s","source_bits","source_bits_sha256","vectors","vector_census","devices","mos_devices","native_caps","expected_samples","expected_comparisons"):
        require(base[key]==cand[key],"unchanged experimental contract "+key)
    expected=copy.deepcopy(base["binding"])
    for ident in LOADS+BUFFERS+SHUNTS:
        entry=expected["groups"]["rppd"]["xpd.xd"+format(ident,"04d")]
        old,new,width=("2.6u","1.5u","32u")if ident in LOADS else(("1.8u","1.0u","8u")if ident in BUFFERS else("5u","3.4u","4u"))
        require(entry["parameters"]["l"]==old and entry["parameters"]["w"]==width,"original exact load or shunt")
        entry["parameters"]["l"]=new
    require(cand["binding"]==expected,"only twenty-four declared intrinsic lengths changed in complete bound circuit")
    require(cand["circuit_candidate"]==DECLARED,"declared candidate")
    require(cand["baseline_wire_rc_retained"] is True and cand["wire_rc_recomputed"] is False and cand["layout_regenerated"] is False and cand["physical_acceptance"] is False,"exploratory physical scope")
    changes={}
    for name in base["device_checks"]:
        changes[name]={key:dict(baseline=base["device_checks"][name][key],candidate=cand["device_checks"][name][key],delta=cand["device_checks"][name][key]-base["device_checks"][name][key]) for key in base["device_checks"][name]}
    return dict(status="COMPLETE_AUTHENTICATED_SAMPLER_LOAD_COMPARISON",baseline=original,candidate=current,all124_hbt_changes=changes,
        all1530_bit_delays={k:dict(baseline=(base["sampler_checks"] if k in "abcd" else base["comparisons"])[k]["clock_to_valid_by_bit_s"],
                                  candidate=(cand["sampler_checks"] if k in "abcd" else cand["comparisons"])[k]["clock_to_valid_by_bit_s"]) for k in "abcdxy"},
        no_gate_or_stimulus_changed=True,native_simulation_rerun=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
def controls(base):
    # Deliberately synthetic positive comparison, never emitted as native evidence.
    synth=copy.deepcopy(base)
    for ident in LOADS+BUFFERS+SHUNTS:
        synth["binding"]["groups"]["rppd"]["xpd.xd"+format(ident,"04d")]["parameters"]["l"]="1.5u"if ident in LOADS else("1.0u"if ident in BUFFERS else"3.4u")
    synth.update(circuit_candidate=copy.deepcopy(DECLARED),
        baseline_wire_rc_retained=True,wire_rc_recomputed=False,layout_regenerated=False,physical_acceptance=False)
    compare(base,synth)
    mutations=[
        ("changed phase gate",lambda x:x["phase_gate"].__setitem__("minimum_signed_v",.01)),
        ("missing HBT",lambda x:x["device_checks"].pop("xpd.xd0061")),
        ("changed stimulus",lambda x:x["source_bits"].__setitem__(0,1-x["source_bits"][0])),
        ("extra device change",lambda x:x["binding"]["groups"]["rppd"]["xpd.xd0189"]["parameters"].__setitem__("l","1.3u")),
        ("shortened delay census",lambda x:x["sampler_checks"]["a"]["clock_to_valid_by_bit_s"].pop()),
        ("invented layout acceptance",lambda x:x.__setitem__("physical_acceptance",True)),
        ("false successful gate",lambda x:x.__setitem__("devices_passed",not x["devices_passed"])),
        ("wrong collector load length",lambda x:x["binding"]["groups"]["rppd"]["xpd.xd0175"]["parameters"].__setitem__("l","1.4u")),
        ("wrong collector load width",lambda x:x["binding"]["groups"]["rppd"]["xpd.xd0175"]["parameters"].__setitem__("w","64u")),
        ("relaxed VI voltage gate",lambda x:x["vi"]["phase_limits"].__setitem__("minimum_signed_voltage_v",.001)),
        ("wrong buffer pullup length",lambda x:x["binding"]["groups"]["rppd"]["xpd.xd0182"]["parameters"].__setitem__("l","1.1u")),
        ("wrong buffer pullup width",lambda x:x["binding"]["groups"]["rppd"]["xpd.xd0182"]["parameters"].__setitem__("w","16u")),
        ("wrong master load length",lambda x:x["binding"]["groups"]["rppd"]["xpd.xd0177"]["parameters"].__setitem__("l","2.6u")),
    ];refused=[]
    for name,change in mutations:
        bad=copy.deepcopy(synth);change(bad)
        try:compare(base,bad)
        except ValueError as exc:refused.append(dict(name=name,reason=str(exc)))
        else:raise AssertionError("accepted "+name)
    return dict(synthetic_controls_only=True,refused=refused,positive_test_does_not_represent_candidate_simulation=True)
def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument("--controls",action="store_true");args=parser.parse_args()
    if args.controls:OUT=pathlib.Path("cloud-sampler-load-comparison-controls")
    require(os.environ.get("GITHUB_ACTIONS")=="true","cloud computation only")
    cfg=json.loads((ROOT/"scripts/cdr-sampler-load-comparison-inputs.json").read_bytes())
    OUT.mkdir(exist_ok=False);reports={}
    for name,pin in cfg["inputs"].items():
        if args.controls and name!="baseline.json":continue
        require(isinstance(pin,dict),"candidate terminal proof must be supplied")
        raw=fetch(pin);(OUT/name).write_bytes(raw);reports[name]=json.loads(raw)
    control_result=controls(reports["baseline.json"])
    (OUT/"controls.json").write_bytes(encode(control_result))
    if args.controls:
        print(json.dumps(control_result,sort_keys=True));return
    require(reports["candidate.json"]["current_context"]==cfg["candidate_context"],"exact actual candidate run and source")
    result=compare(reports["baseline.json"],reports["candidate.json"])
    (OUT/"result.json").write_bytes(encode(result))
    summary={k:v for k,v in result.items() if k not in ("all124_hbt_changes","all1530_bit_delays")}
    (OUT/"summary.json").write_bytes(encode(summary));print(json.dumps(summary,sort_keys=True))
if __name__=="__main__":
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);(OUT/"failure.txt").write_text(traceback.format_exc());raise
