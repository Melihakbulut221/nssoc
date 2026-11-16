import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
run=api('actions/runs/43842116974')
assert run['head_sha']=='36032533cad6853d44f511372480609c22a88c0a' and run['conclusion']=='success' and run['run_attempt']==1
aid=14214896121;digest='fd96c4099db275ad2dcdb0c2a04cc771f896dfaad6ad6de49f974894bd7432b7'
meta=api('actions/artifacts/'+str(aid))
assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha'] and r['sources_unchanged'] and r['returncode']==0 and r['baseline_reproduction']['measured_baseline_matches']
assert r['candidate_odb_sha256']=='5f902cd92df06ac9179a1bc669de8703efb973e59704b4f584f57ff8c8aac9d5'
out=Path('ack-tx-path-review');out.mkdir()
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
logs=[n for n in z.namelist()if n.endswith('/nssoc-acktxpathboundedpostcts.log')];assert len(logs)==1
log=z.read(logs[0]);assert hashlib.sha256(log).hexdigest()==r['outputs'][logs[0]]
assert 'NSSOC_REPLAY_4_MEASURED_BUFFERS_SAME_INCIDENCE' in log.decode()
result['connectivity_guard_passed']=True
targets=[n for n in z.namelist()if '-nssoc-acktxpathboundedpostcts/'in n and n.endswith('/measured-buffer-targets.json')]
assert len(targets)==1
t=z.read(targets[0]);assert hashlib.sha256(t).hexdigest()==r['outputs'][targets[0]]
target=json.loads(t)
assert target['hold39815_unchanged'] and set(target['targets'])=={'fanout4514','fanout1693','fanout9715','$abc$735303$auto$blifparse.cc:397:parse_blif$780452'}
result['measured_targets']=target
result['scope']='Native guard and worst max/min path review only. Placement-estimated timing; no routed or final acceptance.'
result['native_step_log_sha256']=hashlib.sha256(log).hexdigest()
(out/'result.json').write_text(json.dumps(result,indent=2))
