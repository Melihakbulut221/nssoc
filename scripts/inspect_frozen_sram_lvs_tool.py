import hashlib,json,pathlib,tarfile
out=pathlib.Path('out');out.mkdir(exist_ok=True)
with open('pkg.tgz','rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
with tarfile.open('pkg.tgz','r:gz') as t:
 cs=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/input-contract.json')];assert len(cs)==1
 c=json.loads(t.extractfile(cs[0]).read());prefix=str(pathlib.PurePosixPath(cs[0].name).parent)+'/files/'
 rows=[]
 for name,info in c['input_files'].items():
  if '/libs.tech/klayout/' not in name or not any(k in name.lower() for k in ['lvs','extract']):continue
  rows.append({'path':name,'sha256':info['sha256']})
  if name.endswith('/run_lvs.py') or name.endswith('/sg13g2.lvs'):
   data=t.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==info['sha256']
   # Tool source only; no circuit/layout files exported.
   (out/pathlib.PurePosixPath(name).name).write_bytes(data)
 (out/'support-manifest.json').write_text(json.dumps(rows,indent=2))
 print(json.dumps({'support_files':len(rows),'exported_tool_sources':[p.name for p in out.iterdir()]}))
