#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Synthetic same-row and interval controls only; no capture acceptance."""
import copy
import numpy as np
from tx_phase_reset334_saved_diagnosis import bracket,crossing_rows,hbt_state,pair_state,window_events,HBT_FIELDS

def controls():
    t=np.array([0.,1.,2.,3.]);y=np.array([-1.,0.,1.,-1.])
    assert bracket(t,0.)['rows']==[0,0]and bracket(t,3.)['rows']==[3,3]
    assert bracket(t,1.25)['rows']==[1,2]
    edges=crossing_rows(t,y,0.)
    assert [(e['rows'],e['direction'])for e in edges]==[([1,2],'rising'),([2,3],'falling')]
    selected=window_events(edges,1.5,2.5,2.)
    assert [e['relative_to_prescribed_event_s']for e in selected]==[[-1.,0.],[0.,1.]]
    assert all('linear_estimate_s'not in e for e in edges)
    values={'v(c)':np.array([0.,1.3,1.1,1.2]),'v(b)':np.array([0.,1.1,1.,.9]),
      'v(e)':np.array([0.,.4,.8,.5]),'v(sub)':np.zeros(4),'@q.x.qnpn13g2[ic]':np.array([0.,.004,.006,.002])}
    spec=dict(nx=2,terminals=['c','b','e','sub'])
    row=hbt_state(values,'x',spec,2)
    assert row==[1.1,1.,.8,0.,1.1-.8,1.-.8,.006,.003]and len(row)==len(HBT_FIELDS)==8
    pair=pair_state(values,['c','b'],2);assert pair==[1.1,1.,1.1-1.,(1.1+1.)/2]
    bad=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,IndexError,ValueError):bad.append(name)
        else:raise AssertionError('Accepted '+name)
    reject('before_capture',lambda:bracket(t,-.1));reject('after_capture',lambda:bracket(t,3.1))
    reject('duplicate_time',lambda:bracket(np.array([0.,0.,1.]),.5))
    reject('reverse_time',lambda:bracket(t[::-1],1.))
    reject('nonfinite_time',lambda:bracket(np.array([0.,np.nan]),0.))
    reject('nonfinite_request',lambda:bracket(t,float('nan')))
    reject('nonfinite_crossing',lambda:crossing_rows(t,np.array([0.,1.,np.nan,1.]),0.))
    reject('wrong_crossing_shape',lambda:crossing_rows(t,y[:-1],0.))
    reject('nonfinite_threshold',lambda:crossing_rows(t,y,float('nan')))
    reject('bad_window',lambda:window_events(edges,2.,1.,0.))
    reject('bad_origin',lambda:window_events(edges,0.,1.,float('nan')))
    reject('missing_current',lambda:hbt_state({k:v for k,v in values.items()if not k.startswith('@')},'x',spec,2))
    reject('missing_body',lambda:hbt_state(values,'x',dict(spec,terminals=['c','b','e']),2))
    reject('wrong_Nx',lambda:hbt_state(values,'x',dict(spec,nx=3),2))
    reject('wrong_row',lambda:hbt_state(values,'x',spec,4))
    reject('same_pair_node',lambda:pair_state(values,['c','c'],2))
    assert len(bad)==16
    return dict(status='PASS_SYNTHETIC318_SAME_ROW_INTERVAL_CONTROLS_ONLY',rejected=bad,
        native_capture_read=False,original_failure_replayed=False,readback_authorized=False)
if __name__=='__main__':
    import json
    print(json.dumps(controls(),indent=2,allow_nan=False))
