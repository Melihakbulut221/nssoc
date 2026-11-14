import subprocess,json,hashlib,zipfile,tarfile,io
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43618915765');assert r['conclusion']=='success' and r['head_sha']=='b900da8cc1d57b8b2ce80416b6742c36239afd63'
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14123718652/zip'])
assert hashlib.sha256(b).hexdigest()=='c6848d124c65c6aae6af7ee70deb7b516d0a06e91886a0d4945ea12ce4645615'
z=zipfile.ZipFile(io.BytesIO(b));t=tarfile.open(fileobj=io.BytesIO(z.read('build.tgz')),mode='r:gz')
found=[]
for member in t:
 if member.name.endswith('.json'):
  raw=t.extractfile(member).read()
  if hashlib.sha256(raw).hexdigest()=='532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a':found.append(json.loads(raw))
assert len(found)==1
m=found[0]['modules']['soc_top'];cells=m['cells'];names=m['netnames']
targets=['$auto$ff.cc:337:slice$163666','$auto$ff.cc:337:slice$163909','$auto$ff.cc:337:slice$365153','$abc$734260$auto$blifparse.cc:397:parse_blif$738145','$abc$734260$auto$blifparse.cc:397:parse_blif$738151','$abc$734260$auto$blifparse.cc:397:parse_blif$779870','$abc$734260$auto$blifparse.cc:397:parse_blif$780064','$abc$734260$auto$blifparse.cc:397:parse_blif$780073']
rows=[]
for name in targets:
 assert name in cells,name
 c=cells[name];pins={}
 for pin,bits in c['connections'].items():
  aliases=[]
  for n,v in names.items():
   if not n.startswith('$'):
    for i,b in enumerate(v['bits']):
     if b in bits:aliases.append(dict(net=n,index=i+v.get('offset',0),bit=b))
  pins[pin]=dict(bits=bits,rtl_aliases=aliases)
 rows.append(dict(cell=name,type=c['type'],pins=pins))
Path('out').mkdir();Path('out/mapping.json').write_text(json.dumps(dict(source_run=43618915765,mapped_sha256='532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a',targets=rows),indent=2))
