import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
run=api('actions/runs/43830177430')
assert run['head_sha']=='d18e699335cee1bdbd24696c2f085ece7164636e' and run['conclusion']=='success' and run['run_attempt']==1
aid=14210110145;digest='229a1951810b28fe8d0f79837ccf33318d2ef3f819b3d8e1c5d6a30678b6c5db'
meta=api('actions/artifacts/'+str(aid))
assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha'] and r['sources_unchanged'] and r['returncode']==0 and r['baseline_reproduction']['measured_baseline_matches']
assert r['candidate_odb_sha256']=='db6aa409ff63bfa9ff3b448a79858e5fddeb3c57d200f29118f394d95a90f37a'
out=Path('ack-link-sop-path-review');out.mkdir()
result=dict(source_head=os.environ['GITHUB_SHA'],producer=run['id'],artifact=aid,archive_sha256=digest,accepted=False,full_phy_accepted=False,final_timing_complete=False,reports={})
for corner in ['slow','typical','fast']:
 for kind in ['max','min']:
  names=[n for n in z.namelist()if '-nssoc-sized'+corner+'/'in n and n.endswith('/'+kind+'.rpt')];assert len(names)==1
  name=names[0];data=z.read(name);h=hashlib.sha256(data).hexdigest();assert h==r['outputs'][name]
  blocks=data.decode().split('Startpoint:')[1:];assert blocks
  rows=[]
  for block in blocks:
   slack=re.search(r'(-?[\d.]+)\s+slack \((VIOLATED|MET)\)',block);assert slack
   rows.append((float(slack[1]),block))
  rows.sort(key=lambda x:x[0])
  selected=rows[:20]
  dst=out/(corner+'-'+kind+'.txt')
  dst.write_text('Authenticated excerpt of '+name+'; full source SHA256 '+h+'\n'+''.join('Startpoint:'+block for _,block in selected))
  result['reports'][corner+'-'+kind]=dict(source=name,source_sha256=h,total_paths=len(rows),excerpt_paths=len(selected),worst_slack_ns=rows[0][0],excerpt_sha256=hashlib.sha256(dst.read_bytes()).hexdigest())
ledger_names=[n for n in z.namelist()if n.endswith('/measured-buffer-targets.json')];assert len(ledger_names)==1
ledger_data=z.read(ledger_names[0]);assert hashlib.sha256(ledger_data).hexdigest()==r['outputs'][ledger_names[0]]
ledger=json.loads(ledger_data);assert len(ledger['targets'])==4
logs=[n for n in z.namelist()if n.endswith('/nssoc-acklinksopboundedpostcts.log')];assert len(logs)==1
log=z.read(logs[0]);assert hashlib.sha256(log).hexdigest()==r['outputs'][logs[0]]
assert 'NSSOC_REPLAY_4_MEASURED_BUFFERS_SAME_INCIDENCE' in log.decode()
result['connectivity_guard_passed']=True
result['measured_target_ledger']=ledger
result['native_step_log_sha256']=hashlib.sha256(log).hexdigest()
(out/'result.json').write_text(json.dumps(result,indent=2))
