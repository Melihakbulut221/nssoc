# SPDX-License-Identifier: Apache-2.0
"""Cloud-only bounded diagnostics from the exact failed selective-flatten LVS DB."""
import pathlib,zipfile,tarfile,io,hashlib,json,collections
import klayout.db as db
def field(o,n):
 v=getattr(o,n);return v() if callable(v) else v
b=pathlib.Path('native.zip').read_bytes()
assert hashlib.sha256(b).hexdigest()=='80ae85f5200fbae123f8c6ce849832b88f4d320fc9d815134f77d4f988191b3e'
z=zipfile.ZipFile(io.BytesIO(b));members=[n for n in z.namelist() if n.endswith('.tgz')];assert len(members)==1
with tarfile.open(fileobj=io.BytesIO(z.read(members[0])),mode='r:gz') as t:
 raw=t.extractfile('native/lvs.lvsdb').read()
 # Export only whitelisted PDK program source, never circuit/netlist contents.
 deck_sources={}
 for filename in ['res_extraction.lvs','custom_reader.lvs','sg13g2.lvs']:
  matches=[m for m in t.getmembers() if m.isfile() and '/inputs/' in m.name and m.name.endswith('/'+filename)]
  assert len(matches)==1,(filename,len(matches))
  source=t.extractfile(matches[0]).read();assert len(source)<150000
  deck_sources[filename]={'archive_member':matches[0].name,'sha256':hashlib.sha256(source).hexdigest(),'source':source.decode()}

assert hashlib.sha256(raw).hexdigest()=='a78400289638bf4e47f51c7984c08750b41df989de4854d60c4681b596df77fb'
pathlib.Path('exact.lvsdb').write_bytes(raw)
lvs=db.LayoutVsSchematic();lvs.read('exact.lvsdb');xref=lvs.xref()
pairs=[p for p in xref.each_circuit_pair() if p.first() and p.first().name=='RM_IHPSG13_2P_256x16_c2_bm_bist'];assert len(pairs)==1
pair=pairs[0];assert str(pair.status())=='NoMatch'
def device(d):
 if d is None:return None
 dc=field(d,'device_class')
 return {'name':field(d,'name'),'class':field(dc,'name'),'parameters':{field(p,'name'):d.parameter(field(p,'id')) for p in field(dc,'parameter_definitions')}}
def named(o):return field(o,'name') if o is not None else None
r={'scope':'Diagnostic only: bounded unmatched correspondence summaries, no geometry/netlist or waveform exported. No new extraction or acceptance changes.','source_run':43543201489,'database_sha256':hashlib.sha256(raw).hexdigest(),'top_status':str(pair.status()),'production_accepted':False}
for kind,method,describe in [('devices','each_device_pair',device),('nets','each_net_pair',named),('subcircuits','each_subcircuit_pair',named)]:
 counts=collections.Counter();samples=[]
 for p in getattr(xref,method)(pair):
  status=str(p.status());counts[status]+=1
  if status!='Match' and len(samples)<100:samples.append({'status':status,'layout':describe(p.first()),'reference':describe(p.second())})
 r[kind]={'status_counts':dict(counts),'first_100_nonmatches':samples}
# Separate true parameter-distribution differences from failed pairing cascades.
r['device_inventories']={}
for label,circuit in [('layout',pair.first()),('reference',pair.second())]:
 counts=collections.Counter()
 for d in circuit.each_device():
  info=device(d);key=(info['class'].casefold(),tuple(sorted((k,round(v,12)) for k,v in info['parameters'].items())))
  counts[key]+=1
 rows=[{'class':k[0],'parameters':dict(k[1]),'count':v} for k,v in sorted(counts.items())]
 assert len(rows)<2000
 r['device_inventories'][label]=rows
r['warnings']={}
for kind,method,describe in [('devices','each_device_pair',device),('nets','each_net_pair',named),('subcircuits','each_subcircuit_pair',named)]:
 groups={};counts=collections.Counter()
 for p in getattr(xref,method)(pair):
  status=str(p.status())
  if status=='Match':continue
  side='both' if p.first() and p.second() else ('layout_only' if p.first() else 'reference_only')
  key=status+':'+side;counts[key]+=1
  bucket=groups.setdefault(key,[])
  if len(bucket)<20:bucket.append({'layout':describe(p.first()),'reference':describe(p.second())})
 r['warnings'][kind]={'group_counts':dict(counts),'first_20_per_group':groups}
# Compare hierarchy-expanded inventories: direct top counts are not comparable
# while unmatched child boundaries remain on either side. No netlist exported.
def expanded_inventory(circuit, cache, active):
 name=field(circuit,'name')
 if name in cache:return cache[name].copy()
 assert name not in active, ('recursive hierarchy',name)
 active.add(name);counts=collections.Counter()
 for d in circuit.each_device():
  info=device(d);par=info['parameters']
  counts[(info['class'].casefold(),round(par.get('L',0),12),round(par.get('W',0),12))]+=1
 for s in circuit.each_subcircuit():
  counts.update(expanded_inventory(field(s,'circuit_ref'),cache,active))
 active.remove(name);cache[name]=counts.copy();return counts
def rows(counts):
 return [{'class':k[0],'L':k[1],'W':k[2],'count':v} for k,v in sorted(counts.items())]
r['hierarchy_expanded_inventories']={}
r['direct_child_inventories']={}
for label,circuit in [('layout',pair.first()),('reference',pair.second())]:
 cache={};counts=expanded_inventory(circuit,cache,set())
 r['hierarchy_expanded_inventories'][label]={'total':sum(counts.values()),'classes_dimensions':rows(counts)}
 children=collections.Counter(field(field(s,'circuit_ref'),'name') for s in circuit.each_subcircuit())
 r['direct_child_inventories'][label]=dict(sorted(children.items()))
r['cell_pair_inventory_differences']=[]
for cp in xref.each_circuit_pair():
 if cp.first() is None or cp.second() is None:continue
 left=expanded_inventory(cp.first(),{},set());right=expanded_inventory(cp.second(),{},set())
 if left!=right:
  r['cell_pair_inventory_differences'].append({'layout_cell':field(cp.first(),'name'),'reference_cell':field(cp.second(),'name'),'status':str(cp.status()),'layout_only':rows(left-right),'reference_only':rows(right-left)})
r['deck_source_evidence']=deck_sources
pathlib.Path('out').mkdir();pathlib.Path('out/top-mismatch.json').write_text(json.dumps(r,indent=2))
print(json.dumps({k:v['status_counts'] for k,v in r.items() if isinstance(v,dict) and 'status_counts' in v}))
