import os,json,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'credit-crc-driver-trial';OUT.mkdir()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,status='RUNNING')
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 assert os.environ['GITHUB_ACTIONS']=='true'
 prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api('actions/runs/43785058316');assert run['head_sha']=='4455f214f7aae5e367e7f9d33be61e333589e75e' and run['conclusion']=='success' and run['run_attempt']==1
 def archive(aid,digest,label):
  m=prior.api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run['id'] and m['workflow_run']['head_sha']==run['head_sha'] and m['digest']=='sha256:'+digest and not m['expired']
  p=OUT/(label+'.zip')
  with p.open('xb') as dest:subprocess.run(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14190796694,'29f2d636ff904a471a8ad31701024d5d048cb250917782fff31369c710ca12ed','derived')
 native=archive(14190399046,'5bdb6b271dd9ccbdfc0a1a1877dffb868f53c405a747835ae90aafd47b27c2e0','native')
 report=json.loads(safe.read('result.json'));assert report['source_head']==run['head_sha'] and report['sources_unchanged'] and report['returncode']==0 and report['accepted'] is False
 assert report['repaired_odb_sha256']=='b83c2b2d7cb7084a659f9a1b250314b777a9654acf7b736ce0cbfa3c0fb930ba'
 source=ROOT/'hw/soc/out/cloud-predecode-postcts';source.mkdir()
 assert len(native.namelist())==len(set(native.namelist()))
 assert {n for n in native.namelist()if not n.endswith('/')}==set(report['outputs'])|{'result.json'}
 for info in native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  data=native.read(info);expected=hashlib.sha256(safe.read('result.json')).hexdigest()if info.filename=='result.json'else report['outputs'][info.filename]
  assert hashlib.sha256(data).hexdigest()==expected
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 member='run/6-nssoc-corrprebankedafterslow/max.rpt';data=safe.read(member);assert hashlib.sha256(data).hexdigest()==report['outputs'][member]
 first=data.decode().split('Startpoint:')[1].split('data arrival time')[0].split('/Q (',1)[1]
 targets=[('fanout9730', 'sg13g2_buf_1', 'sg13g2_buf_4'), ('fanout9729', 'sg13g2_buf_1', 'sg13g2_buf_4'), ('$abc$735341$auto$blifparse.cc:397:parse_blif$770552', 'sg13g2_buf_1', 'sg13g2_buf_4')]
 assert 'wire3244/A' in first and '$abc$735341$auto$blifparse.cc:397:parse_blif$770517/Y' in first
 for cell,old,new in targets:assert cell+'/' in first and '('+old+')' in first
 r.update(source_run=run['id'],source_odb_sha256=report['repaired_odb_sha256'],targets=targets,source_before=report['measurements']['after'],path_report_sha256=report['outputs'][member]);save()
 safe.close();native.close()
 state=json.loads((source/report['repaired_state']).read_text());odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==r['source_odb_sha256'];state['metrics']={}
 initial=OUT/'initial.json';initial.write_text(json.dumps(state))
 config=json.loads((source/'trial-config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 cfg=OUT/'config.json';cfg.write_text(json.dumps(config));app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
 flow=ROOT/'hw/soc/pnr/credit_crc_driver_flow.py';protected={str(p):prior.sha(p)for p in [odb,initial,cfg,flow,Path(__file__),prior.SOURCE/'prepared/physical.sdc']}
 command=[str(app),'python',str(flow),'--flow','AckChipResetSized','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(cfg)]
 (OUT/'run').mkdir()
 with (OUT/'native.log').open('w')as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r['returncode']=code;assert code==0
 assert 'NSSOC_LINKUP_TAPER_STRUCTURAL_PASS' in (OUT/'native.log').read_text()
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/'run').glob('*-nssoc-sized'+short));assert len(dirs)==1
  assert not(dirs[0]/'unpropagated.rpt').read_text().strip()
  state=json.loads((dirs[0]/'state_out.json').read_text());measurements[corner]={k:v for k,v in state['metrics'].items()if k.endswith('__corner:'+corner)}
 r.update(measurements=measurements,candidate_odb_sha256=prior.sha(Path(state['odb'])),sources_unchanged=True,status='MEASURED_INCREMENTAL_POSTCTS_REPAIR_REQUIRES_REVIEW',scope='Reconstruct qualified source and three driver resizes plus buf2 taper, then continue native bounded100 setup and1000 hold repair with unchanged propagated clocks, derates and constraints. Measure all3corners. Not routed or physical PHY acceptance.')
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'and p.suffix!='.zip'};save()
