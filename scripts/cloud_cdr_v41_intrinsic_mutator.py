#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explore four actual retimer follower emitter counts; retain every original gate."""
import copy,json,subprocess
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v39_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
VARIANTS={'follower_n6':6,'follower_n8':8}
DIAG_ASSET=667470496
DIAG_SHA='d8006c4e3a2784a7062b8bbf0afa5f77911afd5f2c092d25144fe2fb34b6beb8'
def resized(params,nx):
    assert type(nx)is int and nx in (6,8)
    assert parser.number(params['nx'])==Decimal(4)
    assert parser.number(params['we'])==Decimal('.07e-6')
    assert parser.number(params['le'])==Decimal('.9e-6')
    result=copy.deepcopy(params);result['nx']=str(nx)
    assert {k:v for k,v in result.items()if k!='nx'}=={k:v for k,v in params.items()if k!='nx'}
    return result
def controls():
    p=dict(nx='4',we='.07u',le='.9u')
    for nx in VARIANTS.values():assert resized(p,nx)==dict(p,nx=str(nx))
    rejected=[]
    for label,params,nx in [('wrong-parent',dict(p,nx='3'),6),('wrong-width',dict(p,we='.08u'),6),
                            ('wrong-length',dict(p,le='1u'),6),('outside-recipe',p,10),('fractional',p,6.)]:
        try:resized(params,nx)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Undeclared follower accepted: '+label)
    return dict(rejected=rejected,only_declared_four_follower_areas=True)
def selection(records,planes,diag,variant):
    assert variant in VARIANTS and set(diag['retime_transfer'])=={'ac','bd'}
    logical={}
    for a in planes['anchors']:
        value=a['native_cluster']
        assert logical.setdefault(a['logical_net'],value)==value
    edits={};roles={}
    for macro,d in diag['retime_transfer'].items():
        pins=d['actual_parent_pins'];actual=d['actual_devices']
        assert set(actual)=={'positive','negative'}
        for polarity,row in actual.items():
            n=row['name'].removeprefix('xpd.')
            assert n not in edits
            record=records[n];assert record['model']=='npn13g2'and record['native_id']==row['native_id']
            terms={t['terminal']:t['native_cluster']for t in record['terminals']}
            ip,op=('ip','op')if polarity=='positive'else('inn','on')
            assert terms['B']==logical[pins[ip]]and terms['E']==logical[pins[op]]
            assert terms['C']==logical[pins['avdd']]
            edits[n]=resized(record['parameters'],VARIANTS[variant])
            roles[n]=dict(stage=macro,latch='retimer',role='emitter_follower',polarity=polarity,parent_nx=4,candidate_nx=VARIANTS[variant])
    assert len(edits)==4
    return edits,roles
def graph_controls(records,planes,diag):
    for variant in VARIANTS:selection(records,planes,diag,variant)
    faults=[]
    for label in ('duplicate-follower','wrong-emitter','wrong-base','wrong-collector','wrong-model','wrong-native-id'):
        rs,ds=copy.deepcopy((records,diag))
        a=ds['retime_transfer']['ac']['actual_devices'];n=a['positive']['name'].removeprefix('xpd.')
        if label=='duplicate-follower':a['negative']=copy.deepcopy(a['positive'])
        elif label.startswith('wrong-')and label.split('-')[1]in ('emitter','base','collector'):
            terminal={'emitter':'E','base':'B','collector':'C'}[label.split('-')[1]]
            next(t for t in rs[n]['terminals']if t['terminal']==terminal)['native_cluster']=-991
        elif label=='wrong-model':rs[n]['model']='rppd'
        else:rs[n]['native_id']=-992
        try:selection(rs,planes,ds,'follower_n6')
        except (AssertionError,KeyError):faults.append(label)
        else:raise AssertionError('Invalid physical binding accepted: '+label)
    return faults
def apply(model,contract,planes,variant,out):
    checks=controls()
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(DIAG_ASSET),
                                 '-H','Accept: application/octet-stream'])
    path=out/'v39-l18-early-native-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
    diag=json.loads(raw)
    assert diag['source_head']=='fedb0164d7bb87b9a4a7e287ca3ea92d791a2dcd'
    assert diag['all120original_hbt_checks_reproduced']and diag['all4original_sampler_checks_reproduced']
    assert diag['original_rejection_preserved']and not diag['accepted']and diag['original_devices_passed']
    parent=out/'v39-follower-l18-reference';parent.mkdir()
    parent_model,parent_contract,proof=previous.apply(model,contract,planes,'follower_l18',parent)
    assert len(proof['changes'])==76 and proof['all_wire_cards_unchanged']
    assert proof['candidate_model_sha256']==diag['exploratory_intrinsic_source']['candidate_model_sha256']
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in parent_contract['device_records']}
    assert len(records)==len(originals)==476
    checks['actual_graph_faults']=graph_controls(records,planes,diag)
    edits,newroles=selection(records,planes,diag,variant)
    assert not set(edits)&{c['instance']for c in proof['changes']}
    candidate=copy.deepcopy(parent_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    omitted={'instance','original_parameters','candidate_parameters','original_card','candidate_card'}
    roles={c['instance']:{k:v for k,v in c.items()if k not in omitted}for c in proof['changes']}
    roles.update(newroles)
    original_rows=parser.statements(model.read_text());oldcards={r[0].lower():r for r in original_rows}
    parent_rows=parser.statements(parent_model.read_text());rows=[];changes=[];added=[]
    for row in parent_rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            positions=[i for i,x in enumerate(row)if x.startswith('nx=')];assert len(positions)==1
            i=positions[0];assert row[i]=='nx='+records[n]['parameters']['nx']
            new[i]='nx='+edits[n]['nx'];copies[n]['parameters']=copy.deepcopy(edits[n])
            added.append(dict(instance=n,**newroles[n],parent_card=row,candidate_card=new))
        if new!=oldcards[n]:
            assert n in roles
            changes.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],
                candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        rows.append(new)
    assert len(added)==4 and len(changes)==len({c['instance']for c in changes})==80
    assert len(rows)==476+17918+12850+2
    assert [r for r in parent_rows if r[0].lower()not in edits]==[r for r in rows if r[0].lower()not in edits]
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in rows if r[0].startswith(('R','C'))]
    restored=copy.deepcopy(candidate)
    for r in restored['device_records']:
        if r['instance'].lower()in roles:r['parameters']=copy.deepcopy(originals[r['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared topology, native reference or primitive changed'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY four actual follower Nx4->6/8 on v39L1.8, frozen wire RC, no physical acceptance.\n'+'\n'.join(' '.join(r)for r in rows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v39_follower_l18',
      baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
      actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
      all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
      changes=changes,parent_changes=added,controls=checks,source_diagnosis_sha256=DIAG_SHA,
      diffusion_model_scope=proof['diffusion_model_scope'],
      scope='Only four actual ac/bd follower emitter counts4->6 or8. All selectors, data/hold HBTs, current-bias/resistor dimensions, original clocks/stimuli/loads/full windows and gates unchanged relative to v39follower_l18. Current/common-mode/loading changes are measured, never assumed beneficial. FrozenRC experiment requires fresh geometry/DRC/LVS/RC/PVT/loop validation.')
