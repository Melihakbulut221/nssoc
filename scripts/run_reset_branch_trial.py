# SPDX-License-Identifier: Apache-2.0
"""Restore exact new postCTS candidate; measure a five-buffer experiment."""
import os,json,subprocess,zipfile,stat,hashlib,re,time
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get("GITHUB_ACTIONS")=="true"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reset-branch-trial";OUT.mkdir()
prior.OUT=OUT/"cts-restore";prior.OUT.mkdir()
result=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING",scope="Three dedicated noninverting reset distribution branches covering755 reported setup paths; upstream identity-only chains verified in actual DB, original cell placement retained. Exact output-branch successor, placement RC only, three corners; no routed timing or serial PHY acceptance.")
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

 run=prior.api("actions/runs/43686936440")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="7bb39994a5c5f6514f7c5c04bededcce4d3da29b" and run["run_attempt"]==1
 bulk_safe=archive(14151092505,"a6c277eb4a18afcd6a2b885d82682cade29ffdc94ecdf5c71ba2848872b34f44","bulk-safe.zip")
 bulk_native=archive(14151355146,"3ce3acc14505a075a653f0ba34244e3607775d0d9293f22cef12f7abd5207454","bulk-native.zip")
 report=json.loads(bulk_safe.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and not report["accepted"]
 assert report["source_run"]==43685594561
 assert report["source_odb_sha256"]=="613df4f452611b2779d5772d6e65f405ea93c509ce385e575cb43a2fb84f8a16"
 assert report["candidate_odb_sha256"]=="891a32b71b5b1bac5f29a02c0cbea7bd3853da5f26d6ecc356de7b086074a507"
 assert len(bulk_native.namelist())==len(set(bulk_native.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in bulk_native.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"bulk-buffer-trial"
 for info in bulk_native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=bulk_native.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 report["repaired_odb_sha256"]=report["candidate_odb_sha256"]
 report["repaired_state"]=report["candidate_state"]

 run=prior.api("actions/runs/43687918155")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="cbab9f4ea80d64416b82f74ffdf9f6506eaf395a" and run["run_attempt"]==1
 cs=archive(14151645842,"403109626190df03fae6ddf30de9991a48e0263594b68aab198c8dae05a18b7c","critical-safe.zip")
 cn=archive(14151148148,"29cdc353d13b860be8033677e1b99448dbd8a7788c4c87336316023db66bfee9","critical-native.zip")
 report=json.loads(cs.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and not report["accepted"]
 assert report["source_run"]==43686936440 and report["candidate_odb_sha256"]=="a4c18befb2a2bba68b351e0d8e2397174a9fac36a32765372c34108b1ba648c1"
 assert len(cn.namelist())==len(set(cn.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in cn.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"critical-load-trial"
 for info in cn.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=cn.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 report["repaired_odb_sha256"]=report["candidate_odb_sha256"]
 report["repaired_state"]=report["candidate_state"]

 run=prior.api("actions/runs/43688957642")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="14db852f55f5a10b6a1de9c46267a9c3d6a07ce0" and run["run_attempt"]==1
 ns=archive(14151584150,"b7eb5e15f8c7a68f70628197517297a92e0c2f241cd9bf896c56a98d5be1cc1b","one-safe.zip")
 nn=archive(14151119606,"fc2f5eae25f6938a3f50c108dd8b37d1b0ade94e655d4c014d779e96226abea7","one-native.zip")
 report=json.loads(ns.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and report["target_margin_50ps"] and not report["accepted"]
 assert report["candidate_odb_sha256"]=="34a18678010315f75b7d4efd4bf39656f228d50a3133e337afb471302e934dda"
 assert len(nn.namelist())==len(set(nn.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in nn.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"one-branch-trial"
 for info in nn.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=nn.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 report["repaired_odb_sha256"]=report["candidate_odb_sha256"]
 report["repaired_state"]=report["candidate_state"]


 run=prior.api("actions/runs/43690386874")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="a244e33ea53a1d5b80464d3f248c6ee01971e64e" and run["run_attempt"]==1
 osafe=archive(14152013712,"8014a9f65613e24fc1d161a31248e2fe4ead85bec51b10c29b7317817405b6d8","output-safe.zip")
 onative=archive(14151958934,"fd8c35d4c9fc724ef2bad06b4b335b4749bf0fe108fbbf60011f027cef136940","output-native.zip")
 report=json.loads(osafe.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="3cea359235759956213066e4c0c37de2aa62ae19044f20b812e240dba3f28dc3"
 assert len(onative.namelist())==len(set(onative.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in onative.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"output-branch-trial"
 for info in onative.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=onative.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
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
 flow=ROOT/"hw/soc/pnr/reset_branch_flow.py"
 protected={str(p):prior.sha(p) for p in [odb,config,initial,flow,Path(__file__),prior.SOURCE/"prepared/physical.sdc",ROOT/"hw/soc/pnr/corrpre_postcts_flow.py",ROOT/"hw/soc/flow/check_timing_derate.tcl"]}
 result.update(source_run=run["id"],source_odb_sha256=prior.sha(odb),baseline=report["measurements"],protected_inputs=protected)
 save()
 cmd=[str(app),"python",str(flow),"--flow","ResetBranchTrial","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(config)]
 (OUT/"run").mkdir()
 start=time.monotonic()
 with (OUT/"native.log").open("w") as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result.update(returncode=code,elapsed_s=time.monotonic()-start)
 if code:print((OUT/"native.log").read_text()[-12000:])
 assert code==0
 assert "NSSOC_THREE_RESET_BRANCHES_IDENTITY_VERIFIED" in (OUT/"native.log").read_text()
 assert "NSSOC_ORIGINAL_PLACEMENT_UNCHANGED_AND_STATUSES_RESTORED" in (OUT/"native.log").read_text()
 assert all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/"run").glob("*-nssoc-corrpreresetbranchafter"+short));assert len(dirs)==1
  folder=dirs[0];assert not (folder/"unpropagated.rpt").read_text().strip()
  d=json.loads((folder/"state_out.json").read_text())
  measurements[corner]={"metrics":{k:v for k,v in d["metrics"].items() if k.endswith("__corner:"+corner)},"directory":str(folder.relative_to(OUT))}
 states=list((OUT/"run").glob("*-nssoc-resetbrancheco/state_out.json"));assert len(states)==1
 state=json.loads(states[0].read_text())
 target_rows={}
 for p in (OUT/"run").glob("*/one-*.rpt"):
  values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",p.read_text());assert values
  target_rows[str(p.relative_to(OUT))]={"worst_slack_ns":min(map(float,values)),"sha256":prior.sha(p)}
 assert len(target_rows)==12
 result.update(target_reports=target_rows,target_margin_50ps=all(v["worst_slack_ns"]>=.05 for k,v in target_rows.items() if "after" in k))
 result.update(status="MEASURED_NOT_ACCEPTED",measurements=measurements,candidate_odb_sha256=prior.sha(state["odb"]),candidate_state=str(states[0].relative_to(OUT)),sources_unchanged=True)
except BaseException as error:
 result.update(status="FAIL_OR_ERROR",error=repr(error));raise
finally:
 result["outputs"]={str(p.relative_to(OUT)):prior.sha(p) for p in (OUT/"run").rglob("*") if p.is_file()}
 if (OUT/"native.log").exists():result["outputs"]["native.log"]=prior.sha(OUT/"native.log")
 save()
