#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replace both actual retime leaves and route their added AVDD ports."""
import argparse,copy,hashlib,json,re,sys
from pathlib import Path
OLD='nssoc_cdr_pd484_localbus_v12';TOP='nssoc_cdr_pd476_follower_v23';LEAF='nssoc_cdr_retime_follower_layout_v23'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 import pya
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 root=Path.cwd();old=out/'baseline/layout';fresh=out/'inputs/rc_retime/layout';dest=out/'layout';dest.mkdir()
 original=json.loads((old/'result.json').read_text());meta=copy.deepcopy(original)
 leaf=json.loads((fresh/'result.json').read_text());previous=json.loads((out/'baseline/inputs/rc_retime/layout/result.json').read_text())
 assert {k:leaf['ports'][k]for k in previous['ports']}==previous['ports']
 assert len(leaf['core_devices'])==4 and leaf['substrate_contacts']==4
 L=pya.Layout();L.read(str(old/(OLD+'.gds')));N=pya.Layout();N.read(str(fresh/(LEAF+'.gds')))
 T=L.cell(OLD);C=L.cell('pd_child_rc_retime');S=N.cell(LEAF)
 assert all(c is not None for c in (T,C,S))and L.dbu==N.dbu==.001
 assert sum(i.cell.name=='pd_child_rc_retime'for i in T.each_inst())==2
 def snapshot(layout,cell):
  shapes={};texts={}
  for li in layout.layer_indexes():
   info=layout.get_info(li);key=(info.layer,info.datatype);r=pya.Region(cell.shapes(li)).merged()
   if not r.is_empty():shapes[key]=r
   ts=sorted(str(s.text)for s in cell.shapes(li).each()if s.is_text())
   if ts:texts[key]=ts
  instances=sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in cell.each_inst())
  return shapes,texts,instances
 before=snapshot(L,T);oldbbox=T.dbbox()
 def rect(s):return pya.DBox(*map(float,re.findall(r'-?\d+(?:\.\d+)?',s)))
 C.clear();C.copy_tree(S)
 for cell in L.each_cell():
  if cell.cell_index()==T.cell_index():continue
  for layer in (8,10,30,50,67,126,134):
   for dt in (2,25):cell.shapes(L.layer(layer,dt)).clear()
 # Native PCells supply actual via enclosures/cuts; no guessed ideal access.
 src=root/'pdk/libs.tech/klayout/python'
 sys.path[:0]=[str(src),str(src/'pycell4klayout-api/source/python')]
 import sg13g2_pycell_lib
 overlay=L.create_cell('cdr_follower_v23_actual_avdd_connections')
 added_routes=[]
 def box(layer,x0,y0,x1,y1):overlay.shapes(L.layer(layer,0)).insert(pya.DBox(x0,y0,x1,y1))
 def via(bottom,top,x,y):
  c=L.create_cell('via_stack','SG13_dev',dict(b_layer=bottom,t_layer=top,vn_columns=2,vn_rows=1,vt1_columns=2,vt1_rows=1,vt2_columns=1,vt2_rows=1))
  assert c is not None and not c.is_empty()
  b=c.dbbox();dx=round((x-b.center().x)/.005)*.005;dy=round((y-b.center().y)/.005)*.005
  overlay.insert(pya.DCellInstArray(c.cell_index(),pya.DTrans(dx,dy)))
  box(126,x-1.6,y-1.6,x+1.6,y+1.6)
 existing=pya.Region(T.begin_shapes_rec(L.layer(126,0))).merged()
 for tag in ('ac','bd'):
  placed=meta['placements'][tag];b=rect(placed['bbox_um']);tr=pya.DTrans(b.left,b.bottom)
  newports={k:str(rect(v).transformed(tr))for k,v in leaf['ports'].items()}
  assert {k:newports[k]for k in placed['ports']}==placed['ports']
  placed['ports']=newports;placed['bbox_um']=str(S.dbbox().transformed(tr))
  pin=rect(newports['avdd']);y=pin.center().y
  rail=pya.Region(pya.DBox(59.2,y-1.6,62.4,y+1.6).to_itype(L.dbu))
  assert (rail-existing).is_empty(),'AVDD connection is not on the actual retained native rail'
  via('TopMetal1','TopMetal2',60.8,y)
  via('Metal5','TopMetal2',987.6,y)
  box(134,59.2,y-1.6,989.2,y+1.6)
  box(67,987.,y-.6,pin.center().x+.6,y+.6)
  added_routes.append(dict(net='avdd',tag=tag,pin='avdd',layer=134,box_um=str(pya.DBox(59.2,y-1.6,989.2,y+1.6)),native_via_centers_um=[[60.8,y],[987.6,y]],original_rail_witness=True))
  node=next(n for n in meta['source_plan']['nodes']if n['tag']==tag)
  node['pins']['avdd']='avdd';node['source_cards']=['xfollower_'+tag]
 assert len(added_routes)==2
 # Flatten only the newly generated overlay into the parent, retaining all old
 # parent metal (including old same-net supply stubs) and every original transform.
 addition={}
 for li in L.layer_indexes():
  info=L.get_info(li);reg=pya.Region(overlay.begin_shapes_rec(li)).merged()
  if reg.is_empty():continue
  assert (info.layer,info.datatype)in {(67,0),(125,0),(126,0),(133,0),(134,0)}
  addition[(info.layer,info.datatype)]=reg
  T.shapes(li).insert(reg)
 assert T.dbbox()==oldbbox
 after=snapshot(L,T)
 assert before[1:]==after[1:]
 for key in set(before[0])|set(after[0]):
  expected=(before[0].get(key,pya.Region())+addition.get(key,pya.Region())).merged()
  assert (expected^after[0].get(key,pya.Region())).is_empty(),('Undeclared parent edit',key)
 T.name=TOP
 opt=pya.SaveLayoutOptions();opt.select_cell(T.cell_index());L.write(str(dest/(TOP+'.gds')),opt)
 R=pya.Layout();R.read(str(dest/(TOP+'.gds')));actual=snapshot(R,R.cell(TOP))
 def equal(a,b):
  assert a[1:]==b[1:]and a[0].keys()==b[0].keys()
  for k in a[0]:assert(a[0][k]^b[0][k]).is_empty()
 equal(after,actual)
 controls=[]
 bad=(dict(actual[0]),actual[1],actual[2]);bad[0][(133,0)]=pya.Region()
 try:equal(after,bad)
 except AssertionError:controls.append('missing_native_supply_via')
 else:raise AssertionError('Missing via accepted')
 bad=(actual[0],actual[1],actual[2][:-1])
 try:equal(after,bad)
 except AssertionError:controls.append('missing_parent_instance')
 else:raise AssertionError('Missing instance accepted')
 lines=(old/'schematic.cir').read_text().splitlines();reference=[];removed={}
 for tag in ('ac','bd'):
  rows=[l for l in lines if l.split()and l.split()[0][1:].startswith(tag+'_')]
  assert len(rows)==12;removed[tag]=rows
 removed_set={l for rows in removed.values()for l in rows}
 reference=[l.replace(OLD,TOP)for l in lines if l not in removed_set and not l.lower().startswith('.ends')]
 leaflines=[l.split()for l in (fresh/'schematic.cir').read_text().splitlines()if l and l[0]in 'QRM']
 assert len(leaflines)==8
 for tag in ('ac','bd'):
  node=next(n for n in meta['source_plan']['nodes']if n['tag']==tag)
  mapping=dict(node['pins'],BULK='BULK')
  for fields in leaflines:
   f=fields.copy();f[0]=f[0][0]+tag+'_'+f[0][1:]
   count=4 if f[0].startswith('Q')else 2 if 'ptap1'in f else 3
   for i in range(1,count+1):f[i]=mapping[f[i]]
   reference.append(' '.join(f))
 reference.append('.ends '+TOP)
 assert sum(bool(l.split())and l[0]in 'QRCM'for l in reference)==476
 (dest/'schematic.cir').write_text('\n'.join(reference)+'\n')
 (dest/(TOP+'.lef')).write_text((old/(OLD+'.lef')).read_text().replace(OLD,TOP))
 census=dict(npn13g2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)
 meta['primitive_census']=census;meta['source_plan']['primitive_census']=census
 meta['source_plan']['expected_devices']=476
 meta['source_plan']['source_cards_consumed']=sum(len(n['source_cards'])for n in meta['source_plan']['nodes'])
 meta['source_plan']['types']['rc_retime']=dict(top=LEAF,devices=8,layer=67)
 meta['routes']+=added_routes
 meta['source_plan']['source_sha256']['cdr_retime_follower_v23.spice']=sha(root/'hw/soc/analog/pcie/cdr_retime_follower_v23.spice')
 meta['status']='GENERATED_PD476_TWO_ACTIVE_RETIME_FOLLOWERS_REQUIRES_FULL_PHYSICAL_RC_AND_ORIGINAL_WAVES'
 proof=dict(status=meta['status'],replaced_instances=['ac','bd'],retained_other_instances=14,external_ports_unchanged=True,old_six_leaf_pin_coordinates_unchanged=True,actual_added_avdd_routes=added_routes,old_parent_shapes_retained=True,retained_same_net_old_supply_stubs_require_fresh_rc=True,removed_reference_cards=removed,new_native_device_census=census,controls=controls,full_phy_accepted=False,qualified_pex=False)
 meta['active_follower_replacement']=proof
 meta['inputs']={str(p):sha(p)for p in [Path(__file__),*[p for q in ('baseline','inputs')for p in (out/q).rglob('*')if p.is_file()],out/'children.json']}
 meta['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()}
 (dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 (out/'replacement-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
