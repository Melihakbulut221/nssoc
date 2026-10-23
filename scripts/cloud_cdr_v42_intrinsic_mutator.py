#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Screen C/D slave data/hold area from source-bound failed v41 native evidence."""
import copy,json,subprocess
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v41_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
VARIANTS={'slave_data4':4,'slave_data5':5}
DIAG_ASSET=668715769
DIAG_SHA='be4bec77ce03a2b35bfe6c316701919f3101b546809c3355648ed74103d278e7'
def resized(params,nx):
    assert type(nx)is int and nx in (4,5)
    assert parser.number(params['nx'])==Decimal(6)
    assert parser.number(params['we'])==Decimal('.07e-6')
    assert parser.number(params['le'])==Decimal('.9e-6')
    result=copy.deepcopy(params);result['nx']=str(nx)
    assert {k:v for k,v in result.items()if k!='nx'}=={k:v for k,v in params.items()if k!='nx'}
    return result
def controls():
    p=dict(nx='6',we='.07u',le='.9u')
    for nx in VARIANTS.values():assert resized(p,nx)==dict(p,nx=str(nx))
    rejected=[]
    for label,params,nx in [('wrong-parent',dict(p,nx='4'),5),('wrong-width',dict(p,we='.08u'),4),
                            ('wrong-length',dict(p,le='1u'),4),('outside-recipe',p,3),('fractional',p,4.)]:
        try:resized(params,nx)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Undeclared slave area accepted: '+label)
    return dict(rejected=rejected,only_declared_cd_slave_data_hold_areas=True)
def selection(records,diag,variant):
    assert variant in VARIANTS
    edits={};roles={}
    for tag in ('c','d'):
        bank=diag['stages'][tag]['latches']['native_graph']['slave']
        names=[bank['data_positive'],bank['data_negative'],*bank['hold_pair']]
        selectors=set(bank['track_selectors']+bank['hold_selectors'])
        assert len(names)==len(set(names))==4 and len(selectors)==4 and not set(names)&selectors
        ts={}
        for full in names:
            n=full.removeprefix('xpd.');record=records[n]
            assert record['model']=='npn13g2'and n not in edits
            assert int(n[2:])==record['native_id']
            ts[full]={t['terminal']:t['native_cluster']for t in record['terminals']}
            assert ts[full]['C']in (bank['positive_output_native'],bank['negative_output_native'])
            edits[n]=resized(record['parameters'],VARIANTS[variant])
            roles[n]=dict(stage=tag,latch='slave',role='data_hold',parent_nx=6,candidate_nx=VARIANTS[variant])
        dp,dn=bank['data_positive'],bank['data_negative'];hp,hn=bank['hold_pair']
        assert ts[dp]['B']==bank['positive_input_native']and ts[dn]['B']==bank['negative_input_native']
        assert ts[dp]['C']!=ts[dn]['C']and ts[hp]['C']!=ts[hn]['C']
        assert ts[dp]['E']==ts[dn]['E']and ts[hp]['E']==ts[hn]['E']and ts[dp]['E']!=ts[hp]['E']
        assert ts[hp]['B']==ts[hn]['C']and ts[hn]['B']==ts[hp]['C']
    assert len(edits)==8
    return edits,roles
def graph_controls(records,diag):
    for variant in VARIANTS:selection(records,diag,variant)
    rejected=[]
    for label in ('duplicate-device','wrong-collector','wrong-data-base','wrong-hold-base','wrong-emitter','wrong-model','wrong-native-id','wrong-parent-area'):
        rs,ds=copy.deepcopy((records,diag));bank=ds['stages']['c']['latches']['native_graph']['slave']
        name=bank['hold_pair'][0]if label=='wrong-hold-base'else bank['data_positive']
        n=name.removeprefix('xpd.')
        if label=='duplicate-device':bank['data_negative']=bank['data_positive']
        elif label in ('wrong-collector','wrong-data-base','wrong-hold-base','wrong-emitter'):
            terminal={'wrong-collector':'C','wrong-data-base':'B','wrong-hold-base':'B','wrong-emitter':'E'}[label]
            next(t for t in rs[n]['terminals']if t['terminal']==terminal)['native_cluster']=-991
        elif label=='wrong-model':rs[n]['model']='rppd'
        elif label=='wrong-native-id':rs[n]['native_id']=-992
        else:rs[n]['parameters']['nx']='4'
        try:selection(rs,ds,'slave_data4')
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Invalid physical selection accepted: '+label)
    return rejected
