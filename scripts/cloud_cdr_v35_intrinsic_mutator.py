#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Isolate slave collector loading; retain original masters and all HBT geometry."""
import copy,json
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v33_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
VARIANTS={'slave_load20':'load20','slave_load16':'load16'}
def apply(model,contract,planes,variant,out):
    assert variant in VARIANTS
    base_dir=out/'all-load-reference';base_dir.mkdir()
    base_model,base_contract,proof=previous.apply(model,contract,planes,VARIANTS[variant],base_dir)
    assert len(proof['changes'])==24 and proof['all_wire_cards_unchanged']
    original=parser.statements(model.read_text())
    originals={r[0].lower():r for r in original[1:-1]}
    rows=parser.statements(base_model.read_text())
    candidate=copy.deepcopy(base_contract)
    source_records={r['instance'].lower():r for r in contract['device_records']}
    candidates={r['instance'].lower():r for r in candidate['device_records']}
    masters={c['instance']:c for c in proof['changes'] if c['latch']=='master'}
    retained=[c for c in proof['changes'] if c['latch']=='slave']
    assert len(masters)==8 and len(retained)==16
    assert all(c['role']=='collector_load' for c in masters.values())
    assert sum(c['role']=='collector_load'for c in retained)==8
    assert sum(c['role'] in ('track_bleed','hold_bleed')for c in retained)==8
    newrows=[]
    for row in rows:
        name=row[0].lower()
        if name in masters:
            change=masters[name]
            assert row==change['candidate_card'] and originals[name]==change['original_card']
            newrows.append(copy.deepcopy(originals[name]))
            candidates[name]['parameters']=copy.deepcopy(source_records[name]['parameters'])
        else:newrows.append(row)
    changed={c['instance']for c in retained}
    assert len(changed)==16 and len(original)==len(newrows)==476+17918+12850+2
    assert [r for r in original if r[0].lower()not in changed]==[r for r in newrows if r[0].lower()not in changed]
    assert [r for r in original if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
    assert all(candidates[n]==d for n,d in source_records.items()if d['model']=='npn13g2')
    restored=copy.deepcopy(candidate)
    for d in restored['device_records']:
        if d['instance'].lower()in changed:
            d['parameters']=copy.deepcopy(source_records[d['instance'].lower()]['parameters'])
    assert restored==contract,'Unexpected physical reference, topology or parameter edit'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY: only eight slave collector loads and eight slave bleeds changed; frozen v32 wire RC; not layout acceptance.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,baseline_model_sha256=sha(model),
        candidate_model_sha256=sha(output),actual_candidate_layout_verified=False,fresh_candidate_rc=False,
        wire_R=17918,wire_C=12850,all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,
        all_master_collector_loads_unchanged=True,all_hbt_geometry_unchanged=True,
        changes=retained,restored_master_loads=list(masters.values()),unchanged_original_gates=True,
        scope='Isolate slave collector loads at2.0um or1.6um length with32um width; original masters2.6um and HBT areas remain. Eight bleed12 dimensions retained. All original external clocks, stimulus,150fF/50fF loads,34.25ns samples and electrical gates unchanged. Requires actual GDS/DRC/LVS/fresh RC and repeated full simulation before physical acceptance.')
