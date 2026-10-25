#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Small synthetic math/identity controls; not native capture acceptance."""
import copy
import numpy as np
from tx_normal_saved_capture_diagnosis import bracket,hbt_point,native_pairs,crossing_brackets,below_segments,catalog,admitted_window,STOP,START,UI

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
    assert seg[0]['entry_bracket_rows']==[1,2] and seg[0]['exit_bracket_rows']==[3,4]
    end=np.nextafter(STOP,0.); window=admitted_window(np.array([0.,end]),START+255*UI,START+256*UI)
    assert window['admitted_endpoint_clipped'] and window['native_scan_bounds_s'][1]==end
    assert window['requested_UI_bounds_s'][1]==START+256*UI
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
    assert len(faults)==19
    return dict(status='PASS_SYNTHETIC_SAME_ROW_MATH_CONTROLS_ONLY',negative_controls=faults,
                native_capture_read=False,original_failure_replayed=False,readback_authorized=False)
if __name__=='__main__':
    import json
    print(json.dumps(main(),indent=2,allow_nan=False))
