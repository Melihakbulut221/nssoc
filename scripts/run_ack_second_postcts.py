import os,json,subprocess,hashlib,zipfile,io,stat
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path.cwd();OUT=ROOT/'ack-second-postcts';OUT.mkdir()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,status='RUNNING')
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2))
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api('actions/runs/43815423153')
 assert run['head_sha']=='efb293a481fd73730761e5571ff2db4057bc50dd' and run['conclusion']=='success' and run['run_attempt']==1
 aid=14203119130;digest='d5e432dfc6625cb1053de9371a661be40fcc74de33defd7c0b69cfef8d0f9b60'
 meta=prior.api('actions/artifacts/'+str(aid))
 assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'])
 assert hashlib.sha256(blob).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'))
 assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 expected='edd9421227b46d829eadf1ef6fa9902ce9e0ecc2a8efb10a69bc0ed22b1e1220'
 assert report['repaired_odb_sha256']==expected
 source=ROOT/'hw/soc/out/cloud-predecode-postcts';source.mkdir();restored={}
 def member(name):
  rel=prior.relative(name);info=z.getinfo(name)
  assert not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16)
  data=z.read(info);assert hashlib.sha256(data).hexdigest()==report['outputs'][name]
  dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  restored[name]=report['outputs'][name];return dest
 state=json.loads(member(report['repaired_state']).read_text());state['metrics']={};state.pop('sdf',None)
 def restore_paths(v):
  if isinstance(v,str):
   path=Path(v)
   if path.is_absolute():
    if path.is_relative_to(source):member(str(path.relative_to(source)))
    else:assert path.is_file(),v
  elif isinstance(v,dict):
   for x in v.values():restore_paths(x)
  elif isinstance(v,list):
   for x in v:restore_paths(x)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(member('trial-config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
 assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 config['TIME_DERATING_CONSTRAINT']=5.0
 initial=OUT/'initial.json';initial.write_text(json.dumps(state))
 cfg=OUT/'config.json';cfg.write_text(json.dumps(config))
 app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
 flow=ROOT/'hw/soc/pnr/ack_second_postcts_flow.py'
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,flow,Path(__file__),prior.SOURCE/'prepared/physical.sdc']}
 r.update(parent_run=run['id'],source_odb_sha256=expected,restored_files=restored,protected_inputs=protected);save()
 (OUT/'run').mkdir()
 cmd=[str(app),'python',str(flow),'--flow','AckSecondPostCTS','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(cfg)]
 with (OUT/'native.log').open('w')as log:r['returncode']=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 assert r['returncode']==0 and all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/'run').glob('*-nssoc-sized'+short));assert len(dirs)==1
  assert not(dirs[0]/'unpropagated.rpt').read_text().strip()
  final=json.loads((dirs[0]/'state_out.json').read_text())
  measurements[corner]={k:v for k,v in final['metrics'].items()if k.endswith('__corner:'+corner)}
 gates=list((OUT/'run').glob('*-nssoc-acksecondboundedpostcts/baseline-reproduction.json'));assert len(gates)==1
 baseline=json.loads(gates[0].read_text());assert baseline['measured_baseline_matches']
 r.update(status='MEASURED_ACK_SECOND_POSTCTS_REQUIRES_REVIEW',sources_unchanged=True,baseline_reproduction=baseline,measurements=measurements,candidate_odb_sha256=prior.sha(final['odb']),scope='Exact new ACK first repaired state, all-corner baseline reproduction, bounded100setup/1000hold. No routed timing, native boot or fullPHY acceptance.')
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json' and 'restore'not in p.relative_to(OUT).parts};save()
