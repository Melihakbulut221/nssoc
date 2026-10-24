#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare all four repaired schematic cases, retaining original observers."""
import ast,hashlib,json,os
from pathlib import Path
import numpy as np
import tx_phase_fast_assert_diagnostic as candidate
import tx_phase_async_preset_diagnostic as original
import check_tx_phase_async_preset_intrinsic as observers
import cloud_tx_phase_async_preset_intrinsic as provenance
ROOT=Path(__file__).resolve().parents[1]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=json.loads((ROOT/'scripts/tx-phase-fast-assert-preparation-methods.json').read_text())
    for p,h in m['protected'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    a=(ROOT/m['base_path']).read_text();changed=a
    for edit in m['edits']:
        assert changed.count(edit['before'])==edit['count']
        changed=changed.replace(edit['before'],edit['after'])
    assert changed==(ROOT/m['candidate_path']).read_text()
    def funcs(text):return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    old,new=funcs(a),funcs(changed);assert set(old)==set(new)
    preserved=[n for n in old if n not in ('inventory','prepare')]
    assert all(old[n]==new[n]for n in preserved),'An original electrical/phase observer changed'
    raw,bound=provenance.observer();text=(ROOT/candidate.builder.OUTPUT).read_text()
    t=np.arange(0,candidate.STOP+.5e-12,1e-12);cases={}
    for sign in ('p','n'):
        for high in (True,False):
            body,c=candidate.prepare(text,bound,sign,high,'candidate.spice','/models','/r3.osdi')
            assert c['primitive_census']==dict(npn13G2=106,rppd=130,cap_cmim=8)
            assert len(c['hbt'])==106 and len(c['vectors'])==358
            assert len([v for v in c['vectors']if v.endswith('.dt)')])==130
            assert c['oracle']==original.expected(sign,high)and c['limits']==original.LIMITS
            assert candidate.signal_review(t,observers.synthetic(t,c),c)['diagnostic_signal_screen_passed']
            assert c['timing']['STOP_s']==34e-9 and c['timing']['maxstep_s']==.3125e-12
            cases[sign+'-'+str(high)]=dict(prepared=True,primitive_count=244,hbt_count=106,vector_count=358,
              thermal_vectors=130,deck_sha256=candidate.digest(body),contract_sha256=candidate.digest(json.dumps(c,sort_keys=True)),
              original_phase_oracle_equal=True,original_safety_limits_equal=True)
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
    print(json.dumps(dict(status='PASS_FAST_ASSERT244_ALL_FOUR_PREPARED_ORIGINAL_PHASE_AND_SAFETY_NOT_NATIVE',
      positive_cases=cases,unchanged_original_functions=preserved,negative_controls=bad,
      original_numerical_rejection_unresolved=True,native_execution=False,reset_hardware_qualified=False,
      layout_RC_included=False,PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
