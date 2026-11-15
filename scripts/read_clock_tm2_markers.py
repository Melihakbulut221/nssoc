import os,subprocess,json,hashlib,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
meta=json.loads(subprocess.check_output(['gh','api',P+'actions/artifacts/14153712794']))
assert meta['workflow_run']['id']==43694128865 and meta['digest']=='sha256:30b6baa51a98f6f9fa6a2920e5224c7287d57ec348d1fa9118f0b55980f80d38' and not meta['expired']
p=Path('physical.zip')
with p.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/14153712794/zip'],stdout=f,check=True)
with p.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==meta['digest'].split(':')[1]
out=Path('out');out.mkdir()
with zipfile.ZipFile(p)as z:
 names=[n for n in z.namelist()if '/physical/drc/'in n];result={'inventory':names,'reports':{},'accepted':False}
 for n in names:
  if n.endswith(('.lyrdb','.rdb','.xml')):
   raw=z.read(n);root=ET.fromstring(raw)
   items=root.findall('.//items/item')
   result['reports'][n]={'sha256':hashlib.sha256(raw).hexdigest(),'root':root.tag,'categories':ET.tostring(root.find('categories'),encoding='unicode')if root.find('categories')is not None else None,'items':[ET.tostring(x,encoding='unicode')for x in items]}
 (out/'markers.json').write_text(json.dumps(result,indent=2))
 print('reports',[(n,len(r['items']))for n,r in result['reports'].items()])
