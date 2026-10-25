#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-count adapter only; no simulator, runtime install or electrical acceptance."""
import ast,hashlib,json,re
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
INIT='scripts/cloud_tx_phase_zero_op_initialization.py'
OLD='scripts/cloud_tx_phase_assert_offset_intrinsic.py'
PINS={
 INIT:'cada086bcd45e39fde9dfe960123572464125a227a69116aeda6f31d72867485',
 OLD:'b367028706af6fb6c006cfc83903f72426821f1f6e9ebca69731d06d28de2bee'}
PREPARATION=dict(run=40171468821,head='e6c48d4d363a0bdb865dbdbd83e38350ff7291a7',
 summary_asset=674346276,summary_sha256='7a5da3a0e8e7afd80ace24da03365dd4aad223ba9dc4f9fbdedf08bf2b1b9be4',
 parts_asset=674346341,parts_sha256='df73e849b0aa18cd39816021a0f56b7e8f12cbf32a3dfbab285ebcec574f2de0',
 archive_bytes=356475,archive_sha256='c9f227d485aecdc9d923a148cf91cd36c8c51144bdbdad115c2e7b0c0b6eb365')
DERIVATIONS=[
 (INIT,'targets',[('==106','==318',1)]),
 (INIT,'flag_block',[]),
 (INIT,'op_only',[]),
 (INIT,'flags',[('actual_HBT_targets=106','actual_HBT_targets=318',1)]),
 (OLD,'initialized_deck',[]),
 (OLD,'gate',[('all106_flags','all318_flags',1),('actual_HBT_targets=106','actual_HBT_targets=318',1),('(358,359)','(4726,4727)',1)])]
def digest(b):return hashlib.sha256(b.encode()if isinstance(b,str)else b).hexdigest()
def derive(sources=None):
    if sources is None:sources={p:(ROOT/p).read_text()for p in PINS}
    assert set(sources)==set(PINS)
    for p,h in PINS.items():assert digest(sources[p])==h,p
    generated={};proof=[]
    for path,name,edits in DERIVATIONS:
        text=sources[path];nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name]
        assert len(nodes)==1;original=ast.get_source_segment(text,nodes[0])+'\n';changed=original
        for old,new,count in edits:
            assert changed.count(old)==count,(name,old)
            changed=changed.replace(old,new)
        reversed_text=changed
        for old,new,count in reversed(edits):
            assert reversed_text.count(new)==count
            reversed_text=reversed_text.replace(new,old)
        assert reversed_text==original
        generated[name]=changed
        proof.append(dict(path=path,function=name,original_sha256=digest(original),
          derived_sha256=digest(changed),edits=edits,byte_exact_reversal=True))
    return generated,proof
def adapters():
    text,proof=derive();init={'re':re}
    for name in ('targets','flag_block','flags','op_only'):exec(compile(text[name],'<frozen318-'+name+'>','exec'),init)
    native={'re':re,'initialization':SimpleNamespace(**{n:init[n]for n in ('targets','flag_block','flags')})}
    for name in ('initialized_deck','gate'):exec(compile(text[name],'<frozen318-'+name+'>','exec'),native)
    return SimpleNamespace(**{n:init[n]for n in ('targets','flag_block','flags','op_only')},
      initialized_deck=native['initialized_deck'],gate=native['gate'],source_proof=proof)
def prepared_contract(label,deck,contract,summary_raw):
    assert digest(summary_raw)==PREPARATION['summary_sha256']
    summary=json.loads(summary_raw)
    assert summary['status']=='PASS_FOUR_REAL_THREE_MODEL_PREPARATIONS_NOT_ELECTRICAL_ACCEPTANCE'
    assert summary['run_id']==PREPARATION['run']and summary['source_head']==PREPARATION['head']
    assert summary['validation_errors']==[]and summary['sources_unchanged']
    evidence=summary['preparation']['cases'][label]
    assert digest(deck)==evidence['deck_sha256']==contract['deck_sha256']
    assert digest(json.dumps(contract,indent=2,allow_nan=False)+'\n')==evidence['contract_sha256']
    assert contract['schema']=='physical334-three-model-loaded-fixture-v1'
    assert len(contract['hbt'])==contract['hbt_count']==evidence['hbt_devices']==318
    assert len(contract['vectors'])==len(set(contract['vectors']))==evidence['vectors']==4726
    assert len(contract['thermal_nodes'])==len(set(contract['thermal_nodes']))==evidence['thermal_nodes']==390
    assert [r['instance']for r in contract['instances']]==['xdut','xloadm','xloadq']
    assert all(sum(v['fixture_instance']==name for v in contract['hbt'].values())==106 for name in ('xdut','xloadm','xloadq'))
    assert contract['full_internal_model_nodes_saved']and contract['all318_HBT_safety_required']
    assert contract['uniform_OFF_initialization_required_for_all318']and contract['zero_source_OP_required']
    assert not contract['initial_differential_phase_forced']and not contract['observed_phase_fit']
    assert contract['timing']['STOP_s']==34e-9 and contract['timing']['maxstep_s']==.3125e-12
    a=adapters();initialized=a.initialized_deck(deck,contract)
    block=a.flag_block(contract,True)
    assert initialized.replace(block,'')==deck and initialized.count(block)==1
    assert len(a.targets(contract))==318
    return initialized,dict(base_deck_sha256=digest(deck),initialized_deck_sha256=digest(initialized),
      immutable_contract_sha256=evidence['contract_sha256'],uniform_native_targets=318,
      source_derivations=a.source_proof,initialization_phase_selected=False,
      only_added_cards='Uniform OFF=1 and exact ordered show/readback for every actual HBT; all original deck bytes restored by deleting this sole block.',
      native_executed=False,electrical_accepted=False)
def check_gate(row):
    """Original gate plus exact newly prepared full-vector and all-model census."""
    a=adapters();answer=a.gate(row)
    capture=row.get('capture',{});measurement=row.get('measurement',{})
    strengthened=dict(
      native_columns=capture.get('columns')==4727,
      all_three_model_safety=measurement.get('all318_HBT_safety_passed')is True,
      all_three_fixed_phase=measurement.get('all_three_fixed_phase_screens_passed')is True,
      exact_HBT_measurement_count=len(measurement.get('hbt_safety',{}))==318,
      exact_three_model_screens=set(measurement.get('three_model_screens',{}))=={'xdut','xloadm','xloadq'})
    answer['checks'].update(strengthened);answer['passed']=all(answer['checks'].values())
    return answer
