#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Test actual selector emitter areas without changing current-bias dimensions."""
import copy,json,subprocess
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v39_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
VARIANTS={'slave_select4':{'master':2,'slave':4},
          'all_select34':{'master':3,'slave':4}}
DIAG_ASSET=667470496
DIAG_SHA='d8006c4e3a2784a7062b8bbf0afa5f77911afd5f2c092d25144fe2fb34b6beb8'

def resized(params,old,new):
    assert type(old)is int and type(new)is int and (old,new)in ((2,3),(3,4))
    assert parser.number(params['nx'])==Decimal(old)
    result=copy.deepcopy(params);result['nx']=str(new)
    assert {k:v for k,v in result.items()if k!='nx'}=={k:v for k,v in params.items()if k!='nx'}
    return result

def selection(records,diag,variant):
    assert variant in VARIANTS and set(diag['stages'])==set('abcd')
    def record(n):
        d=records[n.removeprefix('xpd.')]
        assert d['model']=='npn13g2'
        return d
    def terminal(n,t):
        found=[x['native_cluster']for x in record(n)['terminals']if x['terminal']==t]
        assert len(found)==1
        return found[0]
    edits={};roles={};seen=set()
    for tag,stage in diag['stages'].items():
        graphs=stage['latches']['native_graph'];assert set(graphs)=={'master','slave'}
        for kind,g in graphs.items():
            track=g['track_selectors'];hold=g['hold_selectors']
            assert len(track)==len(hold)==2 and len(set(track+hold))==4
            assert not seen&set(track+hold);seen.update(track+hold)
            assert len({terminal(n,'E')for n in track+hold})==1
            assert len({terminal(n,'B')for n in track})==len({terminal(n,'B')for n in hold})==1
            assert terminal(track[0],'B')!=terminal(hold[0],'B')
            te=terminal(g['data_positive'],'E')
            assert te==terminal(g['data_negative'],'E')
            he={terminal(n,'E')for n in g['hold_pair']};assert len(he)==1 and te not in he
            assert {terminal(n,'C')for n in track}=={te}
            assert {terminal(n,'C')for n in hold}==he
            old=2 if kind=='master'else 3;new=VARIANTS[variant][kind]
            for side,names in [('track',track),('hold',hold)]:
                for name in names:
                    n=name.removeprefix('xpd.');d=record(name)
                    assert parser.number(d['parameters']['nx'])==Decimal(old)
                    if new!=old:
                        edits[n]=resized(d['parameters'],old,new)
                        roles[n]=dict(stage=tag,latch=kind,role='clock_selector',
                                      selector_side=side,parent_nx=old,candidate_nx=new)
    assert len(seen)==32 and len(edits)==(16 if variant=='slave_select4'else 32)
    return edits,roles

def controls():
    p=dict(nx='2',we='0.07u',le='0.9u',m='1')
    assert resized(p,2,3)==dict(p,nx='3') and p['nx']=='2'
    assert resized(dict(p,nx='3'),3,4)['nx']=='4'
    rejected=[]
    for label,params,a,b in [('wrong_parent',dict(p,nx='4'),2,3),
                            ('undeclared_target',p,2,4),('fractional',p,2,3.0),
                            ('no_change',p,2,2)]:
        try:resized(params,a,b)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Undeclared selector area accepted')
    return dict(rejected=rejected,all_other_parameters_retained=True)

def graph_controls(records,diag):
    checks=[]
    for variant in VARIANTS:selection(records,diag,variant)
    for label in ('duplicate_selector','missing_selector','wrong_collector',
                  'wrong_model','wrong_parent_area','unknown_variant'):
        rs=copy.deepcopy(records);ds=copy.deepcopy(diag);variant='all_select34'
        g=ds['stages']['c']['latches']['native_graph']['master']
        name=g['track_selectors'][0].removeprefix('xpd.')
        if label=='duplicate_selector':g['hold_selectors'][0]=g['track_selectors'][0]
        elif label=='missing_selector':g['track_selectors'].pop()
        elif label=='wrong_collector':
            next(t for t in rs[name]['terminals']if t['terminal']=='C')['native_cluster']=-777
        elif label=='wrong_model':rs[name]['model']='rppd'
        elif label=='wrong_parent_area':rs[name]['parameters']['nx']='4'
        else:variant='undeclared'
        try:selection(rs,ds,variant)
        except (AssertionError,KeyError):checks.append(label)
        else:raise AssertionError('Corrupt actual selector binding accepted: '+label)
    return checks