def apply(model,contract,planes,variant,out):
    checks=controls()
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(DIAG_ASSET),'-H','Accept: application/octet-stream'])
    path=out/'v41-n8-early-native-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
    diag=json.loads(raw)
    assert diag['source_head']=='e3e6c292c81368c193d9635fd8f53d9dfd3ae656'
    assert diag['all120original_hbt_checks_reproduced']and diag['all4original_sampler_checks_reproduced']
    assert diag['original_rejection_preserved']and not diag['accepted']and diag['original_devices_passed']
    for tag in ('c','d'):
        observed=diag['stages'][tag]['latches']['steering_transition_windows']['counts']
        assert observed['unique_transition']==255 and observed['master_output_below_100mv_at_original_deadline']==0
        assert observed['slave_output_below_original_100mv_gate_at_deadline']>0
    parent=out/'v41-follower-n8-reference';parent.mkdir()
    parent_model,parent_contract,proof=previous.apply(model,contract,planes,'follower_n8',parent)
    assert len(proof['changes'])==80 and proof['all_wire_cards_unchanged']
    assert proof['candidate_model_sha256']==diag['exploratory_intrinsic_source']['candidate_model_sha256']
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in parent_contract['device_records']}
    assert len(records)==len(originals)==476
    checks['actual_graph_faults']=graph_controls(records,diag)
    edits,newroles=selection(records,diag,variant)
    prior_roles={c['instance']:c for c in proof['changes']}
    assert set(edits)<=set(prior_roles)
    assert all(prior_roles[n]['stage']in ('c','d')and prior_roles[n]['latch']=='slave'and prior_roles[n]['role']=='data_hold'for n in edits)
    candidate=copy.deepcopy(parent_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    omitted={'instance','original_parameters','candidate_parameters','original_card','candidate_card'}
    roles={c['instance']:{k:v for k,v in c.items()if k not in omitted}for c in proof['changes']}
    roles.update(newroles)
    original_rows=parser.statements(model.read_text());oldcards={r[0].lower():r for r in original_rows}
    parent_rows=parser.statements(parent_model.read_text());rows=[];changes=[];changed_parent=[]
    for row in parent_rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            positions=[i for i,x in enumerate(row)if x.startswith('nx=')];assert len(positions)==1
            i=positions[0];assert row[i]=='nx='+records[n]['parameters']['nx']
            new[i]='nx='+edits[n]['nx'];copies[n]['parameters']=copy.deepcopy(edits[n])
            changed_parent.append(dict(instance=n,**newroles[n],parent_card=row,candidate_card=new))
        if new!=oldcards[n]:
            assert n in roles
            changes.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],
                candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        rows.append(new)
    assert len(changed_parent)==8 and len(changes)==len({c['instance']for c in changes})==(72 if variant=='slave_data4'else 80)
    assert len(rows)==476+17918+12850+2
    assert [r for r in parent_rows if r[0].lower()not in edits]==[r for r in rows if r[0].lower()not in edits]
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in rows if r[0].startswith(('R','C'))]
    restored=copy.deepcopy(candidate)
    for r in restored['device_records']:
        if r['instance'].lower()in roles:r['parameters']=copy.deepcopy(originals[r['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared topology, native reference or primitive changed'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY eight actual C/D slave data/hold Nx6->4/5 on v41Nx8, frozen wire RC, no physical acceptance.\n'+'\n'.join(' '.join(r)for r in rows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v41_follower_n8',
      baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
      actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
      all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
      changes=changes,parent_changes=changed_parent,controls=checks,source_diagnosis_sha256=DIAG_SHA,
      diffusion_model_scope=proof['diffusion_model_scope'],
      scope='Only eight source-bound C/D slave data/hold HBT emitter counts6->4/5 relative to v41follower_n8. Original A/B, master, selectors, followers, currents/bias/resistors, clocks/stimuli/loads/full windows and gates unchanged. Investigate actual late slave output; no predicted pass. FrozenRC requires new geometry/DRC/LVS/RC/PVT/loop qualification.')
