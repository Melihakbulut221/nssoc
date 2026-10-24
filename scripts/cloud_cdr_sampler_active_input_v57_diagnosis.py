#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect full original shared-bias sampler waves without resimulation."""
import argparse,hashlib,json,os,traceback
from pathlib import Path
import numpy as np
import cloud_tx_stream as stream
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
PIN=ROOT/'docs/evidence/cdr-sampler-active-input-v57-results-20261024.json'
METHOD=ROOT/'scripts/cdr-sampler-active-input-v57-diagnosis-method.json'
def check():
 for p,h in json.loads(METHOD.read_text())['protected'].items():assert sha(ROOT/p)==h,p
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['nominal','hot_low','cold_high'],required=True);a=ap.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true';check()
 out=ROOT/('cloud-cdr-sampler-active-input-v57-diagnosis-'+a.case);out.mkdir();reports.OUT=out
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=a.case,full_phy_accepted=False,physical_accepted=False)
 def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'
')
 save()
 try:
  pin=json.loads(PIN.read_text());p=pin['cases'][a.case]
  old,proof=reports.restore_report('cdr-sampler-active-input-v57-'+a.case,pin['run'],p['summary_sha256'],p['parts_sha256'],out/'source',['native/wave.raw','native/bench.cir'])
  assert old==p['report']and old['sources_unchanged']and old['data_passed']and not old['devices_passed']
  t,w,capture=stream.read_streamed_wave(out/'source/native/wave.raw',old['vectors'],34.25e-9,.3125e-12)
  assert capture==old['raw_capture'];active=t>=2e-9
  def v(n):return np.zeros(len(t))if n=='0'else w['v('+n+')']
  def stats(values):
   return dict(minimum=float(values.min()),minimum_time_s=float(t[np.argmin(values)]),maximum=float(values.max()),maximum_time_s=float(t[np.argmax(values)]),active_minimum=float(values[active].min()),active_maximum=float(values[active].max()))
  def bad_times(mask):
   ids=np.flatnonzero(mask);ids_active=ids[t[ids]>=2e-9]
   return dict(alltime_samples=len(ids),active_samples=len(ids_active),first_s=float(t[ids[0]])if len(ids)else None,last_s=float(t[ids[-1]])if len(ids)else None)
  checks={}
  for name,d in old['devices'].items():
   vc,vb,ve,_=map(v,d['nodes']);ic=w['@q.'+name+'.qnpn13g2[ic]']/d['nx']
   checks[name]=dict(vce_v=stats(vc-ve),vbe_v=stats(vb-ve),ic_per_emitter_a=stats(ic),
     low_vce=bad_times(active&((vc-ve)<.4)),high_abs_vce=bad_times(abs(vc-ve)>1.6),
     high_abs_vbe=bad_times(abs(vb-ve)>1),high_abs_ic_per_emitter=bad_times(abs(ic)>=.003))
   reported=old['device_checks'][name]
   for observed,expected in [(np.min((vc-ve)[active]),reported['minimum_active_vce_v']),(np.max(abs(vc-ve)),reported['maximum_alltime_abs_vce_v']),(np.max(abs(vb-ve)),reported['maximum_alltime_abs_vbe_v']),(np.max(abs(ic)),reported['maximum_alltime_abs_ic_per_emitter_a'])]:
    assert abs(float(observed)-expected)<1e-14
  stages={}
  for label,positive,negative in [('input','dp','dn'),('gain','xsamp.lp','xsamp.ln'),('master','xsamp.mp','xsamp.mn'),('output','qp','qn')]:
   stages[label]=dict(differential_v=stats(v(positive)-v(negative)),commonmode_v=stats((v(positive)+v(negative))/2))
  tails={}
  for label,names in [('master',['xsamp.xm.xt'+str(i)for i in range(4)]),('slave',['xsamp.xs.xt'+str(i)for i in range(4)]),('gain',['xsamp.xgt'+str(i)for i in range(2)])]:
   tails[label]=stats(sum(w['@n.'+name+'.nsg13_lv_nmos[ids]']for name in names))
  result.update(source=proof,raw_capture=capture,device_checks=checks,stages=stages,tail_currents_a=tails,
    reference_voltage_v=stats(v('iref')),reference_current_a=stats(w['@n.xsamp.xref.nsg13_lv_nmos[ids]']),
    original_gates_reproduced=True,no_simulation_or_wave_modification=True)
  check();result.update(status='PASS_FULL_SAVED_SHARED_BIAS_DIAGNOSIS_NOT_A_REPAIR',sources_unchanged=True)
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
