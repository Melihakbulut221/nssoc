#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reduce actual slave selector clock-input area; keep all original loaded gates."""
import copy,json,subprocess
from decimal import Decimal
from pathlib import Path
import numpy as np
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v41_intrinsic_mutator as previous
from cdr_selector_headroom import pair_transitions,summary,response_controls
from run_cloud_tx_layout_repair import sha
VARIANTS={'slave_selector2':2}
DIAG_ASSET=668715769
DIAG_SHA='be4bec77ce03a2b35bfe6c316701919f3101b546809c3355648ed74103d278e7'
OBSERVATIONS=[
 (668905286,'845576ec5f00580e667056eac8c40fa7398084dc0532d699114fed0572bb8044'),
 (668908548,'fb8ab9859d2f7ff89c9e5b27a052fd89060bdef1dee9d3b91bae435164d73fd0')]
def resized(params,nx):
    assert type(nx)is int and nx==2
    assert parser.number(params['nx'])==Decimal(3)
    assert parser.number(params['we'])==Decimal('.07e-6')
    assert parser.number(params['le'])==Decimal('.9e-6')
    result=copy.deepcopy(params);result['nx']=str(nx)
    assert {k:v for k,v in result.items()if k!='nx'}=={k:v for k,v in params.items()if k!='nx'}
    return result
def controls():
    p=dict(nx='3',we='.07u',le='.9u')
    assert resized(p,2)==dict(p,nx='2')
    rejected=[]
    for label,params,nx in [('wrong-parent',dict(p,nx='2'),2),('wrong-width',dict(p,we='.08u'),2),
                            ('wrong-length',dict(p,le='1u'),2),('outside-recipe',p,1),('fractional',p,2.)]:
        try:resized(params,nx)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Undeclared selector area accepted: '+label)
    return dict(rejected=rejected,only_sixteen_slave_selectors=True,pair_response_controls=response_controls())
def selection(records,diag,variant):
    assert variant in VARIANTS
    edits={};roles={}
    def terminals(full):
        r=records[full.removeprefix('xpd.')]
        assert r['model']=='npn13g2'and int(r['instance'][2:])==r['native_id']
        return {t['terminal']:t['native_cluster']for t in r['terminals']}
    for tag in 'abcd':
        graph=diag['stages'][tag]['latches']['native_graph'];bank=graph['slave']
        master=graph['master']
        master_track={terminals(n)['B']for n in master['track_selectors']}
        master_hold={terminals(n)['B']for n in master['hold_selectors']}
        assert len(master_track)==len(master_hold)==1 and master_track!=master_hold
        names=bank['track_selectors']+bank['hold_selectors']
        assert len(names)==len(set(names))==4
        assert not set(names)&set(master['track_selectors']+master['hold_selectors'])
        assert len({terminals(n)['E']for n in names})==1
        data_names=[bank['data_positive'],bank['data_negative']]
        assert len({terminals(n)['E']for n in data_names})==1
        data_emitter=terminals(data_names[0])['E']
        assert len({terminals(n)['E']for n in bank['hold_pair']})==1
        hold_emitter=terminals(bank['hold_pair'][0])['E']
        assert data_emitter!=hold_emitter
        for side,collector,bases in [('track',data_emitter,master_hold),('hold',hold_emitter,master_track)]:
            assert len(bank[side+'_selectors'])==2
            for full in bank[side+'_selectors']:
                n=full.removeprefix('xpd.');record=records[n];ts=terminals(full)
                assert n not in edits and ts['C']==collector and ts['B']in bases
                edits[n]=resized(record['parameters'],2)
                roles[n]=dict(stage=tag,latch='slave',role='selector',side=side,parent_nx=3,candidate_nx=2)
    assert len(edits)==16
    return edits,roles
def graph_controls(records,diag):
    selection(records,diag,'slave_selector2')
    rejected=[]
    for label in ('duplicate-selector','wrong-collector','wrong-base','wrong-emitter','wrong-model','wrong-native-id','wrong-parent-area','master-selected'):
        rs,ds=copy.deepcopy((records,diag));g=ds['stages']['c']['latches']['native_graph'];bank=g['slave']
        name=bank['track_selectors'][0];n=name.removeprefix('xpd.')
        if label=='duplicate-selector':bank['track_selectors'][1]=name
        elif label in ('wrong-collector','wrong-base','wrong-emitter'):
            terminal={'wrong-collector':'C','wrong-base':'B','wrong-emitter':'E'}[label]
            next(t for t in rs[n]['terminals']if t['terminal']==terminal)['native_cluster']=-991
        elif label=='wrong-model':rs[n]['model']='rppd'
        elif label=='wrong-native-id':rs[n]['native_id']=-992
        elif label=='wrong-parent-area':rs[n]['parameters']['nx']='2'
        else:bank['track_selectors'][0]=g['master']['track_selectors'][0]
        try:selection(rs,ds,'slave_selector2')
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Invalid selector selection accepted: '+label)
    return rejected
