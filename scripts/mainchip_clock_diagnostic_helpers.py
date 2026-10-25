#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explain exact original clock-snapshot differences without relaxing equality."""
import copy,hashlib,json
from pathlib import Path
def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def differences(snapshots):
    assert set(snapshots)=={'before','after'}
    before,after=(snapshots[k]for k in ('before','after'))
    changed={}
    for name in sorted(before.keys()|after.keys()):
        a=before.get(name);b=after.get(name)
        if a==b:continue
        def prefix(x):
            if x is None:return None
            t=x['statement'];return t[:t.index('+')]if '+'in t else t
        changed[name]=dict(before=a,after=b,
            statement_changed=a is None or b is None or a['statement']!=b['statement'],
            attached_geometry_changed=a is None or b is None or a['instances']!=b['instances'],
            connection_prefix_changed=prefix(a)!=prefix(b))
    return dict(status='EXACT_ORIGINAL_CLOCK_SNAPSHOT_DIAGNOSTIC_NOT_ACCEPTANCE',
        original_equality_passed=before==after,accepted=False,
        before_nets=len(before),after_nets=len(after),changed_nets=len(changed),
        statements_changed=sum(v['statement_changed']for v in changed.values()),
        attached_geometry_changed=sum(v['attached_geometry_changed']for v in changed.values()),
        connection_prefixes_changed=sum(v['connection_prefix_changed']for v in changed.values()),
        snapshot_sha256={k:digest(v)for k,v in snapshots.items()},changes=changed)
def write_diagnosis(out,snapshots,source_hashes):
    out=Path(out);r=differences(snapshots)
    assert len(snapshots['before'])>100
    r['original_postroute_expected_net_count']=1691
    (out/'snapshots.json').write_text(json.dumps(snapshots,sort_keys=True,indent=2)+'\n')
    r['complete_snapshots_sha256']=hashlib.sha256((out/'snapshots.json').read_bytes()).hexdigest()
    r['source_hashes']=source_hashes
    (out/'diagnosis.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
def controls():
    a={'clk':dict(statement=['-','clk','(','u','CLK',')','+','FIXED','Metal3','(','0','0',')',';'],
        instances={'u':dict(master='buf',location=[10,20],orientation='R0',status='PLACED')})}
    r=differences(dict(before=a,after=copy.deepcopy(a)));assert r['original_equality_passed']and not r['changes']
    names=[]
    for key,mutate in [
        ('route_coordinate',lambda b:b['clk']['statement'].__setitem__(12,'5')),
        ('route_type',lambda b:b['clk']['statement'].__setitem__(7,'ROUTED')),
        ('clock_pin',lambda b:b['clk']['statement'].__setitem__(4,'D')),
        ('master',lambda b:b['clk']['instances']['u'].__setitem__('master','other')),
        ('location',lambda b:b['clk']['instances']['u'].__setitem__('location',[11,20])),
        ('orientation',lambda b:b['clk']['instances']['u'].__setitem__('orientation','MY')),
        ('placement',lambda b:b['clk']['instances']['u'].__setitem__('status','FIXED')),
        ('missing_net',lambda b:b.pop('clk')),
        ('added_net',lambda b:b.__setitem__('clk2',copy.deepcopy(b['clk'])))]:
        b=copy.deepcopy(a);mutate(b);v=differences(dict(before=a,after=b))
        assert v['original_equality_passed']is False and v['changed_nets']==1 and v['accepted']is False
        if key=='clock_pin':assert v['connection_prefixes_changed']==1
        if key in ('master','location','orientation','placement'):assert v['attached_geometry_changed']==1
        if key in ('route_coordinate','route_type'):assert v['statements_changed']==1 and v['connection_prefixes_changed']==0
        names.append(key)
    return dict(status='PASS_DIAGNOSTIC_COMPARISON_CONTROLS_NOT_NATIVE',identity=True,changed_cases=names)
