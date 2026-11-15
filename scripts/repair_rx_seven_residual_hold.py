# SPDX-License-Identifier: Apache-2.0
"""Repair measured hold branches of the exact reset-sized new-RX candidate."""
import os,json,re,subprocess,zipfile,stat,hashlib,traceback,math
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'ack-chip-branches';OUT.mkdir()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,status='RUNNING')
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 assert os.environ['GITHUB_ACTIONS']=='true'
 prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api('actions/runs/43725515099')
 assert run['head_sha']=='adfa6e152dcf8560ed6cc5839682376c8a9d0633' and run['conclusion']=='success' and run['run_attempt']==1
 def archive(aid,digest,label):
  m=prior.api('actions/artifacts/'+str(aid))
  assert m['workflow_run']['id']==run['id'] and m['workflow_run']['head_sha']==run['head_sha'] and m['digest']=='sha256:'+digest and not m['expired']
  path=OUT/(label+'.zip')
  with path.open('xb')as dest:subprocess.run(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'],stdout=dest,check=True,timeout=1200)
  assert prior.sha(path)==digest
  z=zipfile.ZipFile(path);assert len(z.namelist())==len(set(z.namelist()));return z
 safe=archive(14166341678,'cb5383123492ae6fc8baf6aefe55a86445d06f8deb6d53ea88acedf07021de37','derived')
 report=json.loads(safe.read('result.json'))
 assert report['sources_unchanged'] and report['returncode']==0 and not report['accepted']
 expected='441ff0490eb3239ba9011e1b5e08e99f7f8304a600e30ec38dc4806d10525e3e'
 assert report['source_odb_sha256']==expected
 targets=json.loads(safe.read('targets.json'));assert targets==report['targets'] and len(targets)==564
 margins={}
 for i,t in enumerate(targets):
  if t['kind']!='pin':continue
  vals={'max':[],'min':[]}
  for folder in ['1-nssoc-ackbranchslow','2-nssoc-ackbranchtypical','3-nssoc-ackbranchfast']:
   for mode in vals:
    name=f'run/{folder}/branch-{i}-{mode}.rpt';data=safe.read(name)
    assert hashlib.sha256(data).hexdigest()==report['outputs'][name]
    assert 'NSSOC_TARGET '+t['name'] in data.decode()
    v=list(map(float,re.findall(r'([-+\d.eE]+)\s+slack \(',data.decode())))
    assert v and all(math.isfinite(x)for x in v);vals[mode]+=v
  margins[t['name']]=(min(vals['max']),min(vals['min']))
 selected={};unselected=[];covered=[]
 for path in report['paths']:
  if path['mode']!='min' or path['slack_ns']>=0:continue
  choices=[]
  for pin,master in reversed(path['pins']):
   setup,hold=margins[pin];count=2 if hold<-.15 else 1
   if setup>=count:choices.append(dict(sink=pin,master=master,expected_port=path['start'],delay_master='sg13g2_dlygate4sd3_1',delay_count=count,worst_setup_slack_ns=setup,worst_hold_slack_ns=hold))
  if not choices:unselected.append(path);continue
  choice=choices[0]
  if choice['sink']in selected:
   assert all(selected[choice['sink']][k]==choice[k]for k in ['master','delay_count','worst_setup_slack_ns','worst_hold_slack_ns'])
  else:selected[choice['sink']]=choice
  covered.append(path)
 assert len(selected)==7 and len(covered)==7 and not unselected
 rows=list(selected.values());count=sum(x['delay_count']for x in rows)
 r.update(source_run=run['id'],source_odb_sha256=expected,targets=targets,paths=report['paths'],selected_targets=rows,inserted_cells=count,covered_paths=covered,unselected_paths=unselected,unselected_reason='No measured input with conservative 1 ns setup reserve per delay; not silently waived.')
 (OUT/'targets.json').write_text(json.dumps(targets,indent=2)+'\n');(OUT/'hold-selected.json').write_text(json.dumps(rows,indent=2)+'\n');save()
 # Margins came from read-only43725515099 on exact441ff. Restore the same
 # physical441ff from its independent native producer, with separate binding.
 r['measurement_run']=run['id']
 run=prior.api('actions/runs/43720921041')
 assert run['head_sha']=='15c019517c9807b26bd39e875d5359b0ea48dbf8' and run['conclusion']=='success' and run['run_attempt']==1
 safe=archive(14165417399,'54b555903714ceebf5648e9319743013f0fbf4cd0027fcf7d80571e8f45dd8e8','source-derived')
 report=json.loads(safe.read('result.json'))
 assert report['sources_unchanged'] and report['returncode']==0 and report['candidate_odb_sha256']==expected and report['inserted_cells']==214
 r['physical_source_run']=run['id']
 native=archive(14166012274,'792adf5a25ee7fb8f331aa19c208a0991a3d89c5620dde157acd36e9b84a973e','native')
 assert {n for n in native.namelist()if not n.endswith('/')}==set(report['outputs'])|{'result.json'}
 source=ROOT/'ack-hold-source';source.mkdir()
 for info in native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  data=native.read(info);h=hashlib.sha256(safe.read('result.json')).hexdigest()if info.filename=='result.json'else report['outputs'][info.filename]
  assert hashlib.sha256(data).hexdigest()==h
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 state=json.loads((source/report['candidate_state']).read_text())
 def relocate(v):
  if isinstance(v,str):return v.replace(str(OUT)+'/',str(source)+'/')
  if isinstance(v,list):return [relocate(x)for x in v]
  if isinstance(v,dict):return {k:relocate(x)for k,x in v.items()}
  return v
 state=relocate(state);odb=Path(state['odb']);assert prior.sha(odb)==expected
 state['metrics']={};initial=OUT/'initial.json';initial.write_text(json.dumps(state))
 config=json.loads((source/'config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0
 cfg=OUT/'config.json';cfg.write_text(json.dumps(config))
 app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
 files=[odb,initial,cfg,OUT/'targets.json',OUT/'hold-selected.json',Path(__file__),ROOT/'hw/soc/pnr/ack_chip_branches_flow.py',ROOT/'hw/soc/pnr/ack_chip_hold_repair_flow.py']
 protected={str(p):prior.sha(p)for p in files}
 command=[str(app),'python',str(ROOT/'hw/soc/pnr/ack_chip_hold_repair_flow.py'),'--flow','AckChipHoldRepair','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(cfg)]
 (OUT/'run').mkdir()
 with(OUT/'native.log').open('w')as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r['returncode']=code;assert code==0
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 final=OUT/'run/4-nssoc-holdfast/state_out.json';state=json.loads(final.read_text());candidate=Path(state['odb']);assert prior.sha(candidate)!=expected
 measurements={}
 for folder in ['2-nssoc-holdslow','3-nssoc-holdtypical','4-nssoc-holdfast']:
  measurements[folder]=json.loads((OUT/'run'/folder/'state_out.json').read_text())['metrics']
 r.update(status='NEW_RX_SEVEN_RESIDUAL_HOLD_REPAIR_NOT_FINAL_ACCEPTANCE',sources_unchanged=True,candidate_odb_sha256=prior.sha(candidate),candidate_state=str(final.relative_to(OUT)),measurements=measurements,scope='Exact441ff newRX with214 existing delays; seven measured residual paths, each selected input has at least1ns all-corner setup margin; seven additional delays and fresh all-corner STA. No final route or serial PHY acceptance.')
except BaseException:r.update(status='FAIL_OR_ERROR',traceback=traceback.format_exc());raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
