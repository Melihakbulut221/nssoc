# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind every unsimplified native device to an actual unchanged PCell location."""
from pathlib import Path
from collections import Counter
import json,pya,hashlib
B=Path(__file__).parent
l=pya.LayoutVsSchematic();l.read('/dev/shm/nssoc-div4-v7-wire-native-01/result.lvsdb');c=l.netlist().top_circuit()
source=json.loads((B/'native-pcell-inventory.json').read_text())
models=dict(npn13G2='npn13G2',rppd='rppd',cmim='cap_cmim',ptap1='ptap1')
leaves=[r for r in source if r['cell'].split('$')[0] in models]
assert len(leaves)==91 and len(source)==678
assert Counter(r['cell'].split('$')[0] for r in source)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=587)
body={("npn13G2","S"),("rppd","rppd_sub"),("ptap1","WELL")}
used=set();rows=[]
assert Counter(d.device_class().name for d in c.each_device())==dict(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)
for d in c.each_device():
 cls=d.device_class();terminals=[];box=pya.Box()
 for t in cls.terminal_definitions():
  shapes=l.shapes_of_terminal(d.terminal_ref(t.id()));assert shapes
  tbox=pya.Box()
  for r in shapes.values():tbox+=r.bbox()
  if (cls.name,t.name) not in body:box+=tbox
  terminals.append(dict(name=t.name,net=d.net_for_terminal(t.id()).name,native_cluster=d.net_for_terminal(t.id()).cluster_id,
                        native_layers=[dict(layer=i,bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=r.count()) for i,r in shapes.items()]))
 candidates=[(i,r) for i,r in enumerate(leaves) if models[r['cell'].split('$')[0]]==cls.name and (pya.DBox.from_s(r['bbox']).to_itype(.001) & box) == box]
 assert len(candidates)==1,(d.id(),cls.name,str(box),len(candidates))
 i,r=candidates[0];assert i not in used;used.add(i)
 rows.append(dict(native_id=d.id(),model=cls.name,parameters={p.name:d.parameter(p.id()) for p in cls.parameter_definitions()},pcell=r,terminals=terminals,enclosure_basis='All non-body native terminal shapes. Shared body regions are preserved but cannot locate one device.'))
assert len(used)==len(leaves)==91
result=dict(status='ALL_91_NATIVE_UNSIMPLIFIED_DEVICES_HAVE_UNIQUE_ACTUAL_PCELL_ENCLOSURE',
 device_count=len(rows),physical_terminal_count=sum(len(r['terminals']) for r in rows),
 model_census=dict(Counter(r['model'] for r in rows)),devices=rows,
 method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 inputs_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [B/'native-pcell-inventory.json',Path('/dev/shm/nssoc-div4-v7-wire-native-01/result.lvsdb')]},
 terminal_to_metal_reference_planes_complete=False,pex_qualified=False,
 limitation='PCell enclosure is a location witness, not by itself a proof of each terminal contact path or an accepted RC model.')
(B/'device-location-geometry.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'],result['physical_terminal_count'])
