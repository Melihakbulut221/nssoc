import os,json,subprocess,hashlib,zipfile,io,stat
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path.cwd();OUT=ROOT/'ack-rx-wire-buffer';OUT.mkdir()
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
 r['inherited_first_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43819886766')
 assert run['head_sha']=='20f1fa07e7e1a9281959dbe64e900b1f07a5f59e' and run['conclusion']=='success' and run['run_attempt']==1
 aid=14204762090;digest='0b45644e82b722767b35567a85f5df1b5a7b919e225740d101a4720e0c64a4b1'
 meta=prior.api('actions/artifacts/'+str(aid))
 assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'])
 assert hashlib.sha256(blob).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'))
 assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 assert report['baseline_reproduction']['measured_baseline_matches']
 expected='110d019ce596c8fe86144869b2a8f22f3e9930d9c4af62bc258578d1060f96d7'
 assert report['candidate_odb_sha256']==expected
 source=ROOT/'ack-second-postcts';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-acksecondboundedpostcts/'in n];assert len(names)==1
 state=json.loads(member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(member('config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
 assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_second_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43821593059')
 assert run['head_sha']=='53bfd01c884c9c41b89098dcbacb2461f04748c1' and run['conclusion']=='success' and run['run_attempt']==1
 aid=14204554830;digest='8262623b889bc2f35e43d23ac071980e95d0e85cf28edfbb15994b2fa426a912'
 meta=prior.api('actions/artifacts/'+str(aid))
 assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'])
 assert hashlib.sha256(blob).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'))
 assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 assert report['baseline_reproduction']['measured_baseline_matches']
 expected='e973a79b546cdff4d104003455fb0a90bcab7bd1fcf1ad14dd81c5777f09edbf'
 assert report['candidate_odb_sha256']==expected
 source=ROOT/'ack-third-postcts';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-ackthirdboundedpostcts/'in n];assert len(names)==1
 state=json.loads(member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(member('config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
 assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_third_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43823463651')
 assert run['head_sha']=='da2ce89e8ac13fa28000c87881a7fa8ea02a877c' and run['conclusion']=='success' and run['run_attempt']==1
 aid=14206831104;digest='870ac8d6eb5ae778ca6a86674e3624b5eaaf7bcdc1e63b801c716767f4f13c0e'
 meta=prior.api('actions/artifacts/'+str(aid))
 assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'])
 assert hashlib.sha256(blob).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'))
 assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 assert report['baseline_reproduction']['measured_baseline_matches']
 expected='14c51b3a61588d9ee6d1bdfc7a0fa581c57ac7453dc1a3ecea929720be92260b'
 assert report['candidate_odb_sha256']==expected
 source=ROOT/'ack-fourth-postcts';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-ackfourthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(member('config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
 assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_fourth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43825457462')
 assert run['head_sha']=='1d0e4d8ebcd07c54b5c0838b6c696d72baca605c' and run['conclusion']=='success' and run['run_attempt']==1
 aid=14206464331;digest='751bc1c520d4adbe375b569da6c78875f62936563446ed9d14fd2578eca4b554'
 meta=prior.api('actions/artifacts/'+str(aid))
 assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'])
 assert hashlib.sha256(blob).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'))
 assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 assert report['baseline_reproduction']['measured_baseline_matches']
 expected='7f6a77a6d54d316ba9b89c9b1432c8080fb7b0306701c5f5ec6f8fba080cc0ae'
 assert report['candidate_odb_sha256']==expected
 source=ROOT/'ack-fifth-postcts';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-ackfifthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(member('config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
 assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_fifth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43827609384')
 assert run['head_sha']=='5b65a92537678e07cb5c5c370106a497a0bc8215' and run['conclusion']=='success' and run['run_attempt']==1
 aid=14207542565;digest='7bfa27a09557b36eb60584b2066f27e3f1c1381288d52ecbbe7f5b46f2226a95'
 meta=prior.api('actions/artifacts/'+str(aid))
 assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'])
 assert hashlib.sha256(blob).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'))
 assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 assert report['baseline_reproduction']['measured_baseline_matches']
 expected='f164e9bf0ff66e895e59eeb7b39e1c8f37194453d46634d0f802529938ac42fc'
 assert report['candidate_odb_sha256']==expected
 source=ROOT/'ack-sixth-postcts';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-acksixthboundedpostcts/'in n];assert len(names)==1
 state=json.loads(member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(member('config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
 assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 r['inherited_sixth_views']=dict(run=run['id'],artifact=aid,restored_files=dict(restored))
 run=prior.api('actions/runs/43830177430')
 assert run['head_sha']=='d18e699335cee1bdbd24696c2f085ece7164636e' and run['conclusion']=='success' and run['run_attempt']==1
 aid=14210110145;digest='229a1951810b28fe8d0f79837ccf33318d2ef3f819b3d8e1c5d6a30678b6c5db'
 meta=prior.api('actions/artifacts/'+str(aid))
 assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
 blob=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'])
 assert hashlib.sha256(blob).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(blob));assert len(z.namelist())==len(set(z.namelist()))
 report=json.loads(z.read('result.json'))
 assert report['source_head']==run['head_sha'] and report['returncode']==0 and report['sources_unchanged'] and report['accepted'] is False
 assert report['baseline_reproduction']['measured_baseline_matches']
 expected='db6aa409ff63bfa9ff3b448a79858e5fddeb3c57d200f29118f394d95a90f37a'
 assert report['candidate_odb_sha256']==expected
 source=ROOT/'ack-link-sop-buffers';source.mkdir();restored={}
 names=[n for n in z.namelist()if n.endswith('/state_out.json') and '-nssoc-acklinksopboundedpostcts/'in n];assert len(names)==1
 state=json.loads(member(names[0]).read_text());state['metrics']={};state.pop('sdf',None)
 restore_paths(state);odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==expected
 config=json.loads(member('config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 assert config['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
 assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 initial=OUT/'initial.json';initial.write_text(json.dumps(state))
 cfg=OUT/'config.json';cfg.write_text(json.dumps(config))
 app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
 flow=ROOT/'hw/soc/pnr/ack_rx_wire_buffer_flow.py'
 protected={str(p):prior.sha(p)for p in [odb,initial,cfg,flow,Path(__file__),prior.SOURCE/'prepared/physical.sdc']}
 r.update(parent_run=run['id'],source_odb_sha256=expected,restored_files=restored,protected_inputs=protected);save()
 (OUT/'run').mkdir()
 cmd=[str(app),'python',str(flow),'--flow','AckRxWireBuffer','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(cfg)]
 with (OUT/'native.log').open('w')as log:r['returncode']=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 assert r['returncode']==0 and all(prior.sha(p)==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/'run').glob('*-nssoc-sized'+short));assert len(dirs)==1
  assert not(dirs[0]/'unpropagated.rpt').read_text().strip()
  final=json.loads((dirs[0]/'state_out.json').read_text())
  measurements[corner]={k:v for k,v in final['metrics'].items()if k.endswith('__corner:'+corner)}
 gates=list((OUT/'run').glob('*-nssoc-ackrxwireboundedpostcts/baseline-reproduction.json'));assert len(gates)==1
 baseline=json.loads(gates[0].read_text());assert baseline['measured_baseline_matches']
 r.update(status='MEASURED_ACK_RX_WIRE_BUFFER_REQUIRES_REVIEW',sources_unchanged=True,baseline_reproduction=baseline,measurements=measurements,candidate_odb_sha256=prior.sha(final['odb']),scope='Exact four-buffer ACK state, baseline reproduction, one noninverting buffer on measured RX ownership gate net. No routed timing, native boot or fullPHY acceptance.')
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json' and 'restore'not in p.relative_to(OUT).parts};save()
