# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import pya,json
from collections import Counter
from pathlib import Path
l=pya.Layout();l.read('/dev/shm/nssoc-div4-v7-power-v2-layout-01/nssoc_clock_div4_v7_power_v2_layout.gds')
rows=[]
def visit(c,t,path):
 if not list(c.each_inst()):
  pins=[]
  for idx in l.layer_indices():
   info=l.get_info(idx)
   if info.datatype in (2,25):
    for sh in c.each_shape(idx):
     if sh.is_text():pins.append(dict(layer=str(info),text=sh.text.string))
     elif sh.is_box():pins.append(dict(layer=str(info),box=str(sh.box)))
  rows.append(dict(cell=c.name,transform=str(t),bbox=str(c.dbbox().transformed(t)),pins=pins,path=path))
  return
 for i,inst in enumerate(c.each_inst()):
  assert not inst.is_regular_array()
  visit(l.cell(inst.cell_index),t*inst.dcplx_trans,path+f'/{inst.cell_index}_{i}')
visit(l.top_cell(),pya.DCplxTrans(),l.top_cell().name)
assert len(rows)==725
assert Counter(r['cell'].split('$')[0] for r in rows)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=634)
print('COUNT',len(rows),Counter(r['cell'].split('$')[0] for r in rows))
seen=set()
for r in rows:
 k=r['cell'].split('$')[0]
 if k not in seen:print(json.dumps(r));seen.add(k)
Path(__file__).with_name('native-pcell-inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
