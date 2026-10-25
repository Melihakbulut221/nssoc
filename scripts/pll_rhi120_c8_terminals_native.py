#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual whole-PLL terminal references; explicit nonmetal/body limitations."""
import copy,hashlib,json,os,sys
from collections import Counter,defaultdict
from pathlib import Path
TOP='nssoc_pll845_divider3p2_rhi120_c8_development'
METALS=(8,10,30,50,67,126,134)
CENSUS=dict(sg13_lv_nmos=132,sg13_hv_nmos=57,sg13_lv_pmos=130,sg13_hv_pmos=58,npn13G2=102,rppd=89,cap_cmim=26,ntap1=60,ptap1=191)
BODY={('npn13G2','S'),('rppd','rppd_sub'),('ptap1','WELL'),('ntap1','WELL'),*[(m,'B')for m in ('sg13_lv_nmos','sg13_hv_nmos','sg13_lv_pmos','sg13_hv_pmos')]}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(out):
 import pya
 source=out/'source';gds=source/'parent/integrated'/(TOP+'.gds');db=source/'parent/physical/lvs_flat/result.lvsdb'
 assert sha(gds)=='7e60ca3b1dd37f8f245e07ad80a29e4a311fc14301c1ab1339c485a59060d3f3'
 assert sha(out/'npn13G2_code.py')=='634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729'
 L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert T is not None and L.dbu==.001
 native=pya.LayoutVsSchematic();native.read(str(db));c=native.netlist().top_circuit()
 devices={d.id():d for d in c.each_device()};assert len(devices)==845 and Counter(d.device_class().name for d in devices.values())==CENSUS
 geo=json.loads((source/'wire/native05/result.json').read_text())
 wire=pya.LayoutToNetlist();wire.read(str(source/'wire/native05/wires.l2n'))
 mim=json.loads((source/'native-mim-geometry.json').read_text())
 assert mim['source_gds_sha256']==sha(gds)and mim['native_terminal_count']==2737 and len(mim['native_mim_bindings'])==26
 mapping={int(k):v for k,v in geo['native_layer_mapping'].items()}
 owners={x['component']:x['native_cluster']for x in geo['wire_components']};assert len(owners)==235
 net_wires=defaultdict(set)
 for key,value in owners.items():net_wires[value].add(key)
 nets={n.cluster_id:n for n in c.each_net()}
 metals={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in METALS}
 poly=pya.Region(T.begin_shapes_rec(L.layer(5,0))).merged()
 contacts=pya.Region(T.begin_shapes_rec(L.layer(6,0))).merged()
 def mask(layer,datatype=0):return pya.Region(T.begin_shapes_rec(L.layer(layer,datatype))).merged()
 active=(mask(1)+mask(1,22)).merged();gate=(poly+mask(5,22)).merged()
 psd=mask(14);nsd_block=mask(7,21);well=mask(31);salblock=mask(28)
 excluded_tap=(mask(46,21)+mask(40)).merged()
 pdk_pins={'general_derivations.lvs':'f2c2ce6c039b1e28fedd3f5c94fc1dddb6194f19917e19b68f1a3750737894fb',
           'general_connections.lvs':'d8698e0b7f38cddd1750341e8e72ad020bb9c89fa6d68b82a63c9ddcf1e74ebb'}
 for filename,digest in pdk_pins.items():assert sha(out/filename)==digest
 hbt_cells=[];rppd_cells=[];hierarchy=Counter()
 def visit(cell,tr):
  hierarchy[cell.name]+=1
  if cell.name.split('$')[0].endswith('npn13G2'):
   hbt_cells.append((cell,tr));return
  if cell.name.split('$')[0].endswith('rppd'):
   rppd_cells.append((cell,tr));return
  for inst in cell.each_inst():
   assert not inst.is_regular_array(),'Explicit expansion of physical arrays required'
   visit(inst.cell,tr*inst.cplx_trans)
 visit(T,pya.ICplxTrans())
 (out/'hierarchy.json').write_text(json.dumps(dict(visited_cells=dict(hierarchy),matched_rppd_instances=len(rppd_cells),matched_rppd_cells=sorted({cell.name for cell,tr in rppd_cells}),matched_hbt_instances=len(hbt_cells),matched_hbt_cells=sorted({cell.name for cell,tr in hbt_cells})),indent=2)+'\n')
 assert len(hbt_cells)==102,('Actual namespaced HBT instance census',len(hbt_cells))
 assert len(rppd_cells)==89,('Actual namespaced resistor census',len(rppd_cells))
 terminals={};by_net=defaultdict(list)
 for did,d in devices.items():
  cls=d.device_class()
  for td in cls.terminal_definitions():
   pieces=native.shapes_of_terminal(d.terminal_ref(td.id()));assert pieces
   reg=pya.Region()
   for area in pieces.values():reg+=area
   reg=reg.merged();assert not reg.is_empty()
   net=d.net_for_terminal(td.id())
   terminals[did,td.name]=dict(model=cls.name,net=net,region=reg,td=td)
   by_net[net.cluster_id].append((did,td.name))
 assert len(terminals)==2737
 mimpins={(d['native_id'],p['terminal']):p for d in mim['native_mim_bindings']for p in d['points']}
 assert len(mimpins)==52
 rows=[];anchors=[];unresolved=[];shared={};used_hbt={};used_rppd={};salicide_bound={}
 def point_probe(m,p,nid):
  wn=wire.probe_net(wire.layer_by_name('gds_'+str(m)),p)
  nn=native.probe_net(native.layer_by_index(mapping[m]),p)
  assert wn is not None and nn is not None,'Missing actual metal at terminal plane'
  assert nn.cluster_id==nid and owners[wn.cluster_id]==nid,'Native conductor owner mismatch'
  witness=pya.Region(pya.Box(p.x-1,p.y-1,p.x+1,p.y+1))
  assert(witness-metals[m]).is_empty(),'Point not inside drawn metal'
  return wn.cluster_id
 def access_contacts(area,nid):
  found=[]
  for contact in contacts.interacting(area).each():
   if (pya.Region(contact)&area).area()==0:continue
   b=contact.bbox()
   if contact.area()!=b.area()or not(pya.Region(contact)-metals[8]).is_empty():continue
   q=b.center()
   try:component=point_probe(8,q,nid)
   except AssertionError:continue
   found.append((8,q,component))
  return found
 def salicide_access(reg,cls,nid,blocked=None,available_contacts=None,implant=None):
  # Pinned IHP rule: unblocked S/D and opposite-type tap can join only at a
  # positive-length shared salicide edge. Never traverse a well or a PN junction
  # without this actual drawn salicide boundary and a local tap contact.
  blocked=salblock if blocked is None else blocked
  available_contacts=contacts if available_contacts is None else available_contacts
  implant=psd if implant is None else implant
  nactive=active-(implant+nsd_block);pactive=active&implant
  is_n=cls.endswith('_nmos');assert is_n or cls.endswith('_pmos')
  sd_domain=(nactive-well-gate)if is_n else(pactive&well)-gate
  tap_domain=(pactive-well-gate-excluded_tap)if is_n else(nactive&well)-gate-excluded_tap
  assert (reg-sd_domain).is_empty(),'Terminal is not wholly inside the correct S/D diffusion domain'
  sd=(reg-blocked).merged();tap_domain=(tap_domain-blocked).merged()
  assert not sd.is_empty(),'Salicide source region blocked'
  matches=[]
  for polygon in tap_domain.interacting(sd.sized(1)).each():
   tap=pya.Region(polygon)
   boundary=sd.edges()&tap.edges()
   if boundary.length()<=0:continue
   joined=(sd+tap).merged()
   if joined.count()!=1:continue
   local=[]
   for contact in available_contacts.inside(tap).each():
    box=contact.bbox()
    if contact.area()!=box.area()or not(pya.Region(contact)-metals[8]).is_empty():continue
    q=box.center();component=point_probe(8,q,nid)
    local.append((8,q,component))
   if not local:continue
   assert len({v[2]for v in local})==1,'Multiple actual metal components on an unmodeled tap access'
   proof=dict(kind='actual_unblocked_salicide_shared_edge_to_local_tap_contact',
    boundary_edges_dbu=sorted(e.to_s()for e in boundary.each()),boundary_length_dbu=boundary.length(),
    sd_shapes=sorted(p.to_s()for p in sd.each()),tap_shapes=[polygon.to_s()],
    contact_points_dbu=sorted([q.x,q.y]for m,q,cid in local),
    native_cluster=nid,salicide_diffusion_access_resistance_modeled=False)
   matches.append((local,proof,tap))
  assert len(matches)==1,('Unique actual salicide-to-tap access required',len(matches))
  return matches[0]
 def shared_diffusion(nid):
  keys=by_net[nid];assert len(keys)>=2 and not net_wires[nid]
  assert all(terminals[k]['model'].startswith('sg13_')and k[1]in ('S','D')for k in keys)
  assert not any(c.net_for_pin(p.id()).cluster_id==nid for p in c.each_pin())
  joined=pya.Region()
  for k in keys:joined+=terminals[k]['region']
  joined=joined.merged();assert joined.count()==1,'Nonmetal terminal shapes are not one contiguous diffusion region'
  for m in METALS:
   assert native.shapes_of_net(nets[nid],native.layer_by_index(mapping[m]),True).is_empty()
  # Do not invent an ideal metal edge; preserve the extracted intrinsic node.
  return dict(native_cluster=nid,native_net=nets[nid].name,terminals=[dict(device=d,terminal=t)for d,t in keys],
   region_bbox_dbu=str(joined.bbox()),region_area_dbu2=joined.area(),
   metal_components=[],diffusion_resistance_modeled=False)
 for (did,name),data in terminals.items():
  cls=data['model'];net=data['net'];nid=net.cluster_id;reg=data['region']
  row=dict(device=did,model=cls,terminal=name,native_cluster=nid,native_net=net.name)
  try:
   if(cls,name)in BODY:
    row['disposition']='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING';rows.append(row);continue
   choices=[];selection=''
   if cls=='cap_cmim':
    a=mimpins[did,name];assert a['native_cluster']==nid
    q=pya.Point(*a['point_dbu']);component=point_probe(a['metal'],q,nid)
    assert component==a['wire_component'];choices=[(a['metal'],q,component)];selection='previously_bound_actual_mim_plate'
   elif cls=='npn13G2':
    enclosure=pya.Box()
    for (other,terminal),v in terminals.items():
     if other==did and terminal!='S':enclosure+=v['region'].bbox()
    matches=[(cell,tr)for cell,tr in hbt_cells if(cell.bbox().transformed(tr)&enclosure)==enclosure]
    assert len(matches)==1,('Unique HBT primitive enclosure',did,len(matches))
    cell,tr=matches[0];used_hbt[did]=(cell.cell_index(),str(tr))
    pins={m:[s.box for s in cell.each_shape(L.layer(m,2))if s.is_box()]for m in (8,10)}
    assert len(pins[8])==2 and len(pins[10])==1,'Missing actual HBT pin annotation'
    base,collector=sorted(pins[8],key=lambda b:b.center().y)
    assert base.center().y<collector.center().y
    m,b={'C':(8,collector),'B':(8,base),'E':(10,pins[10][0])}[name]
    b=b.transformed(tr);assert(pya.Region(b)-metals[m]).is_empty()
    q=b.center();choices=[(m,q,point_probe(m,q,nid))];selection='pinned_native_hbt_'+name+'_pin'
   elif cls=='rppd':
    enclosure=pya.Box()
    ends={t:terminals[did,t]['region'].bbox() for t in ('rppd_1','rppd_2')}
    for b in ends.values():enclosure+=b
    matches=[(cell,tr)for cell,tr in rppd_cells if(cell.bbox().transformed(tr)&enclosure)==enclosure]
    assert len(matches)==1,('Unique resistor primitive enclosure',did,len(matches))
    cell,tr=matches[0];used_rppd[did]=(cell.cell_index(),str(tr))
    pins=[shape.box.transformed(tr)for shape in cell.each_shape(L.layer(8,2))if shape.is_box()]
    assert len(pins)==2,'Exactly two original resistor metal pins required'
    selected={}
    for terminal,box in ends.items():
     center=box.center()
     ranked=sorted(((b.center().x-center.x)**2+(b.center().y-center.y)**2,i)for i,b in enumerate(pins))
     assert ranked[0][0]<ranked[1][0],'Ambiguous resistor physical end'
     selected[terminal]=ranked[0][1]
    assert len(set(selected.values()))==2,'Resistor ends must retain distinct physical planes'
    box=pins[selected[name]];assert(pya.Region(box)-metals[8]).is_empty()
    q=box.center();choices=[(8,q,point_probe(8,q,nid))];selection='unique_original_resistor_end_pin'
   else:
    area=poly.interacting(reg).merged()if cls.startswith('sg13_')and name=='G'else reg
    choices=access_contacts(area,nid);selection='actual_gate_poly_contact'if name=='G'else'actual_native_terminal_contact'
    if not choices and cls.startswith('sg13_')and name in ('S','D')and net_wires[nid]:
     choices,proof,tap=salicide_access(reg,cls,nid)
     row['salicide_access_proof']=proof;salicide_bound[did,name]=(reg,cls,nid,tap,proof)
     selection='actual_salicide_abutment_to_local_tap_contact'
    if not choices and cls.startswith('sg13_')and name in ('S','D')and not net_wires[nid]:
     proof=shared_diffusion(nid);shared[nid]=proof
     row.update(disposition='RETAINED_SHARED_INTRINSIC_DIFFUSION_NO_METAL_OR_DIFFUSION_R',shared_node=nid)
     rows.append(row);continue
   assert choices,('No actual contact/metal reference',did,cls,name,str(reg.bbox()))
   assert len({a[2]for a in choices})==1,'Distinct wire components cannot be shorted through an unmodeled access region'
   center=reg.bbox().center();m,q,component=min(choices,key=lambda a:((a[1].x-center.x)**2+(a[1].y-center.y)**2,a[0],a[1].x,a[1].y))
   label='T'+str(did)+'_'+name
   a=dict(label=label,metal=m,point_dbu=[q.x,q.y],wire_component=component,native_cluster=nid)
   anchors.append(a);row.update(disposition='ACTUAL_TERMINAL_METAL_POINT_REFERENCE',reference_label=label,selection=selection,**{k:a[k]for k in ('metal','point_dbu','wire_component')})
   row['candidate_points']=[dict(metal=m,point_dbu=[q.x,q.y],wire_component=component)for m,q,component in choices]
  except (AssertionError,KeyError,ValueError)as error:
   row.update(disposition='UNRESOLVED_NO_INVENTED_ANCHOR',reason=str(error))
   detail=dict(device=did,model=cls,terminal=name,native_cluster=nid,reason=str(error))
   if cls.startswith('sg13_') and name in ('S','D'):
    nearby=[]
    for contact in contacts.interacting(pya.Region(reg.bbox().enlarged(2000))).each():
     box=contact.bbox();q=box.center()
     nn=native.probe_net(native.layer_by_index(mapping[8]),q)
     nearby.append(dict(box_dbu=[box.left,box.bottom,box.right,box.top],overlap_area_dbu2=(pya.Region(contact)&reg).area(),metal_native_cluster=None if nn is None else nn.cluster_id))
    detail.update(terminal_shapes=[p.to_s()for p in reg.each()],nearby_contacts=nearby)
   unresolved.append(detail)
  rows.append(row)
 metadata=json.loads((source/'parent/integrated/result.json').read_text());public=[]
 assert len(metadata['ports'])==17 and {p.name()for p in c.each_pin()}==set(metadata['ports'])
 for name,v in sorted(metadata['ports'].items()):
  m=v['layer'];assert m in METALS
  box=pya.DBox(*v['rect_um']).to_itype(L.dbu);q=box.center();pin=next(p for p in c.each_pin()if p.name()==name);net=c.net_for_pin(pin.id())
  a=dict(label='P_'+name,metal=m,point_dbu=[q.x,q.y],native_cluster=net.cluster_id,wire_component=point_probe(m,q,net.cluster_id))
  anchors.append(a);public.append(dict(name=name,reference_label=a['label']))
 census=dict(Counter(r['disposition']for r in rows))
 result=dict(status='INCOMPLETE_WHOLE_PLL_TERMINAL_REFERENCES',rows=rows,anchors=anchors,public=public,
  unresolved=unresolved,shared_intrinsic_nodes=list(shared.values()),counts=dict(devices=845,terminals=len(rows),dispositions=census,public_ports=17,anchors=len(anchors),wire_components=235,covered_wire_components=len({a['wire_component']for a in anchors})),
  negative_controls=[],qualified_pex=False,wire_rc_extracted=False,full_phy_accepted=False,
  substrate_spreading_included=False,poly_diffusion_resistance_included=False,
  scope='All2737 native terminal identities; metal anchors only where geometry proves them. Body and contiguous shared diffusion retained explicitly. No modeled substrate/diffusion spreading, wire RC or electrical acceptance.',
  inputs={str(p):sha(p)for p in [Path(__file__).resolve(),gds,db,source/'parent/integrated/result.json',source/'wire/native05/result.json',source/'wire/native05/wires.l2n',source/'native-mim-geometry.json',out/'npn13G2_code.py',*[out/name for name in pdk_pins]]})
 target=out/'anchors.json'
 def save():target.write_text(json.dumps(result,indent=2)+'\n')
 save()
 assert len(rows)==2737 and len({(r['device'],r['terminal'])for r in rows})==2737
 assert census.get('RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING')==819
 assert not unresolved,('Unresolved actual terminal references',len(unresolved),unresolved[:8])
 assert len(used_hbt)==102 and len(set(used_hbt.values()))==102
 assert len(used_rppd)==89 and len(set(used_rppd.values()))==89
 assert {a['wire_component']for a in anchors}==set(owners),'Unanchored actual wire components'
 expected={(r['device'],r['terminal']):copy.deepcopy(r)for r in rows}
 lookup={a['label']:a for a in anchors};assert len(lookup)==len(anchors)
 def verify(observed):
  assert len(observed)==2737 and len({(r['device'],r['terminal'])for r in observed})==2737
  for r in observed:
   key=r['device'],r['terminal'];original=expected[key]
   assert r==original,'Terminal identity, reference plane or disposition changed'
   if r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE':
    a=lookup[r['reference_label']];assert a['point_dbu']==r['point_dbu']and a['metal']==r['metal']
    assert point_probe(r['metal'],pya.Point(*r['point_dbu']),r['native_cluster'])==r['wire_component']
    if r.get('selection')=='actual_salicide_abutment_to_local_tap_contact':
     reg,cls,nid,tap,proof=salicide_bound[key]
     assert salicide_access(reg,cls,nid)[1]==proof==r['salicide_access_proof']
   elif r['disposition'].startswith('RETAINED_SHARED'):
    assert shared_diffusion(r['native_cluster'])==shared[r['native_cluster']]
 verify(rows)
 for fault in ('missing_terminal','duplicate_terminal','off_metal','wrong_owner','body_as_metal','mim_plates_swapped','hbt_base_collector_swapped','rppd_ends_swapped'):
  bad=copy.deepcopy(rows);r=next(r for r in bad if r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE')
  if fault=='missing_terminal':bad.pop()
  elif fault=='duplicate_terminal':bad[-1]=copy.deepcopy(bad[0])
  elif fault=='off_metal':r['point_dbu']=[T.bbox().right+10000,T.bbox().top+10000]
  elif fault=='wrong_owner':r['native_cluster']=next(n for n in nets if n!=r['native_cluster'])
  elif fault=='body_as_metal':
   b=next(x for x in bad if x['disposition']=='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING');b['reference_label']=r['reference_label']
  else:
   kind,first,second=('cap_cmim','mim_top','mim_btm')if fault=='mim_plates_swapped'else('rppd','rppd_1','rppd_2')if fault=='rppd_ends_swapped'else('npn13G2','B','C')
   a=next(x for x in bad if x['model']==kind and x['terminal']==first)
   b=next(x for x in bad if x['device']==a['device']and x['terminal']==second)
   assert a['point_dbu']!=b['point_dbu']or a['metal']!=b['metal']
   for key in ('point_dbu','metal','reference_label','wire_component'):a[key],b[key]=b[key],a[key]
  try:verify(bad)
  except (AssertionError,KeyError):result['negative_controls'].append(dict(fault=fault,rejected=True))
  else:raise AssertionError('Actual terminal corruption accepted '+fault)
 assert len(salicide_bound)==30,'Expected precisely the30 previously unresolved actual MOS references'
 for fault in ('salicide_boundary_cut','local_tap_contacts_removed','opposite_implant_removed'):
  rejected=0
  for reg,cls,nid,tap,proof in salicide_bound.values():
   kwargs={}
   if fault=='salicide_boundary_cut':
    seam=reg.sized(2)&tap.sized(2)
    assert not seam.is_empty();kwargs['blocked']=(salblock+seam).merged()
   elif fault=='local_tap_contacts_removed':
    kwargs['available_contacts']=contacts-tap
   else:
    kwargs['implant']=(psd-tap)if cls.endswith('_nmos')else(psd+tap).merged()
   try:salicide_access(reg,cls,nid,**kwargs)
   except AssertionError:rejected+=1
   else:raise AssertionError('Actual salicide geometry corruption accepted '+fault)
  assert rejected==30
  result['negative_controls'].append(dict(fault=fault,rejected=True,actual_geometry_cases=rejected))
 assert len(result['negative_controls'])==11
 result['salicide_reference_count']=len(salicide_bound)
 assert all(sha(Path(n))==digest for n,digest in result['inputs'].items())
 result['status']='PASS_ALL2737_PLL_TERMINAL_IDENTITIES_AND_ACTUAL_METAL_REFERENCES_REQUIRES_FULL_RC'
 save();print(json.dumps(dict(status=result['status'],counts=result['counts'],controls=11,salicide_references=len(salicide_bound))))
if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 generate(Path(sys.argv[1]).resolve())
