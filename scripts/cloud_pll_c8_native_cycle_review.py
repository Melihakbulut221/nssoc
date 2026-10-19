#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only native PLL cycle observations; never an acceptance or fitted model."""
from collections import Counter,defaultdict
import numpy as np
from cloud_pll_terminal_diagnosis import crossing_times
from review_cloud_pll_loop import records

def observe(data,cycles,inventory,bench):
    t=data['time'];up=data['v(up)'];down=data['v(down)'];control=data['v(vctrl)']
    clock=crossing_times(t,data['v(clkp)']-data['v(clkn)'],0.)
    ref=crossing_times(t,data['v(reference)'],1.25)
    assert len(clock)>1 and len(ref)>1
    pfd_names=['v(up)','v(down)']+sorted(n for n in data if n.startswith('v(xloop.xpfd.'))
    edges={}
    for name in pfd_names:
        thresholds=(1.25,)if name in ('v(up)','v(down)')else(.6,1.25)
        edges[name]={}
        for level in thresholds:
            edges[name][str(level)]=dict(rising=crossing_times(t,data[name],level),falling=crossing_times(t,-data[name],-level))
    rows=[]
    for source in cycles['cycles']:
        lo,hi=source['interval_s']
        if lo<1e-7:continue
        a=int(np.searchsorted(t,lo,side='left'));b=int(np.searchsorted(t,hi,side='right'))
        assert b-a>100
        tt=t[a:b];v=control[a:b];u=up[a:b]>=1.25;d=down[a:b]>=1.25
        # Four states partition every captured sample and every following
        # segment. A segment is classified by its starting sample.
        states={'both_high':u&d,'up_only':u&~d,'down_only':~u&d,'both_low':~u&~d}
        assert np.all(sum(x.astype(np.int8)for x in states.values())==1)
        dv=np.diff(v);dt=np.diff(tt)
        state_stats={}
        for name,mask in states.items():
            selected=mask[:-1]
            state_stats[name]=dict(duration_s=float(dt[selected].sum()),control_delta_v=float(dv[selected].sum()),
                sample_count=int(mask.sum()),scope='Observed control-voltage increments, not inferred pump current or charge')
        assert abs(sum(x['duration_s']for x in state_stats.values())-(tt[-1]-tt[0]))<1e-18
        assert abs(sum(x['control_delta_v']for x in state_stats.values())-(v[-1]-v[0]))<1e-10
        ee=clock[(clock>=lo)&(clock<hi)];periods=np.diff(ee)
        assert len(periods)>70
        ctrl=np.interp((ee[:-1]+ee[1:])/2,t,control)
        corr=float(np.corrcoef(periods,ctrl)[0,1])if np.ptp(ctrl)>0 and np.ptp(periods)>0 else None
        edge_rows={}
        for name,by_level in edges.items():
            edge_rows[name]={}
            for level,by_polarity in by_level.items():
                edge_rows[name][level]={pol:[float(e-lo)for e in values[(values>=lo)&(values<hi)]]for pol,values in by_polarity.items()}
        rr=ref[(ref>=lo)&(ref<hi)]
        rows.append(dict(feedback_edge_ordinal=source['feedback_edge_ordinal'],interval_s=[lo,hi],
            actual_samples=[float(tt[0]),float(tt[-1])],reference_offsets_s=[float(e-lo)for e in rr],
            actual_clock_edges=len(ee),clock_period_quantiles_s={str(q):float(np.quantile(periods,q))for q in (0,.01,.5,.99,1)},
            period_control_correlation=corr,control_range_v=[float(v.min()),float(v.max())],
            control_state_partition=state_stats,pfd_threshold_crossings_relative_s=edge_rows))
    assert len(rows)>70
    public=inventory['ports'];cards=records(bench)
    calls=[c for c in cards if c[0].lower()=='xloop'];assert len(calls)==1 and len(calls[0])==len(public)+2
    mapping=dict(zip(public,calls[0][1:-1],strict=True))
    def voltage(node):
        name=mapping.get(node,'xloop.'+node)
        return None if name.lower()=='0'else'v('+name.lower()+')'
    need={v for device in inventory['devices'].values()for node in device['nodes']if(v:=voltage(node))is not None}
    saved=set(data)-{'time'}
    missing=sorted(need-saved)
    pump={name:d for name,d in inventory['devices'].items()if name.lower().startswith('x_xpump_')}
    assert len(pump)==30
    parent={}
    def root(n):
        parent.setdefault(n,n)
        while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
        return n
    for w in inventory['wires'].values():
        if w['kind']=='R':parent[root(w['nodes'][0])]=root(w['nodes'][1])
    groups=defaultdict(list)
    for p in public:groups[root(p)].append(p)
    target=root('vctrl');incident=[];internal=[]
    for name,w in inventory['wires'].items():
        if w['kind']!='C':continue
        a,b=map(root,w['nodes']);hits=(a==target)+(b==target)
        if not hits:continue
        row=dict(name=name,nodes=w['nodes'],capacitance_f=w['value'])
        if hits==2:internal.append(row)
        else:
            row['other_component_public_ports']=groups[b if a==target else a]
            incident.append(row)
    assert incident
    external=[c for c in cards if c[0][0].lower()in ('r','c','i','v') and len(c)>2 and c[0].lower()not in ('run','reset','resume')]
    return dict(status='COMPLETE_NATIVE_PLL_CYCLE_AND_CONTROL_NODE_OBSERVATIONS_NOT_ACCEPTANCE',
        cycles=rows,control_component_wire_capacitance=dict(incident_sum_f=sum(x['capacitance_f']for x in incident),
          incident=incident,internal_resistor_connected_component_caps=internal,
          scope='Resistor connectivity inventory only. Mutual capacitances are not grounded; the sum is not effective loop capacitance or an RC time constant.'),
        actual_top_level_source_and_passive_cards=external,actual_parent_port_binding=mapping,
        native_pump_devices=pump,full_device_probe_coverage=dict(native_devices=845,required_distinct_terminal_voltage_vectors=len(need),
          saved_terminal_voltage_vectors=len(need&saved),missing_voltage_vectors=missing,
          all_device_safety_verified=False,scope='Coverage inventory only;34saved vectors cannot establish full845-device voltage/current safety.'),
        original_acceptance_windows_shifted=False,threshold_scope='1.25V original UP/DOWN/reference diagnostic; fixed0.6V and1.25V internal observations are not new logic acceptance thresholds.',
        causal_scope='Within-cycle association only. No fitted target, inferred pump current, supply waiver, new transient or electrical acceptance.')
