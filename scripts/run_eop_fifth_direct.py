import os,json,subprocess,hashlib,zipfile,io,stat
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path.cwd();OUT=ROOT/'measured-buffer-batch';OUT.mkdir()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,status='RUNNING')
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2))
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api('actions/runs/43797581183');assert run['head_sha']=='ea55918740b7f140aae812f7eb22bb1c0a326f79' and run['conclusion']=='success' and run['run_attempt']==1
 h='5ee20de15cf437d855a105ec2c700b57ed1c6684bb0db51e50e9e0ada3962206';aid=14196087741
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 expected='c642317504526d0e39edae916091d31b44ffabf521cd3431e0a5168fc50eadbd';assert report['candidate_odb_sha256']==expected
 source=ROOT/'credit-crc-driver-trial';source.mkdir();restored={}
 def restore_member(name):
  rel=prior.relative(name);info=z.getinfo(name);assert not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16)
  data=z.read(info);assert hashlib.sha256(data).hexdigest()==report['outputs'][name]
  dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);restored[name]=report['outputs'][name];return dest
 names=[n for n in z.namelist() if n.endswith('/state_out.json') and '-nssoc-fourthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 def restore_paths(v):
  if isinstance(v,str):
   path=Path(v)
   if path.is_absolute():
    if path.is_relative_to(source):restore_member(str(path.relative_to(source)))
    else:assert path.is_file(),v
  elif isinstance(v,dict):
   for value in v.values():restore_paths(value)
  elif isinstance(v,list):
   for value in v:restore_paths(value)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 # Keep the authenticated fourth-state views available for inherited paths.
 parent_fourth=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43801167959');assert run['head_sha']=='119b202942c561b7797acdb9e9cc10f879c5ac3d' and run['conclusion']=='success' and run['run_attempt']==1
 h='586cfb403c012adcf85b38d699e86d391cf6bb39d5400cbdc34924eb36a1dc87';aid=14197546566
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False and report['baseline_reproduction']['measured_baseline_matches']
 expected='c2149d8ea2551ad09037895eef2284612743fbe9249e61cb730f162f753b98ba';assert report['candidate_odb_sha256']==expected
 source=ROOT/'eop-fifth-direct';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-fifthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_fourth_views']=parent_fourth
 r['inherited_fifth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43803149533');assert run['head_sha']=='4174c7da21b90fa70f1580df0f41feb1ce7e904d' and run['conclusion']=='success' and run['run_attempt']==1
 h='d422a4fd16f46581b6017362e4a6079b53026032a081bd9f86568241f0c0c7ae';aid=14196924061
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False and report['baseline_reproduction']['measured_baseline_matches']
 expected='9d9854dafc6f04849ae192577da85d32d552298e0c00c9ac239a835048004e68';assert report['candidate_odb_sha256']==expected
 source=ROOT/'eop-sixth-direct';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-sixthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_sixth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43804619916');assert run['head_sha']=='bcc9ed076aa249a52b2c40604c9799803ceb593d' and run['conclusion']=='success' and run['run_attempt']==1
 h='984b2e3a9f22ffccd1da46e1ec13f2c68140a92f0db8dabf722dd78291bc12d8';aid=14198156812
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False and report['baseline_reproduction']['measured_baseline_matches']
 expected='b7c7157d4d1afe240a580ca67b741557bbd89c703d9796de1e8ae718fa2f65ee';assert report['candidate_odb_sha256']==expected
 source=ROOT/'eop-seventh-direct';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-seventhboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_seventh_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43806377768');assert run['head_sha']=='d298e2efa84594bafb540c2070e68cf2d451ccdb' and run['conclusion']=='success' and run['run_attempt']==1
 h='460614466bbd6b262625907c8379b76c3feeef94eb9fea3d2e657a98148e2f9a';aid=14198968778
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False and report['baseline_reproduction']['measured_baseline_matches']
 expected='4ab01b2738541227b40b2016281a2d64964ac39ee25ef16cb4838bfe728e8bc7';assert report['candidate_odb_sha256']==expected
 source=ROOT/'eop-eighth-direct';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-eighthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_eighth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43808046126');assert run['head_sha']=='f87c521d905a71f43dbd42520aa21c5f0102d77b' and run['conclusion']=='success' and run['run_attempt']==1
 h='16072b4b5f0ca8f9dfeef9bfcc99f4ca689427e74baaff2b06a73e70a8d787ef';aid=14200350373
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False and report['baseline_reproduction']['measured_baseline_matches']
 expected='d24721b873d2c99e7f4992a256188186bb84848c6e1e4c9245c6352b7ed38b72';assert report['candidate_odb_sha256']==expected
 source=ROOT/'eop-ninth-direct';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-ninthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_ninth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43809912857');assert run['head_sha']=='469c34d082e7d91a3b72fa5c0c74b018f2259fa1' and run['conclusion']=='success' and run['run_attempt']==1
 h='3dfb3c64fbd7189b8c7087be37f54fee7d6d8b412490573b9971c4331f9988e9';aid=14200846061
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False and report['baseline_reproduction']['measured_baseline_matches']
 expected='fa6e794d4098e82a186d56b11567046e62579a401e080939c502935a8af24c4d';assert report['candidate_odb_sha256']==expected
 source=ROOT/'eop-tenth-direct';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-tenthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_tenth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43811737658');assert run['head_sha']=='62cc4ec36c78fa5f28dc800b87fc1f6bef7a00cc' and run['conclusion']=='success' and run['run_attempt']==1
 h='b6beb918e47a93b74ef2735498cbfabbe4c022efb8d168a2e42e56c52dd0cb56';aid=14201456092
 meta=prior.api('actions/artifacts/'+str(aid));assert meta['digest']=='sha256:'+h and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(blob).hexdigest()==h
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'));assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False and report['baseline_reproduction']['measured_baseline_matches']
 expected='06e3133ffbcea6eabe156cbe7107f0a081a01dc31846e3858cc095817121d476';assert report['candidate_odb_sha256']==expected
 source=ROOT/'eop-eleventh-direct';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-eleventhboundedpostcts/'in n];assert len(names)==1
 state=json.loads(restore_member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(restore_member('config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 initial=OUT/'initial.json';initial.write_text(json.dumps(state));cfg=OUT/'config.json';cfg.write_text(json.dumps(config));app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64');flow=ROOT/'hw/soc/pnr/eop_fifth_direct_flow.py'
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,flow,Path(__file__),prior.SOURCE/'prepared/physical.sdc']};r.update(parent_run=run['id'],source_odb_sha256=expected,restored_parent_files=restored,protected_inputs=protected);save()
 (OUT/'run').mkdir();cmd=[str(app),'python',str(flow),'--flow','EopBufferBatchDirect','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(cfg)]
 with (OUT/'native.log').open('w')as log:r['returncode']=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 assert r['returncode']==0;assert all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/'run').glob('*-nssoc-sized'+short));assert len(dirs)==1;assert not(dirs[0]/'unpropagated.rpt').read_text().strip()
  state=json.loads((dirs[0]/'state_out.json').read_text());measurements[corner]={k:v for k,v in state['metrics'].items()if k.endswith('__corner:'+corner)}
 gates=list((OUT/'run').glob('*-nssoc-bufferbatchboundedpostcts/baseline-reproduction.json'));assert len(gates)==1
 baseline=json.loads(gates[0].read_text());assert baseline['measured_baseline_matches']
 r.update(status='MEASURED_BUFFER_BATCH_REQUIRES_REVIEW',sources_unchanged=True,baseline_reproduction=baseline,measurements=measurements,candidate_odb_sha256=prior.sha(state['odb']),scope='Restore exact eleventh ODB and inherited views without replaying repairs; reproduce every eleventh corner metric before143 measured buf1-to-buf4 substitutions and legal placement; no broad timing repair. No routed timing or full PHY acceptance.')
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json' and 'restore'not in p.relative_to(OUT).parts};save()
