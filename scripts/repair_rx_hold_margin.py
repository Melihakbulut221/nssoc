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
 run=prior.api('actions/runs/43728240498')
 assert run['head_sha']=='b2ddf379726944957839e4e3755cc72e199df230' and run['conclusion']=='success' and run['run_attempt']==1
 def archive(aid,digest,label):
  m=prior.api('actions/artifacts/'+str(aid))
  assert m['workflow_run']['id']==run['id'] and m['workflow_run']['head_sha']==run['head_sha'] and m['digest']=='sha256:'+digest and not m['expired']
  path=OUT/(label+'.zip')
  with path.open('xb')as dest:subprocess.run(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'],stdout=dest,check=True,timeout=1200)
  assert prior.sha(path)==digest
  z=zipfile.ZipFile(path);assert len(z.namelist())==len(set(z.namelist()));return z
 safe=archive(14167074480,'fa6cb6d69d33622f36ac4a2bbbb3e7293629ae7c72f40b5abfd84c6f4aaf0b0c','derived')
 report=json.loads(safe.read('result.json'))
 assert report['sources_unchanged'] and report['returncode']==0 and not report['accepted']
 expected='e975526a22a251cb830e24112eec64de5748754fc83000e441f7d2290f3ba9d4'
 assert report['candidate_odb_sha256']==expected
 targets=json.loads(safe.read('targets.json'));assert targets==report['targets'] and len(targets)==564
 margins={}
 for i,t in enumerate(targets):
  if t['kind']!='pin':continue
  vals={'max':[],'min':[]}
  for folder in ['2-nssoc-sizedslow','3-nssoc-sizedtypical','4-nssoc-sizedfast']:
   for mode in vals:
    name=f'run/{folder}/branch-{i}-{mode}.rpt';data=safe.read(name)
    assert hashlib.sha256(data).hexdigest()==report['outputs'][name]
    assert 'NSSOC_TARGET '+t['name'] in data.decode()
    v=list(map(float,re.findall(r'([-+\d.eE]+)\s+slack \(',data.decode())))
    assert v and all(math.isfinite(x)for x in v);vals[mode]+=v
  margins[t['name']]=(min(vals['max']),min(vals['min']))
 # Select from THIS candidate's actual reported sub50ps paths, not old
 # inherited path records. Require each group report to reach50ps or more.
 current_paths=[]
 for corner in ['2-nssoc-sizedslow','3-nssoc-sizedtypical','4-nssoc-sizedfast']:
  name=f'run/{corner}/min.rpt';data=safe.read(name)
  assert hashlib.sha256(data).hexdigest()==report['outputs'][name]
  blocks=data.decode().split('Startpoint:')[1:];groups={}
  for block in blocks:
   vals=list(map(float,re.findall(r'([-+\d.eE]+)\s+slack \(',block)))
   assert len(vals)==1 and math.isfinite(vals[0]) and vals[0]>=0
   group=re.search(r'(?m)^Path Group: (.+)',block)[1]
   groups.setdefault(group,[]).append(vals[0])
   if vals[0]>=.05:continue
   start=block.splitlines()[0].strip().split(' (',1)[0]
   end=re.search(r'(?m)^Endpoint: (.+)',block)[1].strip().split(' (',1)[0]
   pins=[];launched=False
   for line in block.split('data arrival time',1)[0].splitlines():
    m=re.search(r'[\^v] (.+?)/(\S+) \(sg13g2_(\S+)\)',line)
    if m:
     inst,pin,master=m.groups()
     if inst==start and pin in ['Q','Q_N','QN','X','Y']:launched=True;continue
     if launched and pin not in ['X','Y','Q','Q_N','QN','CLK']:pins.append((inst+'/'+pin,'sg13g2_'+master))
    elif start+' (in)'in line:launched=True
   assert pins
   current_paths.append(dict(corner=corner,mode='min',start=start,end=end,pins=list(dict.fromkeys(pins)),slack_ns=vals[0]))
  assert groups and all(max(v)>=.05 for v in groups.values()),'Truncated group report may hide low-margin paths'
 assert current_paths
 report['paths']=current_paths
 r.update(reserve_target_ns=.05,baseline_hold_violations=0,source_sub50ps_reported_paths=len(current_paths),timing_acceptance_gate_unchanged=True)
 selected={};unselected=[];covered=[]
 for path in report['paths']:
  if path['mode']!='min':continue
  choices=[]
  for pin,master in reversed(path['pins']):
   if pin not in margins:continue
   setup,hold=margins[pin];count=1
   if hold>=.05:continue
   if setup>=count:choices.append(dict(sink=pin,master=master,expected_port=path['start'],delay_master='sg13g2_dlygate4sd3_1',delay_count=count,worst_setup_slack_ns=setup,worst_hold_slack_ns=hold))
  if not choices:unselected.append(path);continue
  choice=choices[0]
  if choice['sink']in selected:
   assert all(selected[choice['sink']][k]==choice[k]for k in ['master','delay_count','worst_setup_slack_ns','worst_hold_slack_ns'])
  else:selected[choice['sink']]=choice
  covered.append(path)
 assert selected and covered
 rows=list(selected.values());count=sum(x['delay_count']for x in rows)
 r.update(source_run=run['id'],source_odb_sha256=expected,targets=targets,paths=report['paths'],selected_targets=rows,inserted_cells=count,covered_paths=covered,unselected_paths=unselected,unselected_reason='No measured input with conservative 1 ns setup reserve per delay; not silently waived.')
 (OUT/'targets.json').write_text(json.dumps(targets,indent=2)+'\n');(OUT/'hold-selected.json').write_text(json.dumps(rows,indent=2)+'\n');save()
 native=archive(14167987249,'b484dcac548516118ba1fe04e485174d3057616dfb244b381da0f41c6472c99e','native')
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
 r.update(status='NEW_RX_SUB50PS_MEASURED_HOLD_MARGIN_TRIAL_NOT_FINAL_ACCEPTANCE',sources_unchanged=True,candidate_odb_sha256=prior.sha(candidate),candidate_state=str(final.relative_to(OUT)),measurements=measurements,scope='Exact e975 with221delays and10buffer upsizes; improve actual sub50ps paths using measured inputs with at least1ns setup reserve per added delay. Missing or unsafe inputs explicitly unresolved. Acceptance clocks/gates unchanged; fresh3corner STA, not final routing or PHY acceptance.')
except BaseException:r.update(status='FAIL_OR_ERROR',traceback=traceback.format_exc());raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
