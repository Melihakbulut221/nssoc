import os,json,subprocess,hashlib,io,zipfile,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
repo='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',repo+p]))
run=api('actions/runs/43815423153')
assert run['head_sha']=='efb293a481fd73730761e5571ff2db4057bc50dd' and run['run_attempt']==1 and run['conclusion']=='success'
aid=14203119130;digest='d5e432dfc6625cb1053de9371a661be40fcc74de33defd7c0b69cfef8d0f9b60'
m=api('actions/artifacts/'+str(aid))
assert not m['expired'] and m['digest']=='sha256:'+digest and m['workflow_run']['id']==run['id'] and m['workflow_run']['head_sha']==run['head_sha']
b=subprocess.check_output(['gh','api',repo+'actions/artifacts/'+str(aid)+'/zip'])
assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));assert len(z.namelist())==len(set(z.namelist()))
r=json.loads(z.read('result.json'))
assert r['source_head']==run['head_sha'] and r['returncode']==0 and r['sources_unchanged']
assert r['repaired_odb_sha256']=='edd9421227b46d829eadf1ef6fa9902ce9e0ecc2a8efb10a69bc0ed22b1e1220'
out=Path('ack-postcts-review');out.mkdir()
summary=dict(source_head=os.environ['GITHUB_SHA'],producer=run['id'],artifact=aid,archive_sha256=digest,accepted=False,corners={},files={})
def read(name):
 data=z.read(name);assert hashlib.sha256(data).hexdigest()==r['outputs'][name]
 return data
def paths(text):
 rows=[]
 for block in text.split('Startpoint:')[1:]:
  start=block.splitlines()[0].strip()
  end=re.search(r'Endpoint:\s*(\S+)',block);group=re.search(r'Path Group:\s*(\S+)',block)
  slack=re.search(r'(-?[\d.]+)\s+slack \((VIOLATED|MET)\)',block)
  if slack:
   rows.append(dict(start=start,end=end[1]if end else None,group=group[1]if group else None,slack_ns=float(slack[1]),violated=slack[2]=='VIOLATED'))
 return rows
for corner,v in r['measurements']['after'].items():
 folder=v['directory'];entry=dict(metrics=v['metrics'],reports={})
 for kind in ['min','max']:
  name=folder+'/'+kind+'.rpt';data=read(name);rows=paths(data.decode())
  assert rows
  entry['reports'][kind]=dict(paths=len(rows),reported_violations=sum(x['violated']for x in rows),worst=sorted(rows,key=lambda x:x['slack_ns'])[:30])
 summary['corners'][corner]=entry
 selected=[n for n in z.namelist()if n.startswith(folder+'/') and (n.endswith('.rpt') or n.endswith('or_metrics_out.json') or n.endswith('state_out.json'))]
 for name in selected:
  data=read(name);p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);summary['files'][name]=hashlib.sha256(data).hexdigest()
for name in z.namelist():
 if name in ['native.log','trial-config.json','initial-state.json'] or (name.startswith('run/5-openroad-resizertimingpostcts/')and name.endswith(('.log','.tcl','.json'))):
  if name not in r['outputs']:continue
  data=read(name);p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);summary['files'][name]=hashlib.sha256(data).hexdigest()
(out/'producer-result.json').write_text(json.dumps(r,indent=2))
(out/'result.json').write_text(json.dumps(summary,indent=2))
