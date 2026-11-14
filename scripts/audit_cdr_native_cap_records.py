"""Read native Magic capacitance and anchor records on hosted runner only."""
import hashlib,json,pathlib,tarfile,shlex
h=hashlib.sha256()
with open('metal.tgz','rb') as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
assert h.hexdigest()=='09c2185efebbdb7e60c0457d62c175d98d7bffca35e60bfe7c3f179f62ebbfb6'
targets=['T382_rppd_2','T383_rppd_2','T397_rppd_2','T398_rppd_2'];out={'accepted':False,'archive_sha256':h.hexdigest(),'scope':'Native extraction records and anchor provenance, not qualified capacitance or changed circuit','members':[],'records':{},'json_reports':{}}
def small(x,depth=0):
 if depth>4:return {'kind':type(x).__name__,'length':len(x) if hasattr(x,'__len__') else None}
 if isinstance(x,dict):return {k:small(v,depth+1) for k,v in list(x.items())[:50]}
 if isinstance(x,list):return {'length':len(x),'first': [small(v,depth+1) for v in x[:5]]}
 return x
with tarfile.open('metal.tgz','r|gz') as tar:
 for member in tar:
  n=member.name
  if '/mim-precise/' not in n:continue
  if n.endswith(('.ext','.json','.tech','.py')):out['members'].append({'name':n,'size':member.size})
  if n.endswith('.ext'):
   rows=[];counts={};matches=0
   for raw in tar.extractfile(member):
    line=raw.decode();tok=line.split();key=tok[0] if tok else ''
    counts[key]=counts.get(key,0)+1
    if any(t in line for t in targets):
     matches+=1
     if len(rows)<300:rows.append(line.rstrip())
   out['records'][n]={'record_counts':counts,'matching_count':matches,'first_100_matching':rows}
  if n.endswith('anchors08.json'):
   raw=tar.extractfile(member).read();d=json.loads(raw)
   out['json_reports'][n]={'sha256':hashlib.sha256(raw).hexdigest(),'keys':list(d),'selected_anchors':[r for r in d['anchors'] if any(t in json.dumps(r) for t in targets)]}
   selected=[r for r in d['anchors'] if r['label'] in targets];assert len(selected)==4
   components={r['wire_component'] for r in selected};assert len(components)==4
   conductor_anchors=[r for r in d['anchors'] if r['wire_component'] in components]
   all_anchors=d['anchors']
  if n.endswith('mim-audit.json'):
   raw=tar.extractfile(member).read();out['json_reports'][n]={'sha256':hashlib.sha256(raw).hexdigest(),'summary':small(json.loads(raw))}
assert out['records'] and out['json_reports']
# Independent exact-GDS DBU readback: no assumption about coordinate units.
h=hashlib.sha256()
with open('geometry.tgz','rb') as f:
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
assert h.hexdigest()=='d8bd9f7463e7941e4f0319c5d01c47f217366cd213d83c68b9f6fdc6d256bc36'
found=[]
with tarfile.open('geometry.tgz','r|gz') as tar:
 for m in tar:
  if m.name.endswith('/native/selected/layout/nssoc_cdr_pd500_resistor_v59.gds'):
   raw=tar.extractfile(m).read();assert hashlib.sha256(raw).hexdigest()=='c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c'
   pathlib.Path('source.gds').write_bytes(raw);found.append(m.name)
