import subprocess,json,hashlib,zipfile,io
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',P+path]))
run=api('actions/runs/43734364727')
assert run['conclusion']=='success' and run['head_sha']=='e7b5fc83d56799bb537e14a809c0df7eff83ffa1' and run['run_attempt']==1
aid=14170515411;digest='1306de38b43f8669b7473ee8d10821e2fb7497b2b33d9c875e000d73d330a4f4'
a=api('actions/artifacts/'+str(aid))
assert a['workflow_run']['id']==run['id'] and a['digest']=='sha256:'+digest and not a['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],timeout=300)
assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));r=json.loads(z.read('result.json'))
assert r['returncode']==0 and r['sources_unchanged'] and not r['accepted']
out=Path('compact');out.mkdir()
summary={'artifact':aid,'archive_sha256':digest,'producer':run['id'],'result':{k:v for k,v in r.items()if isinstance(v,(str,int,float,bool))},'corners':{},'verified_members':{}}
for corner in ['1-nssoc-ackbranchslow','2-nssoc-ackbranchtypical','3-nssoc-ackbranchfast']:
 for filename in ['state_out.json','head-last-hold-connectivity.rpt']+[f'branch-{i}-{mode}.rpt'for i in range(3)for mode in ['min','max']]:
  n='run/'+corner+'/'+filename;d=z.read(n)
  assert hashlib.sha256(d).hexdigest()==r['outputs'][n]
  summary['verified_members'][n]=r['outputs'][n]
  if filename=='state_out.json':
   m=json.loads(d)['metrics'];summary['corners'][corner]={k:v for k,v in m.items()if ':'not in k and any(s in k for s in ['setup','hold','max_slew','max_cap'])}
  else:(out/(corner+'-'+filename)).write_bytes(d)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
