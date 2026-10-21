# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact pump metal/via graph bound geometrically to unsimplified native LVS."""
from pathlib import Path
from collections import Counter,defaultdict
import pya,json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent;P=B/'source'
GDS=P/'layout/layout.gds';DB=P/'flat_lvs/result.lvsdb';OUT=B/'native01';OUT.mkdir()
METALS=[8,10,30,50,67,126,134];VIAS=[19,29,49,66,125,133]
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(GDS)['sha256']=='3b1a16d8e96f0326b430c7c9214e61e723dcb0eee07e70266f30bc8a9ba673e7'
assert json.loads((P/'flat_lvs/audit.json').read_text())['status']=='PASS within comparison scope'
g=pya.Layout();g.read(str(GDS));top=g.cell('nssoc_tx_output8088_parent_v1');assert top is not None;l=pya.LayoutVsSchematic();l.read(str(DB));c=l.netlist().top_circuit();assert c.pin_count()==165
classes=Counter(d.device_class().name for d in c.each_device());assert classes==dict(npn13G2=593,sg13_hv_nmos=2560,sg13_lv_nmos=1408,sg13_lv_pmos=1408,ptap1=1485,ntap1=128,rppd=504,rsil=2),classes
wire=pya.Layout();wire.dbu=g.dbu;wt=wire.create_cell('full_tx_output8088_wires');regions={};mapping={};layers={}
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
e=pya.LayoutToNetlist('TXOUTPUT8088WIRES',g.dbu)
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
for n in c.each_net():
 area=sum(l.shapes_of_net(n,l.layer_by_index(mapping[m]),True).area()for m in active)
 if area:assert n.cluster_id in owners
 ts=terminals.get(n.cluster_id,[]);ps=ports.get(n.cluster_id,[])
 if not ts:assert not area and not ps and n.cluster_id not in owners
 coverage.append(dict(native_cluster=n.cluster_id,name=n.name,metal_area_dbu2=area,wire_components=owners.get(n.cluster_id,[]),device_terminals=ts,public_ports=ps))
assert set(ports)<=set(terminals)
wire.write(str(OUT/'wires.gds'));e.write(str(OUT/'wires.l2n'))
r=dict(status='PASS_TX_OUTPUT8088_METAL_VIA_GRAPH_BOUND_TO_ALL_NATIVE_DEVICES_NO_RC',inputs={str(p):pin(p)for p in [GDS,DB,Path(__file__).resolve()]},native_devices=dict(classes),native_device_count=sum(classes.values()),native_ports=[p.name()for p in c.each_pin()],native_layer_mapping=mapping,layers=layers,wire_components=rows,native_net_coverage=coverage,wire_component_count=len(rows),native_net_count=len(coverage),native_electrical_net_count=len(terminals),native_terminal_count=sum(map(len,terminals.values())),no_wire_geometry_change=True,no_component_union_by_native_label=True,wire_rc_extracted=False,full_pex_qualified=False,substrate_r_modeled=False,outputs={p.name:pin(p)for p in OUT.iterdir()if p.is_file()})
(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(rows),len(coverage),r['native_terminal_count'])
