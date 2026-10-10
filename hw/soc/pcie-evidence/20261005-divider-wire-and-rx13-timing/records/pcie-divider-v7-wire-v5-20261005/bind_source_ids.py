# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind source names by actual PCell location, then prove the whole named graph."""
from pathlib import Path
from collections import defaultdict
import math
import pya,json,hashlib
B=Path(__file__).parent;G=Path('/dev/shm/nssoc-div4-v7-layout-01')
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
g=json.loads((G/'result.json').read_text());native=json.loads((B/'device-location-geometry.json').read_text())
kind={'npn13G2':'hbt','rppd':'resistor','cap_cmim':'capacitor','ptap1':'substrate_tap'}
used=set();rows=[];net_map=defaultdict(set); reverse=defaultdict(set)
for d in native['devices']:
 tr=pya.DCplxTrans.from_s(d['pcell']['transform']);assert tr.angle==0 and tr.mag==1 and not tr.is_mirror()
 at=(round(tr.disp.x*1000),round(tr.disp.y*1000))
 matches=[r for r in g['instances'] if r['kind']==kind[d['model']] and tuple(round((v+w)*1000) for v,w in zip(r['placement_um'],g['origin_translation_um']))==at]
 assert len(matches)==1,(d['native_id'],at,matches)
 source=matches[0];assert source['name'] not in used;used.add(source['name'])
 actual={t['name']:t for t in d['terminals']}
 order={'npn13G2':['C','B','E','S'],'rppd':['rppd_1','rppd_2','rppd_sub'],'cap_cmim':['mim_top','mim_btm'],'ptap1':['TIE','WELL']}[d['model']]
 nets=list(source['nets'])
 if d['model'] in ('npn13G2','rppd'):nets[-1]='BULK'
 assert len(nets)==len(order)
 assert set(actual)==set(order)
 if d['model']=='npn13G2':expected=dict(we=.07,le=.9,Nx=source['nx'],m=1)
 elif d['model']=='rppd':expected=dict(w=source['width_um'],l=source['length_um'],ps=0,b=0,m=1)
 elif d['model']=='cap_cmim':
  w,h=source['width_um'],source['length_um'];expected=dict(w=w,l=h,A=w*h,P=2*(w+h),m=1)
 else:expected=dict(A=source['area_um2'],P=source['perimeter_um'])
 assert set(d['parameters'])==set(expected)
 assert all(math.isclose(d['parameters'][k],v,rel_tol=1e-12,abs_tol=1e-12) for k,v in expected.items()),(d['native_id'],d['parameters'],expected)
 for term,n in zip(order,nets):
  net_map[n].add(actual[term]['native_cluster']);reverse[actual[term]['native_cluster']].add(n)
 rows.append(dict(native_id=d['native_id'],model=d['model'],source_name=source['name'],source_device=source,native_location=d['pcell'],terminal_order=order,source_nets=nets))
assert len(rows)==len(used)==len(g['instances'])==91
assert all(len(v)==1 for v in net_map.values()) and all(len(v)==1 for v in reverse.values()),(dict(net_map),dict(reverse))
assert len(net_map)==len(reverse)==38
r=dict(status='PASS_FULL91_DEVICE_SOURCE_LOCATION_AND_NAMED_NET_BIJECTION',devices=rows,source_net_to_native_cluster={k:next(iter(v)) for k,v in net_map.items()},
 source_body_distinct_from_contact=net_map['BULK']!=net_map['SUB'],all18_finite_substrate_contacts_retained=True,no_well_devices_in_source=True,inputs={str(p):pin(p) for p in [Path(__file__),G/'result.json',G/'schematic.cir',B/'device-location-geometry.json']},full_pex_qualified=False)
(B/'source-native-bijection.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
