#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact native whole-PLL composition, including extracted MIM attachment planes."""
import copy,hashlib
from collections import Counter
from decimal import Decimal
import build_pcie_local_vco_hybrid_v6 as parser
MODEL='nssoc_pll845_body_mim_wire_v2'
BODY='RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_SPREADING'
DIFF='RETAINED_SHARED_INTRINSIC_DIFFUSION_NO_METAL_OR_DIFFUSION_R'
METAL='ACTUAL_TERMINAL_METAL_POINT_REFERENCE'
def assemble(binding,anchors,geometry,wiretext,mim_groups,body_plan):
 rows=parser.statements(wiretext)
 assert rows[0][:2]==['.subckt','pump_wires']and rows[-1][0]=='.ends'
 physical={a['label']:a for a in anchors['anchors']}
 assert len(physical)==len(set(rows[0][2:]))==len(rows[0][2:])==1606
 assert set(physical)==set(rows[0][2:])
 aliases=anchors['logical_anchor_aliases'];assert len(aliases)==1879
 assert anchors['logical_anchor_count']==1879 and anchors['physical_anchor_count']==1606
 assert set(aliases.values())==set(physical)
 for logical,label in aliases.items():assert logical in physical[label]['logical_labels']
 assert anchors['counts']['dispositions']=={METAL:1860,BODY:819,DIFF:58}
 assert geometry['native_device_count']==845 and geometry['native_terminal_count']==2737 and geometry['wire_component_count']==235
 component_native={r['component']:r['native_cluster']for r in geometry['wire_components']}
 assert len(component_native)==235
 native={d['native_id']:d for d in binding['devices']};assert len(native)==845
 terminals={(r['device'],r['terminal']):r for r in anchors['rows']}
 assert len(terminals)==len(anchors['rows'])==2737
 assert body_plan['native_body_cluster']==203 and body_plan['native_pmos_body_terminals']==125
 assert body_plan['island_count']==body_plan['tap_count']==4 and body_plan['new_reference_count']==2
 assert body_plan['fresh_wire_rc_required'] and not body_plan['wire_geometry_changed']
 body_assignment={(x['device'],x['terminal']):x for x in body_plan['body_terminals']}
 assert len(body_assignment)==len(body_plan['body_terminals'])==125
 assert set(body_assignment)=={k for k,x in terminals.items()if x['disposition']==BODY and x['native_cluster']==203}
 assert {d for d,t in body_assignment}==set(range(195,320))and all(t=='B'for d,t in body_assignment)
 access=body_plan['access_models'];assert len(access)==4
 assert len({a['instance']for a in access})==len({a['body_node']for a in access})==4
 islands={x['name']for x in body_plan['islands']};assert len(islands)==4
 assert {a['island']for a in access}=={a['island']for a in body_assignment.values()}==islands
 assert {a['body_node']for a in access}=={a['body_node']for a in body_assignment.values()}
 for a in access:
  assert a['model']=='ntap1'and a['native_device_instance']is False and a['source_native_body_cluster']==203
  assert a['body_node']=='body_203_'+a['island'].lower()
  assert set(a['parameters'])=={'r'}and parser.number(a['parameters']['r'])>0
  p=physical[a['wire_anchor']]
  assert p['point_dbu']==a['point_dbu']and p['metal']==a['metal']==8
  assert p['native_cluster']==203 and p['wire_component']==a['wire_component']==95
  assert all(x['body_node']==a['body_node']for x in body_assignment.values()if x['island']==a['island'])
 assert anchors['anchors'][-2:]==body_plan['new_physical_points']

 assert set(terminals)=={(d['native_id'],t)for d in binding['devices']for t in d['native_nodes']}
 public={}
 for port in anchors['public']:
  label=aliases[port['reference_label']]
  assert label==port['wire_anchor']and label not in public,'Coincident public interfaces require explicit proof, never an invented alias'
  public[label]=port['name']
 assert len(public)==17 and set(public.values())==set(binding['native_ports'])
 rc=[r for r in rows[1:-1]if r[0][0]in 'RC']
 mim=[r for r in rows[1:-1]if r[0].startswith('X')]
 assert len(rc)+len(mim)==len(rows)-2 and len(mim)==26
 assert Counter(r[0][0]for r in rc)==dict(R=3381,C=5105)
 assert len({r[0].lower()for r in rows[1:-1]})==len(rows)-2
 graph=parser.Union()
 for r in rc:
  assert len(r)==4 and r[1]!=r[2]
  assert parser.number(r[3])>0 if r[0][0]=='R'else parser.number(r[3])>=0
  if r[0][0]=='R':graph.join(r[1],r[2])
 root_owners={}
 for label,a in physical.items():
  assert label in graph.parent
  root=graph.find(label);root_owners.setdefault(root,a['wire_component'])
  assert root_owners[root]==a['wire_component']
 assert len(root_owners)==len(set(root_owners.values()))==235
 assert all(graph.find(n)in root_owners for n in graph.parent)
 owners={n:root_owners[graph.find(n)]for n in graph.parent}
 assert 'sub'not in owners
 raw_nodes={n for r in rc for n in r[1:3]}
 assert set(raw_nodes)==set(owners)|{'sub'}
 wire_map={n:'wire_cref'if n=='sub'else public.get(n,'w_'+n)for n in raw_nodes}
 assert len(wire_map)==len({v.lower()for v in wire_map.values()})
 # Original raw MIM cards provide actual distributed attachment nodes. The
 # reference anchor is retained as a physical witness, never substituted for
 # that extracted terminal node merely because both have the same net owner.
 raw_mim={r[0]:r for r in mim};mim_by_id={}
 assert len(mim_groups)==26
 for group in mim_groups:
  assert group['per_device_identity_unique']and len(group['native_ids'])==len(group['export_instances'])==1
  did=group['native_ids'][0];card=raw_mim[group['export_instances'][0]]
  assert did not in mim_by_id and native[did]['model']=='cap_cmim'
  assert len(card)==6 and card[3]=='cap_cmim'
  params=dict(v.split('=')for v in card[4:]);assert set(params)=={'w','l'}
  d=native[did]
  assert all(parser.number(params[k])==parser.number(d['parameters'][k])for k in ('w','l'))
  for term,node,component in [('mim_top',card[1],group['plus_component']),('mim_btm',card[2],group['minus_component'])]:
   assert node in owners and owners[node]==component==terminals[did,term]['wire_component']
  assert parser.number(params['w'])==Decimal(group['w_um'])*Decimal('1e-6')
  assert parser.number(params['l'])==Decimal(group['l_um'])*Decimal('1e-6')
  mim_by_id[did]=card
 assert set(mim_by_id)=={d['native_id']for d in binding['devices']if d['model']=='cap_cmim'}
 source_shared={p['native_cluster']:p for p in anchors['shared_intrinsic_nodes']}
 out=[];records=[];body_map={};diffusion_map={};plane_changes=[]
 for d in binding['devices']:
  nodes=[];witnesses=[]
  for term in d['compact_model_order']:
   x=terminals[d['native_id'],term]
   assert x['model']==d['native_model']and x['native_net']==d['native_nodes'][term]and x['native_cluster']==d['native_clusters'][term]
   witness=dict(terminal=term,native_cluster=x['native_cluster'],native_net=x['native_net'],disposition=x['disposition'])
   if x['disposition']==METAL:
    label=aliases[x['reference_label']];a=physical[label]
    assert label==x['wire_anchor']and x['reference_label']in a['logical_labels']
    assert a['native_cluster']==x['native_cluster']==component_native[x['wire_component']]
    assert a['wire_component']==x['wire_component']and a['point_dbu']==x['point_dbu']and a['metal']==x['metal']
    raw_node=label
    if d['model']=='cap_cmim':
     card=mim_by_id[d['native_id']];raw_node=card[1 if term=='mim_top'else 2]
     assert owners[raw_node]==x['wire_component']
     witness.update(native_mim_export=card[0],native_mim_attachment=raw_node)
     plane_changes.append(dict(native_id=d['native_id'],terminal=term,reference_anchor=label,
      actual_native_attachment=raw_node,distinct_node=label!=raw_node,wire_component=x['wire_component']))
    net=wire_map[raw_node];witness.update(reference_anchor=label,raw_wire_node=raw_node)
   elif x['disposition']==BODY:
    assignment=body_assignment.get((d['native_id'],term))
    net=assignment['body_node']if assignment else 'body_'+str(x['native_cluster'])
    if assignment:
     assert d['model']=='sg13_lv_pmos'and term=='B'and x['native_cluster']==203
     witness['actual_nwell_island']=assignment['island']
    body_map.setdefault(net,dict(net=net,native_net=x['native_net'],native_cluster=x['native_cluster']))
    assert body_map[net]['native_net']==x['native_net']
   else:
    assert x['disposition']==DIFF and x['native_cluster']in source_shared
    group=source_shared[x['native_cluster']]
    assert dict(device=d['native_id'],terminal=term)in group['terminals']and not group['metal_components']
    net='diffusion_'+str(x['native_cluster'])
    diffusion_map.setdefault(x['native_cluster'],dict(net=net,native_net=x['native_net'],terminals=[]))
    assert diffusion_map[x['native_cluster']]['native_net']==x['native_net']
    diffusion_map[x['native_cluster']]['terminals'].append(dict(device=d['native_id'],terminal=term))
   witness['node']=net;nodes.append(net);witnesses.append(witness)
  out.append([d['instance'],*nodes,d['model'],*[k+'='+v for k,v in d['parameters'].items()]])
  records.append(dict(native_id=d['native_id'],instance=d['instance'],model=d['model'],native_model=d['native_model'],parameters=d['parameters'],terminals=witnesses))
 assert set(diffusion_map)==set(source_shared)
 for nid,g in diffusion_map.items():
  assert sorted(g['terminals'],key=lambda x:(x['device'],x['terminal']))==sorted(source_shared[nid]['terminals'],key=lambda x:(x['device'],x['terminal']))
 body_nodes={x['net']for x in body_map.values()};diff_nodes={x['net']for x in diffusion_map.values()}
 assert not(body_nodes&diff_nodes or body_nodes&set(wire_map.values())or diff_nodes&set(wire_map.values()))
 body_contacts={nid:[]for nid in body_map}
 for d in records:
  if d['model']in ('ptap1','ntap1'):
   by_term={t['terminal']:t for t in d['terminals']}
   well=by_term['WELL'];tie=by_term['TIE']
   assert well['node']in body_contacts and tie['disposition']==METAL
   body_contacts[well['node']].append(dict(instance=d['instance'],model=d['model'],
    body_node=well['node'],metal_node=tie['node'],metal_anchor=tie['reference_anchor'],resistance_ohm=d['parameters']['r']))
 auxiliary=[]
 for a in access:
  metal=wire_map[a['wire_anchor']];body=a['body_node']
  assert body in body_contacts and not body_contacts[body]
  assert a['instance'].lower()not in {x[0].lower()for x in out}
  out.append([a['instance'],metal,body,'ntap1','r='+a['parameters']['r']])
  rec=dict(instance=a['instance'],model='ntap1',body_node=body,metal_node=metal,
   metal_anchor=a['wire_anchor'],wire_component=a['wire_component'],point_dbu=a['point_dbu'],
   resistance_ohm=a['parameters']['r'],native_device_instance=False,island=a['island'])
  auxiliary.append(rec);body_contacts[body].append(rec)
 assert len(body_contacts)==65
 uncontacted=[body_map[nid]for nid,links in body_contacts.items()if not links]
 for r in rc:out.append([r[0],wire_map[r[1]],wire_map[r[2]],r[3]])
 interface=[*binding['native_ports'],'wire_cref'];assert len(interface)==len(set(interface))==18
 text='\n'.join(['* Native845 devices +4 actual regular tap access models +3381R/5105C. Body/poly/diffusion/salicide spreading/RF PEX not qualified.',
  '.subckt '+MODEL+' '+' '.join(interface),*[' '.join(r)for r in out],'.ends '+MODEL,''])
 assert sum('cap_cmim'in r for r in out)==26
 contract=dict(interface=interface,device_records=records,wire_node_map=wire_map,wire_node_owners=owners,
  body_map=body_map,body_contact_models=body_contacts,uncontacted_body_groups=uncontacted,
  shared_diffusion_map=diffusion_map,native_mim_planes=plane_changes,
  native_mim_cards_projected_once=mim,auxiliary_contact_models=auxiliary,
  actual_regular_body_assignments=body_plan['body_terminals'],
  counts=dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26),
  logical_points=1879,physical_points=1606,wire_components=235,exact_coincident_aliases=273,
  all_raw_wire_tokens_preserved=True,actual_native_mim_attachments_preserved=True,
  intrinsic_mim_models_emitted_once=True,qualified_pex=False,substrate_spreading_included=False,
  poly_diffusion_salicide_access_resistance_included=False,loaded_simulation_passed=False)
 return text,contract
