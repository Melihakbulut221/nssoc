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
# Qualify whether current local physical bands can be moved intact using
# the existing band-reorder strategy, before modifying any GDS.
T=layout.top_cell();children=[i for i in T.each_inst() if i.cell.name.startswith('pd_child_')];assert len(children)==16
ordered=sorted(children,key=lambda i:i.bbox().bottom)
edges=[224000]+[i.bbox().bottom-48000 for i in ordered[1:]]+[T.bbox().top]
assert all(edges[i]<=ordered[i].bbox().bottom and ordered[i].bbox().top<=edges[i+1] for i in range(16))
parent={};full={};child={}
for li in layout.layer_indexes():
 key=str(layout.get_info(li));full[key]=kdb.Region(T.begin_shapes_rec(li)).merged();r=kdb.Region()
 for inst in children:r+=kdb.Region(inst.cell.begin_shapes_rec(li)).transformed(inst.trans)
 child[key]=r.merged();parent[key]=(full[key]-child[key]).merged()
li=layout.layer(126,0);trunks=kdb.Region();records=[]
for shape in T.each_shape(li):
 if not shape.is_box():continue
 b=shape.box
 if b.right<953600 and b.width() in (3200,64000,256000) and b.height()>b.width():trunks.insert(b);records.append(str(b))
assert records and (trunks-parent['126/0']).is_empty()
parent['126/0']=(parent['126/0']-trunks).merged()
violations=[]
for layer,region in parent.items():
 for polygon in region.each():
  b=polygon.bbox();hits=[y for y in edges[:-1] if b.bottom<y<b.top]
  if hits:violations.append({'layer':layer,'bbox_dbu':str(b),'crossed_edges_dbu':hits})
out['physical_band_feasibility']={'edges_dbu':edges,'candidate_vertical_trunks':records,'trunks_removed_only_for_analysis':True,'crossing_conductors':violations,'whole_band_move_without_further_routing_changes_supported':not violations,'scope':'Conservative geometric feasibility, not electrical net ownership or DRC/LVS. Only known-width tall TM1 rectangles left of macros classified as possible global trunks; remaining boundary crossings retained as blockers. No GDS edits.'}
# Actual intersection audit for ALL candidate trunks, including four late
# shortcuts beyond the earlier conservative x bound. No geometry edited.
all_trunks=kdb.Region(); boxes=[]
for shape in T.each_shape(layout.layer(126,0)):
 if not shape.is_box():continue
 b=shape.box
 if b.right<993600 and b.width() in (3200,64000,256000) and b.height()>b.width():
  all_trunks.insert(b);boxes.append(b)
assert (all_trunks-(full['126/0']-child['126/0'])).is_empty()
remaining={key:(reg-child[key]).merged() for key,reg in full.items()}
remaining['126/0']=(remaining['126/0']-all_trunks).merged()
residual=[]
for layer,region in remaining.items():
 for polygon in region.each():
  b=polygon.bbox();hits=[y for y in edges[:-1] if b.bottom<y<b.top]
  if hits:residual.append({'layer':layer,'bbox_dbu':str(b),'edges_dbu':hits})
def band(y):
 if y<edges[0]:return -1
 for n in range(16):
  if edges[n]<=y<=edges[n+1]:return n
 raise ValueError('Contact outside top boundary')
rows=[]
for b in boxes:
 reg=kdb.Region(b);contacts={}
 # Via4 (M5-TM1), TopVia2 (TM1-TM2), and same-layer local tails.
 for layer in ['125/0','133/0','126/0']:
  material=remaining[layer] if layer=='126/0' else full[layer]
  hit=(material & reg.sized(1)).merged()
  contacts[layer]=[{'bbox_dbu':str(poly.bbox()),'band':band(poly.bbox().center().y)} for poly in hit.each()]
 # Metal rectangle may be crossed by unconnected metal on another layer;
 # report actual via intersections only, do not infer a net from proximity.
 rows.append({'bbox_dbu':str(b),'contact_geometry':contacts,'contact_bands':sorted({x['band'] for v in contacts.values() for x in v})})
