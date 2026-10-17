# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact metal/via-only component census bound to native unsimplified LVS."""
from pathlib import Path
from collections import Counter,defaultdict
import pya,json,hashlib,time
B=Path(__file__).parent
GDS=Path('/dev/shm/nssoc-div4-v10-tail-v1-layout-01/nssoc_clock_div4_v10_tail_v1_layout.gds')
DB=Path('/dev/shm/nssoc-div4-v10-tail-v1-wire-native-01/result.l2n')
OUT=Path('/dev/shm/nssoc-div4-v10-tail-v1-wire-geometry-01');OUT.mkdir()
METALS=[8,10,30,50,67,126,134];VIAS=[19,29,49,66,125,133]
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
g=pya.Layout();g.read(str(GDS));top=g.top_cell()
l=pya.LayoutToNetlist();l.read(str(DB));c=l.netlist().top_circuit()
assert c.pin_count()==7
classes=Counter(d.device_class().name for d in c.each_device())
assert classes==dict(npn13G2=34,ptap1=18,rppd=33,cap_cmim=6),classes
wire=pya.Layout();wire.dbu=g.dbu;wt=wire.create_cell('bank_wires')
regions={};mapping={};layers={}
for layer in METALS+VIAS:
 r=pya.Region(top.begin_shapes_rec(g.layer(layer,0))).merged();regions[layer]=r
 wt.shapes(wire.layer(layer,0)).insert(r);assert (r^pya.Region(wt.begin_shapes_rec(wire.layer(layer,0)))).is_empty()
 layers[layer]=dict(explicitly_empty=r.is_empty(),area_dbu2=r.area(),polygons=r.count(),bbox=str(r.bbox()),source_union_sha256=hashlib.sha256('\n'.join(sorted(poly.to_s() for poly in r.each())).encode()).hexdigest())
# Empty layers remain explicitly inventoried; no nonempty polygon is omitted.
ACTIVE_METALS=[m for m in METALS if not regions[m].is_empty()]
assert ACTIVE_METALS==[8,10,30,50,67,126,134]
assert not regions[134].is_empty() and not regions[133].is_empty()
for metal in ACTIVE_METALS:
 r=regions[metal];a=r.area();box=r.bbox();candidates=[]
 for i in l.layer_indexes():
  lr=l.layer_by_index(i)
  if lr.bbox()==box and lr.area()==a and (lr^r).is_empty():candidates.append(i)
 assert len(candidates)==1,(metal,candidates)
 mapping[metal]=candidates[0]
e=pya.LayoutToNetlist('BANKWIRES',g.dbu)
for layer,r in regions.items():
 if not r.is_empty():e.register(r,'gds_'+str(layer));e.connect(r)
for a,v,b in zip(METALS,VIAS,METALS[1:]):
 if not regions[v].is_empty():
  assert not regions[a].is_empty() and not regions[b].is_empty()
  e.connect(regions[a],regions[v]);e.connect(regions[v],regions[b])
e.extract_netlist();ec=e.netlist().top_circuit()
assert len(list(ec.each_device()))==0
rows=[];owners=defaultdict(list);cache={}
for n in ec.each_net():
 pieces={m:e.shapes_of_net(n,regions[m],True) for m in ACTIVE_METALS}
 first=next((m,r) for m,r in pieces.items() if not r.is_empty());m,r=first
 # A native interior point obtained from exact rectangular decomposition.
 boxes=[poly.bbox() for poly in r.decompose_trapezoids_to_region().each() if poly.area()==poly.bbox().area() and poly.bbox().width()>2 and poly.bbox().height()>2]
 assert boxes,'No exact rectangular interior for conductor probe'
 point=boxes[0].center();native=l.probe_net(l.layer_by_index(mapping[m]),point)
 assert native is not None
 nid=native.cluster_id
 checks={}
 for metal,piece in pieces.items():
  key=(nid,metal)
  if key not in cache:cache[key]=l.shapes_of_net(native,l.layer_by_index(mapping[metal]),True)
  assert (piece-cache[key]).is_empty(),('Wire component crosses native device/net boundary',n.cluster_id,nid,metal)
  checks[metal]=dict(area_dbu2=piece.area(),polygons=piece.count())
 owners[nid].append(n.cluster_id)
 rows.append(dict(component=n.cluster_id,native_cluster=nid,native_name=native.name,probe_metal=m,probe_dbu=[point.x,point.y],layers=checks))
