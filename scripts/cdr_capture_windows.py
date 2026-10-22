#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe existing native steering-current crossings without realigning data."""
from collections import Counter
import numpy as np
def observe(t,edges,bits,off,signals,ui):
 t=np.asarray(t);off=np.asarray(off)
 assert len(t)>1 and np.all(np.diff(t)>0) and np.all(np.diff(off)>0)
 assert len(edges)==len(bits) and ui>0
 assert set(signals)=={'master_input','master_output','slave_input','slave_output'}
 assert all(len(v)==len(t) for v in signals.values())
 rows=[];counts=Counter();offsets=[]
 for index,(edge,bit)in enumerate(zip(edges,bits,strict=True),1):
  assert bit in (0,1)
  hits=np.flatnonzero(abs(off-edge)<=.45*ui)
  row=dict(bit_index=index,expected=bit,original_edge_s=float(edge),matching_transitions=len(hits))
  if len(hits)!=1:
   counts['missing_transition'if not len(hits)else'ambiguous_transition']+=1
   rows.append(row);continue
  at=float(off[hits[0]]);deadline=float(edge+.3*ui)
  assert t[0]<=at<=t[-1] and t[0]<=deadline<=t[-1],'No extrapolation beyond actual capture'
  sign=2*bit-1
  sampled={k:float(np.interp(at,t,v))*sign for k,v in signals.items()}
  final={k:float(np.interp(deadline,t,v))*sign for k,v in signals.items()}
  row.update(steering_transition_s=at,transition_minus_original_edge_s=at-edge,
   signed_at_transition_v=sampled,signed_at_original_deadline_v=final)
  offsets.append(at-edge);counts['unique_transition']+=1
  counts['master_input_wrong_sign_at_transition']+=sampled['master_input']<=0
  counts['master_input_below_diagnostic_100mv_at_transition']+=sampled['master_input']<.1
  counts['master_output_below_100mv_at_original_deadline']+=final['master_output']<.1
  counts['slave_output_below_original_100mv_gate_at_deadline']+=final['slave_output']<.1
  label=str((sampled['master_input']<.1,final['master_output']<.1,final['slave_output']<.1))
  counts['weak_input_master_late_slave_late_'+label]+=1
  rows.append(row)
 return dict(original_bits=len(bits),counts=dict(counts),rows=rows,
  transition_offset_s=None if not offsets else dict(minimum=float(min(offsets)),maximum=float(max(offsets)),median=float(np.median(offsets))),
  scope='Exactly one observed master track-minus-hold falling crossing within0.45UI of the unchanged expected edge; missing/ambiguous crossings are reported, never replaced. This is a steering proxy, not a proved latch aperture or causal attribution. Internal100mV markers add no acceptance gate. Original output deadline, expected bits, raw rows and clock phase are unchanged.')
def controls():
 t=np.linspace(0,4,401);edges=[1.,2.,3.];off=np.array([1.08,2.08,3.08])
 signals={k:np.full(len(t),.2)for k in ['master_input','master_output','slave_input','slave_output']}
 good=observe(t,edges,[1,1,1],off,signals,1.)
 assert good['counts']['unique_transition']==3
 assert abs(good['transition_offset_s']['median']-.08)<1e-12
 assert good['counts']['master_input_wrong_sign_at_transition']==0
 wrong=observe(t,edges,[1,0,1],off,signals,1.)
 assert wrong['counts']['master_input_wrong_sign_at_transition']==1
 assert wrong['rows'][1]['signed_at_transition_v']['master_input']==-.2
 ambiguous=observe(t,edges,[1,1,1],np.array([1.08,2.08,2.09,3.08]),signals,1.)
 assert ambiguous['counts']['ambiguous_transition']==1 and ambiguous['counts']['unique_transition']==2
 missing=observe(t,edges,[1,1,1],np.array([1.08,3.08]),signals,1.)
 assert missing['counts']['missing_transition']==1 and missing['counts']['unique_transition']==2
 try:observe(t,[3.95],[1],np.array([3.98]),signals,1.)
 except AssertionError:pass
 else:raise AssertionError('Capture extrapolation accepted')
 return dict(known_offset_reproduced=True,expected_bit_polarity_preserved=True,ambiguous_not_matched=True,missing_not_matched=True,extrapolation_rejected=True,no_native_acceptance_claim=True)
if __name__=='__main__':print(controls())
