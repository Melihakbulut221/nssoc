#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Increase only C/D master collector load to test measured weak data transfer."""
import copy,json,subprocess
from decimal import Decimal
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v41_intrinsic_mutator as previous
from cloud_cdr_v43_intrinsic_mutator import clock_response
from run_cloud_tx_layout_repair import sha
VARIANTS={'cd_master_l34':'3.4','cd_master_l39':'3.9'}
DIAG_ASSET=668715769
DIAG_SHA='be4bec77ce03a2b35bfe6c316701919f3101b546809c3355648ed74103d278e7'
PARENT_ASSET=668664370
PARENT_SHA='9a9c6ff5356e2c5e2da91e04df2f3c76190aff8fd5a1ab400d4ac65ff41b863e'
def resized(params,length):
    assert length in VARIANTS.values()
    assert parser.number(params['l'])==Decimal('2.6e-6')
    assert parser.number(params['w'])==Decimal('32e-6')
    assert parser.number(params['b'])==0 and parser.number(params['sw_et'])==1
    result=copy.deepcopy(params);result['l']=length+'u'
    assert {k:v for k,v in result.items()if k!='l'}=={k:v for k,v in params.items()if k!='l'}
    return result
def controls():
    p=dict(l='2.6u',w='32u',b='0',sw_et='1')
    for length in VARIANTS.values():assert resized(p,length)==dict(p,l=length+'u')
    rejected=[]
    for label,params,length in [('wrong-length',dict(p,l='1.2u'),'3.4'),('wrong-width',dict(p,w='16u'),'3.4'),
      ('wrong-bend',dict(p,b='1'),'3.4'),('disabled-self-heating',dict(p,sw_et='0'),'3.4'),('outside-recipe',p,'5.2')]:
        try:resized(params,length)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Undeclared load accepted: '+label)
    return dict(rejected=rejected,only_four_cd_master_load_lengths=True,original_parameters_unchanged=p==dict(l='2.6u',w='32u',b='0',sw_et='1'))
def selection(records,planes,diag,variant):
    assert variant in VARIANTS
    avdd={p['native_cluster']for p in planes['anchors']if p['logical_net']=='avdd'};assert len(avdd)==1
    avdd=next(iter(avdd));edits={};roles={}
    for tag in ('c','d'):
        bank=diag['stages'][tag]['latches']['native_graph']['master']
        outputs={bank['positive_output_native'],bank['negative_output_native']};assert len(outputs)==2 and avdd not in outputs
        for full in [bank['data_positive'],bank['data_negative'],*bank['hold_pair']]:
            rec=records[full.removeprefix('xpd.')];assert rec['model']=='npn13g2'
            assert next(t['native_cluster']for t in rec['terminals']if t['terminal']=='C')in outputs
        for polarity,output in [('positive',bank['positive_output_native']),('negative',bank['negative_output_native'])]:
            found=[]
            for n,r in records.items():
                if r['model']!='rppd':continue
                terms={t['terminal']:t['native_cluster']for t in r['terminals']}
                if set(terms)=={'rppd_1','rppd_2','rppd_sub'}and {terms['rppd_1'],terms['rppd_2']}=={avdd,output}:found.append(n)
            assert len(found)==1,'Exactly one actual collector load per output required'
            n=found[0];r=records[n]
            assert n not in edits and int(n[2:])==r['native_id']
            edits[n]=resized(r['parameters'],VARIANTS[variant])
            roles[n]=dict(stage=tag,latch='master',role='collector_load',polarity=polarity,parent_length_um=2.6,candidate_length_um=float(VARIANTS[variant]))
    assert len(edits)==4
    return edits,roles
def graph_controls(records,planes,diag):
    for variant in VARIANTS:selection(records,planes,diag,variant)
    selected,_=selection(records,planes,diag,'cd_master_l34');name=next(iter(selected))
    faults=[]
    for label in ('missing-load','duplicate-load','wrong-load-terminal','wrong-model','wrong-native-id','wrong-parent-length','changed-master-output'):
        rs,ps,ds=copy.deepcopy((records,planes,diag))
        if label=='missing-load':del rs[name]
        elif label=='duplicate-load':rs['xd9999']=copy.deepcopy(rs[name]);rs['xd9999']['native_id']=9999
        elif label=='wrong-load-terminal':next(t for t in rs[name]['terminals']if t['terminal']=='rppd_1')['native_cluster']=-991
        elif label=='wrong-model':rs[name]['model']='npn13g2'
        elif label=='wrong-native-id':rs[name]['native_id']=-992
        elif label=='wrong-parent-length':rs[name]['parameters']['l']='1.2u'
        else:ds['stages']['c']['latches']['native_graph']['master']['positive_output_native']=-993
        try:selection(rs,ps,ds,'cd_master_l34')
        except AssertionError:faults.append(label)
        else:raise AssertionError('Invalid collector binding accepted: '+label)
    return faults
