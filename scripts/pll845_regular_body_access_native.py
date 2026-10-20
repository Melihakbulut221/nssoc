#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prove regular n-well contacts missing from the named-device LVS census."""
import copy,json,os,sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
import build_pll845_native_models as models
from run_cloud_tx_layout_repair import sha
TOP='nssoc_pll845_divider3p2_c8_v2_development'
def main(out):
 import pya
 source=out/'planes/source';composition=out/'composition'
 failed=json.loads((composition/'result.json').read_text())
 assert failed['source_head']=='8aef441d948ed54ae0e82276dcbbb19852578a41'and failed['status']=='FAIL_OR_ERROR'
 contract=json.loads((composition/'composition.json').read_text());assert contract==failed['composition']
 assert contract['uncontacted_body_groups']==[dict(native_cluster=203,net='body_203',native_net='core_vdd')]
 gds=source/'parent/integrated'/(TOP+'.gds');db=source/'parent/physical/lvs_flat/result.lvsdb'
 assert sha(gds)=='79b2f5869f620cb5d6ce57756bab18f6ef10743aee953fb9c140202a6b225cdc'
 L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert L.dbu==.001 and T is not None
 N=pya.LayoutVsSchematic();N.read(str(db));c=N.netlist().top_circuit();assert len(list(c.each_device()))==845
 assert N.internal_layout().dbu==.001
 graph=json.loads((source/'wire/native05/result.json').read_text())
 wire=pya.LayoutToNetlist();wire.read(str(source/'wire/native05/wires.l2n'))
 mapping={int(k):v for k,v in graph['native_layer_mapping'].items()}
 owners={r['component']:r['native_cluster']for r in graph['wire_components']}
 anchors=json.loads((composition/'audit/capture/wire/anchors08.json').read_text())
 assert len(anchors['anchors'])==1604 and anchors['logical_anchor_count']==1877
 physical={a['label']:a for a in anchors['anchors']}
 def region(layer,datatype=0):return pya.Region(T.begin_shapes_rec(L.layer(layer,datatype))).merged()
 active=(region(1)+region(1,22)).merged();psd=region(14);nblock=region(7,21)
 gates=(region(5)+region(5,22)).merged();well=region(31);salblock=region(28)
 contacts=region(6);metal=region(8)
 ntap=((active-psd-nblock)&well)-gates-salblock
 body_devices=[]
 for d in c.each_device():
  cls=d.device_class();defs={t.name:t for t in cls.terminal_definitions()}
  if 'B'not in defs or d.net_for_terminal(defs['B'].id()).cluster_id!=203:continue
  assert cls.name=='sg13_lv_pmos','Unexpected device type on unresolved regular well'
  sd=pya.Region()
  for terminal in ('S','D'):
   pieces=N.shapes_of_terminal(d.terminal_ref(defs[terminal].id()));assert pieces
   for piece in pieces.values():sd+=piece
  sd=sd.merged();assert not sd.is_empty()
  body_devices.append((d.id(),sd))
 expected_body={d['native_id']for d in contract['device_records']if any(t['terminal']=='B'and t['native_cluster']==203 for t in d['terminals'])}
 assert len(expected_body)==125
 assert all(d['native_model']=='sg13_lv_pmos'for d in contract['device_records']if d['native_id']in expected_body)
 assert sum(d.device_class().name=='sg13_lv_pmos'for d in c.each_device())==130,'Whole native LV PMOS census changed'
 census=dict(all_native_lv_pmos=130,expected_regular_body_count=125,
  expected_native_ids=sorted(expected_body),observed_native_ids=sorted(did for did,sd in body_devices))
 (out/'body-census.json').write_text(json.dumps(census,indent=2)+'\n')
 assert {did for did,sd in body_devices}==expected_body and len(body_devices)==125,'Exact native body-device identity set changed'
 all_wells=sorted(list(well.each()),key=lambda p:(p.bbox().left,p.bbox().bottom,p.bbox().right,p.bbox().top,p.to_s()))
 assigned={};used=set()
 for did,sd in body_devices:
  matches=[i for i,p in enumerate(all_wells)if(sd-pya.Region(p)).is_empty()]
  assert len(matches)==1,('Unique actual n-well island required',did,len(matches))
  assigned[did]=matches[0];used.add(matches[0])
 island_ids={index:'NWELL_'+str(i+1).zfill(3)for i,index in enumerate(sorted(used))}
 islands={island_ids[i]:pya.Region(all_wells[i])for i in used}
 selected=pya.Region()
 for r in islands.values():selected+=r
 selected=selected.merged()
 planned_taps=[];access=[];tech=json.loads((out/'sg13g2_tech.json').read_text())['techParams']
 for name,island in sorted(islands.items()):
  pieces=(ntap&island).merged();assert not pieces.is_empty(),('No actual regular tap on well island',name)
  for polygon in sorted(list(pieces.each()),key=lambda p:(p.bbox().left,p.bbox().bottom,p.to_s())):
   tap=pya.Region(polygon);candidates=[]
   for label,a in physical.items():
    if a['metal']!=8 or a['native_cluster']!=203:continue
    point=pya.Point(*a['point_dbu']);witness=pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))
    if not(witness-tap).is_empty()or not(witness-contacts).is_empty()or not(witness-metal).is_empty():continue
    nn=N.probe_net(N.layer_by_index(mapping[8]),point);wn=wire.probe_net(wire.layer_by_name('gds_8'),point)
    assert nn is not None and wn is not None and nn.cluster_id==203 and wn.cluster_id==a['wire_component']and owners[wn.cluster_id]==203
    candidates.append((label,a,point))
   assert candidates,('New actual tap reference plane/RC extraction required; no existing contact anchor',name,polygon.to_s())
   center=polygon.bbox().center()
   label,a,point=min(candidates,key=lambda x:((x[2].x-center.x)**2+(x[2].y-center.y)**2,x[0]))
   area=Decimal(tap.area())/Decimal(1000000);perimeter=Decimal(tap.perimeter())/Decimal(1000)
   params=models.model_params(dict(model='ntap1',parameters=dict(A=area,P=perimeter)),tech)
   ordinal=len(access)+1
   row=dict(instance='X_REGULAR_NTAP_'+str(ordinal).zfill(3),model='ntap1',native_device_instance=False,
    source_native_body_cluster=203,island=name,body_node='body_203_'+name.lower(),wire_anchor=label,
    wire_component=a['wire_component'],point_dbu=a['point_dbu'],metal=8,
    area_um2=str(area),perimeter_um=str(perimeter),parameters={k.lower():v for k,v in params.items()},
    actual_tap_polygon_dbu=polygon.to_s(),actual_contact_anchor_candidates=len(candidates),
    reference_plane='existing exact native contact point; audited R/C mesh unchanged',
    distributed_well_or_tap_spreading_modeled=False)
   access.append(row);planned_taps.append((row,tap))
 plan=dict(native_body_cluster=203,native_net='core_vdd',native_pmos_body_terminals=len(expected_body),
  island_count=len(islands),tap_count=len(access),body_terminals=[dict(device=did,terminal='B',native_cluster=203,
   island=island_ids[assigned[did]],body_node='body_203_'+island_ids[assigned[did]].lower())for did,sd in body_devices],
  islands=[dict(name=name,polygons_dbu=[p.to_s()for p in r.each()],area_dbu2=r.area())for name,r in sorted(islands.items())],
  access_models=access,original_named_native_devices=845,auxiliary_geometry_extracted_contact_models=len(access),
  existing_audited_wire_points_only=True,wire_geometry_changed=False,wire_rc_changed=False,qualified_pex=False,
  substrate_spreading_modeled=False,within_tap_and_well_distributed_resistance_modeled=False)
 def validate(well_mask,tap_mask,contact_mask,metal_mask,override=None):
  union=pya.Region()
  for row,tap in planned_taps:
   union+=tap
   assert(tap-tap_mask).is_empty()and(tap-islands[row['island']]).is_empty()
   a=physical[row['wire_anchor']]if override is None else override.get(row['wire_anchor'],physical[row['wire_anchor']])
   assert a['native_cluster']==203 and a['wire_component']==row['wire_component']and a['point_dbu']==row['point_dbu']
   q=pya.Point(*row['point_dbu']);witness=pya.Region(pya.Box(q.x-1,q.y-1,q.x+1,q.y+1))
   assert(witness-tap).is_empty()and(witness-contact_mask).is_empty()and(witness-metal_mask).is_empty()
   nn=N.probe_net(N.layer_by_index(mapping[8]),q);wn=wire.probe_net(wire.layer_by_name('gds_8'),q)
   assert nn is not None and wn is not None and nn.cluster_id==a['native_cluster']and wn.cluster_id==a['wire_component']
  assert(union.merged()^(tap_mask&selected).merged()).is_empty(),'Missing/extra physical regular tap'
  for did,sd in body_devices:
   assigned_well=islands[island_ids[assigned[did]]]
   assert(sd-(assigned_well&well_mask)).is_empty(),'MOS bulk not in original actual well island'
  assert {r['island']for r in access}==set(islands)
 validate(well,ntap,contacts,metal)
 controls=[]
 for fault in ('selected_contact_removed','selected_metal_removed','actual_tap_diffusion_removed','wrong_conductor_owner'):
  count=0
  for row,tap in planned_taps:
   q=pya.Point(*row['point_dbu']);cut=pya.Region(pya.Box(q.x-2,q.y-2,q.x+2,q.y+2))
   kwargs=dict(well_mask=well,tap_mask=ntap,contact_mask=contacts,metal_mask=metal)
   if fault=='selected_contact_removed':kwargs['contact_mask']=contacts-cut
   elif fault=='selected_metal_removed':kwargs['metal_mask']=metal-cut
   elif fault=='actual_tap_diffusion_removed':kwargs['tap_mask']=ntap-tap
   else:
    bad=copy.deepcopy(physical[row['wire_anchor']]);bad['native_cluster']=999999
    kwargs['override']={row['wire_anchor']:bad}
   try:validate(**kwargs)
   except AssertionError:count+=1
   else:raise AssertionError('Accepted regular-body geometry corruption '+fault)
  assert count==len(access);controls.append(dict(name=fault,rejected=True,cases=count))
 count=0
 for name,area in islands.items():
  try:validate(well-area,ntap,contacts,metal)
  except AssertionError:count+=1
  else:raise AssertionError('Missing actual body well accepted')
 assert count==len(islands);controls.append(dict(name='actual_nwell_island_removed',rejected=True,cases=count))
 result=dict(status='PASS_ACTUAL_REGULAR_NWELL_CONTACT_GEOMETRY_REQUIRES_COMPOSITION_AND_LOADED_WAVES',
  source_gds_sha256=sha(gds),plan=plan,controls=controls,qualified_pex=False,full_phy_accepted=False,
  inputs={str(p):sha(p)for p in [Path(__file__).resolve(),gds,db,source/'wire/native05/result.json',
   source/'wire/native05/wires.l2n',composition/'composition.json',composition/'audit/capture/wire/anchors08.json',out/'sg13g2_tech.json']})
 (out/'regular-body-access.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(status=result['status'],body_terminals=len(expected_body),islands=len(islands),tap_models=len(access),
  actual_geometry_fault_cases=sum(x['cases']for x in controls))))
if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 main(Path(sys.argv[1]).resolve())
