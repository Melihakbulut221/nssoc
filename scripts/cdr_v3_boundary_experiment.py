#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Declared external-boundary sensitivities; no intrinsic or wire model change."""
from decimal import Decimal
import cloud_cdr_pd_vi as original
PROFILES={
    'clock145':dict(clock_cm_v=1.45,select_bias_a=.001),
    'select500':dict(clock_cm_v=1.29,select_bias_a=.0005),
    'clock145_select500':dict(clock_cm_v=1.45,select_bias_a=.0005),
}
def tokens(text):
    assert text.startswith('PWL(')and text.endswith(')')
    rows=text[4:-1].split();assert len(rows)%2==0
    return list(zip(rows[::2],rows[1::2],strict=True))
def verify_clock(before,after,scale,cm):
    a,b=tokens(before),tokens(after);assert len(a)==len(b)
    shift=(Decimal(str(cm))-Decimal('1.29'))*Decimal(str(scale))
    assert [t for t,v in a]==[t for t,v in b],'Clock times changed'
    for (t,v),(nt,nv)in zip(a,b,strict=True):
        expected=Decimal(v)+(shift if Decimal(t)>0 else Decimal(0))
        assert abs(Decimal(nv)-expected)<Decimal('1e-12'),'Clock differential amplitude or zero-source start changed'
    return True
def clock(scale,positive,stopped,profile):
    cm=PROFILES[profile]['clock_cm_v'];before=original.clock(scale,positive,stopped)
    shift=(Decimal(str(cm))-Decimal('1.29'))*Decimal(str(scale))
    rows=[(t,str(Decimal(v)+(shift if Decimal(t)>0 else Decimal(0))))for t,v in tokens(before)]
    after='PWL('+' '.join(t+' '+v for t,v in rows)+')'
    verify_clock(before,after,scale,cm);return after
def bias(b,profile):
    assert b in ('ira','irb','irc','ird','irx','iry','ibda','ibdc','ibs0','ibs1')
    value=PROFILES[profile]['select_bias_a']if b in ('ibs0','ibs1')else .001 if b.startswith('ib')else .0005
    return str(value)+')'
def controls():
    count=0
    for profile in PROFILES:
        for positive in (False,True):
            for stopped in (False,True):
                before=original.clock(1.,positive,stopped);after=clock(1.,positive,stopped,profile)
                assert verify_clock(before,after,1.,PROFILES[profile]['clock_cm_v']);count+=1
    before=original.clock(1.,True,False);after=clock(1.,True,False,'clock145');rows=tokens(after);faults=[]
    for case in ('missing_point','phase_shift','wrong_amplitude','nonzero_initial_source'):
        bad=rows.copy()
        if case=='missing_point':del bad[2]
        elif case=='phase_shift':bad[2]=(str(Decimal(bad[2][0])+Decimal('1e-12')),bad[2][1])
        elif case=='wrong_amplitude':bad[2]=(bad[2][0],str(Decimal(bad[2][1])+Decimal('.01')))
        else:bad[0]=(bad[0][0],'.01')
        changed='PWL('+' '.join(t+' '+v for t,v in bad)+')'
        try:verify_clock(before,changed,1.,1.45)
        except AssertionError:faults.append(case)
        else:raise AssertionError('Accepted '+case)
    assert bias('ibs0','clock145')=='0.001)' and bias('ibs1','select500')=='0.0005)'
    assert all(bias(b,p)==('0.001)'if b in ('ibda','ibdc')else'0.0005)')for p in PROFILES for b in ('ira','irb','irc','ird','irx','iry','ibda','ibdc'))
    return dict(positive_clock_cases=count,rejected_clock_changes=faults,only_select_bias_varies=True)
