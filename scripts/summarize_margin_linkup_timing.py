import subprocess,json,hashlib,zipfile,io
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',P+path]))
run=api('actions/runs/43734156396')
assert run['conclusion']=='success' and run['head_sha']=='c355ce32bcaf9c730dbd81bbeed99a9b4155d4a7' and run['run_attempt']==1
aid=14170027132;digest='e2bec5be2990748b61abef5f730157e365436899bf3ec7cb3c1cbd80f4649e8e'
a=api('actions/artifacts/'+str(aid))
assert a['workflow_run']['id']==run['id'] and a['digest']=='sha256:'+digest and not a['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],timeout=300)
assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));r=json.loads(z.read('result.json'))
assert r['returncode']==0 and r['sources_unchanged'] and not r['accepted']
out=Path('compact');out.mkdir()
summary={'artifact':aid,'archive_sha256':digest,'producer':run['id'],'result':{k:v for k,v in r.items()if isinstance(v,(str,int,float,bool))},'corners':{},'verified_members':{}}
for corner in ['2-nssoc-sizedslow','3-nssoc-sizedtypical','4-nssoc-sizedfast']:
 for filename in ['state_out.json','max.rpt','min.rpt']:
  n='run/'+corner+'/'+filename;d=z.read(n)
  assert hashlib.sha256(d).hexdigest()==r['outputs'][n]
  summary['verified_members'][n]=r['outputs'][n]
  if filename=='state_out.json':
   m=json.loads(d)['metrics'];summary['corners'][corner]={k:v for k,v in m.items()if ':'not in k and any(s in k for s in ['setup','hold','max_slew','max_cap'])}
  else:
   text=d.decode();parts=text.split('Startpoint:');assert len(parts)>1
   (out/(corner+'-'+filename)).write_text(parts[0]+''.join('Startpoint:'+p for p in parts[1:6]))
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
