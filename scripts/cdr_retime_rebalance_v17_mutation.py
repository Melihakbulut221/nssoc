#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Twelve intrinsic-resistor sensitivity edits, never a physical-layout claim."""
import copy,hashlib,json
from pathlib import Path
from build_pcie_local_vco_hybrid_v6 import statements,number
ROOT=Path(__file__).resolve().parents[1]
OLD_MODEL='nssoc_cdr_pd484_retime_data_mim_wire_v16'
MODEL='nssoc_cdr_pd484_retime_rebalance_diagnostic_v17'
PIN=ROOT/'docs/evidence/cdr-v16-retime-passive-networks-20261020.json'
PIN_SHA='ed917c3e7d0bcc5c781355dde99771ec520c67ef96e69d6ce130cbf408f158ff'
PARAMETERS={'filter_series':('5.4u','1.8u'),'filter_shunt':('12.6u','16.2u'),'sampler_bias':('2.4u','6u')}
def digest(b):return hashlib.sha256(b).hexdigest()
def select(contract):
    raw=PIN.read_bytes();assert digest(raw)==PIN_SHA
    pin=json.loads(raw);assert pin['run']==39341051275
    assert pin['summary_sha256']=='1ce16c55ab2c5005d76e7cff06f855ff3ef173b0619383125063fa001dff953b'
    p=pin['report'];assert p['sources_unchanged']and p['original_rejection_preserved']
    assert not p['accepted']and not p['full_phy_accepted']
    records={d['native_id']:d for d in contract['device_records']}
    assert len(records)==484
    chosen={}
    for tag in ('c','d'):
        for polarity,leg in p['chains'][tag]['legs'].items():
            assert polarity in ('p','n')
            for role,(old,new) in PARAMETERS.items():
                part=leg['native_chain'][role];record=records[part['native_id']]
                assert record['instance']==part['instance']and record['model']==part['model']=='rppd'
                assert record['parameters']==part['parameters']
                assert part['parameters']['w']=='4u'and part['parameters']['l']==old
                assert part['physical_macro']==(('sc'if tag=='c'else'sd')if role=='sampler_bias'else('ac'if tag=='c'else'bd'))
                terminals={t['terminal']:t for t in record['terminals']}
                for side in ('first','second'):
                    t=part[side];actual=terminals[t['terminal']]
                    for key in ('node','native_cluster','native_net'):assert actual[key]==t[key],(role,key)
                name=record['instance'];assert name not in chosen
                chosen[name]=dict(native_id=part['native_id'],macro=part['physical_macro'],
                    tag=tag,polarity=polarity,role=role,before_l=old,after_l=new)
    assert len(chosen)==12
    assert all(sum(v['role']==role for v in chosen.values())==4 for role in PARAMETERS)
    return chosen,pin
def expected_contract(contract,changes):
    result=copy.deepcopy(contract)
    for d in result['device_records']:
        if d['instance']in changes:d['parameters']['l']=changes[d['instance']]['after_l']
    result.update(status='DIAGNOSTIC_INTRINSIC_REBALANCE_ON_OLD_METAL_NOT_PHYSICAL_COMPOSITION',
        source_geometry_matches_candidate=False,qualified_pex=False,
        original_contract_sha256=digest(json.dumps(contract,sort_keys=True).encode()))
    return result
def expected_rows(text,changes):
    rows=copy.deepcopy(statements(text))
    assert rows[0][1]==rows[-1][1]==OLD_MODEL
    rows[0][1]=rows[-1][1]=MODEL
    seen=set()
    for row in rows[1:-1]:
        if row[0]not in changes:continue
        spec=changes[row[0]];assert row.count('rppd')==1
        i=row.index('rppd');params=dict(v.split('=',1)for v in row[i+1:])
        assert params['w']=='4u'and params['l']==spec['before_l']
        j=row.index('l='+spec['before_l']);row[j]='l='+spec['after_l'];seen.add(row[0])
    assert seen==set(changes)
    return rows
def verify(original,contract,text,candidate,changes):
    assert statements(text)==expected_rows(original,changes),'Unexpected circuit/metal/terminal change'
    assert candidate==expected_contract(contract,changes),'Unexpected candidate-contract change'
    a=statements(original);b=statements(text)
    assert [r for r in a if r[0].startswith(('R','C'))]==[r for r in b if r[0].startswith(('R','C'))]
    assert sum(r[0].startswith('R')for r in b)==17674
    assert sum(r[0].startswith('C')for r in b)==12709
    assert sum(r[0].startswith('X')for r in b)==484
def mutate(original,contract,out):
    assert contract['counts']==dict(devices=484,R=17674,C=12709)
    changes,pin=select(contract);rows=expected_rows(original,changes)
    text='* INTRINSIC PARAMETER SENSITIVITY; OLD METAL GEOMETRY; NOT PHYSICAL ACCEPTANCE\n'+'\n'.join(' '.join(r)for r in rows)+'\n'
    candidate=expected_contract(contract,changes)
    verify(original,contract,text,candidate,changes)
    controls=[]
    for fault in ('missed_intended_length','changed_unselected_device','scaled_metal_resistor','wrong_intrinsic_terminal','wrong_contract_length'):
        bad=copy.deepcopy(rows);c=copy.deepcopy(candidate)
        if fault=='missed_intended_length':
            row=next(r for r in bad if r[0]in changes);spec=changes[row[0]]
            row[row.index('l='+spec['after_l'])]='l='+spec['before_l']
        elif fault=='changed_unselected_device':
            row=next(r for r in bad if 'rppd'in r and r[0]not in changes)
            i=next(i for i,v in enumerate(row)if v.startswith('l='));row[i]='l=99u'
        elif fault=='scaled_metal_resistor':
            row=next(r for r in bad if r[0].startswith('R'));row[-1]=str(float(number(row[-1]))*1.1)
        elif fault=='wrong_intrinsic_terminal':
            row=next(r for r in bad if r[0]in changes);row[1]='avss'if row[1]!='avss'else'avdd'
        else:
            d=next(d for d in c['device_records']if d['instance']in changes);d['parameters']['l']='99u'
        try:verify(original,contract,'\n'.join(' '.join(r)for r in bad)+'\n',c,changes)
        except AssertionError:controls.append(dict(fault=fault,rejected=True))
        else:raise AssertionError('Real sensitivity corruption accepted: '+fault)
    assert len(controls)==5
    out.mkdir()
    model=out/'pd484-rebalance-diagnostic.spice';model.write_text(text)
    (out/'candidate-contract.json').write_text(json.dumps(candidate,indent=2)+'\n')
    result=dict(status='PASS_EXACT12_INTRINSIC_LENGTH_EDITS_AND_FIVE_CORRUPTION_CONTROLS',
        source_geometry_matches_candidate=False,layout_integrated=False,adopted=False,full_phy_accepted=False,qualified_pex=False,
        passive_source=dict(run=pin['run'],summary_sha256=pin['summary_sha256'],receipt_sha256=PIN_SHA),
        changes=changes,controls=controls,old_model_sha256=digest(original.encode()),new_model_sha256=digest(text.encode()),
        old_wire_edges_and_caps_exact=True,other_devices_and_all_terminals_exact=True,
        hypothesis='Fixed C/D filter series/shunt lengths 1.8/16.2um keep their summed length18um; sampler-bias length6um reduces divider attenuation. Native nonlinear models decide actual CM, loading, delay and safety. No changed gate or RF/layout claim.')
    (out/'mutation.json').write_text(json.dumps(result,indent=2)+'\n')
    return model,candidate,result
