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
candidate=physical
assert candidate['source_head']=='4e9d1b6ecca60dd61b808a9d54de185f190f827c'
assert candidate['status']=='PASS_TX_FOUR_P4_NATIVE_DRIVE3_PHYSICAL_REQUIRES_FRESH_RC_AND_LOADED_GATES'
assert hashlib.sha256((P/'result.json').read_bytes()).hexdigest()=='f351c3ab008b764155594fe395f83b319ca384c32073c1106d7bebbb508319cc'
assert candidate['geometry_delta']['candidate_gds_sha256']=='d202185d3691cd7778b8040492bab73492f44a1cfb0896c5f0b8f31350e6bdff'
assert candidate['geometry_delta']['original_master_drawings_unchanged']and candidate['geometry_delta']['parent_drawings_routes_and_pins_unchanged']
# Original topology is separately pinned; every probe below uses the new GDS/LVS.
wirebase=json.loads((P/'source/result.json').read_text())
assert hashlib.sha256((P/'source/result.json').read_bytes()).hexdigest()=='8a9da85ef2508a72a0f26722d9e5b5f9a5c8bfb3d88e5f69e4ae2d36c6a17e7a'
basepath=Path(__file__).resolve().parents[1]/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json'
basepin=json.loads(basepath.read_text())
assert basepin['run']==39304550527 and basepin['summary_sha256']=='03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d'
physical=basepin['report']
assert wirebase['physical_source']['summary_sha256']==basepin['summary_sha256']
assert candidate['physical_source']['summary_sha256']=='8a9da85ef2508a72a0f26722d9e5b5f9a5c8bfb3d88e5f69e4ae2d36c6a17e7a'
assert layout==candidate['layout']
for key in ('ports','bbox_um','origin_translation_um','signal_routes'):
 assert layout[key]==wirebase['layout'][key],key
changes={q['tag']:q for q in candidate['geometry_delta']['changes']}
assert set(changes)=={'p4_0','p4_1','p4_2','p4_3'}
assert set(layout['placements'])==set(wirebase['layout']['placements'])
for tag,before in wirebase['layout']['placements'].items():
 after=layout['placements'][tag]
 if tag not in changes:assert after==before
 else:
  q=changes[tag]
  assert q['public_pin_rectangles_identical']and q['before_transform']==before['transform']and q['before_bbox']==before['bbox_um']
  assert after==dict(before,kind='pre',transform=q['after_transform'],bbox_um=q['after_bbox'])
assert physical['variant']=='budget_balanced_v5'
assert physical['source_head']=='5cbdd0d6eebd458ae85af5c631f5165afba1dd8f'
assert physical['placement_pitch']==dict(name='compact_columns',column_um=700.,row_um=600.,inverse_topology_matches_original=True)
assert layout['outputs']['nssoc_tx_tree32_budget_balanced_v5_timing_priority_core_v1.gds']=='d202185d3691cd7778b8040492bab73492f44a1cfb0896c5f0b8f31350e6bdff'
tight=physical.get('placement_pitch',{}).get('name')=='tight'
if tight:
 assert physical['variant']=='budget_high3_trim'
 assert physical['placement_pitch']==dict(name='tight',column_um=700.,row_um=422.,inverse_topology_matches_original=True)
 assert layout['placement_pitch']==dict(column_um=700.,row_um=422.)
wide64=physical.get('return_rail',{}).get('profile')=='wide64'
assert wide64
if wide64:
 assert not tight and physical['return_rail']['trunk_and_bus_width_um']==64.
 assert physical['return_rail']['child_stub_width_um']==32.
 assert physical['return_rail']['local_final_strap_width_um']==6.
gds=P/'layout'/('nssoc_tx_tree32_'+physical['variant']+('_timing_priority'if wide64 else'_tight'if tight else'')+'_core_v1.gds')
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
result['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),basepath,P/'result.json',P/'source/result.json',P/'layout/result.json',gds,P/'physical/lvs/result.lvsdb',P/'wire96/native05/result.json',P/'wire96/device-locations01.json',P/'wire96/anchors08.json',P/'binding96/binding01.json']}
out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
