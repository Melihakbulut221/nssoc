# SPDX-License-Identifier: Apache-2.0
"""Restore exact new postCTS candidate; measure a five-buffer experiment."""
import os,json,subprocess,zipfile,stat,hashlib,re,time
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get("GITHUB_ACTIONS")=="true"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"selective-hold-trial";OUT.mkdir()
prior.OUT=OUT/"cts-restore";prior.OUT.mkdir()
result=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING",scope="120 selected branch-local identity delays on exact boundary-hold successor. All123 branches and40 boundary ports remeasured in3corners, three unsafe branches remain explicitly open; no full closure. No routed timing or serial PHY acceptance.")
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
 names=[n for n in hs.namelist() if n.endswith("/min.rpt") and "afterfast" in n];assert len(names)==1
 raw=hs.read(names[0]);assert hashlib.sha256(raw).hexdigest()==report["outputs"][names[0]]
 targets=[]
 for part in raw.decode().split("Startpoint: ")[1:]:
  slack=re.search(r"([-+]?\d+\.\d+)\s+slack \(",part)
  if not slack or float(slack[1])>=0:continue
  start=part.splitlines()[0];end=re.search(r"Endpoint: (.+)",part)[1];lines=part.splitlines()
  idx=next(i for i,line in enumerate(lines) if start+"/Q " in line or start+"/Q_N " in line)
  segment="\n".join(lines[idx:]).split("data arrival time")[0]
  pins=re.findall(r"[\^v]\s+(\S+) \((sg13g2_\S+)\)",segment)
  assert len(pins)>=2
  targets.append({"source":pins[0][0],"sink":pins[1][0],"source_cell":pins[0][1],"sink_cell":pins[1][1],"endpoint":end,"observed_fast_hold_ns":float(slack[1])})
 assert len(targets)==len({v["sink"] for v in targets})==123
 target_path=OUT/"targets.json";target_path.write_text(json.dumps(targets,indent=2)+"\n")
 result["branch_targets"]=targets
 result["target_report_sha256"]=hashlib.sha256(raw).hexdigest()

 source_run_record=run
 headroom_run=prior.api("actions/runs/43688204095")
 assert headroom_run["status"]=="completed" and headroom_run["conclusion"]=="success" and headroom_run["head_sha"]=="b3b454d06bdf4b958beeb1ec81acf750c2e3c80b" and headroom_run["run_attempt"]==1
 run=headroom_run
 hp=archive(14151417762,"45be2e9740d76eaedf39fd645e2fc03e8d0df761e84a481eae901c3863899668","headroom-safe.zip")
 run=source_run_record
 hr=json.loads(hp.read("result.json"))
 assert hr["source_head"]==headroom_run["head_sha"] and hr["sources_unchanged"] and hr["returncode"]==0 and hr["repair_executed"] is False
 assert hr["source_run"]==43687226105 and hr["source_odb_sha256"]==hr["candidate_odb_sha256"]==report["candidate_odb_sha256"]
 assert hr["branch_targets"]==targets
 assert len(hr["branch_reports"])==738 and len(hr["boundary_reports"])==240
 setup={}
 for name,row in hr["branch_reports"].items():
  assert hashlib.sha256(hp.read(name)).hexdigest()==row["sha256"]==hr["outputs"][name]
  if name.endswith("-max.rpt"):setup.setdefault(row["pin"],[]).append(row["worst_slack_ns"])
 assert all(len(v)==3 for v in setup.values()) and len(setup)==123
 selected=[row for row in targets if min(setup[row["sink"]])>=1.0]
 excluded=[dict(row,min_setup_ns=min(setup[row["sink"]])) for row in targets if min(setup[row["sink"]])<1.0]
 assert len(selected)==120 and len(excluded)==3
 selected_path=OUT/"selected.json";selected_path.write_text(json.dumps(selected,indent=2)+"\n")
 result.update(selected_targets=selected,excluded_targets=excluded,headroom_run=headroom_run["id"],headroom_head=headroom_run["head_sha"],headroom_source_odb_sha256=hr["source_odb_sha256"])

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
 flow=ROOT/"hw/soc/pnr/selective_hold_flow.py"
 protected={str(p):prior.sha(p) for p in [odb,config,initial,flow,target_path,selected_path,Path(__file__),prior.SOURCE/"prepared/physical.sdc",ROOT/"hw/soc/pnr/corrpre_postcts_flow.py",ROOT/"hw/soc/flow/check_timing_derate.tcl"]}
 result.update(source_run=run["id"],source_odb_sha256=prior.sha(odb),baseline=report["measurements"],protected_inputs=protected)
 save()
 cmd=[str(app),"python",str(flow),"--flow","SelectiveHoldTrial","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(config)]
 (OUT/"run").mkdir()
 start=time.monotonic()
 with (OUT/"native.log").open("w") as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result.update(returncode=code,elapsed_s=time.monotonic()-start)
 if code:print((OUT/"native.log").read_text()[-12000:])
 assert code==0
 assert "NSSOC_120_MEASURED_BRANCH_IDENTITY_DELAYS_VERIFIED" in (OUT/"native.log").read_text()
 assert all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/"run").glob("*-nssoc-corrpretargetioafter"+short));assert len(dirs)==1
  folder=dirs[0];assert not (folder/"unpropagated.rpt").read_text().strip()
  d=json.loads((folder/"state_out.json").read_text())
  measurements[corner]={"metrics":{k:v for k,v in d["metrics"].items() if k.endswith("__corner:"+corner)},"directory":str(folder.relative_to(OUT))}
 states=list((OUT/"run").glob("*-nssoc-selectiveholdeco/state_out.json"));assert len(states)==1
 state=json.loads(states[0].read_text())
 assert "NSSOC_ORIGINAL_PLACEMENT_UNCHANGED_AND_STATUSES_RESTORED" in (OUT/"native.log").read_text()
 rows={}
 for p in (OUT/"run").glob("*/io-*.rpt"):
  text=p.read_text();values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",text);assert values,str(p)
  rows[str(p.relative_to(OUT))]={"port":re.search(r"NSSOC_TARGET_PORT (.+)",text)[1],"worst_slack_ns":min(map(float,values)),"paths":len(values),"sha256":prior.sha(p)}
 assert len(rows)==240,len(rows)
 branch_rows={}
 for p in (OUT/"run").glob("*/branch-*.rpt"):
  text=p.read_text();values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",text);assert values,str(p)
  branch_rows[str(p.relative_to(OUT))]={"pin":re.search(r"NSSOC_TARGET_BRANCH_PIN (.+)",text)[1],"worst_slack_ns":min(map(float,values)),"paths":len(values),"sha256":prior.sha(p)}
 assert len(branch_rows)==738
 selected_pins={v["sink"] for v in selected}
 result.update(boundary_reports=rows,branch_reports=branch_rows,repair_executed=True,selected_margin_50ps=all(v["worst_slack_ns"]>=.05 for v in branch_rows.values() if v["pin"] in selected_pins),boundary_margin_50ps=all(v["worst_slack_ns"]>=.05 for v in rows.values()))
 result.update(status="MEASURED_NOT_ACCEPTED",measurements=measurements,candidate_odb_sha256=prior.sha(state["odb"]),candidate_state=str(states[0].relative_to(OUT)),sources_unchanged=True)
except BaseException as error:
 result.update(status="FAIL_OR_ERROR",error=repr(error));raise
finally:
 result["outputs"]={str(p.relative_to(OUT)):prior.sha(p) for p in (OUT/"run").rglob("*") if p.is_file()}
 if (OUT/"native.log").exists():result["outputs"]["native.log"]=prior.sha(OUT/"native.log")
 save()
