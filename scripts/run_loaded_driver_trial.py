# SPDX-License-Identifier: Apache-2.0
"""Restore exact new postCTS candidate; measure a five-buffer experiment."""
import os,json,subprocess,zipfile,stat,hashlib,re,time
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get("GITHUB_ACTIONS")=="true"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"loaded-driver-trial";OUT.mkdir()
prior.OUT=OUT/"cts-restore";prior.OUT.mkdir()
result=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING",scope="Nine noninverting buffer replacements and one identity buffer load stage on exact current repaired netlist, placement RC only; three-corner global measurements. No routed timing or serial PHY acceptance.")
def save(): (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
save()
try:
 prior.restore(None,{})
 run=prior.api("actions/runs/43682771828")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="486f80761d93074926fcfbfa2bac02b42aba9835" and run["run_attempt"]==1
 def archive(i,h,name):
  m=prior.api("actions/artifacts/"+str(i))
  assert m["workflow_run"]["id"]==run["id"] and m["workflow_run"]["head_sha"]==run["head_sha"] and m["digest"]=="sha256:"+h and not m["expired"]
  p=OUT/name
  with p.open("xb") as f:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(i)+"/zip"],stdout=f,check=True)
  assert prior.sha(p)==h
  return zipfile.ZipFile(p)
 safe=archive(14150425741,"5a51bcb461b07af9822d4408ce2b5d4955e5c88bf619a1e5c720adcb3b64f643","safe.zip")
 native=archive(14150655431,"33ed1d35db904f9f4184d6348e6076f9762c4d154a1c87a6da801c5c12bcaa2f","native.zip")
 report=json.loads(safe.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and not report["accepted"]
 assert report["repaired_odb_sha256"]=="9b80811bdaeb646b09207f83f33eda68a8f59273374001548a19996b92b36fce"
 source=ROOT/"hw/soc/out/cloud-predecode-postcts";source.mkdir()
 assert len(native.namelist())==len(set(native.namelist()))
 assert {n for n in native.namelist() if not n.endswith("/")}==set(report["outputs"])|{"result.json"}
 for i in native.infolist():
  name=prior.relative(i.filename);assert not stat.S_ISLNK(i.external_attr>>16)
  if i.is_dir():continue
  raw=native.read(i);expected=hashlib.sha256(safe.read("result.json")).hexdigest() if i.filename=="result.json" else report["outputs"][i.filename]
  assert hashlib.sha256(raw).hexdigest()==expected
  p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 state=json.loads((source/report["repaired_state"]).read_text())
 odb=Path(state["odb"]);assert prior.sha(odb)==report["repaired_odb_sha256"]
 state["metrics"]={}
 initial=OUT/"initial.json";initial.write_text(json.dumps(state))
 config=source/"trial-config.json"
 cfg=json.loads(config.read_text())
 assert cfg["CLOCK_PERIOD"]==20 and cfg["TIME_DERATING_CONSTRAINT"]==5.0
 assert cfg["SETUP_VIOLATION_CORNERS"]==cfg["HOLD_VIOLATION_CORNERS"]==["*"]
 # Authenticate both original noninverting buffer definitions.
 import base64
 model=json.loads(subprocess.check_output(["gh","api","repos/IHP-GmbH/IHP-Open-PDK/contents/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v?ref=c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c"]))
 raw=base64.b64decode(model["content"])
 assert hashlib.sha256(raw).hexdigest()=="28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4"
 for cell in ["sg13g2_buf_1","sg13g2_buf_2","sg13g2_buf_4","sg13g2_buf_8"]:
  module=re.search(r"module "+cell+r"\b.*?endmodule",raw.decode(),re.S)[0]
  assert re.search(r"buf\s*\(X, A\);",module) and "output X;" in module and "input A;" in module
 app=Path(os.environ["CLOUD_APPIMAGE"]);prior.verify(app,"x86_64")
 flow=ROOT/"hw/soc/pnr/loaded_driver_flow.py"
 protected={str(p):prior.sha(p) for p in [odb,config,initial,flow,Path(__file__),prior.SOURCE/"prepared/physical.sdc",ROOT/"hw/soc/pnr/corrpre_postcts_flow.py",ROOT/"hw/soc/flow/check_timing_derate.tcl"]}
 result.update(source_run=run["id"],source_odb_sha256=prior.sha(odb),baseline=report["measurements"]["after"],protected_inputs=protected)
 save()
 cmd=[str(app),"python",str(flow),"--flow","LoadedDriverTrial","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(config)]
 (OUT/"run").mkdir()
 start=time.monotonic()
 with (OUT/"native.log").open("w") as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result.update(returncode=code,elapsed_s=time.monotonic()-start)
 if code:print((OUT/"native.log").read_text()[-12000:])
 assert code==0
 assert "NSSOC_NINE_SIZES_ONE_IDENTITY_STAGE_INCIDENCE_VERIFIED" in (OUT/"native.log").read_text()
 assert all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/"run").glob("*-nssoc-corrpreloadeddriverafter"+short));assert len(dirs)==1
  folder=dirs[0];assert not (folder/"unpropagated.rpt").read_text().strip()
  d=json.loads((folder/"state_out.json").read_text())
  measurements[corner]={"metrics":{k:v for k,v in d["metrics"].items() if k.endswith("__corner:"+corner)},"directory":str(folder.relative_to(OUT))}
 states=list((OUT/"run").glob("*-nssoc-loadeddrivereco/state_out.json"));assert len(states)==1
 state=json.loads(states[0].read_text())
 result.update(status="MEASURED_NOT_ACCEPTED",measurements=measurements,candidate_odb_sha256=prior.sha(state["odb"]),candidate_state=str(states[0].relative_to(OUT)),sources_unchanged=True)
except BaseException as error:
 result.update(status="FAIL_OR_ERROR",error=repr(error));raise
finally:
 result["outputs"]={str(p.relative_to(OUT)):prior.sha(p) for p in (OUT/"run").rglob("*") if p.is_file()}
 if (OUT/"native.log").exists():result["outputs"]["native.log"]=prior.sha(OUT/"native.log")
 save()
