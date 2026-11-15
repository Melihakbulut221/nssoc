import os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43729972900");assert run["head_sha"]=="a8333ff19420d8bb90a59bc370ebe04119373f0c"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["workflow_run"]["head_sha"]==run["head_sha"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14168124662,"cb76b7d2da9b89c4a3c4ea3b0eea2137f740998a6af88ae354ce30eff1d1cb3f","derived")
 native=archive(14168212861,"f82561949e8cc731bee14e2963bb141f7787b55198b952a8a3c235cb74f98bf7","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="c887b622caf91307037b00e780ec73b52bfc4b8ab9700ba9c919625959876e09"
 assert report["source_run"]==43728240498 and report["inserted_cells"]==125
 # Bind independent all-corner through-path measurement before any ECO.
 measured_run=prior.api('actions/runs/43732030174')
 assert measured_run['head_sha']=='b70c4888f5c912b072f7b594a11339c5de8f4c78' and measured_run['conclusion']=='success' and measured_run['run_attempt']==1
 meta=prior.api('actions/artifacts/14169073173')
 assert meta['workflow_run']['id']==measured_run['id'] and meta['digest']=='sha256:2db2f422baccc23754034e68c2cb2138b1128ee6d69650819f13c2b4710044f6' and not meta['expired']
 path=OUT/'measurement.zip'
 with path.open('xb')as dest:subprocess.run(['gh','api',prior.REPO+'actions/artifacts/14169073173/zip'],stdout=dest,check=True)
 assert prior.sha(path)=='2db2f422baccc23754034e68c2cb2138b1128ee6d69650819f13c2b4710044f6'
 with zipfile.ZipFile(path)as measured:
  mr=json.loads(measured.read('result.json'));assert mr['sources_unchanged'] and mr['candidate_odb_sha256']==report['candidate_odb_sha256'] and mr['returncode']==0
  for folder,minimum in [('1-nssoc-ackbranchslow',1.5),('2-nssoc-ackbranchtypical',.8),('3-nssoc-ackbranchfast',.48)]:
   member=f'run/{folder}/branch-2-min.rpt';data=measured.read(member)
   assert hashlib.sha256(data).hexdigest()==mr['outputs'][member]
   vals=list(map(float,re.findall(r'([-+\d.eE]+)\s+slack \(',data.decode())));assert vals and min(vals)>=minimum
 r['measurement_run']=measured_run['id']
 source=ROOT/"ack-reset-source";source.mkdir()
 assert len(native.namelist())==len(set(native.namelist()))
 assert {n for n in native.namelist()if not n.endswith("/")}==set(report["outputs"])|{"result.json"}
 for info in native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=native.read(info);expected=hashlib.sha256(safe.read("result.json")).hexdigest()if info.filename=="result.json"else report["outputs"][info.filename]
  assert hashlib.sha256(raw).hexdigest()==expected
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 rows=[dict(kind='pin',name='hold33182/A',master='sg13g2_dlygate4sd3_1'),dict(kind='pin',name='hold33182/X',master='sg13g2_dlygate4sd3_1'),dict(kind='pin',name='$abc$734931$auto$blifparse.cc:397:parse_blif$738684/B',master='sg13g2_xor2_1')]
 paths=[]
 member='run/2-nssoc-holdslow/max.rpt';data=safe.read(member)
 assert hashlib.sha256(data).hexdigest()==report['outputs'][member]
 first=data.decode().split('Startpoint:')[1]
 assert 'u_pcie.receive_ownership.head_last[4] (net)' in first
 assert 'hold33182/X (sg13g2_dlygate4sd3_1)' in first
 assert rows[2]['name']+' (sg13g2_xor2_1)' in first
 r['critical_path_report_sha256']=report['outputs'][member]
 (OUT/"targets.json").write_text(json.dumps(rows,indent=2)+"\n")
 r.update(source_run=run["id"],source_odb_sha256=report["candidate_odb_sha256"],target_count=len(rows),paths=paths,targets=rows);save()
 state=json.loads((source/report["candidate_state"]).read_text())
 def relocate(v):
  if isinstance(v,str):return v.replace(str(OUT)+'/',str(source)+'/')
  if isinstance(v,dict):return {k:relocate(x)for k,x in v.items()}
  if isinstance(v,list):return [relocate(x)for x in v]
  return v
 state=relocate(state);odb=Path(state['odb']);assert prior.sha(odb)==r['source_odb_sha256']
 state["metrics"]={};initial=OUT/"initial.json";initial.write_text(json.dumps(state))
 config=json.loads((source/"config.json").read_text());assert config["CLOCK_PERIOD"]==20 and config["TIME_DERATING_CONSTRAINT"]==5.0
 cfg=OUT/"config.json";cfg.write_text(json.dumps(config))
 app=Path(os.environ["CLOUD_APPIMAGE"]);prior.verify(app,"x86_64")
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,OUT/"targets.json",ROOT/"hw/soc/pnr/ack_chip_shared_hold_flow.py"]}
 command=[str(app),"python",str(ROOT/"hw/soc/pnr/ack_chip_shared_hold_flow.py"),"--flow","AckChipSharedHold","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(cfg)]
 (OUT/"run").mkdir()
 with(OUT/"native.log").open("w")as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r["returncode"]=code;assert code==0
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 final=json.loads((OUT/"run/4-nssoc-sharedfast/state_out.json").read_text())
 r.update(candidate_state="run/4-nssoc-sharedfast/state_out.json",candidate_odb_sha256=prior.sha(Path(final["odb"])),measurements=final["metrics"])
 assert r["candidate_odb_sha256"]!=r["source_odb_sha256"]
 r.update(status="CRITICAL_XOR_BRANCH_SHARED_HOLD_BYPASS_TRIAL_NOT_ACCEPTED",sources_unchanged=True,scope="Sourcec887 (346 added hold delays): only XOR738684/B bypasses existing hold33182; other load805438/A remains delayed. No cell removal or movement. Fresh all-corner setup/hold required; baseline has zero hold violations in all corners; any new violation rejects the candidate. No final timing acceptance.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
