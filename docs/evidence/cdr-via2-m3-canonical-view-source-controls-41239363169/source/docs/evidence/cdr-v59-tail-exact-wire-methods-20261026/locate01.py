# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from collections import Counter
import pya,json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent;G=P/'parent/layout/nssoc_cdr_pd500_resistor_v59.gds';DB=P/'parent/physical/lvs_flat/result.lvsdb'
g=pya.Layout();g.read(str(G));assert g.cell('nssoc_cdr_pd500_resistor_v59') is not None and g.cell('nssoc_cdr_pd500_resistor_v59').cell_index() in [cell.cell_index() for cell in g.top_cells()];leaves=[]
def visit(c,t,path):
 if not list(c.each_inst()):
  pins=[]
  for idx in g.layer_indices():
   info=g.get_info(idx)
   if info.datatype in (2,25):
    for s in c.each_shape(idx):
     if s.is_text():pins.append(dict(layer=str(info),text=s.text.string,point=[s.text.trans.disp.x,s.text.trans.disp.y]))
     elif s.is_box():pins.append(dict(layer=str(info),box=str(s.box)))
  leaves.append(dict(cell=c.name,transform=str(t),bbox=str(c.dbbox().transformed(t)),pins=pins,path=path));return
 for i,inst in enumerate(c.each_inst()):
  assert not inst.is_regular_array();visit(g.cell(inst.cell_index),t*inst.dcplx_trans,path+f'/{inst.cell_index}_{i}')
visit(g.cell('nssoc_cdr_pd500_resistor_v59'),pya.DCplxTrans(),g.cell('nssoc_cdr_pd500_resistor_v59').name);(B/'pcell-inventory01.json').write_text(json.dumps(leaves,indent=2)+'\n')
models=dict(npn13G2='npn13G2',rppd='rppd',ptap1='ptap1',cmim='cap_cmim',nmos='sg13_lv_nmos')
physical=[r for r in leaves if r['cell'].split('$')[0]in models];assert len(physical)==500
l=pya.LayoutVsSchematic();l.read(str(DB));c=l.netlist().top_circuit();body={('npn13G2','S'),('sg13_lv_nmos','B'),('sg13_hv_nmos','B'),('sg13_hv_pmos','B'),('rppd','rppd_sub'),('ptap1','WELL'),('ntap1','WELL')};used=set();rows=[]
for d in c.each_device():
 cls=d.device_class();terminals=[];box=pya.Box()
 for td in cls.terminal_definitions():
  shapes=l.shapes_of_terminal(d.terminal_ref(td.id()));assert shapes;tbox=pya.Box()
  for r in shapes.values():tbox+=r.bbox()
  if(cls.name,td.name)not in body:box+=tbox
  terminals.append(dict(name=td.name,net=d.net_for_terminal(td.id()).name,native_cluster=d.net_for_terminal(td.id()).cluster_id,native_layers=[dict(layer=i,bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=r.count())for i,r in shapes.items()]))
 candidates=[(i,r)for i,r in enumerate(physical)if models[r['cell'].split('$')[0]]==cls.name and(pya.DBox.from_s(r['bbox']).to_itype(g.dbu)&box)==box]
 assert len(candidates)==1,(d.id(),cls.name,str(box),len(candidates));i,r=candidates[0];assert i not in used;used.add(i)
 rows.append(dict(native_id=d.id(),model=cls.name,parameters={p.name:d.parameter(p.id())for p in cls.parameter_definitions()},pcell=r,terminals=terminals))
assert len(used)==500
result=dict(status='PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE',devices=rows,model_census=dict(Counter(r['model']for r in rows)),native_terminal_count=sum(len(r['terminals'])for r in rows),inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [G,DB,Path(__file__).resolve(),B/'pcell-inventory01.json']},qualified_pex=False)
(B/'device-locations01.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['native_terminal_count'])
for kind in models:
 print(kind,next(r['pins']for r in physical if r['cell'].split('$')[0]==kind))
