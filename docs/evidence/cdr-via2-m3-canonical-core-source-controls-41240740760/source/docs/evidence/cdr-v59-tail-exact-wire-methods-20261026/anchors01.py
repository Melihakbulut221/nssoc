# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind metal reference points to every actual pump intrinsic terminal."""
from pathlib import Path
from collections import Counter
import pya,json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent;G=P/'parent/layout/nssoc_cdr_pd500_resistor_v59.gds';DB=P/'parent/physical/lvs_flat/result.lvsdb'
g=pya.Layout();g.read(str(G));assert g.cell('nssoc_cdr_pd500_resistor_v59') is not None and g.cell('nssoc_cdr_pd500_resistor_v59').cell_index() in [cell.cell_index() for cell in g.top_cells()];top=g.cell('nssoc_cdr_pd500_resistor_v59');l=pya.LayoutVsSchematic();l.read(str(DB));c=l.netlist().top_circuit();devs={d.id():d for d in c.each_device()};w=pya.LayoutToNetlist();w.read(str(B/'native05/wires.l2n'))
recovered=json.loads((B/'source-pins.json').read_text())['cells']
geo=json.loads((B/'device-locations01.json').read_text());wg=json.loads((B/'native05/result.json').read_text());mapping={int(k):v for k,v in wg['native_layer_mapping'].items()}
body={('npn13G2','S'),('sg13_lv_nmos','B'),('sg13_hv_nmos','B'),('sg13_hv_pmos','B'),('rppd','rppd_sub'),('ptap1','WELL'),('ntap1','WELL')};poly=pya.Region(top.begin_shapes_rec(g.layer(5,0))).merged();contacts=pya.Region(top.begin_shapes_rec(g.layer(6,0))).merged();metal1=pya.Region(top.begin_shapes_rec(g.layer(8,0))).merged();rows=[];anchors=[]
def witness(label,metal,point,nid,detail):
 wn=w.probe_net(w.layer_by_name('gds_'+str(metal)),point);assert wn is not None
 owner=next(x for x in wg['wire_components']if x['component']==wn.cluster_id);assert owner['native_cluster']==nid,(label,nid,owner)
 a=dict(label=label,metal=metal,point_dbu=[point.x,point.y],wire_component=wn.cluster_id,native_cluster=nid,detail=detail);anchors.append(a);return a
for row in geo['devices']:
 d=devs[row['native_id']];cls=d.device_class();cell=g.cell(row['pcell']['cell']);dt=pya.DCplxTrans.from_s(row['pcell']['transform']);tr=pya.ICplxTrans(dt.mag,dt.angle,dt.is_mirror(),round(dt.disp.x/g.dbu),round(dt.disp.y/g.dbu))
 localpins=[(m,pya.Box(*b))for m,b in recovered.get(cell.name,{}).get('pins',[])]
 pins=[(m,b.transformed(tr))for m,b in localpins if m in mapping]
 for td in cls.terminal_definitions():
  net=d.net_for_terminal(td.id());r=dict(device=d.id(),model=cls.name,terminal=td.name,native_cluster=net.cluster_id,native_net=net.name)
  if(cls.name,td.name)in body:
   r['disposition']='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE';rows.append(r);continue
  shapes=l.shapes_of_terminal(d.terminal_ref(td.id()));native=pya.Region()
  for region in shapes.values():native+=region
  if cls.name=='npn13G2':
   local=[b for m,b in localpins if m==8];assert len(local)==2
   if td.name=='E':
    emitter=[b for m,b in localpins if m==10];assert len(emitter)==1;box=emitter[0];metal=10
   else:
    assert td.name in ('C','B');box=(max if td.name=='C'else min)(local,key=lambda b:b.center().y);metal=8
   candidates=[(metal,box.transformed(tr))]
  elif cls.name in ('sg13_lv_nmos','sg13_hv_nmos','sg13_hv_pmos'):
   if td.name in ('S','D'):
    # Distinguish physical source/drain even when electrically shorted.
    candidates=[(m,b)for m,b in pins if not(pya.Region(b)&native).is_empty()]
   else:
    assert td.name=='G';gatepoly=poly.interacting(native);assert gatepoly.count()==1
    gatecontacts=contacts.inside(gatepoly);assert gatecontacts.count()==1
    candidates=[(8,p.bbox())for p in gatecontacts.each()if(pya.Region(p)-metal1).is_empty()]
  elif cls.name=='cap_cmim':
   m=126 if td.name=='mim_top'else 67;plate=pya.Region(cell.begin_shapes_rec(g.layer(m,0))).transformed(tr).merged();candidates=[(m,p.bbox())for p in plate.each()if p.area()==p.bbox().area()]
  else:candidates=pins
  candidates=[(m,b)for m,b in candidates if(pya.Region(b)-l.shapes_of_net(net,l.layer_by_index(mapping[m]),True)).is_empty()]
  assert candidates,(d.id(),cls.name,td.name)
  # All candidate points must belong to the same native conductor.
  seen=[]
  for m,b in candidates:
   p=b.center();wn=w.probe_net(w.layer_by_name('gds_'+str(m)),p);assert wn is not None;seen.append(wn.cluster_id)
  assert len(set(seen))==1
  m,box=sorted(candidates,key=lambda a:(a[0],a[1].center().x,a[1].center().y))[0]
  a=witness(f'T{d.id():03d}_{td.name}',m,box.center(),net.cluster_id,r)
  r.update(disposition='ACTUAL_TERMINAL_METAL_POINT_REFERENCE',metal=m,point_dbu=a['point_dbu'],wire_component=a['wire_component']);rows.append(r)
record=json.loads((P/'parent/layout/result.json').read_text());metals=dict(Metal1=8,Metal2=10,Metal3=30,Metal4=50,Metal5=67,TopMetal1=126,TopMetal2=134)
for name,r in sorted(record['ports'].items()):
 m=134;box=pya.DBox.from_s(r).to_itype(g.dbu);assert(pya.Region(box)-pya.Region(top.begin_shapes_rec(g.layer(m,2)))).is_empty()
 pin=next(p for p in c.each_pin()if p.name()==name);net=c.net_for_pin(pin.id());witness('P_'+name,m,box.center(),net.cluster_id,dict(public_port=name))
assert len(rows)==1446 and len(anchors)==978
result=dict(status='PASS_1446_NATIVE_TERMINALS_WITH_953_METAL_AND_493_BODY_REFERENCES',rows=rows,anchors=anchors,dispositions=dict(Counter(r['disposition']for r in rows)),public_ports=25,inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [G,DB,Path(__file__).resolve(),B/'device-locations01.json',B/'native05/result.json',B/'native05/wires.l2n',P/'parent/layout/result.json']},distributed_intrinsic_terminal_model=False,wire_rc_extracted=False,full_pex_qualified=False)
(B/'anchors03.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['dispositions'])
