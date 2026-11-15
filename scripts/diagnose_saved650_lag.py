# SPDX-License-Identifier: Apache-2.0
"""Diagnose saved full-load wave, never rerun or relax its acceptance gates."""
import os,json,subprocess,hashlib,zipfile,stat
from pathlib import Path
import numpy as np
from cdr_mos650_full650_loaded import read_streamed_wave,START,UI,STOP,STEP
assert os.environ.get("GITHUB_ACTIONS")=="true"
OUT=Path("saved650-diagnosis");OUT.mkdir()
def api(path):
 return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path]))
def sha(p):
 with Path(p).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
run=api("actions/runs/43682293907")
assert run["status"]=="completed" and run["conclusion"]=="failure" and run["head_sha"]=="cf0a6547b53e7dd3b5961bd92bfcd74347cde78f" and run["run_attempt"]==1
def fetch(i,h,name):
 meta=api("actions/artifacts/"+str(i))
 assert meta["workflow_run"]["id"]==run["id"] and meta["digest"]=="sha256:"+h and not meta["expired"]
 p=Path(name)
 with p.open("xb") as f:subprocess.run(["gh","api","repos/Melihakbulut221/nssoc/actions/artifacts/"+str(i)+"/zip"],stdout=f,check=True)
 assert sha(p)==h
 z=zipfile.ZipFile(p);assert len(z.namelist())==len(set(z.namelist()))
 for info in z.infolist():
  n=Path(info.filename);assert not n.is_absolute() and ".." not in n.parts and not stat.S_ISLNK(info.external_attr>>16)
 return z
safe=fetch(14151372439,"e4f73f8e9cfa6544455ddb87c479e91300962c6785ec34515efc615e2cfeddab","safe.zip")
m=json.loads(safe.read("loaded-n1-nominal_late.json"))
assert m["source_head"]==run["head_sha"] and m["sources_unchanged"] and m["returncode"]==0 and not m["accepted"]
native=fetch(14151930537,"1df16dedf119d2511bb1bbddf0881cc258db82bb9251f6015b61ec08c43b1423","native.zip")
names=[n for n in native.namelist() if n.endswith("/loaded-n1-nominal_late/wave.raw")]
assert len(names)==1,names
raw=Path("wave.raw")
with native.open(names[0]) as src,raw.open("xb") as dst:
 import shutil
 shutil.copyfileobj(src,dst,1024*1024)
assert sha(raw)==m["raw_capture"]["raw_sha256"]
t,d,capture=read_streamed_wave(raw,m["vectors"],STOP,STEP)
assert capture["raw_sha256"]==m["raw_capture"]["raw_sha256"]
bound=m["binding"]
def v(n):
 n=bound["aliases"].get(n,n)
 return np.zeros(len(t)) if n=="0" else d["v("+n+")"]
def scalar(rows):return {k:v for k,v in rows.items() if not isinstance(v,(list,dict))}
out=dict(source_run=run["id"],source_head=run["head_sha"],diagnostic_head=os.environ["GITHUB_SHA"],raw_capture={k:v for k,v in capture.items() if k!="logical_vector_order"},accepted=False,full_phy_accepted=False,scope="Read-only saved-wave timing and device diagnosis; no changed circuit, gate or simulator run.",samplers={},comparisons={},unsafe_hbts={})
for tag in "abcdxy":
 is_sampler=tag in "abcd"
 p,n=("xpd."+tag+"qp","xpd."+tag+"qn") if is_sampler else (tag+"p",tag+"n")
 delta=v(p)-v(n)
 expected=m["expected_samples"][tag] if is_sampler else m["expected_comparisons"][tag]
 edges=np.array([START+(i+(0 if tag=="b" else .5))*UI for i in range(1,256)])
 rows={}
 for phase in [.1,.2,.3,.4,.5,.6,.75,.9]:
  values=np.interp(edges+phase*UI,t,delta)*(2*np.array(expected)-1)
  rows[str(phase)]=dict(minimum_v=float(values.min()),weak=int((values<.1).sum()),wrong=int((values<=0).sum()),samples=len(values))
 detail=dict(frozen=scalar((m["sampler_checks"] if is_sampler else m["comparisons"])[tag]),phases=rows)
 if is_sampler:
  delays=np.array(m["sampler_checks"][tag]["clock_to_valid_by_bit_s"])
  detail["delay_quantiles_s"]={str(q):float(np.quantile(delays,q)) for q in [0,.5,.9,.99,1]}
 (out["samplers"] if is_sampler else out["comparisons"])[tag]=detail
