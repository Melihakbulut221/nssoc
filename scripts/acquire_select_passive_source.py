import hashlib,json,subprocess,tarfile
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',P+path]))
def sha(path):
 with open(path,'rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
config=Path('scripts/cdr-mos650-geometry-inputs.json')
assert sha(config)=='0d1e5441924afe02202dc26a3c6c7adda6b2ee6b89470e1e982a1c8055e138ce'
cfg=json.loads(config.read_bytes());prod=cfg['producer']
run=api('actions/runs/'+str(prod['run']))
assert run['conclusion']=='success' and run['head_sha']==prod['source'] and run['run_attempt']==1
release=api('releases/'+str(prod['release']))
assert release['target_commitish']==prod['source'] and release['tag_name']==prod['tag']
assert api('git/ref/tags/'+prod['tag'])['object']['sha']==prod['source']
spec=prod['assets']['native-fresh-rc.tar.gz']
asset=next(x for x in release['assets']if x['id']==spec['id'])
assert asset['size']==spec['bytes'] and asset['digest']=='sha256:'+spec['sha256']
archive=Path('/tmp/select-parent-native.tar.gz')
with archive.open('xb')as f:subprocess.run(['gh','api',P+'releases/assets/'+str(spec['id']),'-H','Accept: application/octet-stream'],stdout=f,check=True,timeout=600)
assert sha(archive)==spec['sha256'] and archive.stat().st_size==spec['bytes']
prefix='binding/inputs/parent/inputs/rc_select/'
selected={n for n in prod['complete_members']if n.startswith(prefix)}
assert len(selected)==5,selected
out=Path('select-parent-source');out.mkdir()
receipt={};seen=set()
with tarfile.open(archive,'r|gz')as tar:
 for m in tar:
  root=prod['archive_root']+'/'
  assert m.isfile() and m.name.startswith(root)
  n=m.name[len(root):];assert n in prod['complete_members']and n not in seen;seen.add(n)
  stream=tar.extractfile(m);h=hashlib.sha256();size=0;chunks=[]
  for b in iter(lambda:stream.read(1024*1024),b''):
   h.update(b);size+=len(b)
   if n in selected:chunks.append(b)
  assert dict(bytes=size,sha256=h.hexdigest())==prod['complete_members'][n]
  if n in selected:
   rel=n[len(prefix):];dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b''.join(chunks))
   receipt[rel]=dict(source_member=n,bytes=size,sha256=h.hexdigest())
assert seen==set(prod['complete_members']) and len(receipt)==5
archive.unlink()
(out/'acquisition.json').write_text(json.dumps(dict(producer=prod['run'],source=prod['source'],asset=spec,verified_archive_members=len(seen),selected=receipt,accepted=False,scope='Authenticated original select-feedforward macro source. No geometry change, new RC or PHY acceptance. MOS650 replacement preserves these non-MOS devices; whole-chip closure not inferred.'),indent=2)+'\n')
print(json.dumps(receipt))
