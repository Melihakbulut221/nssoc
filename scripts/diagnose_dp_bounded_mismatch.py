# SPDX-License-Identifier: Apache-2.0
import hashlib,zipfile,tarfile,io,pathlib,json,collections
import klayout.db as kdb
P=pathlib.Path
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='31142082483dce4751f3abfe3af48cc1e76a48b4ce6f61ce9afbb6f29f5f3ced'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['bounded-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:
 raw=t.extractfile('native/lvs.lvsdb').read()
assert hashlib.sha256(raw).hexdigest()=='341e7da0e6d9552c99f31d058d0250846321051badf48c099add4e60edebc2aa'
P('/tmp/full-macro.lvsdb').write_bytes(raw)
db=kdb.LayoutVsSchematic();db.read('/tmp/full-macro.lvsdb');xref=db.xref()
def field(obj,name):
 v=getattr(obj,name);return v() if callable(v) else v
pairs=list(xref.each_circuit_pair());bad=[p for p in pairs if str(p.status())!='Match'];assert len(bad)==1
cp=bad[0];a,b=cp.first(),cp.second();assert field(a,'name')=='RM_IHPSG13_2P_256x16_c2_bm_bist'
for circuit in [a,b]:
 names=[field(n,'expanded_name') for n in circuit.each_net()]
 assert len(names)==len(set(names)), 'Ambiguous expanded net identity'
net_status=[{},{}];net_counts=collections.Counter();top_ports=[]
def ports(c):
 out={}
 for p in c.each_pin():
  n=c.net_for_pin(field(p,'id'))
  if n is not None:out.setdefault(field(n,'expanded_name'),[]).append(field(p,'name'))
 return out
port_maps=[ports(a),ports(b)]
for pair in xref.each_net_pair(cp):
 status=str(pair.status());net_counts[status]+=1;row={'status':status}
 for i,net in enumerate([pair.first(),pair.second()]):
  if net is not None:
   nid=field(net,'expanded_name');net_status[i][nid]=status;row[['layout_ports','reference_ports'][i]]=port_maps[i].get(nid,[])
 if row.get('layout_ports') or row.get('reference_ports'):top_ports.append(row)
def device(d,i):
 if d is None:return None
 cls=field(d,'device_class');params={field(q,'name'):d.parameter(field(q,'id')) for q in field(cls,'parameter_definitions')}
 terms=[]
 for term in field(cls,'terminal_definitions'):
  n=d.net_for_terminal(field(term,'id'));nid=field(n,'expanded_name') if n is not None else None
  terms.append({'terminal':field(term,'name'),'net_comparison_status':net_status[i].get(nid,'missing'),'top_ports':port_maps[i].get(nid,[])})
 return {'class':field(cls,'name'),'parameters':params,'terminals':terms}
counts=collections.Counter();samples=[];parameter_differences=collections.Counter()
for pair in xref.each_device_pair(cp):
 status=str(pair.status());da,dbb=device(pair.first(),0),device(pair.second(),1)
 key=(status,da['class'] if da else None,dbb['class'] if dbb else None);counts[key]+=1
 if da and dbb:
  for k in set(da['parameters'])|set(dbb['parameters']):
   if da['parameters'].get(k)!=dbb['parameters'].get(k):parameter_differences[(k,da['parameters'].get(k),dbb['parameters'].get(k))]+=1
 if status!='Match' and len(samples)<30:samples.append({'status':status,'layout':da,'reference':dbb})
sub_counts=collections.Counter()
for pair in xref.each_subcircuit_pair(cp):sub_counts[str(pair.status())]+=1
r={'status':'DIAGNOSTIC_ONLY_NOT_LVS_ACCEPTANCE','source_run':43587554414,'native_artifact':14111500413,'database_sha256':hashlib.sha256(raw).hexdigest(),'circuit_status_counts':dict(collections.Counter(str(p.status()) for p in pairs)),'net_status_counts':dict(net_counts),'subcircuit_status_counts':dict(sub_counts),'device_status_and_class_counts':[{'status':k[0],'layout_class':k[1],'reference_class':k[2],'count':v} for k,v in counts.items()],'parameter_difference_counts':[{'parameter':k[0],'layout':k[1],'reference':k[2],'count':v} for k,v in parameter_differences.items()],'top_port_net_pairs':top_ports,'nonmatching_device_samples':samples,'xref_log_api':[n for n in dir(xref) if 'log' in n.lower()],'scope':'Bounded-search mismatch report: no missing graph waived, no schematic/layout change, no closure. Device terminal summaries omit internal net identities and are diagnostic only.'}
P('out').mkdir();P('out/top-mismatch.json').write_text(json.dumps(r,indent=2))