def apply(model,contract,planes,variant,out):
    assert variant in VARIANTS
    checks=controls()
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(DIAG_ASSET),
                                  '-H','Accept: application/octet-stream'])
    path=out/'v39-l18-early-native-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
    diag=json.loads(raw)
    assert diag['source_head']=='fedb0164d7bb87b9a4a7e287ca3ea92d791a2dcd'
    assert diag['all120original_hbt_checks_reproduced']and diag['all4original_sampler_checks_reproduced']
    assert diag['original_rejection_preserved']and not diag['accepted']and diag['original_devices_passed']
    base_dir=out/'v39-follower-l18-reference';base_dir.mkdir()
    base_model,base_contract,proof=previous.apply(model,contract,planes,'follower_l18',base_dir)
    assert len(proof['changes'])==76 and proof['all_wire_cards_unchanged']
    assert proof['candidate_model_sha256']==diag['exploratory_intrinsic_source']['candidate_model_sha256']
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in base_contract['device_records']}
    assert len(originals)==len(records)==476
    checks['actual_graph_faults']=graph_controls(records,diag)
    edits,added_roles=selection(records,diag,variant)
    candidate=copy.deepcopy(base_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    omit={'instance','original_parameters','candidate_parameters','original_card','candidate_card'}
    roles={c['instance']:{k:v for k,v in c.items()if k not in omit}for c in proof['changes']}
    roles.update(added_roles)
    original_rows=parser.statements(model.read_text());oldcards={r[0].lower():r for r in original_rows}
    parent_rows=parser.statements(base_model.read_text());newrows=[];changes=[]
    parent_changes=[]
    for row in parent_rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            positions=[i for i,s in enumerate(row)if s.startswith('nx=')];assert len(positions)==1
            i=positions[0];assert row[i]=='nx='+records[n]['parameters']['nx']
            new[i]='nx='+edits[n]['nx'];copies[n]['parameters']=copy.deepcopy(edits[n])
            parent_changes.append(dict(instance=n,**added_roles[n],parent_card=row,candidate_card=new))
        if new!=oldcards[n]:
            assert n in roles
            changes.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],
                                candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        newrows.append(new)
    changed={c['instance']for c in changes}
    assert len(parent_changes)==len(edits)==(16 if variant=='slave_select4'else 32)
    assert len(changes)==len(changed)==(76 if variant=='slave_select4'else 92)
    assert len(newrows)==476+17918+12850+2
    assert [r for r in parent_rows if r[0].lower()not in edits]==[r for r in newrows if r[0].lower()not in edits]
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
    restored=copy.deepcopy(candidate)
    for rec in restored['device_records']:
        if rec['instance'].lower()in changed:rec['parameters']=copy.deepcopy(originals[rec['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared topology, reference or primitive changed'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY: only selector Nx dimensions relative to v39 follower_l18; frozen wire RC.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v39_follower_l18',
        baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
        actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
        all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
        bias_dimensions_unchanged_relative_to_parent=True,data_hold_dimensions_unchanged_relative_to_parent=True,
        changes=changes,parent_changes=parent_changes,controls=checks,source_diagnosis_sha256=DIAG_SHA,
        diffusion_model_scope=proof['diffusion_model_scope'],
        scope='Only physical-selector HBT emitter count Nx on v39 follower_l18: slave3->4, optionally master2->3. Bias dimensions, data/hold devices, external phases/loads, all original bits, full120HBT/MOS/data/phase/current gates unchanged. Frozen RC is not new layout/PEX; increased area may worsen headroom or loading. Requires actual candidate GDS, DRC/LVS, fresh RC, full-loop/PVT qualification.')
