import hashlib,io,json,os,pathlib,subprocess,tarfile,zipfile
blob=subprocess.check_output(['gh','api','repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts/14103417683/zip'],timeout=180)
assert hashlib.sha256(blob).hexdigest()=='361ca0f3c8fad45e6c8a8a4b49e828804cb48df8835651acb49932222f6e1c31'
z=zipfile.ZipFile(io.BytesIO(blob));names=[n for n in z.namelist() if n.endswith('candidate.tgz')];assert len(names)==1
rows=[];states=[]
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 for member in t:
  if not member.isfile():continue
  name=member.name
  if name.endswith(('.odb','.def','.guide','.sdc')):
   f=t.extractfile(member);h=hashlib.sha256()
   while True:
    block=f.read(1024*1024)
    if not block:break
    h.update(block)
   rows.append({'path':name,'bytes':member.size,'sha256':h.hexdigest(),'mtime':member.mtime})
  elif name.endswith(('state_out.json','state_in.json','routed-state.json')):
   data=json.load(t.extractfile(member))
   states.append({'path':name,'views':{k:v for k,v in data.items() if k!='metrics'},'route_metrics':{k:v for k,v in data.get('metrics',{}).items() if k.startswith(('route__','antenna__'))}})
r={'source':os.environ['GITHUB_SHA'],'parent_run':43541234973,'native_artifact':14103417683,'files':rows,'states':states,'scope':'Cloud-only inventory and hashes, no native design bytes exported. File existence alone is not completed-route or STA acceptance.'}
pathlib.Path('out').mkdir();pathlib.Path('out/recovery-inventory.json').write_text(json.dumps(r,indent=2))