assert len(found)==1
import klayout.db as kdb
layout=kdb.Layout();layout.read('source.gds');assert layout.dbu>0
out['geometry']={'sha256':'c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c','dbu_um':layout.dbu,'top_cells':[{'name':c.name,'bbox_dbu':str(c.bbox())} for c in layout.top_cells()]}
by_label={r['label']:r for r in conductor_anchors};assert len(by_label)==len(conductor_anchors)
rows={}
for root,driver in [('T382_rppd_2','T275_C'),('T383_rppd_2','T273_C'),('T397_rppd_2','T282_C'),('T398_rppd_2','T281_C')]:
 group=[r for r in conductor_anchors if r['wire_component']==by_label[root]['wire_component']]
 assert driver in by_label and by_label[driver]['wire_component']==by_label[root]['wire_component']
 origin=by_label[driver]['point_dbu'];points=[]
 for item in group:
  xy=item['point_dbu'];points.append({'label':item['label'],'point_dbu':xy,'manhattan_distance_from_driver_um':sum(abs(a-b) for a,b in zip(origin,xy))*layout.dbu})
 rows[root]={'driver':driver,'anchor_count':len(group),'span_x_um':(max(r['point_dbu'][0] for r in group)-min(r['point_dbu'][0] for r in group))*layout.dbu,'span_y_um':(max(r['point_dbu'][1] for r in group)-min(r['point_dbu'][1] for r in group))*layout.dbu,'anchors':points}
out['conductor_geometry']=rows
# Preserve actual macro boundaries before proposing any relocation. Device
# shapes and routing are only observed; source GDS stays byte-identical.
macro_rows=[]
for top in layout.top_cells():
 for ordinal,inst in enumerate(top.each_inst()):
  child=inst.cell
  pins=[]
  for li in layout.layer_indexes():
   info=layout.get_info(li)
   if info.datatype not in (2,25):continue
   for shape in child.each_shape(li):
    if shape.is_text():pins.append({'layer':str(info),'text':shape.text.string,'position_dbu':[shape.text.x,shape.text.y]})
  macro_rows.append({'ordinal':ordinal,'cell':child.name,'instance_transform':str(inst.trans),'complex_transform':str(inst.cplx_trans),'bbox_dbu':str(inst.bbox()),'cell_bbox_dbu':str(child.bbox()),'regular_array':inst.is_regular_array(),'array_na':inst.na,'array_nb':inst.nb,'child_instance_count':sum(1 for _ in child.each_inst()),'pin_labels':pins})
out['top_macro_instances']=macro_rows
assert hashlib.sha256(pathlib.Path('source.gds').read_bytes()).hexdigest()==out['geometry']['sha256']

out['geometry_scope']='Exact native physical terminal anchors and GDS DBU. Manhattan distances are lower bounds, not measured routed lengths. No physical edits or acceptance.'
# Derive complete current physical macro/net connectivity and propose only
# macro ordering. No changed GDS: top routing/local additions must be rebuilt.
import collections,random,math
macros=[i for i in layout.top_cell().each_inst() if i.cell.name.startswith('pd_child_')]
assert len(macros)==16 and all(not i.is_regular_array() for i in macros)
boxes=[i.bbox() for i in macros]
netpoints=collections.defaultdict(list);coverage=[];unowned=[]
for row in all_anchors:
 p=row['point_dbu'];owners=[i for i,b in enumerate(boxes) if b.contains(kdb.Point(*p))]
 assert len(owners)<=1,(row['label'],owners)
 owner=owners[0] if owners else None
 # Explicit public port anchors may remain outside functional macro boxes.
 if owner is None:unowned.append(row)
 netpoints[row['wire_component']].append((owner,p[0],p[1],row['label']))
 coverage.append({'label':row['label'],'macro':owner,'component':row['wire_component']})
railnets={r['wire_component'] for r in all_anchors if r['detail'].get('public_port','').lower() in ('avdd','avss','sub')}
assert len(railnets)==3,railnets
# Missing device ownership rejects a plan, rather than silently optimizing a
# partial cone. The source top has exactly25 physical public ports.
assert len(unowned)==25 and all('public_port' in r['detail'] for r in unowned),unowned
critical={by_label[t]['wire_component'] for t in targets}
original_y=[i.trans.disp.y for i in macros];origin=min(original_y)
heights=[i.cell.bbox().height() for i in macros]
def positions(order):
 y=origin;out={}
 for i in order:out[i]=y;y+=heights[i]+80000
 return out
def measures(ys):
 out={}
 for net,pts in netpoints.items():
  xs=[p[1] for p in pts];yv=[p[2]+(ys[p[0]]-original_y[p[0]] if p[0] is not None else 0) for p in pts]
  out[net]=(max(xs)-min(xs)+max(yv)-min(yv))*layout.dbu
 return out
