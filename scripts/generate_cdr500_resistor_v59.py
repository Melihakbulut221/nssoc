#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Four real rppd replacements in one isolated arm of the qualified CDR500.

Only the frozen historical native PCell is used. This generates a candidate;
all full physical, wire, MIM, RC and original electrical gates remain required.
"""
import argparse, copy, hashlib, json, os, re, shutil, sys
from pathlib import Path
OLD='nssoc_cdr_pd500_input_access_v58'
TOP='nssoc_cdr_pd500_resistor_v59'
SUMMARY_SHA='c757b2d7416031b94f625591f8568a08ff61a60d62ec02c5822325083827515c'
GDS_SHA='c51ba01ba4c94a4fd59bb4a7462386b474818caf26739e6bb35dbbd9a38ce125'
RPPD_SHA='58d53384ef0bb92a4fa413d3c92e8dcbcb8f422c5205da9260129049f07f1d6b'
GEOMETRY_SHA='479a648a1d25678af42ebe495ae6cd855e8441fb071f49817972529eee5713e2'
METALS=(8,10,30,50,67,126,134)
ARMS={
 'cd_shunt':dict(kind='sampler_cd',tags=['sc','sd'],names=['DN','DP'],
  ids=[184,185,222,223],width=4.,old_length=7.4,new_length=5.),
 'ab_hold':dict(kind='sampler',tags=['sa','sb'],names=['S_RN','S_RP'],
  ids=[191,194,202,205],width=32.,old_length=2.6,new_length=2.),
}
def sha(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def nums(value):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',value)))
def reference(text,arm,child=False):
 a=ARMS[arm];targets={'R'+n for n in a['names']}if child else {'R'+t+'_'+n for t in a['tags']for n in a['names']}
 lines=text.splitlines(keepends=True);changed=[]
 for i,line in enumerate(lines):
  f=line.split()
  if not f or f[0]not in targets:continue
  assert 'rppd'in f and f.count('w='+format(a['width'],'g')+'u')==1
  old='l='+format(a['old_length'],'g')+'u';new='l='+format(a['new_length'],'g')+'u'
  assert f.count(old)==1 and 'b=0'in f and 'm=1'in f
  # Keep all whitespace, terminal spellings and unrelated reference bytes.
  match=list(re.finditer(r'(?<!\S)'+re.escape(old)+r'(?!\S)',line));assert len(match)==1
  q=match[0];lines[i]=line[:q.start()]+new+line[q.end():];changed.append(f[0])
 assert set(changed)==targets and len(changed)==len(targets)
 result=''.join(lines)
 return result,sorted(changed)
def validate_summary(s):
 assert s['source_head']=='9e7f3d3dd55ec452dfbb27520a73b67f5078067a'
 assert s['status']=='PASS_PD500_V58_OWNED_ACCESS_FULL_PHYSICAL_AND_STRICT_WIRES_REQUIRES_FRESH_MIM_RC'
 assert s['sources_unchanged']and s['outputs']['parent/layout/'+OLD+'.gds']==GDS_SHA
 assert s['device_locations']['status']=='PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE'
 assert len(s['device_locations']['devices'])==500
 assert s['strict_wire_graph']['native_device_count']==500
 assert s['strict_wire_graph']['native_terminal_count']==1446
 assert s['anchors']['logical_anchor_count']==978 and s['anchors']['public_ports']==25
 for arm,a in ARMS.items():
  rows=[d for d in s['device_locations']['devices']if d['native_id']in a['ids']]
  assert len(rows)==4 and {d['native_id']for d in rows}==set(a['ids'])
  for d in rows:
   assert d['model']=='rppd'
   assert d['parameters']==dict(w=a['width'],l=a['old_length'],ps=0.,b=0.,m=1.)
   assert [t['name']for t in d['terminals']]==['rppd_1','rppd_2','rppd_sub']
   assert d['pcell']['transform'].startswith('r0 *1 ')
 return True
def generate(source,summary,pdk,parent,arm):
 import pya
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 assert arm in ARMS and not parent.exists()
 assert sha(summary)==SUMMARY_SHA
 s=json.loads(summary.read_text());validate_summary(s)
 a=ARMS[arm]
 files=[p for p in (source/'parent').rglob('*')if p.is_file()]
 for p in files:assert sha(p)==s['outputs'][str(p.relative_to(source))]
 assert sha(source/'parent/layout'/(OLD+'.gds'))==GDS_SHA
 src=pdk/'libs.tech/klayout/python'
 assert sha(src/'sg13g2_pycell_lib/ihp/rppd_code.py')==RPPD_SHA
 assert sha(src/'sg13g2_pycell_lib/ihp/geometry.py')==GEOMETRY_SHA
 runtime_pins={str(p):sha(p)for p in [*src.rglob('*.py'),*src.rglob('*.json')]}
 sys.dont_write_bytecode=True
 sys.path[:0]=[str(src),str(src/'pycell4klayout-api/source/python')]
 import sg13g2_pycell_lib
 L=pya.Layout();L.read(str(source/'parent/layout'/(OLD+'.gds')))
 T=L.cell(OLD);assert T is not None and L.dbu==.001
 owners=[L]
 def regions(layout,cell,recursive=False,annotation=False):
  result={}
  for li in layout.layer_indexes():
   info=layout.get_info(li);key=(info.layer,info.datatype)
   if not annotation and info.layer in METALS and info.datatype in (2,25):continue
   it=cell.begin_shapes_rec(li)if recursive else cell.shapes(li)
   r=pya.Region(it).flatten().merged()
   if not r.is_empty():result[key]=r
  return result
 def labels(layout,cell):
  rows=[]
  for li in layout.layer_indexes():
   info=layout.get_info(li)
   rows += [(info.layer,info.datatype,str(q.text))for q in cell.shapes(li).each()if q.is_text()]
  return sorted(rows)
 def instances(cell):
  return sorted((i.cell.name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in cell.each_inst())
 def snapshot(layout,cell):
  return (regions(layout,cell),labels(layout,cell),instances(cell))
 def same(expected,actual):
  assert set(expected)==set(actual),'Changed material layer census'
  for k in expected:assert (expected[k].merged()^actual[k].merged()).is_empty(),('Changed exact material',k)
 before={c.name:snapshot(L,c)for c in L.each_cell()}
 old_top_box=T.bbox()
 C=L.cell('pd_child_'+a['kind']);assert C is not None
 placements=[i for i in T.each_inst()if i.cell.name==C.name]
 assert len(placements)==2
 meta=json.loads((source/'parent/layout/result.json').read_text())
 for tag in a['tags']:
  found=[i for i in placements if str(i.dbbox())==meta['placements'][tag]['bbox_um']]
  assert len(found)==1 and found[0].dcplx_trans.angle==0 and not found[0].dcplx_trans.is_mirror()and found[0].dcplx_trans.mag==1
 rows=[d for d in s['device_locations']['devices']if d['native_id']in a['ids']]
 local={}
 for d in rows:
  g=pya.DCplxTrans.from_s(d['pcell']['transform'])
  matches=[]
  for pi in placements:
   for ci in C.each_inst():
    if ci.cell.name!=d['pcell']['cell']:continue
    tr=pi.dcplx_trans*ci.dcplx_trans
    if str(tr)==str(g)and str(ci.cell.dbbox().transformed(tr))==d['pcell']['bbox']:matches.append((pi,ci))
  assert len(matches)==1,('Physical target not uniquely located',d['native_id'])
  pi,ci=matches[0]
  assert ci.size()==1 and ci.dcplx_trans.angle==0 and not ci.dcplx_trans.is_mirror()and ci.dcplx_trans.mag==1
  key=(ci.cell.name,str(ci.dcplx_trans))
  local.setdefault(key,dict(instance=ci,records=[]))['records'].append(d)
 assert len(local)==2 and sorted(len(x['records'])for x in local.values())==[2,2]
 # Render old and new native PCells in a separate owned Layout. Never edit
 # library code, rescale a polygon or infer a pin from nominal W/L.
 N=pya.Layout();owners.append(N)
 params=dict(w=format(a['width'],'g')+'u',l=format(a['old_length'],'g')+'u',b=0,ps=0)
 O=N.create_cell('rppd','SG13_dev',params)
 params['l']=format(a['new_length'],'g')+'u'
 F=N.create_cell('rppd','SG13_dev',params)
 assert O is not None and F is not None and not O.is_empty()and not F.is_empty()and N.dbu==.001
 assert not list(O.each_inst())and not list(F.each_inst())
 def pins(cell):
  boxes=sorted([q.box for q in cell.shapes(N.layer(8,2)).each()if q.is_box()],key=lambda b:b.center().y)
  assert len(boxes)==2 and boxes[0].top<boxes[1].bottom
  return boxes
 op,np=pins(O),pins(F)
 shift=round((a['old_length']-a['new_length'])/N.dbu)
 assert shift>0 and shift%5==0
 assert np[0]==op[0]and np[1].transformed(pya.Trans(0,shift))==op[1]
 assert all((pya.Region(b)-regions(N,c,True)[(8,0)]).is_empty()for c,bs in((O,op),(F,np))for b in bs)
 # Native old drawing must match each original target exactly, without pin annotations.
 for v in local.values():same(regions(N,O,True),regions(L,v['instance'].cell,True))
 name='rppd$v59_'+arm
 assert L.cell(name)is None
 fresh=L.create_cell(name);fresh.copy_tree(F)
 for m in METALS:
  for dt in(2,25):fresh.shapes(L.layer(m,dt)).clear()
 same(regions(N,F,True),regions(L,fresh,True))
 full_m1=regions(L,T,True)[(8,0)]
 db=pya.LayoutVsSchematic();db.read(str(source/'parent/physical/lvs_flat/result.lvsdb'))
 circuit=db.netlist().top_circuit();assert circuit.name==OLD and circuit.pin_count()==25
 assert len(list(circuit.each_device()))==500
 matches=[i for i in db.layer_indexes()if(db.layer_by_index(i).merged()^full_m1).is_empty()]
 assert len(matches)==1,'Original native M1 layer not uniquely matched'
 native_m1=db.layer_by_index(matches[0])
 owner_records=[]
 bridge_records=[];local_bridge=pya.Region();expected_instances=list(before[C.name][2])
 for key,v in sorted(local.items()):
  ci=v['instance'];tr=ci.cplx_trans
  lo=np[1].transformed(tr);hi=op[1].transformed(tr)
  assert lo.left==hi.left and lo.right==hi.right and lo.top<hi.top
  bridge=pya.Region(pya.Box(lo.left,lo.bottom,hi.right,hi.top)).merged()
  assert (pya.Region(lo)-bridge).is_empty()and(pya.Region(hi)-bridge).is_empty()
  assert bridge.interacting(pya.Region(np[0].transformed(tr))).is_empty()
  placed=[]
  for pi in placements:
   actual=bridge.transformed(pi.cplx_trans)
   oldbox=hi.transformed(pi.cplx_trans);oldpin=pya.Region(oldbox)
   selected=[d for d in v['records']if d['pcell']['transform']==str(pi.dcplx_trans*ci.dcplx_trans)]
   assert len(selected)==1
   target=selected[0]
   expected_owner=next(t['native_cluster']for t in target['terminals']if t['name']=='rppd_2')
   native_net=db.probe_net(native_m1,oldbox.center())
   assert native_net is not None and native_net.cluster_id==expected_owner
   owner_records.append((actual,expected_owner))
   owned=full_m1.interacting(oldpin)
   assert owned.count()==1 and(oldpin-owned).is_empty(),'Old MINUS landing not one actual M1 component'
   foreign=(full_m1-owned).merged()
   assert actual.sized(500).interacting(foreign).is_empty(),'M1 bridge violates unchanged500nm planning clearance'
   placed.append(dict(transform=str(pi.dcplx_trans),old_pin_dbu=str(hi.transformed(pi.cplx_trans)),
    new_pin_dbu=str(lo.transformed(pi.cplx_trans)),bridge_dbu=[str(p)for p in actual.each()],
    original_native_id=target['native_id'],native_minus_cluster=expected_owner,owned_m1_components=1,clearance_dbu=500))
  oldrow=(ci.cell.name,str(ci.cplx_trans),ci.na,ci.nb,str(ci.a),str(ci.b))
  assert expected_instances.count(oldrow)==1
  expected_instances.remove(oldrow);expected_instances.append((fresh.name,*oldrow[1:]))
  ci.cell_index=fresh.cell_index();local_bridge+=bridge
  bridge_records.append(dict(local_transform=str(ci.dcplx_trans),old_cell=key[0],new_cell=fresh.name,
    old_local_minus=str(hi),new_local_minus=str(lo),local_bridge=[str(p)for p in bridge.each()],placed=placed))
 assert len(bridge_records)==2 and sum(len(v['placed'])for v in bridge_records)==4
 for i,(r,owner)in enumerate(owner_records):
  for q,other in owner_records[i+1:]:
   if owner!=other:assert r.sized(500).interacting(q).is_empty(),'Different candidate M1 owners collide'
 C.shapes(L.layer(8,0)).insert(local_bridge)
 expected_child=dict(before[C.name][0]);expected_child[(8,0)]=(expected_child.get((8,0),pya.Region())+local_bridge).merged()
 expected_instances=sorted(expected_instances)
 def check_layout(layout,top):
  assert top.bbox()==old_top_box
  for name,old in before.items():
   cell=layout.cell(TOP if name==OLD else name);assert cell is not None,('Missing original cell',name)
   actual=snapshot(layout,cell)
   same(expected_child if name==C.name else old[0],actual[0])
   assert actual[1]==old[1],('Changed existing label',name)
   assert actual[2]==(expected_instances if name==C.name else old[2]),('Changed unrelated hierarchy',name)
  same(regions(N,F,True),regions(layout,layout.cell(fresh.name),True))
 T.name=TOP
 check_layout(L,T)
 parent.mkdir(parents=True)
 shutil.copytree(source/'parent/inputs',parent/'inputs')
 shutil.copyfile(source/'parent/children.json',parent/'children.json')
 dest=parent/'layout';dest.mkdir()
 L.write(str(dest/(TOP+'.gds')))
 R=pya.Layout();R.read(str(dest/(TOP+'.gds')));owners.append(R)
 check_layout(R,R.cell(TOP))
 # Preserve the original leaf source tree except the same two native instances
 # and their real endpoint bridges. The independent geometry checker later
 # compares this actual serialized leaf with the parent child drawing.
 manifest=json.loads((parent/'children.json').read_text())
 directory=parent/manifest['children'][a['kind']]['directory']
 leaf=meta['source_plan']['types'][a['kind']]['top']
 D=pya.Layout();owners.append(D);DT=D.create_cell(leaf);DT.copy_tree(R.cell(C.name))
 old_leaf_gds=directory/(leaf+'.gds')
 shutil.copyfile(old_leaf_gds,directory/('pre-v59-native-primitives-'+arm+'.gds'))
 D.write(str(old_leaf_gds))
 fresh_source=directory/('native-rppd-v59-'+arm+'.gds')
 N.write(str(fresh_source)) # Both native old/new drawings retain actual pin annotations.
 leaf_reference=(directory/'schematic.cir').read_text()
 changed_leaf,names_leaf=reference(leaf_reference,arm,child=True)
 (directory/'schematic.cir').write_text(changed_leaf)
 leaf_meta=json.loads((directory/'result.json').read_text())
 shutil.copyfile(directory/'result.json',directory/('pre-v59-result-'+arm+'.json'))
 targets=[r for r in leaf_meta['instances']if r['name']in a['names']]
 assert len(targets)==2
 dx,dy=leaf_meta['origin_translation_um']
 for row in targets:
  assert row['kind']=='resistor'and row['width_um']==a['width']and row['length_um']==a['old_length']
  x,y=row['placement_um'];tr=pya.DTrans(x,y)
  assert str(O.dbbox().transformed(tr))==row['bbox_um']
  absolute=pya.DTrans(x+dx,y+dy)
  assert len([v for v in local.values()if str(v['instance'].dcplx_trans)==str(pya.DCplxTrans(absolute))])==1
  row['length_um']=a['new_length'];row['bbox_um']=str(F.dbbox().transformed(tr))
 leaf_meta['status']='GENERATED_V59_NATIVE_LENGTH_REPLACEMENT_REQUIRES_FULL_PARENT_QUALIFICATION'
 leaf_meta['historical_source_circuit_sha256']=leaf_meta.pop('source_circuit_sha256',None)
 leaf_meta['source_circuit_sha256']=sha(directory/'schematic.cir')
 leaf_meta['resistor_v59']=dict(arm=arm,names=names_leaf,bridges=bridge_records,original_routes_preserved=True)
 leaf_meta['output_sha256']={p.name:sha(p)for p in directory.iterdir()if p.is_file()and p.name!='result.json'}
 (directory/'result.json').write_text(json.dumps(leaf_meta,indent=2)+'\n')
 original=(source/'parent/layout/schematic.cir').read_text()
 changed,names=reference(original,arm)
 assert changed.count(OLD)==original.count(OLD)>0 and TOP not in changed
 changed=changed.replace(OLD,TOP)
 (dest/'schematic.cir').write_text(changed)
 lef=(source/'parent/layout'/(OLD+'.lef')).read_text()
 assert TOP not in lef and lef.count(OLD)>0
 (dest/(TOP+'.lef')).write_text(lef.replace(OLD,TOP))
 # Genuine mutations of actual rendered native material/hierarchy expectations.
 controls=[]
 def reject(name,f):
  try:f()
  except AssertionError:controls.append(name)
  else:raise AssertionError('Accepted '+name)
 def changed_region(base,key,region):
  q=dict(base);q[key]=region;return q
 native_new=regions(N,F,True);k=next(iter(native_new))
 reject('missing_native_primitive_layer',lambda:same(native_new,{z:r for z,r in native_new.items()if z!=k}))
 reject('shifted_native_primitive',lambda:same(native_new,{z:r.transformed(pya.Trans(5,0))for z,r in native_new.items()}))
 reject('old_length_geometry',lambda:same(native_new,regions(N,O,True)))
 reject('missing_required_m1_bridge',lambda:same(expected_child,before[C.name][0]))
 actual_child=regions(R,R.cell(C.name))
 extra=pya.Region(pya.Box(-10000,-10000,-9000,-9000))
 reject('added_unapproved_m1',lambda:same(expected_child,changed_region(actual_child,(8,0),actual_child[(8,0)]+extra)))
 def rows_equal(x,y):assert x==y
 reject('missing_changed_instance',lambda:rows_equal(expected_instances,expected_instances[:-1]))
 reject('wrong_target_reversion',lambda:rows_equal(expected_instances,before[C.name][2]))
 original_root=before[OLD][0];key=next(iter(original_root))
 reject('removed_root_material',lambda:same(original_root,{q:r for q,r in original_root.items()if q!=key}))
 reject('missing_parent_instance',lambda:rows_equal(before[OLD][2],before[OLD][2][:-1]))
 assert len(controls)==9
 assert all(sha(Path(p))==h for p,h in runtime_pins.items())
 assert all(sha(p)==s['outputs'][str(p.relative_to(source))]for p in files)
 proof=dict(status='GENERATED_FOUR_NATIVE_RPPD_LENGTH_REPLACEMENTS_REQUIRES_FULL_PHYSICAL_AND_RC',
  arm=arm,specification=a,source_summary_sha256=sha(summary),source_gds_sha256=GDS_SHA,
  frozen_rppd_sha256=RPPD_SHA,frozen_geometry_sha256=GEOMETRY_SHA,
  old_native_render_matches_actual_original=True,native_pin_count=2,literal_terminal_names=['PLUS','MINUS'],
  replacement_native_devices=4,changed_reference_names=names,changed_leaf_reference_names=names_leaf,
  native_length_shift_dbu=shift,bridges=bridge_records,controls=controls,
  all_other_original_cell_material_labels_instances_preserved=True,all_parent_routing_and_ports_preserved=True,
  no_transistor_or_external_bias_or_clock_changes=True,changed_only_selected_rppd_lengths_and_owned_m1_bridges=True,
  physical_accepted=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False,
  source_inputs={str(summary):sha(summary),str(Path(__file__)):sha(Path(__file__)),**runtime_pins})
 meta=copy.deepcopy(meta);meta['status']=proof['status'];meta['resistor_v59']=proof
 meta['inputs']=dict(proof['source_inputs'])
 meta['inputs'].update({str(p):sha(p)for p in files})
 meta['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()}
 (dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 (parent/'resistor-replacement.json').write_text(json.dumps(proof,indent=2)+'\n')
 return proof
def main():
 p=argparse.ArgumentParser()
 for name in('source','summary','pdk','out'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--arm',choices=ARMS,required=True);a=p.parse_args()
 generate(a.source.resolve(),a.summary.resolve(),a.pdk.resolve(),a.out.resolve(),a.arm)
if __name__=='__main__':main()
