import os,json,re,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"ack-chip-branches";OUT.mkdir()
r=dict(source_head=os.environ["GITHUB_SHA"],accepted=False,final_timing_complete=False,full_phy_accepted=False,status="RUNNING")
def save():(OUT/"result.json").write_text(json.dumps(r,indent=2)+"\n")
try:
 assert os.environ["GITHUB_ACTIONS"]=="true"
 prior.OUT=OUT/"restore";prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api("actions/runs/43756546386");assert run["head_sha"]=="7ce9a64c4948534323731c88d537ac11a6746712"and run["conclusion"]=="success"and run["run_attempt"]==1
 def archive(aid,digest,label):
  m=prior.api("actions/artifacts/"+str(aid));assert m["workflow_run"]["id"]==run["id"]and m["workflow_run"]["head_sha"]==run["head_sha"]and m["digest"]=="sha256:"+digest and not m["expired"]
  p=OUT/(label+".zip")
  with p.open("xb")as dest:subprocess.run(["gh","api",prior.REPO+"actions/artifacts/"+str(aid)+"/zip"],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14179250243,"7d94769c10ad429f7c704448ea98b2ffaf9d94bbf16ed8868e479230b702a741","derived")
 native=archive(14178727716,"42b1618023962fb787387a4dd711535006b4ffcfd6fc31fb54154015efc8efc5","native")
 report=json.loads(safe.read("result.json"));assert report["sources_unchanged"]and report["returncode"]==0 and not report["accepted"]
 assert report["source_run"]==43755093967
 assert report["candidate_odb_sha256"]=="5d9d77bfea375bde121ec1930f3faec0918270563834cc81742493af4cdbd32b"
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
 # Verify the actual SRAM slew targets in this candidate's report.
 member='run/2-nssoc-sizedslow/checks.rpt';data=safe.read(member)
 assert hashlib.sha256(data).hexdigest()==report['outputs'][member]
 slew=data.decode().split('\nmax slew\n')[1].split('\nmax fanout\n')[0]
 violated={line.split()[0] for line in slew.splitlines() if '(VIOLATED)' in line}
 assert len(violated)==31
 # Independently authenticate the completed native connectivity probe.
 probe_run=prior.api('actions/runs/43754262798')
 assert probe_run['head_sha']=='427c5fe596cb8dc4633885cb893d22b175e305b5' and probe_run['conclusion']=='success' and probe_run['run_attempt']==1
 meta=prior.api('actions/artifacts/14177192726')
 digest='36cfb6730d8615d718e2bce222c3c3ad71f9de54809cf8a81730b5e1ce325df3'
 assert meta['workflow_run']['id']==43754262798 and meta['digest']=='sha256:'+digest and not meta['expired']
 probe_zip=OUT/'probe.zip'
 with probe_zip.open('xb')as dest:subprocess.run(['gh','api',prior.REPO+'actions/artifacts/14177192726/zip'],stdout=dest,check=True)
 assert prior.sha(probe_zip)==digest
 import csv,io
 with zipfile.ZipFile(probe_zip)as pz:
  pr=json.loads(pz.read('result.json'));tsv=pz.read('native-driver-probe.tsv')
  assert pr['returncode']==0 and pr['sources_unchanged'] and hashlib.sha256(tsv).hexdigest()==pr['native_driver_probe_sha256']
  rr=list(csv.DictReader(io.StringIO(tsv.decode()),delimiter='\t'))
  assert len(rr)==1321 and len(set((v['kind'],v['pin'])for v in rr))==1321
  specs=[]
  for row in rr:
   if row['kind']!='slew' or row['pin'] not in violated:continue
   m=re.fullmatch(r'\{\{([^{}]+)\} Y sg13g2_o21ai_1\}',row['output_drivers'])
   if not m:continue
   assert row['iterms']=='2' and row['bterms']=='0'
   instance,terminal=row['pin'].rsplit('/',1)
   specs.append([m[1],instance,terminal])
  assert len(specs)>0 and len(specs)<=31 and len({v[0] for v in specs})==len(specs)
  assert any(v[1].endswith('g_bank[6].u_mem') and v[2]=='A_DIN[9]' for v in specs)
  assert all(not any(c in item for c in '{}\n\r') for row in specs for item in row)
  (OUT/'buffer-specs.tcl').write_text('set buffer_specs {\n'+''.join(' {'+' '.join('{'+item+'}' for item in row)+'}\n' for row in specs)+'}\n')
  (OUT/'buffer-specs.json').write_text(json.dumps(specs,indent=2))
  r['buffer_spec_count']=len(specs);r['buffer_specs']=specs
 probe_zip.unlink()
 r['native_probe_binding']={'run':43754262798,'archive_sha256':digest,'tsv_sha256':pr['native_driver_probe_sha256']}
 r['critical_path_report_sha256']=report['outputs'][member]
 safe.close();native.close()
 r['source_archives']=[dict(id=14179250243,sha256='7d94769c10ad429f7c704448ea98b2ffaf9d94bbf16ed8868e479230b702a741'),dict(id=14178727716,sha256='42b1618023962fb787387a4dd711535006b4ffcfd6fc31fb54154015efc8efc5')]
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
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,OUT/"targets.json",OUT/"buffer-specs.tcl",OUT/"buffer-specs.json",ROOT/"hw/soc/pnr/ack_chip_reset_sizing_flow.py"]}
 command=[str(app),"python",str(ROOT/"hw/soc/pnr/ack_chip_reset_sizing_flow.py"),"--flow","AckChipResetSized","--pdk-root",str(ROOT/"hw/soc/tools/ciel-corrpre"),"--pdk","ihp-sg13g2","--scl","sg13g2_stdcell","--force-run-dir",str(OUT/"run"),"--with-initial-state",str(initial),str(cfg)]
 (OUT/"run").mkdir()
 with(OUT/"native.log").open("w")as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r["returncode"]=code;assert code==0
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 final=json.loads((OUT/"run/4-nssoc-sizedfast/state_out.json").read_text())
 r.update(candidate_state="run/4-nssoc-sizedfast/state_out.json",candidate_odb_sha256=prior.sha(Path(final["odb"])),measurements=final["metrics"])
 assert r["candidate_odb_sha256"]!=r["source_odb_sha256"]
 r.update(status="SRAM_OAI_BUFFER_BATCH_TRIAL_NOT_ACCEPTED",sources_unchanged=True,scope="Source5d9d with five SRAM control ECOs retained: buffer all currently violating singly-loaded SRAM o21ai outputs identified by authenticated native probe. Exact graph and global incidence proof. Fresh allcorner timing required; no routed final signoff.")
except BaseException as e:r.update(status="FAIL_OR_ERROR",error=repr(e),traceback=traceback.format_exc());raise
finally:
 r["outputs"]={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob("*")if p.is_file()and p.name!="result.json"};save()
