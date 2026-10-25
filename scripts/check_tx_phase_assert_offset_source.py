#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only one-resistor proof; no timing, startup or loaded acceptance."""
import hashlib,json,os
from pathlib import Path
import build_tx_phase_assert_offset_source as b
import check_tx_phase_fast_assert_source as prior
ROOT=Path(__file__).resolve().parents[1]
def validate(text):
    recovered=b.recover(text)
    assert recovered==(ROOT/b.BASE).read_text()
    counts=prior.validate(recovered)
    assert text==b.build(recovered)
    assert all(v==dict(primitives=244,terminals=830,npn13G2=106,rppd=130,cap_cmim=8) for v in counts.values())
    return counts
def drawn_resistor_points():
    # rppd values below are L/W sheet-resistance multiples, not measured ohms.
    # Contact, base current, capacitance, thermal and PVT effects are excluded.
    feed=3.6/2.;ground=16.;skew=20.
    rows=[]
    for arm in (-1,1):
      for release in (-1,1):
       for cm in (2.30,2.40):
        for diff in (.113,.24):
          ap=2.2605958859271773+arm*.08531554498100902
          an=2.2605958859271773-arm*.08531554498100902
          rp=cm+release*diff/2.;rn=cm-release*diff/2.
          bip=(ap+rp)/(2.+feed/ground+feed/skew)
          bin=(an+rn)/(2.+feed/ground)
          want=1 if arm==release==1 else -1
          rows.append(dict(arm_sign=arm,release_sign=release,release_cm_v=cm,
            release_diff_v=diff,unloaded_base_diff_v=bip-bin,signed_margin_v=want*(bip-bin)))
    assert len(rows)==16 and all(r['signed_margin_v']>0 for r in rows)
    return dict(scope='Unloaded drawn L/W algebra only; not measured resistance, transfer, delay, safety or waveform-envelope proof',
      feed_sheet_multiples=feed,ground_sheet_multiples=ground,old_offset_sheet_multiples=32.,
      new_offset_sheet_multiples=20.,ideal_offset_conductance_ratio=1.6,cases=rows,
      real_resistance_includes_PDK_contacts_temperature_and_geometry=True,native_electrical_acceptance=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=json.loads((ROOT/'scripts/tx-phase-assert-offset-source-methods.json').read_text())
    for p,h in m['protected'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    text=(ROOT/b.OUTPUT).read_text();counts=validate(text)
    faults=[
      ('original_failed_offset',text.replace(b.NEW,b.OLD,1)),
      ('wrong_offset_length',text.replace(b.NEW,b.NEW.replace('l=20u','l=24u'),1)),
      ('wrong_offset_width',text.replace(b.NEW,b.NEW.replace('w=1u','w=2u'),1)),
      ('wrong_base_endpoint',text.replace(b.NEW,b.NEW.replace('bip avss','bin avss'),1)),
      ('wrong_reference_endpoint',text.replace(b.NEW,b.NEW.replace('bip avss','bip avdd'),1)),
      ('disabled_thermal_model',text.replace(b.NEW,b.NEW.replace('sw_et=1','sw_et=0'),1)),
      ('missing_offset',text.replace(b.NEW+'\n','',1)),
      ('duplicate_offset',text.replace(b.NEW,b.NEW+'\n'+b.NEW,1)),
      ('changed_ARM_feed',text.replace('XARM_P armp bip','XARM_P armn bip',1)),
      ('bypassed_first_fall',text.replace('XRUN releasedp releasedn ARM_P ARM_N','XRUN ARM_P ARM_N ARM_P ARM_N',1)),
      ('changed_latch_bias',text.replace('l=11.5u','l=10u',1)),
      ('internal_ideal_source',text+'\nVforce runp runn .2\n'),
      ('public_port_order',text.replace('ip in armp armn cp cn','ip in armn armp cp cn',1)),
      ('feedback_swap',text.replace('XM QN QP MP MN','XM QP QN MP MN',1))]
    rejected=[]
    for name,bad in faults:
        assert bad!=text,name
        try:validate(bad)
        except (AssertionError,KeyError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(rejected)==14
    print(json.dumps(dict(status='PASS_ASSERT_OFFSET244_SOURCE_ONLY_NOT_ELECTRICAL',
      candidate_sha256=b.digest(text),counts=counts,negative_controls=rejected,
      exact_single_resistor_delta=True,original244_byte_exact_after_declared_reversal=True,
      drawn_resistor_design=drawn_resistor_points(),original244_accepted=False,
      native_execution=False,reset_hardware_qualified=False,layout_RC_included=False,
      PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
