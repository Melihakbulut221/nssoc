import os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43726840782");assert run["head_sha"]=="a164dabeb173f8d9419b564c82001cb441c36c64"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["workflow_run"]["head_sha"]==run["head_sha"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14167680049,"506044747cf8aba10888ab14ff07402a354c6ce3253b23fabebb98e0f4829b9b","derived")
 native=archive(14167575764,"f488cebdfee2a13d71bd9c27d5725864500ed7df565735d0c270ea66d4edc9d4","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["candidate_odb_sha256"]=="7c850577a9c39f4e72383169ce0faa63c07422786ffbc6e5b8570d041b04d95f"
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
 member='run/2-nssoc-sizedslow/max.rpt';data=safe.read(member)
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
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,OUT/"targets.json",ROOT/"hw/soc/pnr/ack_chip_branches_flow.py"]}
 command=[str(app),"python",str(ROOT/"hw/soc/pnr/ack_chip_branches_flow.py"),"--flow","AckChipBranches","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(cfg)]
 (OUT/"run").mkdir()
 with(OUT/"native.log").open("w")as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r["returncode"]=code;assert code==0
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 final=json.loads((OUT/"run/3-nssoc-ackbranchfast/state_out.json").read_text())
 r.update(candidate_state="run/3-nssoc-ackbranchfast/state_out.json",candidate_odb_sha256=prior.sha(Path(final["odb"])),measurements=final["metrics"])
 assert r["candidate_odb_sha256"]==r["source_odb_sha256"]
 r.update(status="READ_ONLY_HEAD_LAST_SHARED_HOLD_MARGIN_MEASUREMENT",sources_unchanged=True,scope="Read-only source7c850 shared hold33182 input/output and critical XOR branch. All-corner minimum/maximum timing plus actual load census. No cell mutation, delay bypass or timing acceptance.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
