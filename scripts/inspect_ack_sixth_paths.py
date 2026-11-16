import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
run=api('actions/runs/43827609384')
assert run['head_sha']=='5b65a92537678e07cb5c5c370106a497a0bc8215' and run['conclusion']=='success' and run['run_attempt']==1
aid=14207134815;digest='63d7393f15ece4917f5da11ec33363d238355c95ae56decd035ff044142cd973'
meta=api('actions/artifacts/'+str(aid))
assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha'] and r['sources_unchanged'] and r['returncode']==0 and r['baseline_reproduction']['measured_baseline_matches']
assert r['candidate_odb_sha256']=='f164e9bf0ff66e895e59eeb7b39e1c8f37194453d46634d0f802529938ac42fc'
out=Path('ack-sixth-path-review');out.mkdir()
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
(out/'result.json').write_text(json.dumps(result,indent=2))
