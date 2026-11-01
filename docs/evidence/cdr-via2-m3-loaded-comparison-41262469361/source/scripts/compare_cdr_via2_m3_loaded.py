#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare two complete derived nominal_late reports on a cloud runner only."""
import base64,copy,hashlib,json,math,os,pathlib,subprocess,traceback,unittest,zlib
R="repos/Melihakbulut221/nssoc/"
P="docs/evidence/cdr-via2-m3-loaded-terminal-41260582673/emission-01/derived/case-nominal_late/measurement-result.json"
CURRENT=dict(source="53e39a2c43bfef518793da536a6bc423398d7262",path=P,bytes=453835,sha256="c64afd8eecfb5c6e31b7b03e7333e51d5cf2124bf01c7e0ea4fb088e1227fbc8")
BASELINE=dict(asset=695889571,bytes=1571404,sha256="721e87699fb8359494e5b20b9f48dd5ad94e6c443f9ea60ecf44346b78353519")
def require(v,s):
    if not v:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def number(x):
    require(type(x)in(int,float) and math.isfinite(x),"finite actual metric");return x
def metric(a,b):return dict(baseline=number(a),current=number(b),delta_current_minus_baseline=b-a)
def compare(a,b):
    frozen=("case","corner","data_offset_s","source_bits","source_bits_sha256","expected_samples","expected_comparisons","phase_gate","stage_tail_current_gate_a","mos_runtime")
    for key in frozen:require(a[key]==b[key],"matching original condition "+key)
    require(a["case"]=="nominal_late"and a["corner"]=="nominal"and a["data_offset_s"]==1.875e-11,"matching actual nominal_late")
    for v in(a,b):
        require(v["returncode"]==0 and v["sources_unchanged"]is True and v["diagnostics"]==[],"completed engine with no diagnostics and unchanged inputs")
        require(v["raw_capture"]["complete_unmodified_rows"]is True and v["raw_capture"]["columns"]==1152 and v["vector_census"]["total"]==1151,"complete actual vector census")
        require(v["closed_loop"]is False and v["cdr_accepted"]is False and v["full_phy_accepted"]is False,"external-clock screen only")
        require(v["native_flags_verified"]==124 and len(v["devices"])==len(v["device_checks"])==124,"all124 HBT checks")
        require(set(v["sampler_checks"])==set("abcd") and set(v["comparisons"])==set("xy"),"all sampler and XOR stages")
        for group in("sampler_checks","comparisons"):
            for x in v[group].values():require(x["samples"]==765 and len(x["clock_to_valid_by_bit_s"])==255,"complete original sampling and bit timing")
    for k in("method","numeric","backend"):require(a["native_options"][k]==b["native_options"][k],"same original native solver "+k)
    require(a["vi"]["phase_limits"]==b["vi"]["phase_limits"],"same VI thresholds")
    require(a["phase_gate"]["minimum_signed_v"]==.03 and a["vi"]["phase_limits"]["minimum_signed_current_a"]==50e-6,"unchanged phase/current limits")
    stages={}
    for group in("sampler_checks","comparisons"):
        stages[group]={}
        for n in a[group]:
            old,new=a[group][n],b[group][n]
            stages[group][n]=dict(metrics={k:metric(old[k],new[k])for k in("wrong_sign_samples","below_100mv_samples","minimum_signed_margin_v","maximum_clock_to_valid_s")},
              baseline_passed=old["passed"],current_passed=new["passed"],
              clock_to_valid_by_bit_s=dict(baseline=old["clock_to_valid_by_bit_s"],current=new["clock_to_valid_by_bit_s"]))
    def ids(v):
        result={}
        for name,row in v["devices"].items():
            i=row["native_id"];require(type(i)is int and i not in result,"unique real HBT identity")
            result[i]=(name,row,v["device_checks"][name])
        return result
    old,new=ids(a),ids(b);require(set(old)==set(new),"same native HBT identities")
    checks=("minimum_active_vce_v","maximum_alltime_abs_vce_v","maximum_alltime_abs_vbe_v","maximum_alltime_abs_ic_per_emitter_a")
    gates={checks[0]:(.4,"at_least"),checks[1]:(1.6,"at_most"),checks[2]:(1.,"at_most"),checks[3]:(.003,"strictly_below")}
    hbt=[];violations=[]
    for i in sorted(old):
        an,ad,ac=old[i];bn,bd,bc=new[i]
        require(ad["parameters"]==bd["parameters"]and ad["nx"]==bd["nx"],"same device geometry "+str(i))
        row=dict(native_id=i,baseline_name=an,current_name=bn,baseline_nodes=ad["nodes"],current_nodes=bd["nodes"],metrics={k:metric(ac[k],bc[k])for k in checks},current_violations=[])
        for k,(limit,rule)in gates.items():
            x=number(bc[k]);passes=x>=limit if rule=="at_least"else x<=limit if rule=="at_most"else x<limit
            if not passes:
                violation=dict(native_id=i,device=bn,metric=k,actual=x,limit=limit,rule=rule)
                row["current_violations"].append(violation);violations.append(violation)
        hbt.append(row)
    return dict(status="COMPLETE_MATCHING_NOMINAL_LATE_COMPARISON",stages=stages,
      phase_average_v=metric(a["phase_average_v"],b["phase_average_v"]),
      vi={k:metric(a["vi"][k],b["vi"][k])for k in("mean_signed_current_a","mean_output_difference_v")},
      hbt=hbt,current_hbt_violations=violations,hbt_limits=gates,
      baseline_acceptance={k:a[k]for k in("accepted","data_passed","phase_passed","devices_passed")},
      current_acceptance={k:b[k]for k in("accepted","data_passed","phase_passed","devices_passed")},
      baseline_vi_passed=a["vi"]["passed"],current_vi_passed=b["vi"]["passed"],
      counts=dict(hbt=len(hbt),samplers=4,xor_stages=2),all_per_bit_timing_retained=True,
      numerical_comparison_executed_in_cloud=True,native_simulation_rerun=False,full_phy_accepted=False,final_timing_complete=False,
      interpretation="Complete same-condition derived report comparison. Limits were not changed. Physical RC changes did not achieve electrical acceptance; this report neither proves root cause nor licenses a stimulus/gate relaxation.")