active=t>=START
for name,check in m["device_checks"].items():
 reasons=[]
 for key,limit,op in [("minimum_active_vce_v",.4,"min"),("maximum_alltime_abs_vce_v",1.6,"max"),("maximum_alltime_abs_vbe_v",1.,"max"),("maximum_alltime_abs_ic_per_emitter_a",.003,"strictmax")]:
  if (check[key]<limit if op=="min" else check[key]>=limit if op=="strictmax" else check[key]>limit):reasons.append(key)
 if reasons:
  dev=bound["groups"]["npn13g2"][name];vc,vb,ve,_=map(v,dev["nodes"]);idx=np.flatnonzero(active)[np.argmin((vc-ve)[active])]
  out["unsafe_hbts"][name]=dict(reasons=reasons,checks=check,device=dev,minimum_vce_at_s=float(t[idx]),voltages_at_minimum=dict(c=float(vc[idx]),b=float(vb[idx]),e=float(ve[idx])))
out["stage_tail_currents_a"]=m["minimum_active_stage_tail_current_a"]
out["phase_average_v"]=m["phase_average_v"];out["vi"]=m["vi"]
out["diagnostics"]=m["diagnostics"]
out["source_measurement_sha256"]=hashlib.sha256(safe.read("loaded-n1-nominal_late.json")).hexdigest()
out["raw_unchanged"]=sha(raw)==capture["raw_sha256"]
assert out["raw_unchanged"]

# Diagnostic lag sweep only: acceptance retains the original unshifted clock.
out["lag_diagnosis"]={}
for tag in "abcdxy":
 expected=np.array(m["expected_samples"][tag] if tag in "abcd" else m["expected_comparisons"][tag])
 p,n=("xpd."+tag+"qp","xpd."+tag+"qn") if tag in "abcd" else (tag+"p",tag+"n")
 delta=v(p)-v(n);rows={}
 for lag in range(-4,5):
  times=START+(np.arange(1,256)+(0 if tag=="b" else .5)+.75+lag)*UI
  mask=(times>=START+8*UI)&(times<=START+255*UI)
  signed=np.interp(times[mask],t,delta)*(2*expected[mask]-1)
  rows[str(lag)]=dict(samples=int(mask.sum()),wrong=int((signed<=0).sum()),weak=int((signed<.1).sum()),mean_signed_v=float(signed.mean()),minimum_signed_v=float(signed.min()))
 out["lag_diagnosis"][tag]=rows
out["clock_pair_observations"]={}
for name in ["xpd.xd0211","xpd.xd0212"]:
 dev=bound["groups"]["npn13g2"][name];vc,vb,ve,_=map(v,dev["nodes"])
 rows={}
 for phase in [0,.1,.25,.4,.5,.6,.75,.9]:
  times=START+(np.arange(8,255)+phase)*UI
  rows[str(phase)]={label:dict(minimum=float(np.interp(times,t,val).min()),maximum=float(np.interp(times,t,val).max()),mean=float(np.interp(times,t,val).mean()))for label,val in [("vc",vc),("vb",vb),("ve",ve),("vce",vc-ve)]}
 out["clock_pair_observations"][name]=rows
out["lag_scope"]="Diagnostic only. No delayed/shifted sampling constitutes acceptance or modifies original electrical gates."

(OUT/"result.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(dict(raw_unchanged=True,unsafe_hbts=list(out["unsafe_hbts"]),phase_average_v=out["phase_average_v"])))