out['all_trunk_connectivity_geometry']={'candidate_count':len(boxes),'trunks':rows,'remaining_crossings':residual,'scope':'Actual geometric via/same-metal intersections only. Electrical net identity, connectivity equivalence, DRC and new RC still required. Source GDS unchanged.'}
assert hashlib.sha256(pathlib.Path('source.gds').read_bytes()).hexdigest()==out['geometry']['sha256']

pathlib.Path('out').mkdir();pathlib.Path('out/capacitor-native-records.json').write_text(json.dumps(out,indent=2))


# Generate a physical candidate, retaining all original primitive hierarchy
# and later local metal/contact overlays. NOT a qualified layout.
assert not residual and len(boxes)==37
original_instances=list(T.each_inst());assert len(original_instances)==40
macro_by_id={n:i for n,i in enumerate(original_instances) if i.cell.name.startswith('pd_child_')}
assert set(macro_by_id)==set(range(16))
old_order=sorted(macro_by_id,key=lambda n:macro_by_id[n].bbox().bottom)
new_order=[3,0,1,2,4,5,8,6,7,12,11,9,10,13,14,15]
assert old_order[:6]==new_order[:6]
old_band={ordinal:index for index,ordinal in enumerate(old_order)}
delta={-1:0};cursor=edges[0]
for ordinal in new_order:
 b=old_band[ordinal];delta[b]=cursor-edges[b];cursor+=edges[b+1]-edges[b]
assert cursor==edges[-1]
assert all(delta[old_band[n]]==0 for n in new_order[:6])
bounds=T.bbox()
windows=[kdb.Region(kdb.Box(bounds.left-1,edges[n],bounds.right+1,edges[n+1])) for n in range(16)]
fixed=kdb.Region(kdb.Box(bounds.left-1,bounds.bottom-1,bounds.right+1,edges[0]))
def relocate(region):
 conserved=(region&fixed).merged();result=conserved
 for n,window in enumerate(windows):
  piece=(region&window).merged();conserved=(conserved+piece).merged()
  result=(result+piece.transformed(kdb.Trans(0,delta[n]))).merged()
 assert (conserved^region).is_empty()
 return result
moved={key:relocate(region) for key,region in remaining.items()}
new_trunks=kdb.Region();trunk_proof=[];new_boxes=[]
for b in boxes:
 reg=kdb.Region(b);contacts={key:(full[key]&reg).merged() for key in ['125/0','133/0']}
 assert contacts['125/0'].is_empty() and not contacts['133/0'].is_empty()
 # No unaccounted same-layer local tails were observed in the source.
 assert (remaining['126/0']&reg.sized(1)).is_empty()
 old_contact_box=contacts['133/0'].bbox();low=old_contact_box.bottom-b.bottom;high=b.top-old_contact_box.top
 assert low>=0 and high>=0
 intended={key:relocate(value) for key,value in contacts.items()}
 cb=intended['133/0'].bbox();nb=kdb.Box(b.left,cb.bottom-low,b.right,cb.top+high)
 # Supplies keep their original outside border endpoints; all supply contact
 # extrema remain covered by the same or conservatively rebuilt trunk.
 if b.width()!=3200:
  nb=kdb.Box(b.left,min(b.bottom,nb.bottom),b.right,max(b.top,nb.top))
 assert (kdb.Region(nb)&new_trunks).is_empty(),'Candidate shorts distinct global trunks'
 for key in ['125/0','133/0']:
  assert ((moved[key]&kdb.Region(nb))^intended[key]).is_empty(),('Changed actual via incidence',str(b),key)
 assert (moved['126/0']&kdb.Region(nb).sized(1)).is_empty(),'New unaccounted same-layer contact'
 new_trunks+=kdb.Region(nb);new_boxes.append(nb)
 trunk_proof.append({'old_bbox_dbu':str(b),'new_bbox_dbu':str(nb),'old_length_um':b.height()*layout.dbu,'new_length_um':nb.height()*layout.dbu,'via_incidence_conserved':True})
