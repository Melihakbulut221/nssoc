# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact pump metal/via graph bound geometrically to unsimplified native LVS."""
from pathlib import Path
from collections import Counter,defaultdict
import pya,json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent
GDS=P/'parent/layout/nssoc_cdr_pd476_follower_v23.gds';DB=P/'parent/physical/lvs_flat/result.lvsdb';OUT=B/'native05';OUT.mkdir()
METALS=[8,10,30,50,67,126,134];VIAS=[19,29,49,66,125,133]
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(GDS)['sha256']==json.loads((P/'parent/layout/result.json').read_text())['outputs'][GDS.name]
assert json.loads((P/'parent/physical/lvs_flat/audit.json').read_text())['status']=='PASS within comparison scope'
g=pya.Layout();g.read(str(GDS));assert g.cell('nssoc_cdr_pd476_follower_v23') is not None and g.cell('nssoc_cdr_pd476_follower_v23').cell_index() in [cell.cell_index() for cell in g.top_cells()];top=g.cell('nssoc_cdr_pd476_follower_v23');l=pya.LayoutVsSchematic();l.read(str(DB));c=l.netlist().top_circuit();assert c.pin_count()==25
classes=Counter(d.device_class().name for d in c.each_device());assert classes==dict(npn13G2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205),classes
wire=pya.Layout();wire.dbu=g.dbu;wt=wire.create_cell('pump_wires');regions={};mapping={};layers={}
for layer in METALS+VIAS:
 r=pya.Region(top.begin_shapes_rec(g.layer(layer,0))).merged();regions[layer]=r;wt.shapes(wire.layer(layer,0)).insert(r)
 assert (r^pya.Region(wt.begin_shapes_rec(wire.layer(layer,0)))).is_empty()
 layers[layer]=dict(explicitly_empty=r.is_empty(),area_dbu2=r.area(),polygons=r.count(),bbox=str(r.bbox()),source_union_sha256=hashlib.sha256('\n'.join(sorted(poly.to_s()for poly in r.each())).encode()).hexdigest())
active=[m for m in METALS if not regions[m].is_empty()]
for metal in active:
 r=regions[metal];candidates=[]
 for i in l.layer_indexes():
  lr=l.layer_by_index(i)
  if lr.bbox()==r.bbox()and lr.area()==r.area()and(lr^r).is_empty():candidates.append(i)
 assert len(candidates)==1,(metal,candidates)
 mapping[metal]=candidates[0]
e=pya.LayoutToNetlist('PUMPWIRES',g.dbu)
for layer,r in regions.items():
 if not r.is_empty():e.register(r,'gds_'+str(layer));e.connect(r)
for a,v,b in zip(METALS,VIAS,METALS[1:]):
 if not regions[v].is_empty():
  assert not regions[a].is_empty()and not regions[b].is_empty();e.connect(regions[a],regions[v]);e.connect(regions[v],regions[b])
e.extract_netlist();ec=e.netlist().top_circuit();assert len(list(ec.each_device()))==0
rows=[];owners=defaultdict(list);cache={}
for n in ec.each_net():
 pieces={m:e.shapes_of_net(n,regions[m],True)for m in active};m,r=next((m,r)for m,r in pieces.items()if not r.is_empty())
 boxes=[poly.bbox()for poly in r.decompose_trapezoids_to_region().each()if poly.area()==poly.bbox().area()and poly.bbox().width()>2 and poly.bbox().height()>2];assert boxes
 point=boxes[0].center();native=l.probe_net(l.layer_by_index(mapping[m]),point);assert native is not None;nid=native.cluster_id;checks={}
 for metal,piece in pieces.items():
  key=nid,metal
  if key not in cache:cache[key]=l.shapes_of_net(native,l.layer_by_index(mapping[metal]),True)
  assert(piece-cache[key]).is_empty(),('Conductor crosses native net',n.cluster_id,nid,metal)
  checks[metal]=dict(area_dbu2=piece.area(),polygons=piece.count())
 owners[nid].append(n.cluster_id);rows.append(dict(component=n.cluster_id,native_cluster=nid,native_name=native.name,probe_metal=m,probe_dbu=[point.x,point.y],layers=checks))
assert all(len(v)==1 for v in owners.values()),'Native metal net split'
coverage=[];terminals=defaultdict(list);ports=defaultdict(list)
for d in c.each_device():
 for td in d.device_class().terminal_definitions():terminals[d.net_for_terminal(td.id()).cluster_id].append(dict(device=d.id(),model=d.device_class().name,terminal=td.name))
for p in c.each_pin():ports[c.net_for_pin(p.id()).cluster_id].append(p.name())

