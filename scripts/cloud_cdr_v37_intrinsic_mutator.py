#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lower C/D input-divider impedance together; preserve its nominal ratio."""
import copy,json
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v36_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
VARIANTS={'cdbias15':'6','cdbias20':'8'}

def resized(params,width):
    assert width in VARIANTS.values()
    assert parser.number(params['w'])==Decimal('4e-6')
    assert parser.number(params['l']) in (Decimal('1.2e-6'),Decimal('.9e-6'))
    result=copy.deepcopy(params);result['w']=width+'u'
    assert {k:v for k,v in result.items() if k!='w'}=={k:v for k,v in params.items() if k!='w'}
    return result

def controls():
    a=dict(w='4u',l='1.2u',b='0',sw_et='1')
    b=dict(w='4u',l='.9u',b='0',sw_et='1')
    for width in VARIANTS.values():
        aa,bb=resized(a,width),resized(b,width)
        old_ratio=(parser.number(a['l'])/parser.number(a['w']))/(parser.number(b['l'])/parser.number(b['w']))
        new_ratio=(parser.number(aa['l'])/parser.number(aa['w']))/(parser.number(bb['l'])/parser.number(bb['w']))
        assert old_ratio==new_ratio and aa['w']==bb['w']
    rejected=[]
    for key,value,width in [('w','5u','6'),('l','.8u','6'),('w','4u','7')]:
        bad=copy.deepcopy(a);bad[key]=value
        try:resized(bad,width)
        except AssertionError:rejected.append((key,value,width))
        else:raise AssertionError('Undeclared divider geometry accepted')
    assert a['w']==b['w']=='4u'
    return dict(rejected=rejected,nominal_geometry_ratio_preserved=True,
                actual_commonmode_and_gain_preservation_proven=False,
                scope='Only nominal geometry ratio proof; real wire/loading/contact effects require full native results.')

def apply(model,contract,planes,variant,out):
    assert variant in VARIANTS
    checks=controls()
    receipt_path=ROOT/'docs/evidence/cdr-v35-input-bias-results-20261023.json'
    receipt=json.loads(receipt_path.read_text())
    assert receipt['run']==39856218758 and len(receipt['cases'])==2
    assert all(c['original_rejection_preserved']and c['all120original_hbt_checks_reproduced']
               and c['all4original_sampler_checks_reproduced']and not c['accepted']for c in receipt['cases'])
    selected=receipt['selected_native_resistors']
    assert set(selected)=={'c','d'}
    base_dir=out/'v36-slave-drive15-load12-reference';base_dir.mkdir()
    base_model,base_contract,proof=previous.apply(model,contract,planes,'slave_drive15_load12',base_dir)
    assert len(proof['changes'])==64 and proof['all_master_primitives_unchanged'] and proof['all_wire_cards_unchanged']
    originals={r['instance'].lower():r for r in contract['device_records']}
    base_records={r['instance'].lower():r for r in base_contract['device_records']}
    candidate=copy.deepcopy(base_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    edits={};roles={}
    for stage,polarities in selected.items():
        assert set(polarities)=={'positive','negative'}
        for polarity,pair in polarities.items():
            assert set(pair)=={'input_resistor','bias_resistor'}
            for role,rec in pair.items():
                n=rec['instance'].lower()
                assert n not in edits and rec==originals[n]==base_records[n]
                assert rec['model']=='rppd'
                new=resized(rec['parameters'],VARIANTS[variant])
                edits[n]=new;roles[n]=dict(stage=stage,latch='master',role=role,polarity=polarity)
    assert len(edits)==8
    assert not set(edits)&{c['instance']for c in proof['changes']}
    rows=parser.statements(base_model.read_text());original_rows=parser.statements(model.read_text())
    oldcards={r[0].lower():r for r in original_rows}
    newrows=[];added=[]
    for row in rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            positions=[i for i,s in enumerate(new)if s.startswith('w=')];assert len(positions)==1
            i=positions[0];assert new[i]=='w='+originals[n]['parameters']['w']
            new[i]='w='+edits[n]['w'];copies[n]['parameters']=copy.deepcopy(edits[n])
            added.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],
                              candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        newrows.append(new)
    changes=proof['changes']+added
    assert len(added)==8 and len(changes)==72 and len(newrows)==476+17918+12850+2
    changed={c['instance']for c in changes};assert len(changed)==72
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
    assert [r for r in original_rows if r[0].lower()not in changed]==[r for r in newrows if r[0].lower()not in changed]
    restored=copy.deepcopy(candidate)
    for rec in restored['device_records']:
        if rec['instance'].lower()in changed:rec['parameters']=copy.deepcopy(originals[rec['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared native topology, references or parameter change'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY: balanced C/D divider widths and v36 slave drive/load; frozen wire RC; no physical acceptance.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
        parent_variant='slave_drive15_load12',actual_candidate_layout_verified=False,fresh_candidate_rc=False,
        wire_R=17918,wire_C=12850,all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,
        all_master_primitives_unchanged=False,only_eight_master_input_resistors_changed=True,
        unchanged_original_gates=True,controls=checks,changes=changes,
        source_diagnosis_sha256=sha(receipt_path),diffusion_model_scope=proof['diffusion_model_scope'],
        scope='Retain v36 load12 slave32HBT/16MOS/16resistor recipe; only eight C/D input/bias resistors widen4->6 or8um together. Nominal ratio is retained, actual common-mode/gain/headroom is not assumed. Original external clocks/biases/data,150fF/50fF loads and complete electrical gates unchanged. Requires actual candidate GDS/DRC/LVS/fresh RC/PVT/closed-loop qualification.')