moved['126/0']=(moved['126/0']+new_trunks).merged()
old_name=T.name;T.name=old_name+'_baseline';candidate=layout.create_cell(old_name)
expected=dict(moved)
for n,inst in macro_by_id.items():
 assert not inst.is_regular_array() and inst.cplx_trans.mag==1 and inst.cplx_trans.angle==0 and not inst.cplx_trans.is_mirror()
 tr=kdb.Trans(inst.trans);tr.disp=kdb.Vector(tr.disp.x,tr.disp.y+delta[old_band[n]])
 candidate.insert(kdb.CellInstArray(inst.cell_index,tr))
 for li in layout.layer_indexes():
  key=str(layout.get_info(li));r=kdb.Region(inst.cell.begin_shapes_rec(li)).transformed(tr)
  expected[key]=(expected.get(key,kdb.Region())+r).merged()
for key,r in moved.items():
 layer,datatype=map(int,key.split('/'));candidate.shapes(layout.layer(layer,datatype)).insert(r)
pins=[]
for li in layout.layer_indexes():
 for shape in T.each_shape(li):
  if not shape.is_text():continue
  text=shape.text;dy=delta[band(text.y)];copy=text.transformed(kdb.Trans(0,dy));candidate.shapes(li).insert(copy)
  pins.append({'name':text.string,'layer':str(layout.get_info(li)),'old_xy_dbu':[text.x,text.y],'new_xy_dbu':[copy.x,copy.y]})
assert len(pins)==25
native=pathlib.Path('native');native.mkdir();opts=kdb.SaveLayoutOptions();opts.select_cell(candidate.cell_index());layout.write(str(native/'candidate.gds'),opts)
check=kdb.Layout();check.read(str(native/'candidate.gds'));actual={str(check.get_info(li)):kdb.Region(check.top_cell().begin_shapes_rec(li)).merged() for li in check.layer_indexes()}
keys=set(expected)|set(actual)
def equal(got):return all((got.get(key,kdb.Region())^expected.get(key,kdb.Region())).is_empty() for key in keys)
assert equal(actual)
controls=[]
bad=dict(actual);bad['126/0']=bad['126/0']-kdb.Region(new_boxes[0]);assert not equal(bad);controls.append('delete_real_trunk')
bad=dict(actual);assert not bad['6/0'].is_empty();bad['6/0']=kdb.Region();assert not equal(bad);controls.append('delete_native_contacts')
proof={'status':'GENERATED_REQUIRES_NATIVE_DRC_LVS_FRESH_RC_AND_FROZEN_ELECTRICAL_TESTS','accepted':False,'full_phy_accepted':False,'main_chip_integrated':False,'source_gds_sha256':out['geometry']['sha256'],'candidate_gds_sha256':hashlib.sha256((native/'candidate.gds').read_bytes()).hexdigest(),'old_order':old_order,'candidate_order':new_order,'band_translations_y_dbu':delta,'primitive_child_instances':16,'local_overlays_conserved':True,'serialized_geometry_checked':True,'trunks':trunk_proof,'ports':pins,'controls':controls,'scope':'Complete current650 child geometry and local overlays preserved; 37 real global TM1 trunks rebuilt using exact via incidence. Public pins move with physical bands, so earlier fixed-pin proxy is NOT the new electrical result. Native DRC/LVS and fresh extraction still mandatory.'}
pathlib.Path('out/paired-layout-proof.json').write_text(json.dumps(proof,indent=2))
# Keep source and candidate native geometry exclusively in cloud artifact.
(native/'source.gds').write_bytes(pathlib.Path('source.gds').read_bytes())
