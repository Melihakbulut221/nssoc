import os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43720921041");assert run["head_sha"]=="15c019517c9807b26bd39e875d5359b0ea48dbf8"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["workflow_run"]["head_sha"]==run["head_sha"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14165417399,"54b555903714ceebf5648e9319743013f0fbf4cd0027fcf7d80571e8f45dd8e8","derived")
 native=archive(14166012274,"792adf5a25ee7fb8f331aa19c208a0991a3d89c5620dde157acd36e9b84a973e","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="441ff0490eb3239ba9011e1b5e08e99f7f8304a600e30ec38dc4806d10525e3e"
 source=ROOT/"ack-hold-source";source.mkdir()
 assert len(native.namelist())==len(set(native.namelist()))
 assert {n for n in native.namelist()if not n.endswith("/")}==set(report["outputs"])|{"result.json"}
 for info in native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=native.read(info);expected=hashlib.sha256(safe.read("result.json")).hexdigest()if info.filename=="result.json"else report["outputs"][info.filename]
  assert hashlib.sha256(raw).hexdigest()==expected
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 targets={};paths=[]
 for corner,entry in [(x,{"directory":"run/"+x}) for x in report["measurements"]]:
  for mode in ["min","max"]:
   blocks=(source/entry["directory"]/(mode+".rpt")).read_text().split("Startpoint:")[1:]
   def slack(block):
    values=re.findall(r'([-+\d.eE]+)\s+slack \(',block);assert len(values)==1
    return float(values[0])
   if mode=='min':
    groups={}
    for b in blocks:
     group=re.search(r'(?m)^Path Group: (.+)',b)[1]
     groups.setdefault(group,[]).append(slack(b))
    assert groups and all(max(v)>=.05 for v in groups.values()),'Report truncation could hide sub50ps paths'
   chosen=[b for b in blocks if slack(b)<(.05 if mode=='min' else 0)]
   if mode=="max":chosen=chosen[:10]
   for b in chosen:
    start=b.splitlines()[0].strip().split(" (",1)[0]
    end=re.search(r"(?m)^Endpoint: (.+)",b)[1].strip().split(" (",1)[0]
    data=b.split("data arrival time",1)[0];pins=[];launched=False
    for line in data.splitlines():
     m=re.search(r"[\^v] (.+?)/(\S+) \(sg13g2_(\S+)\)",line)
     if m:
      inst,pin,master=m.groups()
      if inst==start and pin in ["Q","Q_N","QN","X","Y"]:launched=True;continue
      if launched and pin not in ["X","Y","Q","Q_N","QN","CLK"]:pins.append((inst+"/"+pin,"sg13g2_"+master))
     elif start+" (in)"in line:launched=True
    assert pins,(corner,mode,start,end)
    selection=list(dict.fromkeys(pins))
    for pin,master in selection:targets[("pin",pin)]={"kind":"pin","name":pin,"master":master}
    if "(output port"in b.split("Path Group:",1)[0]:targets[("port",end)]={"kind":"port","name":end}
    paths.append(dict(corner=corner,mode=mode,start=start,end=end,pins=selection,slack_ns=slack(b)))
 assert len([p for p in paths if p["mode"]=="min" and p["slack_ns"]<0])==7
 assert all(p["corner"]=="4-nssoc-holdfast"for p in paths if p["mode"]=="min"and p["slack_ns"]<0)
 rows=list(targets.values());assert len(rows)>0 and paths
 (OUT/"targets.json").write_text(json.dumps(rows,indent=2)+"\n")
 r.update(source_run=run["id"],source_odb_sha256=report["candidate_odb_sha256"],target_count=len(rows),paths=paths,targets=rows);save()
 state=json.loads((source/report["candidate_state"]).read_text());
 def relocate(value):
  if isinstance(value,str):return value.replace(str(ROOT/'ack-chip-branches')+'/',str(source)+'/')
  if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
  if isinstance(value,list):return [relocate(v) for v in value]
  return value
 state=relocate(state);odb=Path(state["odb"]);assert prior.sha(odb)==r["source_odb_sha256"]
 state["metrics"]={};initial=OUT/"initial.json";initial.write_text(json.dumps(state))
 config=json.loads((source/"config.json").read_text());assert config["CLOCK_PERIOD"]==20 and config["TIME_DERATING_CONSTRAINT"]==5.0
 cfg=OUT/"config.json";cfg.write_text(json.dumps(config))
 app=Path(os.environ["CLOUD_APPIMAGE"]);prior.verify(app,"x86_64")
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,OUT/"targets.json",ROOT/"hw/soc/pnr/ack_chip_branches_flow.py"]}
 command=[str(app),"python",str(ROOT/"hw/soc/pnr/ack_chip_branches_flow.py"),"--flow","AckChipBranches","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(cfg)]
 (OUT/"run").mkdir()
 with(OUT/"native.log").open("w")as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r["returncode"]=code;assert code==0
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 r.update(status="READ_ONLY_ALL_CORNER_BRANCH_REPORTS_REQUIRE_REPAIR_SELECTION",sources_unchanged=True,scope="Measured inputs on exact newRX hold-repaired441ff candidate, all inputs on all reported sub50ps hold paths, including exact seven negative fast paths and top10 setup paths per corner; verify report reaches >=50ps for each group; no cell changes, no route/final acceptance.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
