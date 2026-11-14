# SPDX-License-Identifier: Apache-2.0
"""Inspect failed frozen SRAM comparison; export only derived device summaries."""
import hashlib,zipfile,tarfile,io,pathlib,json,collections
import klayout.db as db
def field(obj,name):
 value=getattr(obj,name);return value() if callable(value) else value
P=pathlib.Path
b=P('native.zip').read_bytes();assert hashlib.sha256(b).hexdigest()=='1500e77278169018c45451e0fc0d18c0d51bab3a7bb981b15b0e87bda3538654'
z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist() if n.endswith('.tgz')];assert len(names)==1
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 raw=t.extractfile('native/lvs.lvsdb').read();assert hashlib.sha256(raw).hexdigest()=='d712c5238849180c09e9ca7bc09d97b292047b945485d0911d9708f5b2ac5f4b'
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
 row['device_pair_status_counts']=dict(collections.Counter(str(p.status()) for p in lvs.xref().each_device_pair(pair)))
 row['net_pair_status_counts']=dict(collections.Counter(str(p.status()) for p in lvs.xref().each_net_pair(pair)))
 if str(pair.status())!='Skipped':
  row['nonmatching_device_pairs']=[]
  for dp in lvs.xref().each_device_pair(pair):
   if str(dp.status())=='Match':continue
   dr={'status':str(dp.status())}
   for side,d in [('layout',dp.first()),('schematic',dp.second())]:
    if d is None:dr[side]=None;continue
    cls=d.device_class()
    dr[side]={'class':cls.name,'parameters':{field(p,'name'):d.parameter(field(p,'id')) for p in cls.parameter_definitions()}}
   row['nonmatching_device_pairs'].append(dr)
 rows.append(row)
r={'status':'DIAGNOSTIC_ONLY_NOT_LVS_PASS','source_run_id':43529228292,'source_artifact_id':14087058081,'database_sha256':hashlib.sha256(raw).hexdigest(),'nonmatching_circuits':rows,'lvs_api_methods':[x for x in dir(lvs) if any(k in x for k in ['netlist','schematic','reference','compare'])],'manufacturing_approval':False}
P('out').mkdir();P('out/device-diagnosis.json').write_text(json.dumps(r,indent=2));print(json.dumps({'status':r['status'],'circuits':len(rows)}))
