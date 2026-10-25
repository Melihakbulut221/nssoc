#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure phase/control/actual wire-charge response on the original rejected capture."""
import hashlib,json,os,traceback
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import pll845_vctrl_wire_observation as wire
from review_pcie_pll_acquisition_v1 import independent_analysis
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll845-loop-response'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def integrate(t,y):return float(np.trapezoid(y,t))
def window(t,a,b):
 lo,hi=np.searchsorted(t,[a,b])
 grid=np.concatenate(([a],t[lo:hi],[b]))
 assert np.all(np.diff(grid)>0)
 return grid
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],acquisition_accepted=False,full_phy_accepted=False,qualified_pex=False,native_activation_performed=False,
  scope='Exact cached columns from original full1us failed native capture. Descriptive feedback-cycle charge and control response; not a static Kvco experiment or fitted acceptance.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  method=json.loads((ROOT/'scripts/pll845-loop-response-methods.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in method.items())
  pin=json.loads((ROOT/'docs/evidence/pll845-complete-wire-current-results-20261023.json').read_text())
  assert pin['run']==39873653454 and pin['summary_sha256']=='4743066311755546af13f7c2b43111fc76f113697d08766ed037773efe535f6a'
  names=['original-vctrl-columns.npy','original-vctrl-column-names.json','wire-current-plan.json','original-reader-result.json','wire-current-observation.json']
  source,proof=reports.restore_report('pll845-vctrl-wire',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
  assert source['status']=='COMPLETE_MODELED_WIRE_CURRENT_DIAGNOSIS_ORIGINAL_ACQUISITION_STILL_REJECTED'
  assert source['full_capture']and source['exact_original_acquisition_and_cycle_results']
  prior=json.loads((OUT/'source/original-reader-result.json').read_text())
  assert prior['status']=='REJECTED_ORIGINAL_FULL845_ACQUISITION_GATES'and prior['full_capture']
  binding=json.loads((OUT/'source/wire-current-plan.json').read_text())
  observed=json.loads((OUT/'source/wire-current-observation.json').read_text())
  cols=json.loads((OUT/'source/original-vctrl-column-names.json').read_text())
  values=np.load(OUT/'source/original-vctrl-columns.npy',mmap_mode='r',allow_pickle=False)
  assert values.shape==(3201410,len(cols))and values.dtype==np.dtype('<f8')and cols==observed['selected_columns']
  h=hashlib.sha256()
  for lo in range(0,len(values),8192):
   block=values[lo:lo+8192];assert np.isfinite(block).all();h.update(block.tobytes())
  assert h.hexdigest()==observed['selected_row_major_sha256']and observed['exact_original_sample_bits']
  data={n:np.asarray(values[:,i])for i,n in enumerate(cols)}
  original=independent_analysis(data)
  assert original==prior['independent_acquisition']and not original['passed'],'Original acquisition gates or waveform identity changed'
  t=data['time'];edges=np.asarray(original['feedback_edges_s']);refs=np.asarray(original['reference_edges_s'])
  # Bind actual model devices, not assumed schematic names or pulse polarity.
  model,comp,inst,original_names,old=wire.inputs()
  rebound=wire.plan(model,comp,inst,original_names);assert rebound==binding
  devices={d['instance']:d for d in comp['device_records']}
  r['control_devices']={name:devices[name]for name in ['XD0187','XD0376','XD0567','XD0568','XD0574']}
  r['source']=proof;r['raw_sha256']=wire.RAW_SHA;r['original_acquisition_rejection_reproduced']=True
  r['waveform_scope']=dict(rows=len(t),native_samples_removed=0,selected_row_major_sha256=h.hexdigest(),
    original_raw_sha256=wire.RAW_SHA,edge_method='Original independent1.25V rising edges; no refitting or phase shift.',
    integration='Original adaptive samples with linearly interpolated cycle endpoints only; trapezoidal quadrature. Source samples unchanged.')
  volt={n:(np.zeros(len(t))if v is None else data[v])for n,v in binding['vector_map'].items()}
  currents={row['instance']+'.'+row['terminal']:sum((volt[q['positive']]-volt[q['negative']])/q['ohms']for q in row['outgoing_resistors'])for row in binding['terminals']}
  rows=[]
  for i,(a,b)in enumerate(zip(edges[:-1],edges[1:])):
   grid=window(t,a,b);dt=b-a
   vc=np.interp(grid,t,data['v(vctrl)']);up=np.interp(grid,t,data['v(up)']);dn=np.interp(grid,t,data['v(down)'])
   branch={name:integrate(grid,np.interp(grid,t,y))for name,y in currents.items()}
   rows.append(dict(ordinal=i,start_s=float(a),end_s=float(b),feedback_hz=float(1/dt),vctrl_start_v=float(vc[0]),vctrl_end_v=float(vc[-1]),
     vctrl_mean_v=integrate(grid,vc)/dt,vctrl_min_v=float(vc.min()),vctrl_max_v=float(vc.max()),
     phase_start_s=float(original['phase_s'][i]),reference_ordinal=int(original['reference_ordinals'][i]),
     up_duty=integrate(grid,(up>1.25).astype(float))/dt,down_duty=integrate(grid,(dn>1.25).astype(float))/dt,
     branch_charge_c=branch,net_wire_charge_c=sum(branch.values())))
  r['cycles']=rows
  def correlation(a,b):
   assert len(a)==len(b)>3
   if np.std(a)==0 or np.std(b)==0:return None
   return float(np.corrcoef(a,b)[0,1])
  v=np.asarray([x['vctrl_mean_v']for x in rows]);f=np.asarray([x['feedback_hz']for x in rows])
  dv=np.asarray([x['vctrl_end_v']-x['vctrl_start_v']for x in rows]);q=np.asarray([x['branch_charge_c']['XD0187.D']+x['branch_charge_c']['XD0376.D']for x in rows])
  correlations=[]
  for lag in range(9):
   target=slice(lag,None);origin=slice(None,-lag)if lag else slice(None)
   correlations.append(dict(lag_feedback_cycles=lag,mean_vctrl_vs_later_frequency=correlation(v[origin],f[target]),
    pump_wire_charge_vs_later_vctrl_delta=correlation(q[origin],dv[target])))
  r['descriptive_correlations']=correlations
  states=[]
  for start,end in [(0.,1e-6),(8e-7,9e-7),(9e-7,1e-6)]:
   lo=int(np.searchsorted(t,start));hi=int(np.searchsorted(t,end,side='right'));tw=t[lo:hi];duration=tw[-1]-tw[0]
   up=data['v(up)'][lo:hi]>1.25;dn=data['v(down)'][lo:hi]>1.25
   record=dict(requested_interval_s=[start,end],actual_interval_s=[float(tw[0]),float(tw[-1])],states={})
   for u,d in [(False,False),(False,True),(True,False),(True,True)]:
    mask=(up==u)&(dn==d);seconds=integrate(tw,mask.astype(float))
    branch={n:integrate(tw,y[lo:hi]*mask)for n,y in currents.items()}
    record['states'][f'up{int(u)}_down{int(d)}']=dict(duration_s=seconds,duty=seconds/duration,branch_charge_c=branch,
      branch_mean_while_state_a={n:q/seconds if seconds else None for n,q in branch.items()})
   states.append(record)
  r['pulse_state_wire_charge']=states
  # Store compact exact-cycle numerical observations, not another waveform copy.
  (OUT/'cycles.json').write_text(json.dumps(rows,indent=2)+'\n')
  assert all(sha(OUT/'source'/n)==source['outputs'][n]for n in names)
  assert all(sha(ROOT/p)==h for p,h in method.items())
  r.update(status='COMPLETE_ORIGINAL_PLL_LOOP_RESPONSE_OBSERVATION_ACQUISITION_STILL_REJECTED',sources_unchanged=True,
    next_action='Use actual branch charges, device identities and cycle/control ordering to choose a physical filter/pump candidate. Correlations do not establish causal/static Kvco or qualify acquisition.')
 except BaseException as e:r.update(status='FAIL_LOOP_RESPONSE_OBSERVATION',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  # The exact original cache remains in its immutable release. Publish only new observations and source provenance.
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'and 'source'not in p.relative_to(OUT).parts};save()
if __name__=='__main__':main()
