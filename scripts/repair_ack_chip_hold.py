import os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43700966904");assert run["head_sha"]=="de22dcaec98353379bd970648f0b97a59b767246"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14156558964,"43c92ec5528353be0ae288cc813e405d47d351c1ca21195d0e60d03d1f979850","derived")
 native=archive(14157198878,"9d6c9e73416ec8783b2e3ae558c409266f3733f6e4864bd4368d85ee8842feb9","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["repaired_odb_sha256"]=="97f3161d2f6c36a062f9db94cad37d175282b981a8b4060306f6f6c32d0ff6e9"
 source=ROOT/"hw/soc/out/cloud-predecode-postcts";source.mkdir()
 assert len(native.namelist())==len(set(native.namelist()))
 assert {n for n in native.namelist()if not n.endswith("/")}==set(report["outputs"])|{"result.json"}
 for info in native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=native.read(info);expected=hashlib.sha256(safe.read("result.json")).hexdigest()if info.filename=="result.json"else report["outputs"][info.filename]
  assert hashlib.sha256(raw).hexdigest()==expected
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 targets={};paths=[]
 for corner,entry in report["measurements"]["after"].items():
  for mode in ["min","max"]:
   blocks=(source/entry["directory"]/(mode+".rpt")).read_text().split("Startpoint:")[1:]
   chosen=[b for b in blocks if "slack (VIOLATED)"in b]
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
    selection=pins if mode=="max"else list(dict.fromkeys(pins[:1]+pins[-2:]))
    for pin,master in selection:targets[("pin",pin)]={"kind":"pin","name":pin,"master":master}
    if "(output port"in b.split("Path Group:",1)[0]:targets[("port",end)]={"kind":"port","name":end}
    paths.append(dict(corner=corner,mode=mode,start=start,end=end,pins=selection))
 rows=list(targets.values());assert len(rows)>100 and paths
 (OUT/"targets.json").write_text(json.dumps(rows,indent=2)+"\n")
 r.update(source_run=run["id"],source_odb_sha256=report["repaired_odb_sha256"],target_count=len(rows),paths=paths,targets=rows);save()
 # Bind repair choices to the complete native branch measurements.
 saved_run=run
 run=prior.api('actions/runs/43704514831')
 assert run['conclusion']=='success' and run['head_sha']=='1733c2ce4e780c0fef02e3c32cd38cb26f63384f' and run['run_attempt']==1
 measured=archive(14158067560,'bdb1030257c058024fb03a5acbffa39b57d934b31851bb01f573d43f799e908d','branch-measured')
 mr=json.loads(measured.read('result.json'));assert mr['source_odb_sha256']==r['source_odb_sha256'] and mr['sources_unchanged'] and mr['returncode']==0
 assert json.loads(measured.read('targets.json'))==rows and mr['paths']==json.loads(json.dumps(paths))
 margins={}
 for index,target in enumerate(rows):
  if target['kind']!='pin':continue
  values={}
  for folder in ['1-nssoc-ackbranchslow','2-nssoc-ackbranchtypical','3-nssoc-ackbranchfast']:
   for mode in ['max','min']:
    member=f'run/{folder}/branch-{index}-{mode}.rpt';raw=measured.read(member)
    assert hashlib.sha256(raw).hexdigest()==mr['outputs'][member]
    vs=re.findall(r'([-+\d.eE]+)\s+slack \(',raw.decode());assert vs
    values.setdefault(mode,[]).append(min(map(float,vs)))
  margins[target['name']]=(min(values['max']),min(values['min']))
 selected={}
 for path in paths:
  if path['mode']!='min':continue
  choices=[]
  for pin,master in reversed(path['pins']):
   setup,hold=margins[pin];count=2 if hold<-.15 else 1
   if setup>=count:choices.append(dict(sink=pin,master=master,expected_port=path['start'],delay_master='sg13g2_dlygate4sd3_1',delay_count=count,worst_setup_slack_ns=setup,worst_hold_slack_ns=hold))
  assert choices,('No safe measured choice',path)
  choice=choices[0];selected[choice['sink']]=choice
 assert len(selected)==254 and sum(x['delay_count']for x in selected.values())==267
 (OUT/'hold-selected.json').write_text(json.dumps(list(selected.values()),indent=2)+'\n')
 r.update(repair_measurement_run=run['id'],selected_targets=list(selected.values()),inserted_cells=267)
 run=saved_run
 state=json.loads((source/report["repaired_state"]).read_text());odb=Path(state["odb"]);assert prior.sha(odb)==r["source_odb_sha256"]
 state["metrics"]={};initial=OUT/"initial.json";initial.write_text(json.dumps(state))
 config=json.loads((source/"trial-config.json").read_text());assert config["CLOCK_PERIOD"]==20 and config["TIME_DERATING_CONSTRAINT"]==5.0
 cfg=OUT/"config.json";cfg.write_text(json.dumps(config))
 app=Path(os.environ["CLOUD_APPIMAGE"]);prior.verify(app,"x86_64")
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,OUT/"hold-selected.json",ROOT/"hw/soc/pnr/ack_chip_branches_flow.py",Path(__file__),OUT/"targets.json",ROOT/"hw/soc/pnr/ack_chip_hold_repair_flow.py"]}
 command=[str(app),"python",str(ROOT/"hw/soc/pnr/ack_chip_hold_repair_flow.py"),"--flow","AckChipHoldRepair","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(cfg)]
 (OUT/"run").mkdir()
 with(OUT/"native.log").open("w")as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r["returncode"]=code;assert code==0
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 final=OUT/'run/4-nssoc-holdfast/state_out.json';state=json.loads(final.read_text())
 candidate=Path(state['odb']);assert prior.sha(candidate)!=r['source_odb_sha256']
 measurements={}
 for folder in ['2-nssoc-holdslow','3-nssoc-holdtypical','4-nssoc-holdfast']:
  state_out=json.loads((OUT/'run'/folder/'state_out.json').read_text())
  measurements[folder]=state_out['metrics']
 r.update(status='MEASURED_254_BRANCH_HOLD_REPAIR_REQUIRES_REVIEW',sources_unchanged=True,candidate_odb_sha256=prior.sha(candidate),candidate_state=str(final.relative_to(OUT)),measurements=measurements,scope='267 native identity delays on254 actual measured branches; all778 original branch and global corner reports retained. No route or fullPHY acceptance.')
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
