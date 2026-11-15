import os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43759885305");assert run["head_sha"]=="a4803beeb5ec80d27088ea868e45817f7b7b8e78"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["workflow_run"]["head_sha"]==run["head_sha"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14180460681,"7de05629c8c45da8a34757eb1daf52cfa58998b02ba44f68b142105cdd570316","derived")
 native=archive(14179614696,"77cb2268c36def7019817570cef1482fc529d2fc7ec9e408c65d164913b1c45d","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["source_run"]==43758008035
 assert report["candidate_odb_sha256"]=="2b33af5c60ab854b77829f5865bc67a3b7335026abce224d4ce4b372d8ba1b9f"
 source=ROOT/"ack-reset-source";source.mkdir()
 assert len(native.namelist())==len(set(native.namelist()))
 assert {n for n in native.namelist()if not n.endswith("/")}==set(report["outputs"])|{"result.json"}
 for info in native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  raw=native.read(info);expected=hashlib.sha256(safe.read("result.json")).hexdigest()if info.filename=="result.json"else report["outputs"][info.filename]
  assert hashlib.sha256(raw).hexdigest()==expected
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 rows=report['targets'];paths=report['paths']
 assert rows==json.loads(safe.read('targets.json')) and len(rows)==3
 # Select shared drivers only from reported violating Q-start paths.
 member='run/2-nssoc-sizedslow/max.rpt';data=safe.read(member)
 assert hashlib.sha256(data).hexdigest()==report['outputs'][member]
 violated=[p for p in data.decode().split('Startpoint:')[1:] if 'slack (VIOLATED)' in p and '/Q (' in p.split('data arrival time')[0]]
 selected=[('$abc$734931$auto$blifparse.cc:397:parse_blif$738674','Y','sg13g2_nor4_1',233),('fanout10862','X','sg13g2_buf_2',145)]
 census=[]
 for cell,pin,master,expected in selected:
  count=sum(cell+'/'+pin+' ('+master+')' in p.split('data arrival time')[0].split('/Q (',1)[1] for p in violated)
  assert count==expected,(cell,count,expected)
  census.append(dict(instance=cell,master=master,reported_violating_paths=count))
 r['critical_path_report_sha256']=report['outputs'][member]
 r['shared_driver_census']=census
 safe.close();native.close()
 r['source_archives']=[dict(id=14180460681,sha256='7de05629c8c45da8a34757eb1daf52cfa58998b02ba44f68b142105cdd570316'),dict(id=14179614696,sha256='77cb2268c36def7019817570cef1482fc529d2fc7ec9e408c65d164913b1c45d')]
 r['removed_verified_download_copies']=[]
 for name in ['derived.zip','native.zip']:
  path=OUT/name;assert path.is_file() and not path.is_symlink()
  path.unlink();r['removed_verified_download_copies'].append(name)
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
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,OUT/"targets.json",ROOT/"hw/soc/pnr/ack_chip_reset_sizing_flow.py"]}
 command=[str(app),"python",str(ROOT/"hw/soc/pnr/ack_chip_reset_sizing_flow.py"),"--flow","AckChipResetSized","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(cfg)]
 (OUT/"run").mkdir()
 with(OUT/"native.log").open("w")as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r["returncode"]=code;assert code==0
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 final=json.loads((OUT/"run/4-nssoc-sizedfast/state_out.json").read_text())
 r.update(candidate_state="run/4-nssoc-sizedfast/state_out.json",candidate_odb_sha256=prior.sha(Path(final["odb"])),measurements=final["metrics"])
 assert r["candidate_odb_sha256"]!=r["source_odb_sha256"]
 r.update(status="SHARED_PCIE_DRIVER_TRIAL_NOT_ACCEPTED",sources_unchanged=True,scope="Source2b33 SRAM improvements retained. Only shared NOR738674 size1to2 and fanout10862 buf2to4; exact old masters and all original incidence preserved. Independent of combined reset/NOR761461 and final SRAM buffer candidates. Three corner STA required, not final routed signoff.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
