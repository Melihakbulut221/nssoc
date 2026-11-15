import subprocess,json,hashlib,zipfile,io
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',P+path]))
for runid,head,aid,digest,kind in [(43735491108,'7b1b49fd31f792e97f259b2aaf03a1b08ccf24bb',14170063336,'581d6036b40dc4ff3f96f43072c922b983fbeaee813fe6ae9d40dbcaee7d6970','sized'),(43735708592,'81d677c715cc29465403ed38bc7b9fbb1a736928',14170865589,'36f5fcc727690f6cfd5e0c0a9e020631a6766603b754692fdf1c4f3034996537','shared')]:
 run=api('actions/runs/'+str(runid));assert run['conclusion']=='success'and run['head_sha']==head and run['run_attempt']==1
 meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==runid and meta['digest']=='sha256:'+digest and not meta['expired']
 b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],timeout=300);assert hashlib.sha256(b).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(b));r=json.loads(z.read('result.json'));assert r['returncode']==0 and r['sources_unchanged']and not r['accepted']
 assert r['removed_verified_download_copies']==(['derived.zip','native.zip']if kind=='sized'else['derived.zip','native.zip','measurement.zip'])
 assert not any(n in r['outputs']for n in r['removed_verified_download_copies'])
 out=Path('compact')/str(runid);out.mkdir(parents=True)
 summary={'producer':runid,'artifact':aid,'archive_sha256':digest,'result':{k:v for k,v in r.items()if isinstance(v,(str,int,float,bool))or k in ['removed_verified_download_copies','source_archives']},'corners':{},'verified_members':{}}
 for index,corner in [(2,'slow'),(3,'typical'),(4,'fast')]:
  folder=f'{index}-nssoc-{kind}{corner}'
  names=['state_out.json','max.rpt','min.rpt']+[f'branch-{i}-{mode}.rpt'for i in range(3)for mode in ['min','max']]
  for filename in names:
   n='run/'+folder+'/'+filename;d=z.read(n);assert hashlib.sha256(d).hexdigest()==r['outputs'][n];summary['verified_members'][n]=r['outputs'][n]
   if filename=='state_out.json':
    m=json.loads(d)['metrics'];summary['corners'][corner]={k:v for k,v in m.items()if ':'not in k and any(s in k for s in ['setup','hold','max_slew','max_cap'])}
   elif filename.startswith('branch-'):(out/(folder+'-'+filename)).write_bytes(d)
   else:
    parts=d.decode().split('Startpoint:');assert len(parts)>1
    (out/(folder+'-'+filename)).write_text(parts[0]+''.join('Startpoint:'+p for p in parts[1:6]))
 (out/'summary.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary))
