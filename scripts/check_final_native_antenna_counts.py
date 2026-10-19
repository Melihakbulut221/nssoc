#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind final OpenROAD antenna counts to actual violating net/pin sections."""
import copy,re
def validate(text,metrics):
    net=pin=None;headings=[];bad=set()
    for line in text.splitlines():
        m=re.match(r'^Net:\s*(\S+)\s*$',line)
        if m:
            net=m.group(1);pin=None;headings.append(net);continue
        m=re.match(r'^\s+Pin:\s+(\S+)\s+\(',line)
        if m:
            assert net is not None;pin=m.group(1);continue
        if '(VIOLATED)'in line:
            assert net is not None and pin is not None
            bad.add((net,pin))
    badnets={n for n,p in bad}
    assert len(headings)==len(set(headings)) and set(headings)==badnets
    ns=re.findall(r'^\[INFO ANT-0002\] Found (\d+) net violations\.\s*$',text,re.M)
    ps=re.findall(r'^\[INFO ANT-0001\] Found (\d+) pin violations\.\s*$',text,re.M)
    assert len(ns)==len(ps)==1
    assert len(badnets)==int(ns[0])==metrics['antenna__violating__nets']
    assert len(bad)==int(ps[0])==metrics['antenna__violating__pins']
    return dict(final_violating_nets=len(badnets),final_violating_pins=len(bad),violating_pins=[dict(net=n,pin=p)for n,p in sorted(bad)],earlier_route_counter=metrics.get('route__antenna_violation__count'),passed=len(badnets)==len(bad)==0)
def controls():
    text='Net: A\n  Pin: U/A (cell)\n    Required ratio: 200 (VIOLATED)\n    Required ratio: 200 (VIOLATED)\n  Pin: V/A (cell)\n    Required ratio: 200 (VIOLATED)\n[INFO ANT-0002] Found 1 net violations.\n[INFO ANT-0001] Found 2 pin violations.\n'
    m={'antenna__violating__nets':1,'antenna__violating__pins':2,'route__antenna_violation__count':999}
    result=validate(text,m);assert not result['passed']and result['final_violating_pins']==2
    assert validate('[INFO ANT-0002] Found 0 net violations.\n[INFO ANT-0001] Found 0 pin violations.\n',{'antenna__violating__nets':0,'antenna__violating__pins':0})['passed']
    faults=[]
    for case in ['wrong_net_metric','wrong_pin_metric','removed_violation','missing_pin','missing_summary','extra_net','duplicate_net']:
        t=text;x=copy.deepcopy(m)
        if case=='wrong_net_metric':x['antenna__violating__nets']=0
        elif case=='wrong_pin_metric':x['antenna__violating__pins']=1
        elif case=='removed_violation':t=t.replace('(VIOLATED)','')
        elif case=='missing_pin':t=t.replace('  Pin: U/A (cell)\n','')
        elif case=='missing_summary':t=t.replace('[INFO ANT-0002] Found 1 net violations.\n','')
        elif case=='extra_net':t='Net: UNUSED\n'+t
        else:t='Net: A\n'+t
        try:validate(t,x)
        except AssertionError:faults.append(case)
        else:raise AssertionError('Accepted corrupted final antenna report: '+case)
    return dict(status='PASS_FINAL_ANTENNA_COUNTS_AND_SEVEN_FAULTS',rejected=faults,stale_route_counter_cannot_override_final_check=True)
if __name__=='__main__':print(controls())
