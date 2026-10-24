# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind every wire reference point to original native source geometry."""
from pathlib import Path
import hashlib,json,pya
B=Path(__file__).parent
P=B
W=Path('/dev/shm/nssoc-div4-v9-bias-v1-wire-geometry-01')
G=Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01')
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
assert pin(G/'nssoc_clock_div4_v9_bias_v1_layout.gds')['sha256']=='471d53ef06f4a5c123aa9c41bb773294bb1db0f827059855a1a034d6c1c0924d'
v=json.loads((P/'wire-component-geometry.json').read_text());t=json.loads((P/'terminal-reference-planes.json').read_text())
for n,expected in v['outputs'].items():assert pin(W/n)==expected,(n,expected)
for n,expected in t['inputs'].items():assert pin(n)==expected,n
record=json.loads((G/'result.json').read_text())
layout=pya.Layout();layout.read(str(G/'nssoc_clock_div4_v9_bias_v1_layout.gds'));top=layout.top_cell()
e=pya.LayoutToNetlist();e.read(str(W/'wires.l2n'))
components={r['component']:r for r in v['wire_components']};assert len(components)==37
anchors=[]
def add(label,metal,xy,component,kind,detail):
 n=e.probe_net(e.layer_by_name('gds_'+str(metal)),pya.Point(*xy))
 assert n is not None and n.cluster_id==component,(label,metal,xy,component)
 assert label not in {r['label'] for r in anchors}
 anchors.append(dict(label=label,metal=metal,point_dbu=xy,wire_component=component,kind=kind,detail=detail))
# No auxiliary component labels: only actual intrinsic and public terminals.
body=[]
for i,r in enumerate(t['rows']):
 if r['disposition']=='ACTUAL_METAL_POINT_REFERENCE':add(f'T{i:04d}',r['metal'],r['point_dbu'],r['wire_component'],'INTRINSIC_DEVICE_TERMINAL_REFERENCE',r)
 else:body.append(r)
metals=dict(Metal1=8,Metal2=10,Metal3=30,Metal4=50,Metal5=67,TopMetal1=126,TopMetal2=134)
assert set(record['ports'])==set(v['native_ports'])
for i,(name,r) in enumerate(sorted(record['ports'].items())):
 metal=metals[r['layer']];box=pya.DBox(*r['rect_um']).to_itype(layout.dbu);point=box.center()
 actual=pya.Region(top.begin_shapes_rec(layout.layer(metal,2)))
 assert (pya.Region(box)-actual).is_empty(),('Missing public pin rectangle',name)
 texts=[s.text for s in top.each_shape(layout.layer(metal,25)) if s.is_text() and s.text.string==name]
 assert len(texts)==1 and box.contains(texts[0].trans.disp),('Missing public pin label',name)
 n=e.probe_net(e.layer_by_name('gds_'+str(metal)),point);assert n is not None
 c=components[n.cluster_id];assert c['native_name']==name,(name,c)
 add(f'P{i:03d}',metal,[point.x,point.y],n.cluster_id,'PUBLIC_PORT_REFERENCE',dict(name=name,rect_dbu=[box.left,box.bottom,box.right,box.top]))
assert len(anchors)==205 and len(body)==85
r=dict(status='PASS_EXACT_GEOMETRY_REFERENCE_POINTS_ONLY',anchors=anchors,unmodeled_body_well_terminals=body,
 source_geometry=pin(W/'wires.gds'),source_native_device_count=91,source_public_ports=7,source_wire_components=37,
 actual_metal_terminals=198,body_well_terminals=85,substrate_resistance_modeled=False,
 inputs={str(p):pin(p) for p in [Path(__file__),P/'wire-component-geometry.json',P/'terminal-reference-planes.json',G/'result.json',G/'nssoc_clock_div4_v9_bias_v1_layout.gds',W/'wires.gds',W/'wires.l2n']})
(B/'anchors.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],len(anchors),len(body))
