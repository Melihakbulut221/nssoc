# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit real terminal metal reference planes; intrinsic body nodes retained."""
from pathlib import Path
from collections import Counter
import hashlib,json,pya
B=Path(__file__).parent
GDS=Path('/dev/shm/nssoc-div4-v7-layout-01/nssoc_clock_div4_v7_layout.gds')
LVS=Path('/dev/shm/nssoc-div4-v7-checks-02/lvs/result.lvsdb')
l=pya.LayoutVsSchematic();l.read(str(LVS));c=l.netlist().top_circuit();devices={d.id():d for d in c.each_device()}
g=pya.Layout();g.read(str(GDS));top=g.top_cell();wire=pya.LayoutToNetlist();wire.read('/dev/shm/nssoc-div4-v7-wire-geometry-02/wires.l2n')
geo=json.loads((B/'device-location-geometry.json').read_text());wg=json.loads((B/'wire-component-geometry.json').read_text());mapping={int(k):v for k,v in wg['native_layer_mapping'].items()}
body={('npn13G2','S'),('rppd','rppd_sub'),('ptap1','WELL')}
rows=[];unresolved=[]
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
for row in geo['devices']:
 d=devices[row['native_id']];cls=d.device_class();cell=g.cell(row['pcell']['cell']);dt=pya.DCplxTrans.from_s(row['pcell']['transform']);tr=pya.ICplxTrans(dt.mag,dt.angle,dt.is_mirror(),round(dt.disp.x/g.dbu),round(dt.disp.y/g.dbu))
 pinboxes=[]
 for idx in g.layer_indices():
  info=g.get_info(idx)
  if info.datatype==2 and info.layer in mapping:
   for s in cell.each_shape(idx):
    if s.is_box():pinboxes.append((info.layer,s.box.transformed(tr)))
 for td in cls.terminal_definitions():
  net=d.net_for_terminal(td.id());r=dict(device=d.id(),model=cls.name,terminal=td.name,native_net=net.name,native_cluster=net.cluster_id)
  if (cls.name,td.name) in body:
   r.update(disposition='UNCHANGED_INTRINSIC_BODY_TERMINAL_NO_ADDED_SUBSTRATE_R',native_geometry=row['terminals'][td.id()]);rows.append(r);continue
  candidates=[]
  if cls.name=='npn13G2':
   # Native npn13G2_code.py MkPin defines C as upper M1, B as lower
   # M1, E as M2 in local coordinates. Select before instance transform.
   local=[s.box for s in cell.each_shape(g.layer(8,2)) if s.is_box()]
   assert len(local)==2
   box=(max(local,key=lambda b:b.center().y) if td.name=='C' else min(local,key=lambda b:b.center().y)) if td.name!='E' else next(s.box for s in cell.each_shape(g.layer(10,2)) if s.is_box())
   candidates=[(10 if td.name=='E' else 8,box.transformed(tr))]
  elif cls.name=='cap_cmim':
   metal=126 if td.name=='mim_top' else 67
   reg=pya.Region(cell.begin_shapes_rec(g.layer(metal,0))).transformed(tr).merged()
   # The native cmim source declares TopMetal1 PLUS / Metal5 MINUS.
   candidates=[(metal,p.bbox()) for p in reg.each() if p.area()==p.bbox().area()]
  else:candidates=pinboxes
  candidates=[(m,b) for m,b in candidates if (pya.Region(b)-l.shapes_of_net(net,l.layer_by_index(mapping[m]),True)).is_empty()]
  # Repeated overlapping pin declarations are one actual electrical access.
  unique={}
  for m,b in candidates:unique.setdefault(m,pya.Region()).insert(b)
  regions=[(m,reg.merged()) for m,reg in unique.items()]
  clusters=set();anchors=[]
  for m,reg in regions:
   for p in reg.decompose_trapezoids_to_region().each():
    box=p.bbox()
    if p.area()!=box.area() or box.width()<4 or box.height()<4:continue
    point=box.center();wn=wire.probe_net(wire.layer_by_name('gds_'+str(m)),point)
    if wn is None:continue
    clusters.add(wn.cluster_id);anchors.append((m,point,box))
  if len(clusters)!=1 or not anchors:
   unresolved.append(dict(**r,candidate_regions=[dict(layer=m,region=str(reg)) for m,reg in regions],wire_components=sorted(clusters)));continue
  # Deterministic point reference plane, not a distributed intrinsic terminal.
  m,point,box=sorted(anchors,key=lambda x:(x[0],x[1].x,x[1].y))[0]
  r.update(disposition='ACTUAL_METAL_POINT_REFERENCE',metal=m,point_dbu=[point.x,point.y],access_box_dbu=[box.left,box.bottom,box.right,box.top],wire_component=next(iter(clusters)))
  owner=next(x for x in wg['wire_components'] if x['component']==r['wire_component']);assert owner['native_cluster']==net.cluster_id
  rows.append(r)
result=dict(status='TERMINAL_REFERENCE_PLANE_CENSUS_ONLY' if not unresolved else 'INCOMPLETE_TERMINAL_REFERENCE_PLANE_CENSUS',
 inputs={str(p):pin(p) for p in [GDS,LVS,B/'device-location-geometry.json',B/'wire-component-geometry.json',Path(__file__),
 Path('/dev/shm/nssoc-div4-v7-wire-geometry-02/wires.l2n'),
 *[Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp')/(name+'_code.py') for name in ('npn13G2','cmim','rppd','ptap1')]]},
 rows=rows,unresolved=unresolved,dispositions=dict(Counter(r['disposition'] for r in rows)),
 native_device_count=91,native_terminal_count=283,declared_terminal_count=len(rows)+len(unresolved),
 substrate_resistance_added=False,device_or_body_node_deletion=False,distributed_intrinsic_terminal_model=False,qualified_pex=False)
assert result['declared_terminal_count']==283
assert not unresolved
assert result['dispositions']==dict(ACTUAL_METAL_POINT_REFERENCE=198,UNCHANGED_INTRINSIC_BODY_TERMINAL_NO_ADDED_SUBSTRATE_R=85)
(B/'terminal-reference-planes.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['dispositions'],'UNRESOLVED',[(r['device'],r['model'],r['terminal']) for r in unresolved])
