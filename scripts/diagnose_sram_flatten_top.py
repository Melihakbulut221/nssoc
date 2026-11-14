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
 for filename in ['res_extraction.lvs','custom_reader.lvs','sg13g2.lvs','custom_classes.lvs','res_derivations.lvs','layers_definitions.lvs','custom_devices.lvs']:
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
# Independently count original polygon intersections instead of trusting LVS W/L.
with tarfile.open(fileobj=io.BytesIO(z.read(members[0])),mode='r:gz') as t:
 targets=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/RM_IHPSG13_2P_256x16_c2_bm_bist.gds')]
 assert len(targets)==1
 geometry=t.extractfile(targets[0]).read()
assert hashlib.sha256(geometry).hexdigest()=='420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b'
pathlib.Path('original.gds').write_bytes(geometry)
layout=db.Layout();layout.read('original.gds');top=layout.cell('RM_IHPSG13_2P_256x16_c2_bm_bist');assert top is not None
geom={'gds_sha256':hashlib.sha256(geometry).hexdigest(),'dbu_um':layout.dbu,'scope':'Independent bounding-dimension inventory from original merged metal drawing/filler minus slit intersect resistor marker. No coordinates, netlist or geometry exported; no acceptance waiver.','layers':{}}
for number,name in [(10,'res_metal2'),(30,'res_metal3')]:
 def region(datatype):
  idx=layout.find_layer(number,datatype)
  return db.Region(top.begin_shapes_rec(idx)) if idx is not None else db.Region()
 metal=region(0)+region(22);metal-=region(24)
 resistors=(metal & region(29)).merged()
 histogram=collections.Counter();nonrectangular=0
 for poly in resistors.each():
  box=poly.bbox()
  if poly.area()!=box.area():nonrectangular+=1
  dimensions=tuple(sorted([round(box.width()*layout.dbu,12),round(box.height()*layout.dbu,12)]))
  histogram[dimensions]+=1
 expected=collections.Counter()
 for row in r['hierarchy_expanded_inventories']['layout']['classes_dimensions']:
  if row['class']==name:expected[tuple(sorted([row['L'],row['W']]))]+=row['count']
 geom['layers'][name]={'polygon_count':sum(histogram.values()),'nonrectangular_count':nonrectangular,'dimensions_um':[{'short':k[0],'long':k[1],'count':v} for k,v in sorted(histogram.items())],'equals_extracted_dimension_inventory':nonrectangular==0 and histogram==expected}
 # Preserve the failed one-polygon-per-device test. Aggregation is diagnostic,
 # not a waiver and does not establish series connectivity.
 def length_inventory(counts):
  totals=collections.Counter()
  for (width,length),count in counts.items():totals[width]+=round(length*1000000)*count
  return dict(sorted(totals.items()))
 geom['layers'][name]['polygon_length_by_width_um_times_1e6']=length_inventory(histogram)
 geom['layers'][name]['extracted_length_by_width_um_times_1e6']=length_inventory(expected)
 geom['layers'][name]['equal_length_by_width']=length_inventory(histogram)==length_inventory(expected)
r['independent_original_geometry']=geom
geom['previous_direct_count_check_run']=43552738032
geom['direct_count_equality_proven']=all(v['equals_extracted_dimension_inventory'] for v in geom['layers'].values())
geom['width_and_aggregate_length_agree']=all(v['equal_length_by_width'] and v['nonrectangular_count']==0 for v in geom['layers'].values())

pathlib.Path('out').mkdir();pathlib.Path('out/top-mismatch.json').write_text(json.dumps(r,indent=2))
print(json.dumps({k:v['status_counts'] for k,v in r.items() if isinstance(v,dict) and 'status_counts' in v}))

assert geom['width_and_aggregate_length_agree'], 'Original polygon aggregate differs; see preserved diagnostic JSON'
