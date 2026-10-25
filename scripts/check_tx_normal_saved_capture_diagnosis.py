#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Small synthetic math/identity controls; not native capture acceptance."""
import copy
import numpy as np
from tx_normal_saved_capture_diagnosis import bracket,hbt_point,native_pairs,crossing_brackets,below_segments,catalog,admitted_window,bit_context,STOP,START,UI,probe_inventory,replay_receipt

def main():
    t=np.array([0.,1.,2.,3.,4.]); v={'v(c)':np.array([2.,2.,1.,2.,2.]),
        'v(b)':np.array([1.,1.,.9,1.,1.]),'v(e)':np.array([.1,.2,.7,.3,.1]),
        'v(s)':np.zeros(5),'@q.x.qnpn13g2[ic]':np.array([0.,.002,.004,.002,0.])}
    spec=dict(model='npn13g2',nx=2,terminals=['c','b','e','s'])
    assert bracket(t,0.)['left_row']==0 and bracket(t,4.)['right_row']==4
    assert bracket(t,2.)['exact_native_row'] and bracket(t,1.25)['left_row']==1
    p=hbt_point(t,v,'x',spec,2)
    assert p['collector_v']==1 and p['base_v']==.9 and p['emitter_v']==.7
    assert p['vce_v']==1-.7 and p['vbe_v']==.9-.7 and p['ic_per_emitter_a']==.002
    assert p['thermal_state'] is None and p['row']==2
    for k,value in [('p1',1.),('p2',1.1),('p3',1.2),('n1',.8),('n2',.7),('n3',.6)]:
        v['v('+k+')']=np.full(5,value)
    pairs=native_pairs(t,v,['p1','p2','p3'],['n1','n2','n3'],2,1)
    assert len(pairs)==9 and pairs[0]['signed_margin_v']==1.-.8
    assert native_pairs(t,v,['p1'],['n1'],2,-1)[0]['signed_margin_v']==-(1.-.8)
    y=np.array([-1.,0.,1.,-1.,1.]); c=crossing_brackets(t,y,0.,0.,4.)
    assert [(r['left_row'],r['right_row']) for r in c]==[(0,1),(2,3),(3,4)]
    assert all('linear_estimate_s' not in r for r in c)
    seg=below_segments(t,np.array([0.,1.,0.,0.,1.]),.4,1.)
    assert len(seg)==1 and seg[0]['first_row']==2 and seg[0]['last_row']==3
    assert seg[0]['entry']['rows']==[1,2] and seg[0]['exit']['rows']==[3,4]
    assert seg[0]['entry']['native_threshold_transition'] and not seg[0]['entry']['censored_by_observation_window']
    censored=below_segments(t,np.zeros(5),.4,1.)[0]
    assert censored['entry']['censored_by_observation_window'] and censored['exit']['censored_by_observation_window']
    assert censored['entry']['values']==[0.,0.] and not censored['entry']['native_threshold_transition']
    assert bit_context(0.) is None and bit_context(np.nextafter(START,0.)) is None
    assert bit_context(START)==0 and bit_context(np.nextafter(STOP,0.))==255
    assert bit_context(STOP) is None
    end=np.nextafter(STOP,0.); window=admitted_window(np.array([0.,end]),START+255*UI,START+256*UI)
    assert window['admitted_endpoint_clipped'] and window['native_scan_bounds_s'][1]==end
    assert window['requested_UI_bounds_s'][1]==START+256*UI
    prefixes=['d'+str(i)for i in range(32)]+['p16_'+str(i)for i in range(16)]+['p8_'+str(i)for i in range(8)]+['p4_'+str(i)for i in range(4)]+['a','b']
    mapping={p+s:[p+s+'_'+str(i)for i in range(3)]for p in prefixes for s in ('p','n')}
    clocks=[dict(name=p+str(i))for p,n in [('sp16_',16),('sp8_',8),('sp4_',4)]for i in range(n)]+[dict(name=n)for n in ('sa','sb','s')]
    observed={'v('+n+')'for nodes in mapping.values()for n in nodes}|{'v(op)','v(on)','v(c)','v(b)','v(e)','v(s)','@q.x.qnpn13g2[ic]'}
    observed|={'v('+c['name']+s+')'for c in clocks for s in ('p','n')}
    contract=dict(interface_probes=mapping,tree_plan=dict(clocks=clocks),vectors=sorted(observed),hbt={'x':spec})
    inventory=probe_inventory(contract)
    assert inventory['all_256_bit_group_sets_checked']==256 and inventory['physical_interface_legs']==124
    assert inventory['public_clock_pairs']==31 and inventory['unavailable_diagnostics']['mux_output_diagnostic_only']['available'] is False
    assert 'v(mp)' not in inventory['requested_vectors'] and 'v(op)' in inventory['requested_vectors']
    report=dict(all_engineering_gates_passed=False,capture_transport={'raw_sha256':'fixture-only'},failed_hbts=['x'],failed_mos=[],signals={'wrong_sign_samples':1})
    assert replay_receipt(report,copy.deepcopy(report))['original_acceptance'] is False
    faults=[]
    def reject(name,func):
        try:func()
        except (AssertionError,KeyError,IndexError,ValueError):faults.append(name)
        else:raise AssertionError('Accepted corruption: '+name)
    for name,arr,at in [('before',t,-.1),('after',t,4.1),('nan_time',np.array([0.,np.nan]),0.),
        ('duplicate_time',np.array([0.,0.,1.]),.5),('reverse_time',np.array([1.,0.]),.5)]:
        reject(name,lambda arr=arr,at=at:bracket(arr,at))
    reject('missing_hbt_current',lambda:hbt_point(t,{k:z for k,z in v.items() if not k.startswith('@')},'x',spec,2))
    reject('wrong_nx',lambda:hbt_point(t,v,'x',dict(spec,nx=0),2))
    reject('wrong_model',lambda:hbt_point(t,v,'x',dict(spec,model='mos'),2))
    reject('missing_substrate',lambda:hbt_point(t,v,'x',dict(spec,terminals=['c','b','e']),2))
    reject('row_outside',lambda:hbt_point(t,v,'x',spec,5))
    reject('wrong_sign',lambda:native_pairs(t,v,['p1'],['n1'],2,0))
    reject('missing_parallel',lambda:native_pairs(t,v,['p1','p2'],['n1','n2'],2,1))
    reject('aliased_parallel',lambda:native_pairs(t,v,['p1','p1','p3'],['n1','n2','n3'],2,1))
    reject('shared_leg',lambda:native_pairs(t,v,['p1'],['p1'],2,1))
    reject('nonfinite_crossing',lambda:crossing_brackets(t,np.array([0.,1.,np.nan,0.,1.]),0.,0.,4.))
    reject('crossing_outside',lambda:crossing_brackets(t,y,0.,-.1,4.))
    reject('wrong_crossing_shape',lambda:crossing_brackets(t,y[:-1],0.,0.,4.))
    reject('wrong_segment_shape',lambda:below_segments(t,y[:-1],.4,1.))
    reject('unadmitted_end_truncation',lambda:admitted_window(np.array([0.,STOP-1e-10]),START+255*UI,START+256*UI))
    reject('nonfinite_ui_context',lambda:bit_context(float('nan')))
    def inventory_fault(label,mutation):
        changed=copy.deepcopy(contract);mutation(changed);assert changed!=contract
        reject(label,lambda:probe_inventory(changed))
    for label,vector in [('missing_stage_probe','v(op)'),('missing_public_clock_probe','v(sp16_0p)'),
                         ('missing_current_probe','@q.x.qnpn13g2[ic]'),('missing_terminal_probe','v(e)')]:
        inventory_fault(label,lambda c,vector=vector:c['vectors'].remove(vector))
    inventory_fault('stale_mux_probe',lambda c:c['vectors'].append('v(mp)'))
    inventory_fault('missing_interface_key',lambda c:c['interface_probes'].pop('ap'))
    inventory_fault('duplicate_clock_name',lambda c:c['tree_plan']['clocks'][0].__setitem__('name','s'))
    inventory_fault('duplicate_probe_vector',lambda c:c['vectors'].append(c['vectors'][0]))
    reject('changed_original_review',lambda:replay_receipt(report,dict(report,failed_hbts=[])))
    reject('accepted_original_review',lambda:replay_receipt(dict(report,all_engineering_gates_passed=True),dict(report,all_engineering_gates_passed=True)))
    assert len(faults)==30
    return dict(status='PASS_SYNTHETIC_SAME_ROW_MATH_CONTROLS_ONLY',negative_controls=faults,
                native_capture_read=False,original_failure_replayed=False,readback_authorized=False)
if __name__=='__main__':
    import json
    print(json.dumps(main(),indent=2,allow_nan=False))
