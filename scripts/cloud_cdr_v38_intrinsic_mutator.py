#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Test reduced slave data/hold emitter count with unchanged drive and gates."""
import copy,json
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v36_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
VARIANTS={'data_area5':'5','data_area4':'4'}

def resized(params,nx):
    assert nx in VARIANTS.values()
    assert parser.number(params['nx'])==Decimal(6)
    assert parser.number(params['we'])==Decimal('.07e-6')
    assert parser.number(params['le'])==Decimal('.9e-6')
    result=copy.deepcopy(params);result['nx']=nx
    assert {k:v for k,v in result.items() if k!='nx'}=={k:v for k,v in params.items() if k!='nx'}
    return result

def controls():
    p=dict(nx='6',we='.07u',le='.9u')
    for nx in VARIANTS.values():
        q=resized(p,nx);assert q['nx']==nx and p['nx']=='6'
    rejected=[]
    for key,value,nx in [('nx','4','5'),('we','.08u','5'),('le','1u','5'),('nx','6','3'),('nx','6','7')]:
        bad=copy.deepcopy(p);bad[key]=value
        try:resized(bad,nx)
        except AssertionError:rejected.append((key,value,nx))
        else:raise AssertionError('Undeclared data/hold geometry accepted')
    return dict(rejected=rejected,only_declared_emitter_count_changes=True,
                new_current_density_or_headroom_proven=False)

def apply(model,contract,planes,variant,out):
    assert variant in VARIANTS
    checks=controls()
    receipt_path=ROOT/'docs/evidence/cdr-v36-four-full-screen-rejections-20261023.json'
    receipt=json.loads(receipt_path.read_text())
    assert receipt['run']==39850649751 and receipt['all_four_rejected']and not receipt['full_phy_accepted']
    parents=[c for c in receipt['cases']if c['variant']=='slave_drive15_load10']
    assert len(parents)==2 and {c['case']for c in parents}=={'nominal_early','nominal_late'}
    assert all(c['devices_passed']and c['samplers']['b']['passed']and not c['data_passed']
               and c['sources_unchanged']and c['returncode']==0 and not c['diagnostics']for c in parents)
    base_dir=out/'v36-slave-drive15-load10-reference';base_dir.mkdir()
    base_model,base_contract,proof=previous.apply(model,contract,planes,'slave_drive15_load10',base_dir)
    assert len(proof['changes'])==64 and proof['all_master_primitives_unchanged']and proof['all_wire_cards_unchanged']
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in base_contract['device_records']}
    candidate=copy.deepcopy(base_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    selected={c['instance']:c for c in proof['changes']if c['role']=='data_hold'}
    assert len(selected)==16 and {c['stage']for c in selected.values()}==set('abcd')
    edits={}
    for n,c in selected.items():
        assert c['latch']=='slave'and originals[n]['model']==records[n]['model']=='npn13g2'
        assert parser.number(originals[n]['parameters']['nx'])==Decimal(4)
        assert c['candidate_parameters']==records[n]['parameters']
        edits[n]=resized(records[n]['parameters'],VARIANTS[variant])
    roles={c['instance']:{k:c[k]for k in ['stage','latch','role']}for c in proof['changes']}
    original_rows=parser.statements(model.read_text());oldcards={r[0].lower():r for r in original_rows}
    rows=parser.statements(base_model.read_text());newrows=[];changes=[]
    for row in rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            positions=[i for i,s in enumerate(new)if s.startswith('nx=')];assert len(positions)==1
            i=positions[0];assert new[i]=='nx='+records[n]['parameters']['nx']
            new[i]='nx='+edits[n]['nx'];copies[n]['parameters']=copy.deepcopy(edits[n])
        if new!=oldcards[n]:
            assert n in roles
            changes.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],
                                candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        newrows.append(new)
    expected=48 if VARIANTS[variant]=='4'else 64
    assert len(changes)==expected and len(newrows)==476+17918+12850+2
    changed={c['instance']for c in changes};assert len(changed)==expected
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
    assert [r for r in original_rows if r[0].lower()not in changed]==[r for r in newrows if r[0].lower()not in changed]
    restored=copy.deepcopy(candidate)
    for rec in restored['device_records']:
        if rec['instance'].lower()in changed:rec['parameters']=copy.deepcopy(originals[rec['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared topology, native reference or parameter edit'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY: smaller slave data/hold emitter count on v36 drive15/load10, frozen wire RC; not physical acceptance.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='slave_drive15_load10',
        baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
        actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
        all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,all_master_primitives_unchanged=True,
        unchanged_original_gates=True,changes=changes,controls=checks,
        data_hold_relative_to_parent=[dict(instance=n,**roles[n],parent_nx='6',candidate_nx=VARIANTS[variant])for n in sorted(selected)],
        source_parent_receipt_sha256=sha(receipt_path),diffusion_model_scope=proof['diffusion_model_scope'],
        scope='Only16 slave data/hold HBT emitter counts6->5 or4 relative to rejected v36 load10. Slave selectorsNx3,54um MOS drive/diffusion hypothesis,collector1.0um/bleed12 and all original clocks,biases,loads,samples and gates retained. No inferred current/headroom acceptance; requires new full native and candidate physical/PVT/loop qualification.')
