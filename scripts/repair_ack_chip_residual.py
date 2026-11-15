import time,os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43708228938");assert run["head_sha"]=="4c2f65da2aae34d7e3116ba8edcca84a9c93e21f"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14160105837,"207970d03d9c52d70508cc18513a5d083cf4e018a5e0292b9cda9d48177776aa","derived")
 native=archive(14160125922,"8fd442bb947cde2c8e355f7a22eb818179aa2b1361d8c9800c6e600ffe499355","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="e2b5649189b950d742c363bc5e3c36f41e299bf0130843384c4a5e5b142c939d"
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
 assert len([p for p in paths if p["mode"]=="min"])==4
 rows=list(targets.values());assert len(rows)>0 and paths
 (OUT/"targets.json").write_text(json.dumps(rows,indent=2)+"\n")
 r.update(source_run=run["id"],source_odb_sha256=report["candidate_odb_sha256"],target_count=len(rows),paths=paths,targets=rows);save()
 # Bind repair choices to the complete native branch measurements.
 saved_run=run
 deadline=time.monotonic()+5400
 while True:
  run=prior.api('actions/runs/43709880012')
  assert run['head_sha']=='8ecd5371a47ec0dfbba719e203a15a0fa02c7a17' and run['run_attempt']==1
  if run['status']=='completed':break
  assert time.monotonic()<deadline,'Residual branch measurement still live; no acceptance'
  print('Waiting for exact residual branch measurements',flush=True);time.sleep(30)
 assert run['conclusion']=='success'
 found=[x for x in prior.api('actions/runs/43709880012/artifacts')['artifacts'] if x['name']=='ack-chip-residual-derived-43709880012' and not x['expired']]
 assert len(found)==1
 meta=found[0];assert meta['workflow_run']['head_sha']==run['head_sha'] and meta['digest'].startswith('sha256:')
 assert meta['id']==14160212631 and meta['digest']=='sha256:14457999d8492281e9087dd953c45be7ba1d90e9d711252fae4dd868df289e54'
 measured=archive(meta['id'],meta['digest'].removeprefix('sha256:'),'residual-measured')
 r['measurement_artifact_binding']={k:meta[k] for k in ['id','name','digest','workflow_run']}
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
   setup,hold=margins[pin];count=1
   if setup>=count:choices.append(dict(sink=pin,master=master,expected_port=path['start'],delay_master='sg13g2_dlygate4sd3_1',delay_count=count,worst_setup_slack_ns=setup,worst_hold_slack_ns=hold))
  assert choices,('No safe measured choice',path)
  choice=choices[0];selected[choice['sink']]=choice
 assert len(selected)==4 and sum(x['delay_count']for x in selected.values())==4
 print('QUALIFIED_FOUR_RESIDUAL_CHOICES',json.dumps(list(selected.values())),flush=True)
 (OUT/'hold-selected.json').write_text(json.dumps(list(selected.values()),indent=2)+'\n')
 r.update(repair_measurement_run=run['id'],selected_targets=list(selected.values()),inserted_cells=4)
 run=saved_run
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
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,OUT/"targets.json",ROOT/"hw/soc/pnr/ack_chip_branches_flow.py",ROOT/"hw/soc/pnr/ack_chip_hold_repair_flow.py",OUT/"hold-selected.json",Path(__file__)]}
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
 r.update(status='MEASURED_FOUR_RESIDUAL_HOLD_REPAIR_REQUIRES_REVIEW',sources_unchanged=True,candidate_odb_sha256=prior.sha(candidate),candidate_state=str(final.relative_to(OUT)),measurements=measurements,scope='Four additional native identity delays selected from current residual branch measurements; preserve original267 delays. All measured branch and global corner reports retained. No route or fullPHY acceptance.')
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
