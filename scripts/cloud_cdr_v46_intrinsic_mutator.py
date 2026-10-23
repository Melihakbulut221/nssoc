#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Test source-bound C/D slave regeneration capacitance after measured master/slave separation."""
import copy,json,subprocess
from decimal import Decimal
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v44_intrinsic_mutator as previous
from cloud_cdr_v43_intrinsic_mutator import clock_response
from run_cloud_tx_layout_repair import sha
VARIANTS={'cd_slave_hold5':False,'cd_slave_data5_hold5':True}
DIAG_ASSET=669833963
DIAG_SHA='cbe2e04bebd90b7aa984940700aa754afe306ca94d1a1186d9a3ba2cba747c58'
PARENTS=[('nominal_early',669073404,'bec2ab47a567f0a6ff2f8a0e403c179e8eeb2952388dcef28906693b8846f82a'),('nominal_late',669064409,'95f13c2d46aaa09c59e5233e43d5bfc245e8986333df952ef1aff727cbcfdcb8')]
def resized(params,nx):
    assert nx=='5'
    assert parser.number(params['nx'])==6
    assert parser.number(params['we'])==Decimal('0.070e-6')and parser.number(params['le'])==Decimal('0.900e-6')
    result=copy.deepcopy(params);result['nx']=nx
    assert {k:v for k,v in result.items()if k!='nx'}=={k:v for k,v in params.items()if k!='nx'}
    return result
def controls():
    p=dict(nx='6',we='0.070u',le='0.900u')
    assert resized(p,'5')==dict(p,nx='5')
    rejected=[]
    for label,params,nx in [('wrong-parent-nx',dict(p,nx='2'),'5'),('wrong-width',dict(p,we='0.14u'),'5'),
      ('wrong-length',dict(p,le='1.8u'),'5'),('outside-recipe',p,'2')]:
        try:resized(params,nx)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Undeclared HBT area accepted: '+label)
    return dict(rejected=rejected,only_cd_slave_hold_or_data_hold_nx=True,
        original_parameters_unchanged=p==dict(nx='6',we='0.070u',le='0.900u'))
def selection(records,planes,diag,variant):
    assert variant in VARIANTS
    edits={};roles={}
    for tag in ('c','d'):
        bank=diag['stages'][tag]['latches']['native_graph']['slave']
        outputs={bank['positive_output_native'],bank['negative_output_native']};assert len(outputs)==2
        data=[bank['data_positive'],bank['data_negative']]
        holds=bank['hold_pair']
        assert len(holds)==2 and len(set([*data,*holds]))==4
        for role,names in [('data',data),('hold',holds)]:
            if role=='data'and not VARIANTS[variant]:continue
            emitter_groups=set()
            for full in names:
                name=full.removeprefix('xpd.');r=records[name]
                assert r['model']=='npn13g2'and int(name[2:])==r['native_id']
                terminals={t['terminal']:t['native_cluster']for t in r['terminals']}
                assert {'C','B','E'}.issubset(terminals)and len(terminals)==4 and terminals['C']in outputs
                emitter_groups.add(terminals['E'])
                assert name not in edits
                edits[name]=resized(r['parameters'],'5')
                roles[name]=dict(stage=tag,latch='slave',role=role,parent_nx=6,candidate_nx=5)
            assert len(emitter_groups)==1
    assert len(edits)==(8 if VARIANTS[variant]else 4)
    return edits,roles
def graph_controls(records,planes,diag):
    for variant in VARIANTS:selection(records,planes,diag,variant)
    selected,_=selection(records,planes,diag,'cd_slave_data5_hold5');name=next(iter(selected))
    faults=[]
    for label in ('missing-device','wrong-model','wrong-native-id','wrong-parent-nx','wrong-geometry','changed-slave-output','duplicate-hold'):
        rs,ps,ds=copy.deepcopy((records,planes,diag))
        if label=='missing-device':del rs[name]
        elif label=='wrong-model':rs[name]['model']='rppd'
        elif label=='wrong-native-id':rs[name]['native_id']=-992
        elif label=='wrong-parent-nx':rs[name]['parameters']['nx']='2'
        elif label=='wrong-geometry':rs[name]['parameters']['we']='0.14u'
        elif label=='changed-slave-output':ds['stages']['c']['latches']['native_graph']['slave']['positive_output_native']=-993
        else:
            bank=ds['stages']['c']['latches']['native_graph']['slave'];bank['hold_pair']=[bank['data_positive'],bank['hold_pair'][0]]
        try:selection(rs,ps,ds,'cd_slave_data5_hold5')
        except (AssertionError,KeyError):faults.append(label)
        else:raise AssertionError('Invalid slave binding accepted: '+label)
    return faults
