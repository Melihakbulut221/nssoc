# SPDX-License-Identifier: Apache-2.0
"""Inspect failed frozen SRAM comparison; export only derived device summaries."""
import hashlib,zipfile,tarfile,io,pathlib,json,collections
import klayout.db as db
def field(obj,name):
 value=getattr(obj,name);return value() if callable(value) else value
P=pathlib.Path
b=P('native.zip').read_bytes();assert hashlib.sha256(b).hexdigest()=='99bf37da6cd409e5df0834b88d7972add8dac7ebd67cdd720e91b70d25c0a870'
z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist() if n.endswith('.tgz')];assert len(names)==1
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 raw=t.extractfile('native/lvs.lvsdb').read();assert hashlib.sha256(raw).hexdigest()=='910e8ce880e58fdb86140ab745d962ab868f55eb3c6d499e960b5073ca48ca39'
 P('lvs.lvsdb').write_bytes(raw)
lvs=db.LayoutVsSchematic();lvs.read('lvs.lvsdb');rows=[]
for pair in lvs.xref().each_circuit_pair():
 if str(pair.status())=='Match':continue
 row={'status':str(pair.status())}
 for side,c in [('layout',pair.first()),('schematic',pair.second())]:
  if c is None:row[side]=None;continue
  counts=collections.Counter();params=collections.Counter()
  for d in c.each_device():
   cls=d.device_class();counts[cls.name]+=1
   values=tuple((field(p,'name'),d.parameter(field(p,'id'))) for p in cls.parameter_definitions())
   params[(cls.name,values)]+=1
  row[side]={'name':c.name,'direct_device_classes':dict(counts),'parameter_groups':[{'class':k[0],'parameters':dict(k[1]),'count':v} for k,v in params.most_common(60)],'unique_parameter_groups':len(params),'subcircuits':dict(collections.Counter(s.circuit_ref().name for s in c.each_subcircuit()))}
 rows.append(row)
r={'status':'DIAGNOSTIC_ONLY_NOT_LVS_PASS','source_run_id':43526718142,'source_artifact_id':14085134607,'database_sha256':hashlib.sha256(raw).hexdigest(),'nonmatching_circuits':rows,'lvs_api_methods':[x for x in dir(lvs) if any(k in x for k in ['netlist','schematic','reference','compare'])],'manufacturing_approval':False}
P('out').mkdir();P('out/device-diagnosis.json').write_text(json.dumps(r,indent=2));print(json.dumps({'status':r['status'],'circuits':len(rows)}))
