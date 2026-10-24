#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Screen matched HBT area changes; preserve original gates and all frozen wire RC."""
import copy,json,subprocess
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v33_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
VARIANTS={'slave_area15':('slave',3,6),'all_area15':('all',3,6),'all_area20':('all',4,8)}
DIAG_SHA='27660d1d4c18160a5932f5ca5852d4272908a7fd673cd34c0fd971021d9fce26'
def apply(model,contract,planes,variant,out):
 assert variant in VARIANTS
 raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/665725446','-H','Accept: application/octet-stream'])
 path=out/'v33-native-steering-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
 diag=json.loads(raw)
 assert diag['source_head']=='a63c0e9775bb1d671a82660db88ff31c2e0917ee'
 assert diag['case']=='nominal_early'and diag['variant']=='bleed12'
 assert diag['all120original_hbt_checks_reproduced']and diag['all4original_sampler_checks_reproduced']and diag['original_rejection_preserved']
 assert diag['original_devices_passed']and not diag['accepted']
 base_dir=out/'bleed12-base';base_dir.mkdir()
 base_model,base_contract,base_proof=previous.apply(model,contract,planes,'bleed12',base_dir)
 target,selector_nx,data_nx=VARIANTS[variant];selected={}
 for tag,stage in diag['stages'].items():
  for latch,g in stage['latches']['native_graph'].items():
   if target!='all'and latch!=target:continue
   for role,names,old,new in [
    ('selector',g['track_selectors']+g['hold_selectors'],2,selector_nx),
    ('data_hold',[g['data_positive'],g['data_negative']]+g['hold_pair'],4,data_nx)]:
    assert len(names)==len(set(names))==4
    for name in names:
     key=name.removeprefix('xpd.');assert key not in selected
     selected[key]=dict(stage=tag,latch=latch,role=role,old_nx=old,new_nx=new)
 assert len(selected)==(32 if target=='slave'else 64)
 records={r['instance'].lower():r for r in base_contract['device_records']}
 candidate=copy.deepcopy(base_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
 assert len(records)==len(copies)==476
 rows=parser.statements(base_model.read_text());newrows=[];changes=[]
 for row in rows:
  new=row.copy();name=row[0].lower()
  if name in selected:
   spec=selected[name];record=records[name]
   assert record['model']=='npn13g2'and parser.number(record['parameters']['nx'])==Decimal(spec['old_nx'])
   positions=[i for i,v in enumerate(row)if v.startswith('nx=')];assert len(positions)==1
   i=positions[0];assert row[i]=='nx='+record['parameters']['nx']
   value=str(spec['new_nx']);new[i]='nx='+value;copies[name]['parameters']['nx']=value
   changes.append(dict(instance=name,**spec,original_card=row,candidate_card=new))
  newrows.append(new)
 assert len(changes)==len(selected)
 original=parser.statements(model.read_text())
 assert len(original)==len(newrows)==476+17918+12850+2
 assert [r for r in original if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
 changed_names=set(selected)|{c['instance']for c in base_proof['changes']}
 assert len(changed_names)==len(selected)+8
 assert [r for r in original if r[0].lower()not in changed_names]==[r for r in newrows if r[0].lower()not in changed_names]
 restored=copy.deepcopy(candidate);restored_by_name={r['instance'].lower():r for r in restored['device_records']}
 for name in selected:restored_by_name[name]['parameters']['nx']=records[name]['parameters']['nx']
 assert restored==base_contract,'Unexpected topology or parameter change'
 output=out/('exploratory-'+variant+'.spice')
 output.write_text('* EXPLORATORY: matched HBT area and slave bleed dimensions on frozen v32 RC; no candidate GDS or fresh extraction.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
 (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
 return output,candidate,dict(variant=variant,baseline_model_sha256=sha(model),bleed12_model_sha256=sha(base_model),candidate_model_sha256=sha(output),
  actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
  all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
  resistor_changes=base_proof['changes'],hbt_area_changes=changes,
  scope='Exploratory matched HBT area increases with fixed original stimuli and current/safety/data/phase gates; eight disclosed slave-bleed edits retained from bleed12. Frozen wire RC, unchanged external clocks and loads. Any useful result requires actual layout, DRC/LVS, fresh RC and repeated full tests.')