assert all(len(v)==1 for v in owners.values()), 'One native metal net split into multiple physical conductors'
# Complete native metal coverage, including nets that are not public ports.
coverage=[]
terminal_members=defaultdict(list);public_members=defaultdict(list)
for d in c.each_device():
 for td in d.device_class().terminal_definitions():
  terminal_members[d.net_for_terminal(td.id()).cluster_id].append(dict(device=d.id(),model=d.device_class().name,terminal=td.name))
for port in c.each_pin():public_members[c.net_for_pin(port.id()).cluster_id].append(port.name())
assert sum(len(v) for v in terminal_members.values())==283
assert sum(len(v) for v in public_members.values())==7
assert len(terminal_members)==38
for n in c.each_net():
 a=sum(l.shapes_of_net(n,l.layer_by_index(mapping[m]),True).area() for m in ACTIVE_METALS)
 if a:assert n.cluster_id in owners,(n.name,n.cluster_id,a)
 terminals=terminal_members.get(n.cluster_id,[]);ports=public_members.get(n.cluster_id,[])
 if not terminals:assert not a and not ports and n.cluster_id not in owners,('Unbound real native net',n.cluster_id,n.name,a,ports)
 coverage.append(dict(native_cluster=n.cluster_id,name=n.name,metal_area_dbu2=a,wire_components=owners.get(n.cluster_id,[]),device_terminals=terminals,public_ports=ports,classification='ELECTRICAL_DEVICE_TERMINAL_NET' if terminals else 'RETAINED_AUXILIARY_NO_METAL_DEVICE_TERMINAL_OR_PUBLIC_PIN'))
assert len(rows)==37 and len(coverage)==72
assert len({r['native_cluster'] for r in coverage})==72
assert {r['native_cluster'] for r in coverage if r['device_terminals']}==set(terminal_members)
assert set(public_members)<=set(terminal_members)
aux=[r for r in coverage if not r['device_terminals']]
assert len(aux)==34 and all(not r['metal_area_dbu2'] and not r['wire_components'] and not r['public_ports'] for r in aux)
body=[r for r in coverage if r['device_terminals'] and not r['metal_area_dbu2']]
assert len(body)==1 and len(body[0]['device_terminals'])==85 and not body[0]['public_ports']
assert all((t['model'],t['terminal']) in {('npn13G2','S'),('rppd','rppd_sub'),('ptap1','WELL')} for t in body[0]['device_terminals'])
assert set(owners)==set(terminal_members)-{body[0]['native_cluster']}
wire.write(str(OUT/'wires.gds'));e.write(str(OUT/'wires.l2n'))
result=dict(status='GEOMETRY_ONLY_ALL_METAL_VIA_COMPONENTS_BOUND_TO_NATIVE_LVS_NO_RC_YET',method=pin(__file__),inputs={str(p):pin(p) for p in [GDS,DB]},
 native_devices=dict(classes),native_device_count=sum(classes.values()),native_ports=[p.name() for p in c.each_pin()],
 native_layer_mapping=mapping,layers=layers,wire_components=rows,native_net_coverage=coverage,
 native_electrical_net_count=len(terminal_members),retained_auxiliary_native_net_count=len(aux),raw_native_clusters_purged=False,
 wire_component_count=len(rows),native_net_count=len(coverage),native_metal_net_count=sum(bool(r['metal_area_dbu2']) for r in coverage),
 no_wire_geometry_change=True,no_component_union_by_native_label=True,no_device_deleted_from_native_graph=True,
 rc_qualified=False,full_pex_qualified=False,substrate_r_modeled=False,
 outputs={p.name:pin(p) for p in OUT.iterdir() if p.is_file()})
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');(B/'wire-component-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],len(rows),len(coverage),[(r['name'],len(r['wire_components'])) for r in coverage if len(r['wire_components'])>1])