def verify_observations(out):
    pins=[]
    for aid,digest in OBSERVATIONS:
        raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
        p=out/('parent-selector-observations-'+str(aid)+'.json');p.write_bytes(raw);assert sha(p)==digest
        d=json.loads(raw);assert d['variant']=='follower_n8'and d['original_rejection_preserved']
        assert d['all120_hbt_and4_sampler_results_reproduced']and not d['new_acceptance_gate']
        for tag,stage in d['stages'].items():
            assert tag in 'abcd'and len(stage['devices'])==8
            for pair in stage['response_crossings']['pairs'].values():
                assert pair['unique_triplets']==255 and pair['unresolved_triplets']==0
                assert 0<pair['measurements']['collector_minus_base_s']['median']<1e-12
            master=[x for x in stage['devices'].values()if x['latch']=='master']
            slave=[x for x in stage['devices'].values()if x['latch']=='slave']
            assert len(master)==len(slave)==4
            assert all(x['nx']==2 and x['full_active']['ic_a']['maximum']>.003 for x in master)
            assert all(x['nx']==3 and x['full_active']['ic_a']['maximum']/2<.003 for x in slave)
        pins.append(dict(asset=aid,sha256=digest,case=d['case']))
    return dict(pins=pins,scope='Measured parent active current motivates a candidate only; no prediction of candidate safety. Full original all-time current and device gates run again.')
def clock_response(t,v,w,devices,out,edges_by_stage,ui):
    diag=json.loads((out/'v41-n8-early-native-diagnosis.json').read_text())
    delta=v('cp')-v('cn');a,b=delta[:-1],delta[1:]
    ref={}
    for direction in ('rising','falling'):
        ids=np.flatnonzero((a<0)&(b>=0)if direction=='rising'else(a>0)&(b<=0))
        ref[direction]=t[ids]-a[ids]*(t[ids+1]-t[ids])/(b[ids]-a[ids])
    stages={}
    for tag,edges in edges_by_stage.items():
        graph=diag['stages'][tag]['latches']['native_graph']
        response=pair_transitions(t,graph,devices,v,w,edges,ui)
        direction='falling'if tag=='b'else'rising';rows=[];offsets=[]
        for i,edge in enumerate(edges,1):
            hits=ref[direction][abs(ref[direction]-edge)<=.45*ui]
            row=dict(bit_index=i,original_edge_s=float(edge),source_crossing_count=len(hits))
            if len(hits)==1:
                row['source_crossing_s']=float(hits[0]);offsets.append(float(hits[0]-edge))
            rows.append(row)
        stages[tag]=dict(selector_pairs=response,source_direction=direction,source_rows=rows,
            source_minus_original_edge_s=summary(offsets)if offsets else None,
            missing_or_ambiguous_source_edges=sum(r['source_crossing_count']!=1 for r in rows))
    report=dict(stages=stages,new_acceptance_gate=False,clocks_or_samples_modified=False,
      scope='Actual loaded cp/cn source-port and selector pair crossings on complete new native capture, original edge windows unchanged. External ideal source is not substituted for measured port.')
    path=out/'selector-clock-response.json';path.write_text(json.dumps(report,indent=2)+'\n')
    return dict(path=path.name,sha256=sha(path),source_offsets={tag:s['source_minus_original_edge_s']for tag,s in stages.items()},missing_or_ambiguous={tag:s['missing_or_ambiguous_source_edges']for tag,s in stages.items()})

def apply(model,contract,planes,variant,out):
    checks=controls();checks["parent_response_observations"]=verify_observations(out)
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
    assert all(prior_roles[n]['stage']in 'abcd'and prior_roles[n]['latch']=='slave'and prior_roles[n]['role']=='selector'for n in edits)
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
    assert len(changed_parent)==16 and len(changes)==len({c['instance']for c in changes})==64
    assert len(rows)==476+17918+12850+2
    assert [r for r in parent_rows if r[0].lower()not in edits]==[r for r in rows if r[0].lower()not in edits]
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in rows if r[0].startswith(('R','C'))]
    restored=copy.deepcopy(candidate)
    for r in restored['device_records']:
        if r['instance'].lower()in roles:r['parameters']=copy.deepcopy(originals[r['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared topology, native reference or primitive changed'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY sixteen actual slave selector Nx3->2 on v41Nx8, frozen wire RC, no physical acceptance.\n'+'\n'.join(' '.join(r)for r in rows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v41_follower_n8',
      baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
      actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
      all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
      changes=changes,parent_changes=changed_parent,controls=checks,source_diagnosis_sha256=DIAG_SHA,
      diffusion_model_scope=proof['diffusion_model_scope'],
      scope='Only sixteen source-bound slave selector HBT emitter counts3->2 relative to v41follower_n8. All master, slave data/hold, followers, currents/bias/resistors, clocks/stimuli/loads/full windows and gates unchanged. Investigate clock-input loading without changing external source resistance or phase. No predicted pass; frozenRC requires new geometry/DRC/LVS/RC/PVT/loop qualification.')
