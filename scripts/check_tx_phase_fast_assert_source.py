#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source/census controls for the real244-device fast-assert candidate."""
import copy,hashlib,json,os
from collections import Counter
from pathlib import Path
import build_tx_phase_fast_assert_source as b
import check_tx_phase_async_preset_source as original
ROOT=Path(__file__).resolve().parents[1]
PRIMITIVES=original.PRIMITIVES
def validate(text):
    base=(ROOT/b.BASE).read_text();assert b.digest(base)==b.BASE_SHA
    original.validate(base)
    suffix='\n'+b.addition(base)
    assert text.endswith(suffix)and text.count(b.NEW)==2
    recovered=text[:-len(suffix)].replace(b.NEW,b.OLD)
    assert recovered==base,'Original241-source changed outside two declared XRUN connections'
    d=b.definitions(text);old=b.definitions(base)
    assert set(d)==set(old)|{b.AND}
    level=d[b.AND]
    assert level['ports']==['ip','in','armp','armn','cp','cn','avdd','avss','sub']
    assert level['cards']==old[b.NAMES['level']]['cards']+[s.split()for s in b.EXTRA]
    assert len({r[0]for r in level['cards']})==len(level['cards'])==20
    for sign in ('p','n'):
        top=d[b.NAMES['parent'+sign]]
        row=next(r for r in top['cards']if r[0]=='XRUN')
        assert row==b.NEW.split()
        assert next(r for r in top['cards']if r[0]=='XRELEASE')==next(r for r in old[b.NAMES['parent'+sign]]['cards']if r[0]=='XRELEASE')
    counts={}
    for sign in ('p','n'):
        records=[]
        def walk(name,trail=()):
            assert name not in trail
            for r in d[name]['cards']:
                found=[(m,n)for m,n in PRIMITIVES.items()if len(r)>n+1 and r[n+1]==m]
                if found:assert len(found)==1;records.append((found[0][0],found[0][1]))
                else:
                    assert r[-1]in d and len(r[1:-1])==len(d[r[-1]]['ports'])
                    walk(r[-1],(*trail,name))
        walk(b.NAMES['parent'+sign])
        census=dict(Counter(m for m,n in records))
        assert census==dict(npn13G2=106,rppd=130,cap_cmim=8)
        assert len(records)==244 and sum(n for m,n in records)==830
        counts[sign]=dict(primitives=244,terminals=830,**census)
    return counts
def passive_unloaded_design():
    # Equal sheet resistance, zero HBT base current/contact/temperature effects:
    # conductances are inverse drawn aspect ratios, NOT a PDK electrical model.
    rin=3.6/2;ground=16.;skew=32.
    cm_arm=2.2605958859271773;amplitude_arm=.08531554498100902
    rows=[]
    for arm in (-1,1):
        for rel in (-1,1):
            for release_cm in (2.30,2.40):
                for release_diff in (.113,.24):
                    ap=cm_arm+arm*amplitude_arm;an=cm_arm-arm*amplitude_arm
                    rp=release_cm+rel*release_diff/2;rn=release_cm-rel*release_diff/2
                    bip=(ap+rp)/(2+rin/ground+rin/skew)
                    bin=(an+rn)/(2+rin/ground)
                    want=1 if arm==rel==1 else-1
                    rows.append(dict(arm=arm,release=rel,release_cm_v=release_cm,release_diff_v=release_diff,
                      unloaded_bip_minus_bin_v=bip-bin,signed_margin_v=want*(bip-bin)))
    assert len(rows)==16 and all(r['signed_margin_v']>0 for r in rows)
    return dict(scope='Declared nominal unloaded drawn-resistor algebra only; excludes HBT loading, contacts, PVT and delay. Chosen release interval is a source design sweep, not a claimed stable waveform envelope.',
      cases=rows,native_electrical_acceptance=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=json.loads((ROOT/'scripts/tx-phase-fast-assert-source-methods.json').read_text())
    for p,h in m['protected'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    text=(ROOT/b.OUTPUT).read_text();assert text==b.build();counts=validate(text)
    faults=[
      ('missing_ARM_feed',text.replace(b.EXTRA[0]+'\n','',1)),
      ('swapped_ARM_feed',text.replace('XARM_P armp bip','XARM_P armn bip',1)),
      ('changed_offset',text.replace('l=32u','l=16u',1)),
      ('missing_offset',text.replace(b.EXTRA[2]+'\n','',1)),
      ('swapped_public_ports',text.replace('ip in armp armn cp cn','in ip armp armn cp cn',1)),
      ('bypassed_first_fall',text.replace('XRUN releasedp releasedn ARM_P ARM_N','XRUN ARM_P ARM_N ARM_P ARM_N',1)),
      ('removed_fast_path',text.replace(b.NEW,b.OLD,1)),
      ('changed_original_bias',text.replace('l=11.5u','l=10u',1)),
      ('reversed_release',text.replace('XRUN releasedp releasedn','XRUN releasedn releasedp',1)),
      ('extra_ideal_source',text.replace('.ends '+b.AND,'Vforce cp cn .2\n.ends '+b.AND)),
      ('duplicate_card',text.replace(b.EXTRA[0],b.EXTRA[0]+'\n'+b.EXTRA[0],1))]
    rejected=[]
    for name,bad in faults:
        assert bad!=text,name
        try:validate(bad)
        except (AssertionError,KeyError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(rejected)==11
    print(json.dumps(dict(status='PASS_FAST_ASSERT244_SOURCE_CONNECTIONS_AND_CENSUS_NOT_ELECTRICAL',
      source_sha256=b.digest(text),counts=counts,negative_controls=rejected,original241_devices_recovered_exactly=True,
      original_release_FF_and_clock_stacks_unchanged=True,only_added_intrinsics='Three actual rppd in XRUN; actual ARM fan-in and fixed negative input offset',
      unloaded_design=passive_unloaded_design(),native_execution=False,reset_hardware_qualified=False,
      original_numerical_rejection_unresolved=True,layout_RC_included=False,PLL_connected=False,full_PHY_accepted=False),indent=2))
if __name__=='__main__':main()
