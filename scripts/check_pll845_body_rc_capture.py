#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Whole PLL native capture checks; a raw R/C audit is still separately required."""
import copy,json
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser

def exact_mim_dimensions(device):
 """Use integer GDS geometry; allow only one binary64 ULP in native dimensions."""
 import math
 box=device['mask_bbox_dbu']
 assert len(box)==4 and all(type(v)is int for v in box)
 x=Decimal(box[2]-box[0])/Decimal(1000);y=Decimal(box[3]-box[1])/Decimal(1000)
 assert x>0 and y>0
 values=tuple(float(device['parameters'][k])for k in ('w','l'))
 assert all(math.isfinite(v)and v>0 for v in values)
 candidates=set()
 for dims in ((x,y),(y,x)):
  if all(abs(float(d)-v)<=math.ulp(v)for d,v in zip(dims,values)):candidates.add(dims)
 assert len(candidates)==1,'Native MIM dimensions do not match integer GDS within one binary64 ULP'
 return next(iter(candidates))
def dimension_controls(mim):
 result=[]
 for fault in ('native_dimension_metadata_shift_1nm','mask_dimension_metadata_shift_1nm'):
  rejected=0
  for device in mim['native_mim_bindings']:
   exact_mim_dimensions(device);bad=copy.deepcopy(device)
   if fault=='native_dimension_metadata_shift_1nm':bad['parameters']['w']+=.001
   else:bad['mask_bbox_dbu'][2]+=1
   try:exact_mim_dimensions(bad)
   except AssertionError:rejected+=1
   else:raise AssertionError('Accepted one-nanometre dimension metadata corruption')
  assert rejected==26
  result.append(dict(name=fault,rejected=True,actual_source_device_cases=rejected,
   corruption_scope='native/GDS dimension metadata; original GDS bytes unchanged'))
 return result