# The original no-terminal-metal gate is not weakened. Diagnose and remove only
# native components with zero device terminals and zero public pins.
floating=[];removed={layer:pya.Region()for layer in METALS+VIAS}
ec_nets={n.cluster_id:n for n in ec.each_net()}
for n in c.each_net():
 area=sum(l.shapes_of_net(n,l.layer_by_index(mapping[m]),True).area()for m in active)
 ts=terminals.get(n.cluster_id,[]);ps=ports.get(n.cluster_id,[])
 if not area or ts:continue
 assert not ps,'Never remove public interface geometry'
 assert n.cluster_id in owners and len(owners[n.cluster_id])==1
 component=owners[n.cluster_id][0];wn=ec_nets[component];pieces={}
 for layer in METALS+VIAS:
  piece=e.shapes_of_net(wn,regions[layer],True).merged()
  if piece.is_empty():continue
  parent=pya.Region(top.shapes(g.layer(layer,0))).merged()
  assert(piece-parent).is_empty(),('Floating geometry not exclusively parent-owned',n.cluster_id,layer)
  # This condition excludes any native child/device geometry.
  child=pya.Region()
  for instance in top.each_inst():
   child+=pya.Region(instance.cell.begin_shapes_rec(g.layer(layer,0))).transformed(instance.trans)
  assert(piece&child).is_empty(),('Attempt to remove actual child/device metal',n.cluster_id,layer)
  removed[layer]+=piece
  pieces[str(layer)]=dict(area_dbu2=piece.area(),bbox_dbu=str(piece.bbox()),polygons_dbu=[poly.to_s()for poly in piece.each()])
 floating.append(dict(native_cluster=n.cluster_id,native_name=n.name,wire_component=component,device_terminals=ts,public_ports=ps,layers=pieces))
assert floating,'Expected actual floating-metal rejection must be reproduced'
assert len(floating)==len({v['wire_component']for v in floating})
proof=dict(status='DIAGNOSED_NATIVE_FLOATING_PARENT_COMPONENTS_REQUIRES_NEW_PHYSICAL_CHECKS',floating_components=floating,original_wire_components=len(rows),retained_wire_components=len(rows)-len(floating),native_device_census=dict(classes),native_devices=sum(classes.values()),no_device_or_public_terminal_removed=True,source_inputs={str(p):pin(p)for p in [GDS,DB,Path(__file__).resolve()]})
(P/'floating-metal-diagnosis.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(dict(floating_components=len(floating),original_wire_components=len(rows),retained_wire_components=len(rows)-len(floating),bounds=[{k:v['bbox_dbu']for k,v in x['layers'].items()}for x in floating])),flush=True)
before={layer:pya.Region(top.shapes(g.layer(layer,0))).merged()for layer in METALS+VIAS}
oldbbox=top.dbbox();before_text={li:sorted(str(s.text)for s in top.shapes(li).each()if s.is_text())for li in g.layer_indexes()}
instances=sorted((x.cell.name,str(x.dcplx_trans))for x in top.each_inst())
for layer,reg in removed.items():
 if reg.is_empty():continue
 old=before[layer];new=(old-reg).merged()
 assert (new&reg).is_empty()and((new+reg).merged()^old).is_empty()
 top.shapes(g.layer(layer,0)).clear();top.shapes(g.layer(layer,0)).insert(new)
assert top.dbbox()==oldbbox
assert before_text=={li:sorted(str(s.text)for s in top.shapes(li).each()if s.is_text())for li in g.layer_indexes()}
assert instances==sorted((x.cell.name,str(x.dcplx_trans))for x in top.each_inst())
dest=P/'layout';dest.mkdir()
opts=pya.SaveLayoutOptions();opts.select_cell(top.cell_index());g.write(str(dest/GDS.name),opts)
readback=pya.Layout();readback.read(str(dest/GDS.name));actual=readback.cell(top.name)
for layer in METALS+VIAS:
 expected=(before[layer]-removed[layer]).merged()
 assert(expected^pya.Region(actual.shapes(readback.layer(layer,0))).merged()).is_empty()
import shutil
for name in ['schematic.cir',top.name+'.lef']:shutil.copyfile(GDS.parent/name,dest/name)
meta=json.loads((GDS.parent/'result.json').read_text())
meta['floating_metal_cleanup']=proof;meta['status']='GENERATED_PD476_WITH_ONLY_PROVEN_FLOATING_PARENT_METAL_REMOVED'
meta['inputs']={str(p):pin(p)['sha256']for p in [GDS,DB,GDS.parent/'result.json',Path(__file__).resolve()]}
meta['outputs']={p.name:pin(p)['sha256']for p in dest.iterdir()if p.is_file()}
(dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
# Actual device/public connectivity remains protected by the unchanged full
# native DRC/LVS and fault suite; this geometrical cleanup is not that approval.
