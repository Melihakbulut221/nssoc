import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
run=api('actions/runs/43834590445')
assert run['head_sha']=='eb18ae3599f828157b8f0e4da7c350f4432f2c37' and run['conclusion']=='success' and run['run_attempt']==1
aid=14211017269;digest='22a95de3025c14121419c37962887102a8cfa6e9a6b78bb42063270aa31b176b'
meta=api('actions/artifacts/'+str(aid))
assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha'] and r['sources_unchanged'] and r['returncode']==0 and r['baseline_reproduction']['measured_baseline_matches']
assert r['candidate_odb_sha256']=='35ac3ceda3e3b9e8065b723242f905fd5a03d8672e4e1ede8156f0de3021ead9'
out=Path('ack-rx-wire-path-review');out.mkdir()
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
logs=[n for n in z.namelist()if n.endswith('/nssoc-ackrxwireboundedpostcts.log')];assert len(logs)==1
log=z.read(logs[0]);assert hashlib.sha256(log).hexdigest()==r['outputs'][logs[0]]
assert 'NSSOC_RX_SINGLE_NONINVERTING_BUFFER_TOPOLOGY_VERIFIED' in log.decode()
result['connectivity_guard_passed']=True
actual_names=re.findall(r'^NSSOC_INSERTED_BUFFER_ACTUAL_NAME (.+)$',log.decode(),re.M)
assert len(actual_names)==1
result['inserted_buffer_actual_name']=actual_names[0]
result['native_step_log_sha256']=hashlib.sha256(log).hexdigest()
(out/'result.json').write_text(json.dumps(result,indent=2))