def verify(text,binding,anchors,geometry,wiretext,mim_groups,body_plan):
 expected,contract=assemble(binding,anchors,geometry,wiretext,mim_groups,body_plan)
 got=parser.statements(text);wanted=parser.statements(expected)
 assert got[0]==wanted[0]and got[-1]==wanted[-1]
 by={r[0].lower():r for r in got[1:-1]};ref={r[0].lower():r for r in wanted[1:-1]}
 assert len(by)==len(got)-2 and set(by)==set(ref)
 for name,row in ref.items():
  actual=by[name]
  if name.startswith(('r','c')):
   assert actual[:3]==row[:3]and len(actual)==4 and parser.number(actual[3])==parser.number(row[3])
  else:assert actual==row
 return contract
def faults(text,binding,anchors,geometry,wiretext,mim_groups,body_plan):
 contract=verify(text,binding,anchors,geometry,wiretext,mim_groups,body_plan)
 original=parser.statements(text);cases=[]
 for kind in binding['census']:
  d=next(d for d in contract['device_records']if d['native_model']==kind)
  for fault in ('missing_instance','changed_parameter','changed_terminal'):
   rows=copy.deepcopy(original);i=next(i for i,r in enumerate(rows)if r[0]==d['instance'])
   if fault=='missing_instance':del rows[i]
   elif fault=='changed_terminal':rows[i][1]='FAULT_UNBOUND_NODE'
   else:
    key='r'if kind in ('ptap1','ntap1')else'nx'if kind=='npn13G2'else'w'
    k=next(k for k,v in enumerate(rows[i])if v.startswith(key+'='))
    rows[i][k]=key+'='+str(parser.number(rows[i][k].split('=')[1])*2)
   cases.append((kind+'_'+fault,rows))
 for kind in ('sg13_lv_nmos','sg13_hv_nmos','sg13_lv_pmos','sg13_hv_pmos'):
  d=next(d for d in contract['device_records']if d['model']==kind and d['terminals'][1]['node']!=d['terminals'][2]['node'])
  for fault in ('gate_source_swap','body_changed'):
   rows=copy.deepcopy(original);i=next(i for i,r in enumerate(rows)if r[0]==d['instance'])
   if fault=='gate_source_swap':rows[i][2],rows[i][3]=rows[i][3],rows[i][2]
   else:rows[i][4]='FAULT_BODY'
   cases.append((kind+'_'+fault,rows))
 for fault in ('dropped_wire_r','changed_wire_r','dropped_wire_c','changed_wire_c','extra_alias_resistor',
  'cref_supply_alias','body_wire_alias','shared_diffusion_wire_alias','duplicate_mim','retained_extractor_mim','same_conductor_mim_attachment_shift'):
  rows=copy.deepcopy(original)
  if fault in ('dropped_wire_r','changed_wire_r','dropped_wire_c','changed_wire_c'):
   prefix='R'if fault.endswith('_r')else'C';i=next(i for i,r in enumerate(rows)if r[0].startswith(prefix))
   if fault.startswith('dropped'):del rows[i]
   else:rows[i][3]=str(parser.number(rows[i][3])*2+1)
  elif fault=='extra_alias_resistor':rows.insert(-1,['R_ALIAS',binding['native_ports'][0],binding['native_ports'][1],'1'])
  elif fault=='cref_supply_alias':
   i=next(i for i,r in enumerate(rows)if r[0].startswith('C')and 'wire_cref'in r[1:3])
   k=rows[i].index('wire_cref');rows[i][k]=binding['native_ports'][0]
  elif fault in ('body_wire_alias','shared_diffusion_wire_alias'):
   prefix='body_'if fault=='body_wire_alias'else'diffusion_'
   i=next(i for i,r in enumerate(rows)if r[0].startswith('XD')and any(n.startswith(prefix)for n in r))
   k=next(k for k,n in enumerate(rows[i])if n.startswith(prefix));rows[i][k]=binding['native_ports'][0]
  elif fault=='duplicate_mim':
   cap=next(r for r in rows if 'cap_cmim'in r);rows.insert(-1,[cap[0]+'_DUPLICATE',*cap[1:]])
  elif fault=='retained_extractor_mim':rows.insert(-1,contract['native_mim_cards_projected_once'][0].copy())
  else:
   plane=contract['native_mim_planes'][0];did=plane['native_id'];old=plane['actual_native_attachment']
   other=next(n for n,owner in contract['wire_node_owners'].items()if owner==plane['wire_component']and n!=old)
   d=next(d for d in contract['device_records']if d['native_id']==did)
   i=next(i for i,r in enumerate(rows)if r[0]==d['instance'])
   k=1+next(k for k,t in enumerate(d['terminals'])if t['terminal']==plane['terminal'])
   rows[i][k]=contract['wire_node_map'][other]
  cases.append((fault,rows))
 for a in contract['auxiliary_contact_models']:
  for fault in ('missing_access','wrong_access_resistance','wrong_metal_point_same_conductor','wrong_nwell_island'):
   rows=copy.deepcopy(original);i=next(i for i,r in enumerate(rows)if r[0]==a['instance'])
   if fault=='missing_access':del rows[i]
   elif fault=='wrong_access_resistance':rows[i][-1]='r='+str(parser.number(a['resistance_ohm'])*2)
   elif fault=='wrong_nwell_island':
    rows[i][2]=next(x['body_node']for x in contract['auxiliary_contact_models']if x['body_node']!=a['body_node'])
   else:
    n=next(n for n,owner in contract['wire_node_owners'].items()if owner==a['wire_component']and n!=a['metal_anchor'])
    rows[i][1]=contract['wire_node_map'][n]
   cases.append((a['instance']+'_'+fault,rows))
 result=[]
 for name,rows in cases:
  mutant='\n'.join(' '.join(r)for r in rows)+'\n'
  assert parser.statements(mutant)!=original
  try:verify(mutant,binding,anchors,geometry,wiretext,mim_groups,body_plan)
  except (AssertionError,ValueError):result.append(dict(name=name,rejected=True,mutated_sha256=hashlib.sha256(mutant.encode()).hexdigest()))
  else:raise AssertionError('Accepted '+name)
 assert len(result)==62
 return result

