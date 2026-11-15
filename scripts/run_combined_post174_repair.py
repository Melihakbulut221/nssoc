# SPDX-License-Identifier: Apache-2.0
"""Restore exact new postCTS candidate; measure a five-buffer experiment."""
import os,json,subprocess,zipfile,stat,hashlib,re,time
from pathlib import Path
import cloud_predecode_postcts as prior
assert os.environ.get("GITHUB_ACTIONS")=="true"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"combined-post174-repair-trial";OUT.mkdir()
prior.OUT=OUT/"cts-restore";prior.OUT.mkdir()
result=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING",scope="35 native cells on34 measured inputs covering35 remaining reported paths on actual174-repair3b0afb ODB, all corners and40boundaryports. No mutation or routed/fullPHY acceptance.")
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


 run=prior.api("actions/runs/43691893753")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="8993198b17ea0a4f3fa76211ee82141208f98b89" and run["run_attempt"]==1
 rs=archive(14152692973,"ac6398c0738207b4fb3805f95c166f1e335a48e16bbfa1a602a4b545289ed562","reset-safe.zip")
 rn=archive(14153077350,"1e50fd1359572512c930ab780350b160c463498840667793ae97471c5120ad3c","reset-native.zip")
 report=json.loads(rs.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="d2c53ac45dc6f60418d2b1ef5dc27222826f8d91bddd128907e3fb09ff977ebd"
 assert len(rn.namelist())==len(set(rn.namelist()))
 expected={n[len("run/"):] for n in report["outputs"] if n.startswith("run/")}
 assert {n for n in rn.namelist() if not n.endswith("/")}==expected
 successor=ROOT/"reset-branch-trial"
 for info in rn.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=rn.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 report["repaired_odb_sha256"]=report["candidate_odb_sha256"]
 report["repaired_state"]=report["candidate_state"]
 saved_run=run
 run=prior.api("actions/runs/43690493434")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="d6671978da578bc7fe8840c4c9ca6053b667aaee"
 selected_report=json.loads(archive(14152756388,"25615ebb6be631cae972991f6c4d65d4d3cf01c5ee6d8dbd13ca10568b0e26f1","selected-plan.zip").read("result.json"))
 selected=selected_report["selected_targets"];assert len(selected)==120 and len({v["sink"]for v in selected})==120
 (OUT/"selected.json").write_text(json.dumps(selected,indent=2)+"\n")
 extra=["$abc$735036$auto$blifparse.cc:397:parse_blif$771053/A1","$abc$735036$auto$blifparse.cc:397:parse_blif$770030/A2","$abc$735036$auto$blifparse.cc:397:parse_blif$770358/A"]
 targets=[dict(sink=r["sink"])for r in selected]+[dict(sink=p)for p in extra]
 assert len({r["sink"]for r in targets})==123
 (OUT/"targets.json").write_text(json.dumps(targets,indent=2)+"\n")
 result.update(selected_plan_run=run["id"],selected_targets=selected,remaining_pins=extra)
 run=saved_run


 run=prior.api("actions/runs/43693300169")
 assert run["status"]=="completed" and run["conclusion"]=="success" and run["head_sha"]=="9ebc5aaeec99b2303b6c3e74439370a2588b94d8" and run["run_attempt"]==1
 cs=archive(14154072583,"1dffb409ed2343c1e386a81ed97216b4faca4851d15bcf5b6e33f0af621fbf23","combined-safe.zip")
 cn=archive(14153798487,"a74a0c46411f4f015f804a53ea1e5aae636a4d5a01c471e5c1b276863e8d6ea6","combined-native.zip")
 report=json.loads(cs.read("result.json"))
 assert report["source_head"]==run["head_sha"] and report["sources_unchanged"] and report["returncode"]==0 and report["hold_zero_all_corners"] and not report["accepted"]
 assert report["candidate_odb_sha256"]=="254b1e467fbdd6a94ce274a2c58a32168ff145b99cb54b4cb60faeab80ac5d33"
 assert len(cn.namelist())==len(set(cn.namelist()))
 expected={n[len("run/"):]for n in report["outputs"]if n.startswith("run/")}
 assert {n for n in cn.namelist()if not n.endswith("/")}==expected
 successor=ROOT/"combined-hold-trial"
 for info in cn.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=cn.read(info);assert hashlib.sha256(raw).hexdigest()==report["outputs"]["run/"+info.filename]
  dest=successor/"run"/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 report["repaired_odb_sha256"]=report["candidate_odb_sha256"]
 report["repaired_state"]=report["candidate_state"]
 targets=[dict(sink=p)for p in [
  "$abc$735036$auto$blifparse.cc:397:parse_blif$811030/B",
  "$abc$735036$auto$blifparse.cc:397:parse_blif$811031/B1",
  "$abc$735036$auto$blifparse.cc:397:parse_blif$811032/A0",
  "$auto$ff.cc:337:slice$176920/D",
  "$auto$ff.cc:337:slice$164200/D",
  "$auto$ff.cc:337:slice$160646/Q"]]
 (OUT/"targets.json").write_text(json.dumps(targets,indent=2)+"\n")

 run=prior.api("actions/runs/43698884172")
 assert run["head_sha"]=="8efcfa852e866f4a0db100f3c5bda36a9e260c6d" and run["conclusion"]=="success" and run["run_attempt"]==1
 margins=archive(14156430096,"098fdc23f1ca7bd164862758d12bab3331282ef8176c83f5cee84c62d67868db","post174-derived.zip")
 rn=archive(14155663198,"5bbb8f2d04216d0e2284e2c576b6b04779d4c9c382b49445059daa7e2b0350b2","post174-native.zip")
 mr=json.loads(margins.read("result.json"))
 assert mr["source_head"]==run["head_sha"] and mr["sources_unchanged"] and mr["returncode"]==0 and mr["hold_zero_all_corners"]
 assert mr["source_odb_sha256"]=="254b1e467fbdd6a94ce274a2c58a32168ff145b99cb54b4cb60faeab80ac5d33"
 assert mr["candidate_odb_sha256"]=="3b0afb4c09cd12fea658ad96bf4958385b4ef6270f03f619752b25b0decde780"
 successor=ROOT/"combined-nearzero-repair"
 expected={n[len("run/"):]for n in mr["outputs"]if n.startswith("run/")}
 seen=set()
 for info in rn.infolist():
  if info.is_dir():continue
  p=Path(info.filename);assert not p.is_absolute() and ".."not in p.parts and info.filename in expected and info.filename not in seen
  raw=rn.read(info);assert hashlib.sha256(raw).hexdigest()==mr["outputs"]["run/"+info.filename]
  target=successor/"run"/p;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);seen.add(info.filename)
 assert seen==expected
 report=mr
 report["repaired_odb_sha256"]=report["candidate_odb_sha256"]
 report["repaired_state"]=report["candidate_state"]
 plans=[];chosen=set()
 for path in margins.namelist():
  if not path.endswith("/min.rpt"):continue
  raw=margins.read(path);assert hashlib.sha256(raw).hexdigest()==mr["outputs"][path]
  for block in raw.decode().split("Startpoint: ")[1:]:
   slack=re.search(r"([-+]?\d+\.\d+)\s+slack\s+\(",block)
   if not slack or float(slack[1])>=.05:continue
   start=block.splitlines()[0].strip();end=re.search(r"Endpoint: (\S+)",block)[1]
   arrival=block.split("data arrival time",1)[0]
   gatepins=re.findall(r"[\^v]\s+(\S+/\S+)\s+\(([^()]+)\)",arrival)
   source_indices=[i for i,(pin,master)in enumerate(gatepins)if pin in [start+"/Q",start+"/Q_N",start+"/QN"]]
   assert source_indices,(path,start)
   data=gatepins[source_indices[-1]+1:]
   # Native data path alternates input/output pins; known cell outputs are
   # excluded. Keep first input and last two inputs as measured alternatives.
   inputs=[(pin,master)for pin,master in data if pin.rsplit('/',1)[1] not in ['X','Y','Q','QN','Q_N','GCLK']]
   assert inputs,(path,start,end)
   options=list(dict.fromkeys(inputs))
   for pin,master in options:chosen.add(pin)
   plans.append(dict(report=path,start=start,end=end,slack_ns=float(slack[1]),candidates=[dict(pin=p,master=m)for p,m in options]))
 assert len(plans)==35 and len({p['end']for p in plans})==35,(len(plans),len(chosen))
 targets=[dict(sink=p)for p in sorted(chosen)]
 (OUT/"targets.json").write_text(json.dumps(targets,indent=2)+"\n")
 result.update(nearzero_source_run=run["id"],nearzero_paths=plans,target_count=len(targets))

 saved_run=run
 run=prior.api("actions/runs/43700042818")
 assert run["head_sha"]=="d1b65dacd823d2a09e6d11164640227c46fa26cb" and run["conclusion"]=="success" and run["run_attempt"]==1
 observed=archive(14156406361,"5871ebb877266cdea737e3b77a5e8f4cd0472617f8c726be55396b0374d3a3e1","actual35-measured.zip")
 measured=json.loads(observed.read("result.json"));assert measured["candidate_odb_sha256"]==measured["source_odb_sha256"]==report["candidate_odb_sha256"] and measured["sources_unchanged"]
 by={}
 for path,v in measured["branch_reports"].items():
  assert hashlib.sha256(observed.read(path)).hexdigest()==v["sha256"]
  if path.endswith("-max.rpt"):by.setdefault(v["target"],[]).append(v["worst_slack_ns"])
 selected={};thin=[]
 for path in measured["nearzero_paths"]:
  choices=[c for c in reversed(path["candidates"])if len(by[c["pin"]])==3 and min(by[c["pin"]])>=1.0]
  if not choices:thin.append(path);continue
  c=choices[0];selected[c["pin"]]=dict(sink=c["pin"],master=c["master"],delay_master="sg13g2_dlygate4sd3_1",delay_count=1,worst_setup_slack_ns=min(by[c["pin"]]),experiment_headroom_guard_ns=1.0)
 assert len(selected)==31 and len(thin)==3
 prefix="$abc$735036$auto$blifparse.cc:397:parse_blif$"
 small=[("736135/B","sg13g2_nand2_1",2),("772540/B","sg13g2_nor2_1",1),("772710/B","sg13g2_nand2_1",1)]
 for suffix,master,count in small:
  pin=prefix+suffix
  assert any(c["pin"]==pin and c["master"]==master for path in thin for c in path["candidates"])
  assert len(by[pin])==3 and min(by[pin])>=.4
  selected[pin]=dict(sink=pin,master=master,delay_master="sg13g2_buf_1",delay_count=count,worst_setup_slack_ns=min(by[pin]),experiment_headroom_guard_ns=.4)
 targets=list(selected.values());assert len(targets)==34 and sum(x["delay_count"]for x in targets)==35
 (OUT/"targets.json").write_text(json.dumps(targets,indent=2)+"\n")
 result.update(repair_measurement_run=run["id"],new_cells=35,target_count=34,selection_is_not_final_timing_acceptance=True,late_input_preferred=True)
 run=saved_run

 result["measured_targets"]=targets

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
 for cell in ["sg13g2_dlygate4sd3_1","sg13g2_buf_1"]:
  module=re.search(r"module "+cell+r"\b.*?endmodule",raw.decode(),re.S)[0]
  assert re.search(r"buf\s*\(X, A\);",module) and "output X;" in module and "input A;" in module
 app=Path(os.environ["CLOUD_APPIMAGE"]);prior.verify(app,"x86_64")
 flow=ROOT/"hw/soc/pnr/combined_post174_repair_flow.py"
 protected={str(p):prior.sha(p) for p in [odb,config,initial,flow,OUT/"selected.json",OUT/"targets.json",ROOT/"hw/soc/pnr/combined_boundary_hold.py",ROOT/"hw/soc/pnr/combined_selective_hold.py",ROOT/"hw/soc/pnr/combined_remaining_hold.py",Path(__file__),prior.SOURCE/"prepared/physical.sdc",ROOT/"hw/soc/pnr/corrpre_postcts_flow.py",ROOT/"hw/soc/flow/check_timing_derate.tcl"]}
 result.update(source_run=run["id"],source_odb_sha256=prior.sha(odb),baseline=report["measurements"],protected_inputs=protected)
 save()
 cmd=[str(app),"python",str(flow),"--flow","CombinedPost174Repair","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(config)]
 (OUT/"run").mkdir()
 start=time.monotonic()
 with (OUT/"native.log").open("w") as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 result.update(returncode=code,elapsed_s=time.monotonic()-start)
 if code:print((OUT/"native.log").read_text()[-12000:])
 assert code==0
 assert all(prior.sha(p)==h for p,h in protected.items())
 measurements={};before_measurements={}
 for phase,dest in [("after",measurements)]:
  for short,corner in prior.CORNERS:
   dirs=list((OUT/"run").glob("*-nssoc-combined"+phase+short));assert len(dirs)==1
   folder=dirs[0];assert not (folder/"unpropagated.rpt").read_text().strip()
   data=json.loads((folder/"state_out.json").read_text())
   dest[corner]={"metrics":{k:v for k,v in data["metrics"].items()if k.endswith("__corner:"+corner)},"directory":str(folder.relative_to(OUT))}
 states=list((OUT/"run").glob("*-nssoc-combinedafterfast/state_out.json"));assert len(states)==1
 state=json.loads(states[0].read_text())
 branch_rows={};io_rows={}
 for glob,dest,marker in [("*/branch-*.rpt",branch_rows,"NSSOC_TARGET_BRANCH_PIN"),("*/io-*.rpt",io_rows,"NSSOC_TARGET_PORT")]:
  for p in (OUT/"run").glob(glob):
   text=p.read_text();values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",text);assert values
   dest[str(p.relative_to(OUT))]={"target":re.search(marker+r" (.+)",text)[1],"worst_slack_ns":min(map(float,values)),"sha256":prior.sha(p)}
 assert len(branch_rows)==6*len(targets) and len(io_rows)==240
 after_rows={k:v for group in [branch_rows,io_rows]for k,v in group.items()if "combinedafter"in k}
 result.update(before_measurements=before_measurements,branch_reports=branch_rows,boundary_reports=io_rows,selected_margin_50ps=all(v["worst_slack_ns"]>=.05 for v in after_rows.values()))
 result["hold_zero_all_corners"]=all(v["metrics"]["timing__hold_vio__count__corner:"+c]==0 for c,v in measurements.items())
 assert prior.sha(state["odb"])!=report["repaired_odb_sha256"],"Expected native branch ECO"
 result.update(status="REPAIR_MEASURED_NOT_ACCEPTED",measurements=measurements,candidate_odb_sha256=prior.sha(state["odb"]),candidate_state=str(states[0].relative_to(OUT)),sources_unchanged=True)
except BaseException as error:
 result.update(status="FAIL_OR_ERROR",error=repr(error));raise
finally:
 result["outputs"]={str(p.relative_to(OUT)):prior.sha(p) for p in (OUT/"run").rglob("*") if p.is_file()}
 if (OUT/"native.log").exists():result["outputs"]["native.log"]=prior.sha(OUT/"native.log")
 save()