def check_capture(text,anchors,mim,diagnostic_path=None):
 rows=parser.statements(text)
 assert rows[0][:2]==['.subckt','pump_wires']and rows[-1][0]=='.ends'
 points={x['label']:x for x in anchors['anchors']}
 assert len(points)==anchors['physical_anchor_count']and len(points)>17
 assert len(rows[0][2:])==len(points)and set(rows[0][2:])==set(points)
 R=[];C=[];X=[]
 for row in rows[1:-1]:
  if row[0].startswith('R'):
   assert len(row)==4 and parser.number(row[3])>0;R.append(row)
  elif row[0].startswith('C'):
   assert len(row)==4 and parser.number(row[3])>=0;C.append(row)
  else:
   assert row[0].startswith('X')and len(row)==6 and row[3]=='cap_cmim';X.append(row)
 assert len({x[0]for x in rows[1:-1]})==len(rows)-2 and len(X)==26
 assert R and C
 graph=parser.Union()
 for _,a,b,v in R:graph.join(a,b)
 owners={}
 for name,point in points.items():
  assert name in graph.parent,'Physical point unattached to native R graph'
  root=graph.find(name);owners.setdefault(root,point['wire_component'])
  assert owners[root]==point['wire_component'],'Distinct physical conductors shorted'
 assert len(owners)==len(set(owners.values()))==235
 assert all(graph.find(n)in owners for n in graph.parent),'Unanchored R component'
 for _,a,b,v in C:assert all(n=='sub'or n in graph.parent for n in (a,b))
 terminal={(r['device'],r['terminal']):r for r in anchors['rows']}
 assert len(terminal)==2737 and anchors['logical_anchor_count']==1879
 expected=Counter();identity_groups=defaultdict(list)
 for device in mim['native_mim_bindings']:
  did=device['native_id'];pair=tuple(terminal[did,t]['wire_component']for t in ('mim_top','mim_btm'))
  assert pair[0]!=pair[1]
  key=(*pair,*exact_mim_dimensions(device))
  expected[key]+=1;identity_groups[key].append(did)
 assert sum(expected.values())==26
 actual=Counter();exports=defaultdict(list)
 for x in X:
  assert all(n in graph.parent for n in x[1:3])
  p=dict(v.split('=')for v in x[4:]);assert set(p)=={'w','l'}
  key=(owners[graph.find(x[1])],owners[graph.find(x[2])],
       parser.number(p['w'])/Decimal('1e-6'),parser.number(p['l'])/Decimal('1e-6'))
  actual[key]+=1;exports[key].append(x[0])
 if diagnostic_path is not None:
  def serial(counter):
   return [dict(plus_component=k[0],minus_component=k[1],w_um=str(k[2]),l_um=str(k[3]),count=v)for k,v in counter.items()]
  diagnostic_path.write_text(json.dumps(dict(R=len(R),C=len(C),physical_points=len(points),
   expected=serial(expected),actual=serial(actual),missing=serial(expected-actual),extra=serial(actual-expected),
   native_dimensions=[dict(native_id=d['native_id'],parameters=d['parameters'],mask_bbox_dbu=d['mask_bbox_dbu'])for d in mim['native_mim_bindings']]),indent=2)+'\n')
 assert actual==expected,'Native MIM terminal-owner/dimension multiset differs'
 return dict(status='PASS_CAPTURE_235_COMPONENTS_AND26_NATIVE_MIM_MULTISET_REQUIRES_RAW_RC_AUDIT',
  R=len(R),C=len(C),physical_components=235,physical_points=len(points),logical_points=1879,
  native_mim_devices=26,mim_groups=[dict(plus_component=k[0],minus_component=k[1],
   w_um=str(k[2]),l_um=str(k[3]),native_ids=sorted(ids),export_instances=sorted(exports[k]),
   per_device_identity_unique=len(ids)==1)for k,ids in identity_groups.items()],
  all_mim_identities_unique=all(len(v)==1 for v in identity_groups.values()),
  dimension_proofs=[dict(native_id=d['native_id'],native_w_um=str(d['parameters']['w']),
   native_l_um=str(d['parameters']['l']),exact_gds_w_um=str(exact_mim_dimensions(d)[0]),
   exact_gds_l_um=str(exact_mim_dimensions(d)[1]),mask_bbox_dbu=d['mask_bbox_dbu'],
   maximum_native_float_discrepancy_ulps=1)for d in mim['native_mim_bindings']],
  raw_point_capacitance_audited=False,qualified_pex=False,full_phy_accepted=False)
def fault_controls(text,anchors,mim):
 rows=parser.statements(text);controls=[]
 for label in ('missing_mim','wrong_mim_width','swapped_mim_plates','wrong_mim_model',
               'cross_wire_short','missing_physical_port','negative_resistance','negative_capacitance'):
  changed=copy.deepcopy(rows);i=next(i for i,x in enumerate(changed)if x[0].startswith('X'))
  if label=='missing_mim':del changed[i]
  elif label=='wrong_mim_width':
   k=next(k for k,x in enumerate(changed[i])if x.startswith('w='));changed[i][k]='w=999u'
  elif label=='swapped_mim_plates':changed[i][1],changed[i][2]=changed[i][2],changed[i][1]
  elif label=='wrong_mim_model':changed[i][3]='cap_rfcmim'
  elif label=='cross_wire_short':
   a=anchors['anchors'][0];b=next(x for x in anchors['anchors']if x['wire_component']!=a['wire_component'])
   changed.insert(-1,['R_FAULT',a['label'],b['label'],'1'])
  elif label=='missing_physical_port':changed[0].pop()
  else:
   prefix='R'if label=='negative_resistance'else'C'
   next(x for x in changed if x[0].startswith(prefix))[3]='-1'
  mutant='\n'.join(' '.join(x)for x in changed)+'\n'
  try:check_capture(mutant,anchors,mim)
  except (AssertionError,ValueError):controls.append(dict(name=label,rejected=True))
  else:raise AssertionError('Native capture accepted '+label)
 assert len(controls)==8
 return controls
