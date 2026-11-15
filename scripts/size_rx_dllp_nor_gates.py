import os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43751933582");assert run["head_sha"]=="c7bc39794e3b8ae2f6e33a390617d9106e327d9e"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["workflow_run"]["head_sha"]==run["head_sha"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14176744096,"687b1a284e7cbd6e0d3924a402754bc2224b7b8af8ccdb35c2a613c3eb6a80de","derived")
 native=archive(14176139147,"d6ea40ac2e7a3fa4d3b9eec6f069ff9d8525b67bdb54509a42daa86cfc3f797b","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["source_run"]==43750556058
 assert report["candidate_odb_sha256"]=="3972efe44d18244b27274c0204bde31bb79fa5e8a91a489871af5d16f8785ba4"
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
 # Bind newly worst reset-to-data path and measured weak drivers.
 member='run/2-nssoc-sizedslow/max.rpt';data=safe.read(member)
 assert hashlib.sha256(data).hexdigest()==report['outputs'][member]
 first=data.decode().split('Startpoint:')[1]
 assert '$auto$ff.cc:337:slice$343559' in first
 assert 'Endpoint: $auto$ff.cc:337:slice$160968' in first
 for cell,pin,master in [('$abc$734931$auto$blifparse.cc:397:parse_blif$735962','Y','sg13g2_inv_1'),('fanout6391','X','sg13g2_buf_1'),('fanout4141','X','sg13g2_buf_1')]:
  assert cell+'/'+pin+' ('+master+')' in first
 r['critical_path_report_sha256']=report['outputs'][member]
 check_member='run/2-nssoc-sizedslow/checks.rpt'
 checks=safe.read(check_member)
 assert hashlib.sha256(checks).hexdigest()==report['outputs'][check_member]
 text=checks.decode()
 slew=text.split('\nmax slew\n')[1].split('\nmax fanout\n')[0]
 pins=[line.split()[0] for line in slew.splitlines() if '(VIOLATED)' in line]
 assert len(pins)==36 and len(set(pins))==36
 m=re.search(r'Found (\d+) unannotated drivers\.',text);assert m and int(m[1])==1285
 rest=text[m.end():].splitlines();unannotated=[]
 for line in rest:
  if not line.strip():
   if unannotated:break
   continue
  if len(line.split())!=1:break
  unannotated.append(line.strip())
 assert len(unannotated)==1285 and len(set(unannotated))==1285
 assert all(not any(c in pin for c in '{}\n\r') for pin in pins+unannotated)
 (OUT/'probe-pins.json').write_text(json.dumps({'slew':pins,'unannotated':unannotated}))
 (OUT/'probe-pins.tcl').write_text('set slew_pins {'+' '.join('{'+p+'}' for p in pins)+'}\nset unannotated_pins {'+' '.join('{'+p+'}' for p in unannotated)+'}\n')
 r['probe_checks_sha256']=report['outputs'][check_member]

 safe.close();native.close()
 r['source_archives']=[dict(id=14176744096,sha256='687b1a284e7cbd6e0d3924a402754bc2224b7b8af8ccdb35c2a613c3eb6a80de'),dict(id=14176139147,sha256='d6ea40ac2e7a3fa4d3b9eec6f069ff9d8525b67bdb54509a42daa86cfc3f797b')]
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
 final=json.loads((OUT/"run/1-nssoc-resetbuffereco/state_out.json").read_text())
 r.update(candidate_state="run/1-nssoc-resetbuffereco/state_out.json",candidate_odb_sha256=prior.sha(Path(final["odb"])),measurements=final["metrics"])
 assert (OUT/"native-driver-probe.tsv").is_file()
 r["native_driver_probe_sha256"]=prior.sha(OUT/"native-driver-probe.tsv")
 r["timing_remeasured"]=False
 assert (OUT/"native-reset-release.tsv").is_file()
 r["native_reset_release_sha256"]=prior.sha(OUT/"native-reset-release.tsv")
 assert (OUT/"native-buffer-capabilities.txt").is_file()
 r["native_buffer_capabilities_sha256"]=prior.sha(OUT/"native-buffer-capabilities.txt")
 r.update(status="READ_ONLY_NATIVE_DRIVER_PROBE_NOT_SIGNOFF",sources_unchanged=True,scope="Read-only native ODB pin/net incidence probe for 36 SRAM slew pins and 1285 unannotated drivers. No resize or placement operation; no timing closure or fullPHY claim.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
