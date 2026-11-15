# SPDX-License-Identifier: Apache-2.0
"""Restore exact new postCTS candidate; measure a five-buffer experiment."""
import os,json,subprocess,zipfile,stat,hashlib,re,time
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get("GITHUB_ACTIONS")=="true"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"remaining-hold-trial";OUT.mkdir()
prior.OUT=OUT/"cts-restore";prior.OUT.mkdir()
result=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING",scope="Three branch-local native identity delays after authenticated same-ODB setup margin >=1ns. All10 remaining-path pins and40boundary ports plus global3corner STA remeasured; original placement protected. No routed timing or full serialPHY acceptance.")
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

 run=prior.api("actions/runs/43687226105")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="be6bcaff0adfd2b82d9addc94dff3fa592d73411" and run["run_attempt"]==1
 hs=archive(14151266033,"a302206994c7d36c5c4b434753f279e39fa179a669d83df04427c6c12ec5d67b","hold-safe.zip")
 hn=archive(14151216414,"0bc6d45ae804f69c1fab2a7118d8ff9f30a18060b6a523e3789e118dca15a708","hold-native.zip")
 report=json.loads(hs.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and not report["accepted"]
 assert report["all_boundary_margins_50ps"] is True and report["source_run"]==43682771828
 assert report["candidate_odb_sha256"]=="041148ea5b9550a31c6ad2a804f0c192702a928dd114dde00aaa6bad835015e7"
 assert len(hn.namelist())==len(set(hn.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in hn.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"boundary-hold-trial"
 for info in hn.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=hn.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)

 run=prior.api("actions/runs/43690493434")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="d6671978da578bc7fe8840c4c9ca6053b667aaee" and run["run_attempt"]==1
 ss=archive(14152756388,"25615ebb6be631cae972991f6c4d65d4d3cf01c5ee6d8dbd13ca10568b0e26f1","selective-safe.zip")
 sn=archive(14152826262,"72c2789cc116cad1500b6fe75595a24e2b6101483908a73db3a31be3a8bae1a9","selective-native.zip")
 report=json.loads(ss.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and report["selected_margin_50ps"] and report["boundary_margin_50ps"] and not report["accepted"]
 assert report["source_odb_sha256"]=="041148ea5b9550a31c6ad2a804f0c192702a928dd114dde00aaa6bad835015e7"
 assert report["candidate_odb_sha256"]=="9627224813c5ce11cf43ffc3758d9f5f3b47802081ce587911e0944ccb0445f8"
 assert len(sn.namelist())==len(set(sn.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in sn.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"selective-hold-trial"
 for info in sn.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=sn.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 names=[n for n in ss.namelist() if n.endswith("/min.rpt") and "afterfast" in n];assert len(names)==1
 raw=ss.read(names[0]);assert hashlib.sha256(raw).hexdigest()==report["outputs"][names[0]]
 targets=[];paths=[]
 for part in raw.decode().split("Startpoint: ")[1:]:
  slack=re.search(r"([-+]?\d+\.\d+)\s+slack \(",part)
  if not slack or float(slack[1])>=0:continue
  start=part.splitlines()[0];end=re.search(r"Endpoint: (.+)",part)[1];lines=part.splitlines()
  idx=next(i for i,line in enumerate(lines) if start+"/Q " in line or start+"/Q_N " in line)
  segment="\n".join(lines[idx:]).split("data arrival time")[0]
  pins=re.findall(r"[\^v]\s+(\S+) \((sg13g2_\S+)\)",segment)
  assert len(pins)>=2
  candidates=[(pin,cell) for pin,cell in pins[1:] if pin.rsplit("/",1)[-1] not in ("X","Y","Q","Q_N")]
  assert candidates
  paths.append(dict(start=start,endpoint=end,observed_fast_hold_ns=float(slack[1]),candidate_pins=[p for p,c in candidates]))
  for pin,cell in candidates:
   if pin not in {v["sink"] for v in targets}:targets.append(dict(sink=pin,sink_cell=cell))
 assert len(paths)==3 and 3<=len(targets)<=15
 target_path=OUT/"targets.json";target_path.write_text(json.dumps(targets,indent=2)+"\n")
 result.update(branch_targets=targets,remaining_paths=paths,target_report_sha256=hashlib.sha256(raw).hexdigest())

 # Authenticate completed same-ODB through-pin setup measurement before repair.
 run_saved=run
 run=prior.api("actions/runs/43691367680")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="d322dcdad7844ec794a47252e9d9fcebc3b89ca9" and run["run_attempt"]==1
 headroom=archive(14152613116,"8fb6a5f3e443a53d20889a6a0332358f43277ad1a90c671301ff2646908d1a26","remaining-hold-trial.zip")
 measured=json.loads(headroom.read("result.json"))
 assert measured["source_odb_sha256"]==report["candidate_odb_sha256"]==measured["candidate_odb_sha256"]
 assert measured["sources_unchanged"] and measured["returncode"]==0 and not measured["repair_executed"]
 selected=[ "$abc$735036$auto$blifparse.cc:397:parse_blif$771053/A1", "$abc$735036$auto$blifparse.cc:397:parse_blif$770030/A2", "$abc$735036$auto$blifparse.cc:397:parse_blif$770358/A" ]
 for pin in selected:
  entries=[(name,row)for name,row in measured["branch_reports"].items()if row["pin"]==pin and name.endswith("-max.rpt")]
  assert len(entries)==3 and min(row["worst_slack_ns"]for name,row in entries)>=1.0
  for name,row in entries:
   raw=headroom.read(name);assert hashlib.sha256(raw).hexdigest()==row["sha256"]==measured["outputs"][name]
 result.update(headroom_run=run["id"],headroom_head=run["head_sha"],selected_pins=selected)
 run=run_saved

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
 for cell in ["sg13g2_dlygate4sd3_1"]:
  module=re.search(r"module "+cell+r"\b.*?endmodule",raw.decode(),re.S)[0]
  assert re.search(r"buf\s*\(X, A\);",module) and "output X;" in module and "input A;" in module
 app=Path(os.environ["CLOUD_APPIMAGE"]);prior.verify(app,"x86_64")
 flow=ROOT/"hw/soc/pnr/remaining_hold_flow.py"
 protected={str(p):prior.sha(p) for p in [odb,config,initial,flow,target_path,Path(__file__),prior.SOURCE/"prepared/physical.sdc",ROOT/"hw/soc/pnr/corrpre_postcts_flow.py",ROOT/"hw/soc/flow/check_timing_derate.tcl"]}
 result.update(source_run=run["id"],source_odb_sha256=prior.sha(odb),baseline=report["measurements"],protected_inputs=protected)
 save()
 cmd=[str(app),"python",str(flow),"--flow","RemainingHoldTrial","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(config)]
 (OUT/"run").mkdir()
 start=time.monotonic()
 with (OUT/"native.log").open("w") as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result.update(returncode=code,elapsed_s=time.monotonic()-start)
 if code:print((OUT/"native.log").read_text()[-12000:])
 assert code==0
 assert "NSSOC_IO_PATHS_MEASURED" in (OUT/"native.log").read_text()
 assert "NSSOC_THREE_REMAINING_HOLD_BRANCHES_IDENTITY_VERIFIED" in (OUT/"native.log").read_text()
 assert "NSSOC_ORIGINAL_PLACEMENT_UNCHANGED_AND_STATUSES_RESTORED" in (OUT/"native.log").read_text()
 assert all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/"run").glob("*-nssoc-corrpretargetioafter"+short));assert len(dirs)==1
  folder=dirs[0];assert not (folder/"unpropagated.rpt").read_text().strip()
  d=json.loads((folder/"state_out.json").read_text())
  measurements[corner]={"metrics":{k:v for k,v in d["metrics"].items() if k.endswith("__corner:"+corner)},"directory":str(folder.relative_to(OUT))}
 states=list((OUT/"run").glob("*-nssoc-corrpretargetioafterfast/state_out.json"));assert len(states)==1
 state=json.loads(states[0].read_text())
 assert prior.sha(state["odb"])!=report["repaired_odb_sha256"]
 rows={}
 for p in (OUT/"run").glob("*/io-*.rpt"):
  text=p.read_text();values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",text);assert values,str(p)
  rows[str(p.relative_to(OUT))]={"port":re.search(r"NSSOC_TARGET_PORT (.+)",text)[1],"worst_slack_ns":min(map(float,values)),"paths":len(values),"sha256":prior.sha(p)}
 assert len(rows)==240,len(rows)
 branch_rows={}
 for p in (OUT/"run").glob("*/branch-*.rpt"):
  text=p.read_text();values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",text);assert values,str(p)
  branch_rows[str(p.relative_to(OUT))]={"pin":re.search(r"NSSOC_TARGET_BRANCH_PIN (.+)",text)[1],"worst_slack_ns":min(map(float,values)),"paths":len(values),"sha256":prior.sha(p)}
 assert len(branch_rows)==len(targets)*6
 result.update(boundary_reports=rows,branch_reports=branch_rows,repair_executed=True,selected_margin_50ps=all(v["worst_slack_ns"]>=.05 for v in branch_rows.values()if v["pin"] in selected),boundary_margin_50ps=all(v["worst_slack_ns"]>=.05 for v in rows.values()))
 result.update(status="MEASURED_NOT_ACCEPTED",measurements=measurements,candidate_odb_sha256=prior.sha(state["odb"]),candidate_state=str(states[0].relative_to(OUT)),sources_unchanged=True)
except BaseException as error:
 result.update(status="FAIL_OR_ERROR",error=repr(error));raise
finally:
 result["outputs"]={str(p.relative_to(OUT)):prior.sha(p) for p in (OUT/"run").rglob("*") if p.is_file()}
 if (OUT/"native.log").exists():result["outputs"]["native.log"]=prior.sha(OUT/"native.log")
 save()