def parent_headroom(out,diag):
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(PARENT_ASSET),'-H','Accept: application/octet-stream'])
    path=out/'parent-v41-n8-early.json';path.write_bytes(raw);assert sha(path)==PARENT_SHA
    parent=json.loads(raw);assert parent['intrinsic_screen']['variant']=='follower_n8'and parent['case']=='nominal_early'
    assert parent['devices_passed']and parent['sources_unchanged']and parent['status']=='REJECTED_EXPLORATORY_INTRINSIC_SCREEN'
    rows={}
    for tag in ('c','d'):
        stage=diag['stages'][tag];bank=stage['latches']['native_graph']['master']
        at_edge=next(p for p in stage['latches']['phase_summary']if p['offset_ui']==0)
        assert at_edge['signals']['master_input']['below_100mv_marker']==255
        assert at_edge['signals']['master_output']['below_100mv_marker']>=100
        for name in [bank['data_positive'],bank['data_negative'],*bank['hold_pair']]:
            q=parent['device_checks'][name];assert q['minimum_active_vce_v']>.55
            rows[name]=q
    assert len(rows)==8
    return dict(asset=PARENT_ASSET,sha256=PARENT_SHA,actual_parent_device_checks=rows,
      scope='Measured parent headroom and weak master output motivate finite load candidates, not a prediction of candidate safety or settling. Original full all-device gates still run.')

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
    checks['parent_headroom']=parent_headroom(out,diag)
    parent=out/'v41-follower-n8-reference';parent.mkdir()
    parent_model,parent_contract,proof=previous.apply(model,contract,planes,'follower_n8',parent)
    assert len(proof['changes'])==80 and proof['all_wire_cards_unchanged']
    assert proof['candidate_model_sha256']==diag['exploratory_intrinsic_source']['candidate_model_sha256']
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in parent_contract['device_records']}
    assert len(records)==len(originals)==476
    checks['actual_graph_faults']=graph_controls(records,planes,diag)
    edits,newroles=selection(records,planes,diag,variant)
    prior_roles={c['instance']:c for c in proof['changes']}
    assert not set(edits)&set(prior_roles)
    assert all(records[n]==originals[n]for n in edits)
    candidate=copy.deepcopy(parent_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    omitted={'instance','original_parameters','candidate_parameters','original_card','candidate_card'}
    roles={c['instance']:{k:v for k,v in c.items()if k not in omitted}for c in proof['changes']}
    roles.update(newroles)
    original_rows=parser.statements(model.read_text());oldcards={r[0].lower():r for r in original_rows}
    parent_rows=parser.statements(parent_model.read_text());rows=[];changes=[];changed_parent=[]
    for row in parent_rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            positions=[i for i,x in enumerate(row)if x.startswith('l=')];assert len(positions)==1
            i=positions[0];assert row[i]=='l='+records[n]['parameters']['l']
            new[i]='l='+edits[n]['l'];copies[n]['parameters']=copy.deepcopy(edits[n])
            changed_parent.append(dict(instance=n,**newroles[n],parent_card=row,candidate_card=new))
        if new!=oldcards[n]:
            assert n in roles
            changes.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],
                candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        rows.append(new)
    assert len(changed_parent)==4 and len(changes)==len({c['instance']for c in changes})==84
    assert len(rows)==476+17918+12850+2
    assert [r for r in parent_rows if r[0].lower()not in edits]==[r for r in rows if r[0].lower()not in edits]
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in rows if r[0].startswith(('R','C'))]
    restored=copy.deepcopy(candidate)
    for r in restored['device_records']:
        if r['instance'].lower()in roles:r['parameters']=copy.deepcopy(originals[r['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared topology, native reference or primitive changed'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY four actual C/D master collector loads L2.6->3.4/3.9um on v41Nx8, frozen wire RC, no physical acceptance.\n'+'\n'.join(' '.join(r)for r in rows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v41_follower_n8',
      baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
      actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
      all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
      changes=changes,parent_changes=changed_parent,controls=checks,source_diagnosis_sha256=DIAG_SHA,
      diffusion_model_scope=proof['diffusion_model_scope'],
      scope='Only four source-bound C/D master collector load resistor lengths2.6->3.4/3.9um at width32um relative to v41follower_n8. All other original A/B, slave, HBT, follower, bias, current, resistor, externalclock/stimulus/load/window/gate values unchanged. Test measured weak master transfer against increased load gain/settling and headroom tradeoff; no predicted pass. FrozenRC requires new geometry/DRC/LVS/RC/PVT/loop qualification.')
