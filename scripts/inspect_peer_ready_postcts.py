import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
run=api('actions/runs/43866781175')
assert run['head_sha']=='f6b2f1f02f0fd5665b4cd4aeadc1638506f6e90c' and run['conclusion']=='success' and run['run_attempt']==1
aid=14227350691;digest='8bea695200bd49d4f9bcb461b1838f8a0209e6a8ba152ec59016e35148605161'
meta=api('actions/artifacts/'+str(aid))
assert meta['digest']=='sha256:'+digest and not meta['expired'] and meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha'] and r['sources_unchanged'] and r['returncode']==0
assert r['candidate_odb_sha256']=='75de26e7adf277c1324ea33874e7df581257f0d70cd4c3054afb58a962121db4'
out=Path('peer-ready-postcts-review');out.mkdir()
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
logs=[n for n in z.namelist()if n == 'run/5-openroad-resizertimingpostcts/openroad-resizertimingpostcts.log'];assert len(logs)==1,logs
log=z.read(logs[0]);assert hashlib.sha256(log).hexdigest()==r['outputs'][logs[0]]
(out/'repair-native.txt').write_bytes(log)
result['repair_log_sha256']=hashlib.sha256(log).hexdigest()
state_path='run/5-openroad-resizertimingpostcts/state_out.json';state_data=z.read(state_path);assert hashlib.sha256(state_data).hexdigest()==r['outputs'][state_path]
state=json.loads(state_data)
odb_name='run/5-openroad-resizertimingpostcts/soc_top.odb'
assert state['odb'].endswith('/peer-advertiser-load-place/'+odb_name)
data=z.read(odb_name);assert hashlib.sha256(data).hexdigest()==r['candidate_odb_sha256']==r['outputs'][odb_name]
result['odb_sha256']=r['candidate_odb_sha256']
result['measurements']=r['measurements']
result['scope']='Authenticated new peer-ready placement-estimated repair/path diagnostics; no final timing or full PHY acceptance.'
(out/'result.json').write_text(json.dumps(result,indent=2))
