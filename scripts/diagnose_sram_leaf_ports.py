# SPDX-License-Identifier: Apache-2.0
import pathlib,hashlib,zipfile,tarfile,io,json
import klayout.db as db
def field(o,n):
 v=getattr(o,n);return v() if callable(v) else v
b=pathlib.Path('native.zip').read_bytes();assert hashlib.sha256(b).hexdigest()=='c2eaadd37f656dfa8ad8e03bd84450f2134648ab4213c300f0af343aa1bb39bb'
z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist() if n.endswith('.tgz')];assert len(names)==1
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 raw=t.extractfile('native/control-mapped-original/lvs.lvsdb').read();pathlib.Path('leaf.lvsdb').write_bytes(raw)
lvs=db.LayoutVsSchematic();lvs.read('leaf.lvsdb');rows=[]
for pair in lvs.xref().each_circuit_pair():
 row={'status':str(pair.status())}
 for side,c in [('layout',pair.first()),('reference',pair.second())]:
  row[side]={'name':c.name,'pins':[{'id':field(p,'id'),'name':field(p,'name')} for p in c.each_pin()],'named_nets':[field(n,'name') for n in c.each_net() if field(n,'name')]}
 rows.append(row)
r={'status':'PORT_DIAGNOSTIC_ONLY','database_sha256':hashlib.sha256(raw).hexdigest(),'circuits':rows,'xref_methods':[x for x in dir(lvs.xref()) if 'pin' in x],'production_accepted':False}
pathlib.Path('out').mkdir();pathlib.Path('out/leaf-ports.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