def api(path,binary=False):
    cmd=["gh","api",R+path]+(["-H","Accept: application/octet-stream"]if binary else[])
    p=subprocess.run(cmd,capture_output=True,timeout=90);require(p.returncode==0,p.stderr.decode(errors="replace")[:2000])
    return p.stdout if binary else json.loads(p.stdout)
def acquire(rule):
    if "asset"in rule:
        meta=api("releases/assets/"+str(rule["asset"]));require(meta["state"]=="uploaded"and meta["size"]==rule["bytes"]and meta["digest"]=="sha256:"+rule["sha256"],"original result asset metadata")
        raw=api("releases/assets/"+str(rule["asset"]),True)
    else:
        meta=api("contents/"+rule["path"]+"?ref="+rule["source"]);blob=meta if meta.get("content")else api("git/blobs/"+meta["sha"])
        raw=base64.b64decode(blob["content"]);require(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==meta["sha"],"exact current proof Git blob")
    require(len(raw)==rule["bytes"]and sha(raw)==rule["sha256"],"complete actual report pin")
    return raw
def fixture():
    timing=dict(samples=765,clock_to_valid_by_bit_s=[1e-11]*255,wrong_sign_samples=0,below_100mv_samples=0,minimum_signed_margin_v=.12,maximum_clock_to_valid_s=1e-11,passed=True)
    v=dict(case="nominal_late",corner="nominal",data_offset_s=1.875e-11,source_bits=[0,1],source_bits_sha256="fixture",expected_samples={},expected_comparisons={},phase_gate=dict(minimum_signed_v=.03),stage_tail_current_gate_a=.0005,mos_runtime={},returncode=0,sources_unchanged=True,diagnostics=[],raw_capture=dict(complete_unmodified_rows=True,columns=1152),vector_census=dict(total=1151),closed_loop=False,cdr_accepted=False,full_phy_accepted=False,native_flags_verified=124,devices={},device_checks={},sampler_checks={n:copy.deepcopy(timing)for n in"abcd"},comparisons={n:copy.deepcopy(timing)for n in"xy"},native_options=dict(method="TRAPEZOIDAL",numeric={},backend="klu"),vi=dict(phase_limits=dict(minimum_signed_current_a=50e-6),mean_signed_current_a=60e-6,mean_output_difference_v=.01,passed=True),phase_average_v=.04,accepted=True,data_passed=True,phase_passed=True,devices_passed=True)
    for i in range(124):
        n="device"+str(i);v["devices"][n]=dict(native_id=i,parameters=dict(nx="2"),nx=2,nodes=["c","b","e","s"])
        v["device_checks"][n]=dict(minimum_active_vce_v=.5,maximum_alltime_abs_vce_v=1.4,maximum_alltime_abs_vbe_v=.9,maximum_alltime_abs_ic_per_emitter_a=.002)
    return v
