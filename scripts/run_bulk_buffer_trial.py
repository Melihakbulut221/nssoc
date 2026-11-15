# SPDX-License-Identifier: Apache-2.0
"""Restore exact new postCTS candidate; measure a five-buffer experiment."""
import os,json,subprocess,zipfile,stat,hashlib,re,time
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get("GITHUB_ACTIONS")=="true"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"bulk-buffer-trial";OUT.mkdir()
prior.OUT=OUT/"cts-restore";prior.OUT.mkdir()
result=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING",scope="102 measured noninverting buffer replacements on exact current repaired netlist, placement RC only; three-corner global measurements. No routed timing or serial PHY acceptance.")
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

 # Restore the exact five-buffer successor, not a recreated placement.
 run=prior.api("actions/runs/43685594561")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="e96a0f224c2d1e89d4a7b4398a1695a6239b6f23" and run["run_attempt"]==1
 nextsafe=archive(14150651901,"9d8bc3997b63a084357b525af386bd003e240ad246489c112978c0b244f333b9","five-safe.zip")
 nextnative=archive(14150412445,"086a5f3b6e6370c406e779a994e733ea5191419be0e0539aab94357d15d7f613","five-native.zip")
 report=json.loads(nextsafe.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="613df4f452611b2779d5772d6e65f405ea93c509ce385e575cb43a2fb84f8a16"
 assert len(nextnative.namelist())==len(set(nextnative.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in nextnative.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"five-buffer-trial"
 for info in nextnative.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=nextnative.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 # Derive targets only from authenticated negative slow setup paths.
 targets={}
 names=[n for n in nextsafe.namelist() if n.endswith("/max.rpt") and "afterslow" in n];assert len(names)==1
 raw=nextsafe.read(names[0]);assert hashlib.sha256(raw).hexdigest()==report["outputs"][names[0]]
 for part in raw.decode().split("Startpoint: ")[1:]:
  if "slack (VIOLATED)" not in part:continue
  for match in re.finditer(r"^\s*(\d+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+[\^v]\s+(.+)/X \(sg13g2_buf_([124])\)",part,re.M):
   name=match[6];cap=float(match[2]);slew=float(match[3]);delay=float(match[4])
   if not(name.startswith("fanout") or name.startswith("$abc$")) or cap<0.03 or slew<0.3:continue
   row={"name":name,"cell":"sg13g2_buf_"+match[7],"cap_pf":cap,"slew_ns":slew,"delay_ns":delay}
   if name not in targets or targets[name]["delay_ns"]<delay:targets[name]=row
 assert len(targets)==102,len(targets)
 target_path=OUT/"targets.json";target_path.write_text(json.dumps(sorted(targets.values(),key=lambda x:x["name"]),indent=2)+"\n")
 result["target_report_sha256"]=hashlib.sha256(raw).hexdigest()
 result["targets"]=json.loads(target_path.read_text())
 report["repaired_odb_sha256"]=report["candidate_odb_sha256"]
 report["repaired_state"]=report["candidate_state"]
 state=json.loads((successor/report["repaired_state"]).read_text())

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
 for cell in ["sg13g2_buf_1","sg13g2_buf_2","sg13g2_buf_4","sg13g2_buf_8","sg13g2_buf_16"]:
  module=re.search(r"module "+cell+r"\b.*?endmodule",raw.decode(),re.S)[0]
  assert re.search(r"buf\s*\(X, A\);",module) and "output X;" in module and "input A;" in module
 app=Path(os.environ["CLOUD_APPIMAGE"]);prior.verify(app,"x86_64")
 flow=ROOT/"hw/soc/pnr/bulk_buffer_flow.py"
 protected={str(p):prior.sha(p) for p in [odb,config,initial,flow,target_path,Path(__file__),prior.SOURCE/"prepared/physical.sdc",ROOT/"hw/soc/pnr/corrpre_postcts_flow.py",ROOT/"hw/soc/flow/check_timing_derate.tcl"]}
 result.update(source_run=run["id"],source_odb_sha256=prior.sha(odb),baseline=report["measurements"],protected_inputs=protected)
 save()
 cmd=[str(app),"python",str(flow),"--flow","BulkBufferTrial","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(config)]
 (OUT/"run").mkdir()
 start=time.monotonic()
 with (OUT/"native.log").open("w") as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result.update(returncode=code,elapsed_s=time.monotonic()-start)
 if code:print((OUT/"native.log").read_text()[-12000:])
 assert code==0
 assert "NSSOC_102_MEASURED_BUFFER_SIZES_SAME_INCIDENCE" in (OUT/"native.log").read_text()
 assert all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/"run").glob("*-nssoc-corrprebulkbufferafter"+short));assert len(dirs)==1
  folder=dirs[0];assert not (folder/"unpropagated.rpt").read_text().strip()
  d=json.loads((folder/"state_out.json").read_text())
  measurements[corner]={"metrics":{k:v for k,v in d["metrics"].items() if k.endswith("__corner:"+corner)},"directory":str(folder.relative_to(OUT))}
 states=list((OUT/"run").glob("*-nssoc-bulkbuffereco/state_out.json"));assert len(states)==1
 state=json.loads(states[0].read_text())
 result.update(status="MEASURED_NOT_ACCEPTED",measurements=measurements,candidate_odb_sha256=prior.sha(state["odb"]),candidate_state=str(states[0].relative_to(OUT)),sources_unchanged=True)
except BaseException as error:
 result.update(status="FAIL_OR_ERROR",error=repr(error));raise
finally:
 result["outputs"]={str(p.relative_to(OUT)):prior.sha(p) for p in (OUT/"run").rglob("*") if p.is_file()}
 if (OUT/"native.log").exists():result["outputs"]["native.log"]=prior.sha(OUT/"native.log")
 save()