def parent_headroom(out,diag,variant):
    all_rows={}
    for phase,asset,digest in PARENTS:
        raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(asset),'-H','Accept: application/octet-stream'])
        path=out/('parent-v44-l39-'+phase+'.json');path.write_bytes(raw);assert sha(path)==digest
        parent=json.loads(raw)
        assert parent['intrinsic_screen']['variant']=='cd_master_l39'and parent['case']==phase
        assert parent['devices_passed']and parent['sources_unchanged']and parent['status']=='REJECTED_EXPLORATORY_INTRINSIC_SCREEN'
        assert not parent['data_passed']and not parent['phase_passed']
        rows={}
        for tag in ('c','d'):
            bank=diag['stages'][tag]['latches']['native_graph']['slave']
            names=list(bank['hold_pair'])
            if VARIANTS[variant]:names += [bank['data_positive'],bank['data_negative']]
            for name in names:
                q=parent['device_checks'][name];dev=parent['devices'][name]
                assert dev['nx']==6 and q['minimum_active_vce_v']>=.4
                total=q['maximum_alltime_abs_ic_per_emitter_a']*dev['nx']
                projected=total/5
                assert projected<.003
                rows[name]=dict(actual_parent=q,actual_parent_nx=6,
                    parent_peak_current_a=total,fixed_parent_current_per_candidate_emitter_a=projected)
        all_rows[phase]=dict(asset=asset,sha256=digest,devices=rows)
    return dict(phases=all_rows,
      scope='Both measured parent phases justify finite smaller HBT candidates. Fixed-current density arithmetic is not candidate safety; full native currents and original all-device gates must be rerun. Original l39 hold headroom is only about76mV above the0.4V gate, so no further collector resistance increase is used.')

def apply(model,contract,planes,variant,out):
    checks=controls()
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(DIAG_ASSET),'-H','Accept: application/octet-stream'])
    path=out/'v44-l39-early-native-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
    diag=json.loads(raw)
    assert diag['source_head']=='fed6c3a1f2aa3b2e3e992f81b330a07143ea0f0f'
    assert diag['all120original_hbt_checks_reproduced']and diag['all4original_sampler_checks_reproduced']
    assert diag['original_rejection_preserved']and not diag['accepted']and diag['original_devices_passed']
    for tag in ('c','d'):
        observed=diag['stages'][tag]['latches']['steering_transition_windows']['counts']
        assert observed['unique_transition']==255 and observed['master_output_below_100mv_at_original_deadline']==0
        assert observed['slave_output_below_original_100mv_gate_at_deadline']>0
    checks['parent_headroom']=parent_headroom(out,diag,variant)
    parent=out/'v44-l39-reference';parent.mkdir()
    parent_model,parent_contract,proof=previous.apply(model,contract,planes,'cd_master_l39',parent)
    assert len(proof['changes'])==84 and proof['all_wire_cards_unchanged']
    assert proof['candidate_model_sha256']=='b75950141d51db8d013bf06a5124f13a6fbe4448fe0fa92b9fc3925670f93a99'
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in parent_contract['device_records']}
    assert len(records)==len(originals)==476
    checks['actual_graph_faults']=graph_controls(records,planes,diag)
    edits,newroles=selection(records,planes,diag,variant)
    prior_roles={c['instance']:c for c in proof['changes']}
    assert set(edits)<=set(prior_roles),'Selected slave devices must be declared parent Nx4->6 edits'
    for n in edits:
        assert prior_roles[n]['original_parameters']==originals[n]['parameters']
        assert prior_roles[n]['candidate_parameters']==records[n]['parameters']
        assert parser.number(originals[n]['parameters']['nx'])==4
        assert parser.number(records[n]['parameters']['nx'])==6
        assert {k:v for k,v in originals[n]['parameters'].items()if k!='nx'}=={k:v for k,v in records[n]['parameters'].items()if k!='nx'}
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
    assert len(changed_parent)==len(edits)and len(changes)==len({c['instance']for c in changes})==84
    assert len(rows)==476+17918+12850+2
    assert [r for r in parent_rows if r[0].lower()not in edits]==[r for r in rows if r[0].lower()not in edits]
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in rows if r[0].startswith(('R','C'))]
    restored=copy.deepcopy(candidate)
    for r in restored['device_records']:
        if r['instance'].lower()in roles:r['parameters']=copy.deepcopy(originals[r['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared topology, native reference or primitive changed'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY C/D slave hold or data/hold Nx6->5 on measured v44L3.9 parent, frozen wire RC, no physical acceptance.\n'+'\n'.join(' '.join(r)for r in rows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v44_cd_master_l39',
      baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
      actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
      all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
      changes=changes,parent_changes=changed_parent,controls=checks,source_diagnosis_sha256=DIAG_SHA,
      diffusion_model_scope=proof['diffusion_model_scope'],
      scope='Only four C/D slave hold HBTs or those four plus four data HBTs change Nx6->5 relative to measured v44l39. Original HBT We/Le, A/B, slaves, selectors, followers, current/bias and all resistors unchanged from that parent. Test a finite slave-stage capacitance hypothesis after full-wave evidence shows master outputs pass at the original deadline while64 slave outputs fail. This is not inferred causality; all original gates decide. Projected parent current density is not candidate safety; all original full native gates rerun. FrozenRC requires new geometry/DRC/LVS/RC/PVT/loop qualification.')
