#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind all124 real tree input legs to all372 native data-base terminals."""
import json,sys,hashlib
from pathlib import Path
import pya
P=Path(sys.argv[1]);out=Path(sys.argv[2])
physical=json.loads((P/'result.json').read_text())
layout=json.loads((P/'layout/result.json').read_text())
source=json.loads((P/'wire96/native05/result.json').read_text())
locations=json.loads((P/'wire96/device-locations01.json').read_text())
anchors=json.loads((P/'wire96/anchors08.json').read_text())
binding=json.loads((P/'binding96/binding01.json').read_text())
assert physical['variant']=='budget_balanced_v5'
assert physical['source_head']=='7a1d1445ffdf55f82b8f6411280fc68719c3d63a'
assert physical['placement_pitch']==dict(name='original',column_um=1000.,row_um=600.,inverse_topology_matches_original=True)
assert layout['outputs']['nssoc_tx_tree32_budget_balanced_v5_core_v1.gds']=='aaf09a52c7f5f9fdd3307c73f9dc0c57966e461a5f2e8ddfd6666fb87900c5d4'
tight=physical.get('placement_pitch',{}).get('name')=='tight'
if tight:
 assert physical['variant']=='budget_high3_trim'
 assert physical['placement_pitch']==dict(name='tight',column_um=700.,row_um=422.,inverse_topology_matches_original=True)
 assert layout['placement_pitch']==dict(column_um=700.,row_um=422.)
wide64=physical.get('return_rail',{}).get('profile')=='wide64'
if wide64:
 assert tight and physical['return_rail']['trunk_and_bus_width_um']==64.
 assert physical['return_rail']['child_stub_width_um']==32.
 assert physical['return_rail']['local_final_strap_width_um']==4.
gds=P/'layout'/('nssoc_tx_tree32_'+physical['variant']+('_tight_return64'if wide64 else'_tight'if tight else'')+'_core_v1.gds')
assert hashlib.sha256(gds.read_bytes()).hexdigest()==layout['outputs'][gds.name]
g=pya.Layout();g.read(str(gds))
l=pya.LayoutVsSchematic();l.read(str(P/'physical/lvs/result.lvsdb'))
layer=l.layer_by_index(source['native_layer_mapping']['134'])
dx,dy=layout['origin_translation_um']
def shifted(box):
 b=pya.DBox.from_s(box);return pya.DBox(b.left+dx,b.bottom+dy,b.right+dx,b.top+dy)
def probe(endpoint):
 macro,port=endpoint.split('.');point=shifted(layout['placements'][macro]['ports'][port]).center()
 point=pya.Point(round(point.x/g.dbu),round(point.y/g.dbu));net=l.probe_net(layer,point)
 assert net is not None
 return dict(endpoint=endpoint,point_dbu=[point.x,point.y],native_net=net.name,native_cluster=net.cluster_id)
def equal(source_endpoint,sink_endpoint):
 a,b=probe(source_endpoint),probe(sink_endpoint)
 assert a['native_cluster']==b['native_cluster'],'Actual endpoint conductor mismatch'
 return a,b
faults=[]
for src,sink in [('a.op','f.an'),('b.op','f.ap')]:
 try:equal(src,sink)
 except AssertionError:faults.append(dict(source=src,sink=sink,rejected=True))
 else:raise AssertionError('Wrong actual physical endpoint accepted')
devices={d['native_id']:d for d in locations['devices']}
result=dict(status='RUNNING',modes={'compact':{},'wire':{}},references={},actual_endpoint_faults=faults)
used=set()
for node in physical['plan']['nodes']:
 macro=node['label'];box=shifted(layout['placements'][macro]['bbox_um'])
 for bank,label in zip(('a','b'),node['inputs'],strict=True):
  for suffix,childout in [('p','op'),('n','on')]:
   key=label+suffix;assert key not in result['references']
   sink=probe(macro+'.'+bank+suffix)
   if label.startswith('d'):
    assert sink['native_net']==key and key in binding['native_ports']
    endpoints=[sink]
   else:endpoints=list(equal(label+'.'+childout,macro+'.'+bank+suffix))
   rows=[]
   for r in anchors['rows']:
    if r['model']!='npn13G2' or r['terminal']!='B' or r['native_cluster']!=sink['native_cluster']:continue
    device_box=pya.DBox.from_s(devices[r['device']]['pcell']['bbox'])
    if (device_box & box)!=device_box:continue
    assert r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE'
    rows.append(r)
   assert len(rows)==3 and len({r['device'] for r in rows})==3
   for r in rows:
    assert r['device'] not in used;used.add(r['device'])
   result['references'][key]=dict(endpoints=endpoints,intrinsic_terminals=rows)
   compact_node=binding['node_map'][sink['native_net']].lower()
   # Public data pins are bound at the bench scope; internal nets stay hierarchical.
   result['modes']['compact'][key]=[compact_node if compact_node in binding['native_ports'] else 'xtree.'+compact_node]
   result['modes']['wire'][key]=sorted('xtree.'+r['wire_anchor'].lower() for r in rows)
assert len(result['references'])==124 and len(used)==372
for mode in ('compact','wire'):
 rows=[p for v in result['modes'][mode].values() for p in v]
 assert len(rows)==len(set(rows))==(124 if mode=='compact' else 372)
result['status']='PASS_ALL124_PHYSICAL_INPUT_LEGS_AND372_DATA_BASES'
result['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),P/'result.json',P/'layout/result.json',gds,P/'physical/lvs/result.lvsdb',P/'wire96/native05/result.json',P/'wire96/device-locations01.json',P/'wire96/anchors08.json',P/'binding96/binding01.json']}
out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