def objective(values,weight):return sum(v*(weight if n in critical else 1) for n,v in values.items() if n not in railnets)
baseline=measures(dict(enumerate(original_y)));initial=sorted(range(16),key=lambda i:original_y[i]);plans=[]
# Preserve all six frontend macro transforms and complete divider/buffer
# pairs. The earlier unconstrained weighted plan lengthened the C divider
# outputs by1355um and is not adopted.
import itertools
prefix=initial[:6];assert set(prefix)==set(range(6))
units=[(6,7),(9,10),(8,),(11,),(12,),(13,),(14,),(15,)]
protected={n for n,pts in netpoints.items() if {p[0] for p in pts if p[0] is not None} in ({6,7},{9,10})}
assert len(protected)>=4,protected
def paired_positions(order):
 ys={i:original_y[i] for i in prefix};y=original_y[6]
 for i in order[6:]:ys[i]=y;y+=heights[i]+80000
 return ys
best=None;evaluated=0;eligible=0
for permutation in itertools.permutations(units):
 order=prefix+[i for unit in permutation for i in unit];assert len(set(order))==16
 ys=paired_positions(order);v=measures(ys);evaluated+=1
 if any(v[n]>baseline[n]+1e-6 for n in protected):continue
 eligible+=1
 # Equal extra weight on all intermacro signal nets discourages moving delay
 # into another analog stage; targeted data/select nets get weight4.
 score=objective(v,4)
 if best is None or (score,order)<(best[0],best[1]):best=(score,order,ys,v)
assert evaluated==40320 and eligible and best is not None
score,order,ys,changed=best
newboxes=[boxes[i].transformed(kdb.Trans(0,ys[i]-original_y[i])) for i in range(16)]
assert all((kdb.Region(newboxes[i])&kdb.Region(newboxes[j])).is_empty() for i in range(16) for j in range(i))
assert all(ys[i]==original_y[i] for i in prefix)
plans.append({'critical_weight':4,'order':order,'positions_y_dbu':ys,'objective_before':objective(baseline,4),'objective_after':score,'macro_bbox_nonoverlap':True,'fixed_frontend_macros':prefix,'preserved_divider_buffer_pairs':[[6,7],[9,10]],'protected_components':sorted(protected),'evaluated':evaluated,'eligible':eligible,'net_changes':[{'component':n,'labels':[v[3] for v in netpoints[n]],'supply':n in railnets,'critical':n in critical,'before_hpwl_um':baseline[n],'after_hpwl_um':changed[n],'delta_um':changed[n]-baseline[n]} for n in sorted(netpoints)]})
out['placement_plans']={'status':'PROPOSED_MACRO_ORDERS_REQUIRES_ROUTING_REBUILD','geometry_changed':False,'coverage':coverage,'unowned_public_ports':unowned,'rail_components':sorted(railnets),'critical_components':sorted(critical),'plans':plans,'scope':'Complete physical anchor graph; fixed external pins and six frontend macros; constant X; contiguous divider/buffer pairs; exhaustive40320 macro-unit permutations with80um gaps. HPWL is a placement proxy, not routed wirelength or timing. All signal changes including clocks and upstream sampler paths retained. No LVS/DRC or electrical acceptance.'}
out['top_shape_inventory']={}
for li in layout.layer_indexes():
 counts=collections.Counter();bounds=[]
 for shape in layout.top_cell().each_shape(li):
  kind='box' if shape.is_box() else 'polygon' if shape.is_polygon() else 'path' if shape.is_path() else 'text' if shape.is_text() else 'other'
  counts[kind]+=1
  if len(bounds)<10:bounds.append({'kind':kind,'bbox_dbu':str(shape.bbox())})
 if counts:out['top_shape_inventory'][str(layout.get_info(li))]={'counts':dict(counts),'first_ten_bounds':bounds}
pathlib.Path('out').mkdir();pathlib.Path('out/capacitor-native-records.json').write_text(json.dumps(out,indent=2))
