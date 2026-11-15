import time,os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43710888222");assert run["head_sha"]=="386adc72f170ef69d298ce817a5e11de14b071a7"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14160404103,"a95289e0de482a8a0f6e9a39d79dca1f28ed9e36cc1e3d4f04ac68de917ac291","derived")
 native=archive(14160612913,"4fd7159bf3acab4d34eb0f426c45c2dd1459e80810d185347161c6f9afbb2e95","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="9a163c3124826ca5bdbb12fab75e8808a6064d18d1b099ed489c865d359c65cd"
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
    selection=pins if mode=="max"else list(dict.fromkeys(pins[:1]+pins[-2:]))
    for pin,master in selection:targets[("pin",pin)]={"kind":"pin","name":pin,"master":master}
    if "(output port"in b.split("Path Group:",1)[0]:targets[("port",end)]={"kind":"port","name":end}
    paths.append(dict(corner=corner,mode=mode,start=start,end=end,pins=selection))
 assert len([p for p in paths if p["mode"]=="min"])==157
 rows=list(targets.values());assert len(rows)>0 and paths
 (OUT/"targets.json").write_text(json.dumps(rows,indent=2)+"\n")
 r.update(source_run=run["id"],source_odb_sha256=report["candidate_odb_sha256"],target_count=len(rows),paths=paths,targets=rows);save()
 # Bind repair choices to the complete native branch measurements.
 saved_run=run
 deadline=time.monotonic()+5400
 while True:
  run=prior.api('actions/runs/43711850416')
  assert run['head_sha']=='01fd5593f442a7adaa70c83173035cd074a87fcf' and run['run_attempt']==1
  if run['status']=='completed':break
  assert time.monotonic()<deadline,'Residual branch measurement still live; no acceptance'
  print('Waiting for exact residual branch measurements',flush=True);time.sleep(30)
 assert run['conclusion']=='success'
 found=[x for x in prior.api('actions/runs/43711850416/artifacts')['artifacts'] if x['name']=='ack-chip-margin-derived-43711850416' and not x['expired']]
 assert len(found)==1
 meta=found[0];assert meta['workflow_run']['head_sha']==run['head_sha'] and meta['digest'].startswith('sha256:')
 assert meta['id']==14161562880 and meta['digest']=='sha256:bedcfb0dd51ffc34e2fbbc0bcd6860937515f11e678fbfe771b0b217cca4a0d2'
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
 selected={};unselected=[]
 for path in paths:
  if path['mode']!='min':continue
  choices=[]
  for pin,master in reversed(path['pins']):
   setup,hold=margins[pin];count=1
   if setup>=count:choices.append(dict(sink=pin,master=master,expected_port=path['start'],delay_master='sg13g2_dlygate4sd3_1',delay_count=count,worst_setup_slack_ns=setup,worst_hold_slack_ns=hold))
  if not choices:
   unselected.append(path);continue
  choice=choices[0];selected[choice['sink']]=choice
 assert len(selected)==141 and sum(x['delay_count']for x in selected.values())==141
 print('QUALIFIED_141_MARGIN_CHOICES',json.dumps(list(selected.values())),flush=True)
 assert len(unselected)==5 and {p['end'] for p in unselected}=={'$auto$ff.cc:337:slice$'+x for x in ['181448','365799','155696','159982','160400']}
 r['unselected_paths']=unselected;r['covered_low_margin_paths']=152;r['unselected_reason']='No selected measured input has >=1ns all-corner setup reserve; no delay inserted on these five paths.'
 (OUT/'hold-selected.json').write_text(json.dumps(list(selected.values()),indent=2)+'\n')
 r.update(repair_measurement_run=run['id'],selected_targets=list(selected.values()),inserted_cells=141)
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
 r.update(status='MEASURED_141_MARGIN_BRANCH_REPAIR_WITH_FIVE_UNSELECTED_PATHS',sources_unchanged=True,candidate_odb_sha256=prior.sha(candidate),candidate_state=str(final.relative_to(OUT)),measurements=measurements,scope='141 additional native identity delays selected from current9a1633 measurements covering152of157 sub50ps paths; all271 original delays retained. Five explicit unselected paths remain; all574 branch and global corner reports retained. No route or fullPHY acceptance.')
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
