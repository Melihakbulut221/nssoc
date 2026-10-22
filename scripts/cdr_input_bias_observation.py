#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe real C/D input-divider terminals and headroom; no fitted circuit."""
import copy
import numpy as np
from decimal import Decimal
import build_pcie_local_vco_hybrid_v6 as parser

def between(records, a, b):
    assert a != b
    found = [r for r in records.values() if r['model']=='rppd'
             and {a,b} <= {t['native_cluster'] for t in r['terminals']}]
    assert len(found)==1, ('Unique actual native input resistor', a,b,len(found))
    record = found[0]
    endpoint = {}
    for cluster in (a,b):
        terms=[t for t in record['terminals'] if t['native_cluster']==cluster]
        assert len(terms)==1, 'One actual terminal per endpoint'
        endpoint[cluster]=terms[0]
    return record, endpoint

def sample(t, values, when):
    assert t.ndim == values.ndim == 1 and len(t)==len(values)>1
    assert np.all(np.diff(t)>0) and np.isfinite(values).all()
    assert np.isfinite(when).all() and min(when)>=t[0] and max(when)<=t[-1], 'No extrapolation'
    return np.interp(when,t,values)

def controls():
    r=dict(instance='xr',model='rppd',parameters=dict(w='4u',l='1.2u'),
           terminals=[dict(terminal='P',native_cluster=10,node='p'),
                      dict(terminal='N',native_cluster=20,node='n'),
                      dict(terminal='B',native_cluster=1,node='sub')])
    selected,points=between({'xr':r},10,20)
    assert selected==r and points[10]['node']=='p' and points[20]['node']=='n'
    rejected=[]
    bads=[('missing',{},10,20),('ambiguous',{'a':r,'b':r},10,20),
          ('wrong_net',{'xr':r},10,30),('same_endpoint',{'xr':r},10,10)]
    duplicate=copy.deepcopy(r);duplicate['terminals'].append(copy.deepcopy(r['terminals'][0]))
    bads.append(('duplicate_terminal',{'xr':duplicate},10,20))
    wrong_model=copy.deepcopy(r);wrong_model['model']='npn13g2'
    bads.append(('wrong_model',{'xr':wrong_model},10,20))
    for name,records,a,b in bads:
        try:between(records,a,b)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Invalid topology accepted: '+name)
    t=np.array([0.,1.,2.]);v=np.array([1.,2.,3.])
    assert np.array_equal(sample(t,v,[.5,1.5]),[1.5,2.5])
    for when in ([-.1],[2.1]):
        try:sample(t,v,when)
        except AssertionError:rejected.append('extrapolation')
        else:raise AssertionError('Extrapolated observation')
    return dict(rejected=rejected,known_interpolation_exact=True,
                scope='Physical endpoint binding and observation controls, no new circuit acceptance')

