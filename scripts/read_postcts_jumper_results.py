import json,subprocess,hashlib,zipfile
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
OUT=Path('out');OUT.mkdir()
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s],timeout=60))
inputs=[(43610680141, 'd42836ac2566de769473973bb15625e27f788f8d', 14129471164, '4e9033aca2d5d1a3cdbf4d9624f2a462f8a1c93ded31e641de5f44a1483bc19b'), (43610680141, 'd42836ac2566de769473973bb15625e27f788f8d', 14128673725, 'd4f9bfd320e9038081d7364550609214968e463a4fb985098d48ab625a3cff00')]
for run,head,aid,digest in inputs:
 r=api('actions/runs/'+str(run));assert r['status']=='completed'and r['head_sha']==head
 meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==run and meta['workflow_run']['head_sha']==head and meta['digest']=='sha256:'+digest and not meta['expired']
 path=Path(str(aid)+'.zip')
 with path.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True,timeout=300)
 with path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
 z=zipfile.ZipFile(path);data={'run':run,'head':head,'run_conclusion':r['conclusion'],'artifact':aid,'archive_sha256':digest,'members':z.namelist(),'json_reports':{},'path_excerpts':{},'accepted':False}
 for name in z.namelist():
  if name.endswith('/')or name.endswith('config.json'):continue
  if name.endswith('.json'):
   raw=z.read(name);j=json.loads(raw)
   if name.endswith('state_in.json'):continue
   if name.endswith('state_out.json'):j={'metrics':j.get('metrics',{})}
   elif isinstance(j,dict):j={k:v for k,v in j.items()if k not in ('outputs','protected_inputs','placement_source','current_boot_source_revalidation','source_hashes')}
   data['json_reports'][name]={'source_sha256':hashlib.sha256(raw).hexdigest(),'value':j}
  elif Path(name).name in ('max.rpt','min.rpt','summary.rpt','antenna.rpt'):
   raw=z.read(name);data['path_excerpts'][name]={'source_sha256':hashlib.sha256(raw).hexdigest(),'text':'\n'.join(raw.decode().splitlines()[:85])}
 (OUT/(str(aid)+'.json')).write_text(json.dumps(data,indent=2)+'\n')