class Controls(unittest.TestCase):
    def test_complete_unchanged(self):
        a=fixture();b=copy.deepcopy(a);r=compare(a,b);self.assertEqual(r["current_hbt_violations"],[]);self.assertEqual(len(r["hbt"]),124);self.assertEqual(r["phase_average_v"]["delta_current_minus_baseline"],0)
    def test_actual_failure_and_strict_current_limit(self):
        a=fixture();b=copy.deepcopy(a);b["device_checks"]["device3"]["minimum_active_vce_v"]=.35;b["device_checks"]["device4"]["maximum_alltime_abs_ic_per_emitter_a"]=.003
        r=compare(a,b);self.assertEqual([v["native_id"]for v in r["current_hbt_violations"]],[3,4])
    def test_conditions_must_match(self):
        for k,value in (("data_offset_s",0),("source_bits",[1,0]),("phase_gate",dict(minimum_signed_v=.02))):
            a=fixture();b=copy.deepcopy(a);b[k]=value
            with self.subTest(k=k),self.assertRaises(ValueError):compare(a,b)
    def test_incomplete_or_unqualified_engine(self):
        for change in(lambda v:v.update(returncode=1),lambda v:v["raw_capture"].update(complete_unmodified_rows=False),lambda v:v["sampler_checks"]["a"].update(samples=764)):
            a=fixture();b=copy.deepcopy(a);change(b)
            with self.assertRaises(ValueError):compare(a,b)
    def test_device_identity_and_nonfinite_refusals(self):
        for change in(lambda v:v["devices"]["device3"].update(native_id=2),lambda v:v["devices"]["device3"].update(nx=4),lambda v:v["device_checks"]["device3"].update(minimum_active_vce_v=float("nan"))):
            a=fixture();b=copy.deepcopy(a);change(b)
            with self.assertRaises(ValueError):compare(a,b)
def main():
    require(os.environ.get("GITHUB_ACTIONS")=="true","cloud execution only")
    out=pathlib.Path("cloud-loaded-comparison");out.mkdir(exist_ok=False)
    result=dict(status="INCOMPLETE_COMPARISON",full_phy_accepted=False,final_timing_complete=False)
    try:
        test=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
        controls=dict(tests=test.testsRun,failures=len(test.failures),errors=len(test.errors),skips=len(test.skipped))
        (out/"controls.json").write_bytes(enc(controls));require(controls==dict(tests=5,failures=0,errors=0,skips=0),"all five hosted comparison controls")
        a=acquire(BASELINE);(out/"baseline.json").write_bytes(a)
        b=acquire(CURRENT);(out/"current.json").write_bytes(b)
        result=compare(json.loads(a),json.loads(b));result.update(inputs=dict(baseline=BASELINE,current=CURRENT),source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]))
    except BaseException as e:
        result.update(error=repr(e),traceback=traceback.format_exc());raise
    finally:
        (out/"result.json").write_bytes(enc(result))
        for name in("controls.json","result.json"):
            p=out/name
            if not p.exists():continue
            raw=p.read_bytes();packed=zlib.compress(raw,9);parts=[packed[i:i+24000]for i in range(0,len(packed),24000)]
            print("LOADED_COMPARE_INDEX "+json.dumps(dict(name=name,bytes=len(raw),sha256=sha(raw),chunks=len(parts))),flush=True)
            for i,data in enumerate(parts):print("LOADED_COMPARE_CHUNK "+json.dumps(dict(name=name,index=i,data=base64.b64encode(data).decode())),flush=True)
if __name__=="__main__":main()