def observe(tag, t, voltage, records, logical, graph, members, layout, macro, expected, edges, ui, active):
    assert tag in ('c','d')
    plan=next(p for p in layout['source_plan']['nodes'] if p['tag']==macro)
    pins={k.lower():v for k,v in plan['pins'].items()}
    assert {'dp','dn','avdd','sub'} <= set(pins)
    assert (pins['dp'],pins['dn']) == (('cup','cun') if tag=='c' else ('dup','dun'))
    g=graph['master'];connections={};traces={}
    for polarity,pin in [('positive','dp'),('negative','dn')]:
        base=g[polarity+'_input_native'];source=logical[pins[pin]][0];supply=logical[pins['avdd']][0]
        ri,ri_terms=between(records,source,base)
        rb,rb_terms=between(records,supply,base)
        assert ri['instance']!=rb['instance']
        assert parser.number(ri['parameters']['w'])==parser.number(rb['parameters']['w'])==Decimal('4e-6')
        assert parser.number(ri['parameters']['l'])==Decimal('1.2e-6')
        assert parser.number(rb['parameters']['l'])==Decimal('.9e-6')
        def val(term):return voltage('xpd.'+term['node'].lower())
        traces[polarity+'_source_terminal']=val(ri_terms[source])
        traces[polarity+'_input_resistor_base_terminal']=val(ri_terms[base])
        traces[polarity+'_bias_resistor_base_terminal']=val(rb_terms[base])
        traces[polarity+'_supply_terminal']=val(rb_terms[supply])
        dev=g['data_'+polarity]
        traces[polarity+'_hbt_base']=voltage(members[dev]['nodes'][1])
        connections[polarity]=dict(source_pin=pins[pin],source_native=source,base_native=base,
                                   input_resistor=ri,bias_resistor=rb,data_device=dev)
    for label,p,n in [('source','positive_source_terminal','negative_source_terminal'),
                      ('input_resistor_base','positive_input_resistor_base_terminal','negative_input_resistor_base_terminal'),
                      ('hbt_base','positive_hbt_base','negative_hbt_base')]:
        traces[label+'_differential_v']=traces[p]-traces[n]
        traces[label+'_commonmode_v']=(traces[p]+traces[n])/2
    for polarity in ('positive','negative'):
        traces[polarity+'_input_resistor_drop_v']=traces[polarity+'_source_terminal']-traces[polarity+'_input_resistor_base_terminal']
        traces[polarity+'_bias_resistor_drop_v']=traces[polarity+'_supply_terminal']-traces[polarity+'_bias_resistor_base_terminal']
        traces[polarity+'_base_wire_drop_v']=traces[polarity+'_input_resistor_base_terminal']-traces[polarity+'_hbt_base']
    roles=dict(master_data=[g['data_positive'],g['data_negative']],master_track=g['track_selectors'],
               master_hold=g['hold_selectors'])
    for role,names in roles.items():
        for name in names:
            vc=voltage(members[name]['nodes'][0]);ve=voltage(members[name]['nodes'][2])
            traces[role+':'+name+':vce_v']=vc-ve
    full_stats={}
    for name,values in traces.items():
        assert len(values)==len(t) and np.isfinite(values).all()
        active_values=values[active]
        full_stats[name]=dict(minimum=float(active_values.min()),maximum=float(active_values.max()),
                              mean=float(active_values.mean()))
    offsets=(-.5,-.3,-.1,0.,.1,.3,.6,.9)
    times=[edge+offset*ui for edge in edges for offset in offsets]
    sampled={name:sample(t,values,times) for name,values in traces.items()}
    rows=[]
    for i,(edge,bit) in enumerate(zip(edges,expected,strict=True)):
        for j,offset in enumerate(offsets):
            k=i*len(offsets)+j
            values={name:float(data[k])for name,data in sampled.items()}
            rows.append(dict(bit_index=i+1,expected=bit,offset_ui=offset,time_s=times[k],
                             values=values,
                             signed_source_differential_v=(2*bit-1)*values['source_differential_v'],
                             signed_hbt_base_differential_v=(2*bit-1)*values['hbt_base_differential_v']))
    summary=[]
    for offset in offsets:
        group=[r for r in rows if r['offset_ui']==offset]
        summary.append(dict(offset_ui=offset,samples=len(group),
            minimum_signed_source_v=min(r['signed_source_differential_v']for r in group),
            minimum_signed_base_v=min(r['signed_hbt_base_differential_v']for r in group),
            base_commonmode_range_v=[min(r['values']['hbt_base_commonmode_v']for r in group),
                                     max(r['values']['hbt_base_commonmode_v']for r in group)],
            source_commonmode_range_v=[min(r['values']['source_commonmode_v']for r in group),
                                       max(r['values']['source_commonmode_v']for r in group)],
            minimum_observed_master_vce_v=min(r['values'][n]for r in group for n in traces if n.endswith(':vce_v'))))
    return dict(actual_native_connections=connections,full_active_statistics=full_stats,
                original_aperture_rows=rows,phase_summary=summary,
                original_samples_changed=False,new_acceptance_gate=False,
                scope='Real resistor endpoints, HBT bases and native device VCE on original full rejected waveform. Interpolation observes fixed original apertures only. No ideal divider fit, current inference, circuit change or causal proof.')
