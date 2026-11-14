import json,subprocess,hashlib,zipfile
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
OUT=Path('out');OUT.mkdir()
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s],timeout=60))
inputs=[(43625119515,'63a2a8fbed52f0765a46cd5f5cbacff5cf773623',14126103113,'06c0631fee76d2e8e360286c87e1d576c1deaf3adf0f7e2a284fbf52ef3f8032'),(43614100441,'b83bc3a3f204bf9a2833c89fd632ae9308a58b56',14126777842,'daa567669be4ef93410162062ed8a65865dfaac8b3d6885097c4d70aaf276c81'),(43614100441,'b83bc3a3f204bf9a2833c89fd632ae9308a58b56',14126605652,'7a5308faca9cc59da239de71c5699df75e49d838cd65973568ac1a9bfcc9a784')]
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
