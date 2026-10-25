#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare actual offset244 decks; retain original state, timing and safety gates."""
import ast,hashlib,json,os
from pathlib import Path
import numpy as np
import tx_phase_assert_offset_diagnostic as candidate
import tx_phase_fast_assert_diagnostic as original
import check_tx_phase_async_preset_intrinsic as observers
import cloud_tx_phase_async_preset_intrinsic as provenance
import build_tx_phase_async_preset_source as definitions
import check_tx_phase_async_preset_source as grammar
ROOT=Path(__file__).resolve().parents[1]
def funcs(text):
    return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=json.loads((ROOT/'scripts/tx-phase-assert-offset-preparation-methods.json').read_text())
    for p,h in m['protected'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    base=(ROOT/m['base_path']).read_text();derived=base
    for edit in m['edits']:
        assert derived.count(edit['before'])==edit['count']
        derived=derived.replace(edit['before'],edit['after'])
    assert derived==(ROOT/m['candidate_path']).read_text()
    old,new=funcs(base),funcs(derived);assert set(old)==set(new)
    preserved=[n for n in old if n!='inventory']
    assert all(old[n]==new[n]for n in preserved),'Original prepare, fixture or electrical observer changed'
    assert candidate.source_definitions is definitions.definitions
    assert candidate.SOURCE_NAMES is definitions.NAMES
    assert candidate.SOURCE_PRIMITIVES is grammar.PRIMITIVES
    raw,bound=provenance.observer()
    text=(ROOT/candidate.builder.OUTPUT).read_text()
    oldtext=(ROOT/original.builder.OUTPUT).read_text()
    assert candidate.builder.recover(text)==oldtext
    t=np.arange(0,candidate.STOP+.5e-12,1e-12);cases={}
    for sign in ('p','n'):
      for high in (True,False):
        body,c=candidate.prepare(text,bound,sign,high,'candidate.spice','/models','/r3.osdi')
        oldbody,o=original.prepare(oldtext,bound,sign,high,'candidate.spice','/models','/r3.osdi')
        assert body==oldbody,'External stimuli, include topology or solver changed'
        assert c['primitive_census']==dict(npn13G2=106,rppd=130,cap_cmim=8)
        assert len(c['hbt'])==106 and len(c['vectors'])==358
        assert len([v for v in c['vectors']if v.endswith('.dt)')])==130
        for key in ('hbt','vectors','oracle','limits','timing','boundary','ports','top'):
            assert c[key]==o[key],key
        changes=[(a,b)for a,b in zip(o['devices'],c['devices'],strict=True)if a!=b]
        assert len(changes)==1
        a,b=changes[0]
        assert a['instance']==b['instance']=='xdut.xrun.xand_skew'
        assert a['model']==b['model']=='rppd'and a['nodes']==b['nodes']==['xdut.xrun.bip','0','0']
        assert a['parameters']==['w=1u','l=32u','b=0','sw_et=1']
        assert b=={**a,'parameters':['w=1u','l=20u','b=0','sw_et=1']}
        assert candidate.signal_review(t,observers.synthetic(t,c),c)['diagnostic_signal_screen_passed']
        assert c['timing']['STOP_s']==34e-9 and c['timing']['maxstep_s']==.3125e-12
        cases[sign+'-'+str(high)]=dict(prepared=True,primitive_count=244,hbt_count=106,vector_count=358,
          thermal_vectors=130,deck_sha256=candidate.digest(body),contract_sha256=candidate.digest(json.dumps(c,sort_keys=True)),
          exact_old_deck=True,exact_old_vectors_HBT_oracle_limits=True,one_real_device_parameter_delta=changes)
    c=candidate.prepare(text,bound,'p',True,'candidate.spice','/models','/r3.osdi')[1]
    good=observers.synthetic(t,c);bad=[]
    for name,signals in [('master_polarity',{**good,'MP':-good['MP']}),('slave_polarity',{**good,'QP':-good['QP']}),
      ('late_release',{**good,'release':np.interp(t-80e-12,t,good['release'])}),('missing_reset',{**good,'release':np.where(t>candidate.RESET_ASSERT,.2,good['release'])})]:
        assert not candidate.signal_review(t,signals,c)['diagnostic_signal_screen_passed'];bad.append(name)
    tt=np.array([0.,candidate.START,candidate.STOP]);zero=np.zeros(3);cv=np.ones(3);bv=np.full(3,.75);ic=np.full(3,.001)
    for name,col,base,cur in [('headroom',np.full(3,.39),bv,ic),('VCE',np.full(3,1.61),bv,ic),
      ('VBE',cv,np.full(3,1.01),ic),('current',cv,bv,np.full(3,.00301))]:
        assert not candidate.hbt_screen(tt,col,base,zero,cur,1)['passed'];bad.append(name)
    assert len(bad)==8
    print(json.dumps(dict(status='PASS_ASSERT_OFFSET244_FOUR_PREPARED_UNCHANGED_ORACLE_NOT_NATIVE',
      positive_cases=cases,unchanged_original_functions=preserved,negative_controls=bad,
      original244_accepted=False,native_execution=False,reset_hardware_qualified=False,
      layout_RC_included=False,PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
