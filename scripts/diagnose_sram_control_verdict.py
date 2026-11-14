# SPDX-License-Identifier: Apache-2.0
import pathlib,hashlib,zipfile,tarfile,io,json
b=pathlib.Path('native.zip').read_bytes();assert hashlib.sha256(b).hexdigest()=='6936344d7fe899168c647234912382af85ff0638a4cd7be37d1567840a040233'
z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist() if n.endswith('.tgz')];assert len(names)==1
r={}
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 for m in t.getmembers():
  if m.isfile() and '/control-' in m.name and m.name.endswith(('deck.log','run.log','audit.json')):
   raw=t.extractfile(m).read();r[m.name]={'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode()}
assert len(r)>=6
pathlib.Path('out').mkdir();pathlib.Path('out/control-verdict-logs.json').write_text(json.dumps(r,indent=2))
