#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit exploratory intrinsic-geometry screen on unchanged v32 wire RC."""
import copy,json,subprocess
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
VARIANTS={'bleed12':'2.6','load20':'2.0','load16':'1.6'}
DIAG_SHA='e0634f115cb578bd19d4bcd90bfbf19b87f87cc32cb6339804ce512679c09cc0'
def apply(model,contract,planes,variant,out):
 assert variant in VARIANTS
 raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/665296163','-H','Accept: application/octet-stream'])
 path=out/'v32-native-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
 diag=json.loads(raw)
 assert diag['source_head']=='0560b231f7dbfb1a09b70b9679849a69c83f2dfe'
 assert diag['all120original_hbt_checks_reproduced']and diag['all4original_sampler_checks_reproduced']and diag['original_rejection_preserved']
 assert diag['original_devices_passed']and not diag['accepted']
 records={d['instance'].lower():d for d in contract['device_records']}
 assert len(records)==476
 logical={}
 for a in planes['anchors']:
  assert logical.setdefault(a['logical_net'],a['native_cluster'])==a['native_cluster']
 def term(name,t):
  d=records[name.removeprefix('xpd.')]
  return next(x['native_cluster']for x in d['terminals']if x['terminal']==t)
 resistor_records={n:d for n,d in records.items()if d['model']=='rppd'}
 assert len(resistor_records)==98
 def between(a,b):
  found=[n for n,d in resistor_records.items()if {a,b}<={t['native_cluster']for t in d['terminals']}]
  assert len(found)==1,(a,b,found)
  return found[0]
 selected={}
 for tag,stage in diag['stages'].items():
  for kind,g in stage['latches']['native_graph'].items():
   for polarity in ['positive','negative']:
    n=between(logical['avdd'],g[polarity+'_output_native'])
    assert n not in selected
    selected[n]=dict(stage=tag,latch=kind,role='collector_load',width_um='32',old_length_um='2.6',new_length_um=VARIANTS[variant])
   if kind=='slave':
    for role,selectors,old,new in [('track_bleed',g['track_selectors'],'6.4','12.8'),('hold_bleed',g['hold_selectors'],'4.8','9.6')]:
     clusters={term(n,'C')for n in selectors};assert len(clusters)==1
     n=between(logical['avss'],next(iter(clusters)));assert n not in selected
     selected[n]=dict(stage=tag,latch=kind,role=role,width_um='1',old_length_um=old,new_length_um=new)
 assert len(selected)==24 and sum(v['role']=='collector_load'for v in selected.values())==16
 text=model.read_text();rows=parser.statements(text);newrows=[];changed=[];candidate=copy.deepcopy(contract)
 copies={d['instance'].lower():d for d in candidate['device_records']}
 assert len(rows)==476+17918+12850+2
 for row in rows:
  new=row.copy();name=row[0].lower()
  if name in selected:
   spec=selected[name];d=records[name];params=d['parameters']
   assert parser.number(params['w'])==Decimal(spec['width_um'])*Decimal('1e-6')
   assert parser.number(params['l'])==Decimal(spec['old_length_um'])*Decimal('1e-6')
   positions=[i for i,v in enumerate(row)if v.startswith('l=')];assert len(positions)==1
   i=positions[0];assert row[i]=='l='+params['l']
   if Decimal(spec['new_length_um'])!=Decimal(spec['old_length_um']):
    value=spec['new_length_um']+'u';new[i]='l='+value;copies[name]['parameters']['l']=value
    changed.append(dict(instance=name,**spec,original_card=row,candidate_card=new))
  newrows.append(new)
 assert len(changed)==(8 if variant=='bleed12'else24)
 assert [r for r in rows if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
 assert [r for r in rows if r[0].lower()not in selected]==[r for r in newrows if r[0].lower()not in selected]
 candidate_path=out/('exploratory-'+variant+'.spice')
 candidate_path.write_text('* EXPLORATORY: intrinsic dimensions changed on frozen v32 wire RC; no candidate layout or extraction.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
 (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
 return candidate_path,candidate,dict(variant=variant,baseline_model_sha256=sha(model),candidate_model_sha256=sha(candidate_path),actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,changes=changed,unchanged_original_gates=True,scope='Intrinsic PDK dimension screen only, not post-layout acceptance. All original bits, samples, vectors, loads, clock/data phases and electrical gates retained. Any useful candidate requires actual GDS, DRC/LVS, fresh RC and repeated full loaded tests.')
