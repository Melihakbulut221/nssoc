#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reproduce rejected CDR HBT bounds and locate their real physical owners."""
import argparse,json,os,re
from pathlib import Path
import numpy as np
import cloud_tx_stream as stream
import cloud_cdr_pd_vi as timing
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
PINS={
 'nominal_early':('8b4f7e85437ec1b3b81f3a39df31306d4f58a5195874278367182d09c631c2e5','ec647572dd8006b187312403142435114c8437ca2ff0e06a3212722326b33eff'),
 'nominal_late':('1bcd53b9e19d09840461fc3eef2d181d240830dc18bf2df6ffc9e43afeddd688','0050b50a210142bc96627b320f1a7b6e7cf8f7457c122675bab35118ba9b4364')}
def rect(text):
 q=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',text)));assert len(q)==4 and q[0]<=q[2]and q[1]<=q[3];return q
def owner(box,placements):
 hits=[n for n,p in placements.items()if box[0]>=p[0]-1e-8 and box[1]>=p[1]-1e-8 and box[2]<=p[2]+1e-8 and box[3]<=p[3]+1e-8]
 assert len(hits)==1,('Physical primitive owner is not unique',box,hits)
 return hits[0]
def measure(vc,vb,ve,ic,nx,active):
 assert nx>0 and len(vc)==len(vb)==len(ve)==len(ic)==len(active) and np.any(active)
 assert all(np.isfinite(v).all()for v in (vc,vb,ve,ic))
 return dict(minimum_active_vce_v=float((vc-ve)[active].min()),
   maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),
   maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),
   maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/nx))
def controls():
 a=np.array([False,True,True]);vc=np.array([0.,1.2,1.3]);ve=np.array([0.,.8,.8]);vb=np.array([0.,1.5,1.5]);ic=np.array([0.,.002,.004])
 x=measure(vc,vb,ve,ic,4,a)
 assert abs(x['minimum_active_vce_v']-.4)<1e-15 and x['maximum_alltime_abs_ic_per_emitter_a']==.001
 assert measure(ve,vb,vc,ic,4,a)!=x
 for boxes in ({'one':[0,0,2,2],'two':[0,0,2,2]},{}):
  try:owner([.1,.1,.2,.2],boxes)
  except AssertionError:pass
  else:raise AssertionError('Ambiguous/missing macro owner accepted')
 assert owner([.1,.1,.2,.2],{'one':[0,0,2,2]})=='one'
 return dict(original_active_window_and_per_emitter_current_checked=True,swapped_collectors_emitters_detected=True,missing_and_ambiguous_physical_owner_rejected=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=tuple(PINS),required=True);args=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 out=ROOT/('cloud-cdr-source-access-headroom-'+args.case);out.mkdir(exist_ok=False)
 inputs=ROOT/('cdr-headroom-inputs-'+args.case);inputs.mkdir(exist_ok=False);reports.OUT=inputs
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,full_phy_accepted=False,no_new_simulation=True)
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['controls']=controls()
  pin=json.loads((ROOT/('docs/evidence/cdr-source-access-v14-fullwave-'+args.case+'-20261019.json')).read_text())
  sh,ph=PINS[args.case];assert pin['run']==39302582087 and pin['summary_sha256']==sh and pin['parts_sha256']==ph
  prior,proof=reports.restore_report('cdr-source-access-v14-mim-streamed-'+args.case,pin['run'],sh,ph,inputs/'wave',['native/wave.raw','composed/composition.json'])
  assert prior==pin['report'] and prior['status']=='REJECTED_WHOLE_MIM_PD484_LOADED'
  assert prior['case']==args.case and prior['source_head']=='4a459a18aa8333e83154302926829013a7d5d1ca'
  assert prior['returncode']==0 and not prior['diagnostics'] and prior['sources_unchanged']
  cp=json.loads((ROOT/'docs/evidence/cdr-source-access-v14-mim-parent-capture-pass-20261019.json').read_text())
  assert cp['run']==39300720018 and cp['summary_sha256']=='9f7a83ecb49a63feb198f9b3276ec9bc11eb0c1e2c35081fd2d4427ed19ee06e'
  names=['source/wire/device-locations01.json','source/parent/layout/result.json']
  captured,cproof=reports.restore_report('cdr-source-access-v14-mim-parent-rc',cp['run'],cp['summary_sha256'],cp['parts_sha256'],inputs/'geometry',names)
  assert captured==cp['report']and captured['sources_unchanged']
  contract=json.loads((inputs/'wave/composed/composition.json').read_text())
  locations=json.loads((inputs/'geometry/source/wire/device-locations01.json').read_text())
  layout=json.loads((inputs/'geometry/source/parent/layout/result.json').read_text())
  devices={d['native_id']:d for d in locations['devices']};assert len(devices)==484
  records={d['native_id']:d for d in contract['device_records']};assert devices.keys()==records.keys()
  placements={n:rect(p['bbox_um'])for n,p in layout['placements'].items()};assert len(placements)==16
  frozen={str(q):sha(q)for q in [Path(__file__),*[q for q in inputs.rglob('*')if q.is_file()]]}
  t,d,capture=stream.read_streamed_wave(inputs/'wave/native/wave.raw',prior['vectors'],timing.STOP,timing.STEP)
  assert capture==prior['raw_capture']
  active=t>=timing.START;active_indices=np.flatnonzero(active)
  def v(node):return np.zeros(len(t))if node=='0'else d['v('+node+')']
  measured={};details={}
  assert len(prior['devices'])==116
  for name,dev in prior['devices'].items():
   vc,vb,ve,_=map(v,dev['nodes']);ic=d['@q.'+name+'.qnpn13g2[ic]'];c=measure(vc,vb,ve,ic,dev['nx'],active);measured[name]=c
   assert c==prior['device_checks'][name],('Original device result did not reproduce',name)
   native=dev['native_id'];geo=devices[native];card=records[native]
   assert geo['model'].lower()==card['model']=='npn13g2' and 'xpd.'+card['instance'].lower()==name
   assert card['parameters']==dev['parameters']
   box=rect(geo['pcell']['bbox']);tag=owner(box,placements)
   i=int(active_indices[np.argmin((vc-ve)[active])]);violating=np.flatnonzero(active&((vc-ve)<.4))
   details[name]=dict(native_id=native,macro=tag,macro_kind=layout['placements'][tag]['kind'],primitive_bbox_um=box,
    primitive_geometry=geo,model_record=card,original_check=c,active_vce_violation_samples=len(violating),
    first_vce_violation_s=float(t[violating[0]])if len(violating)else None,
    last_vce_violation_s=float(t[violating[-1]])if len(violating)else None,
    worst_vce_sample=dict(index=i,time_s=float(t[i]),vc_v=float(vc[i]),vb_v=float(vb[i]),ve_v=float(ve[i]),
      vce_v=float(vc[i]-ve[i]),vbe_v=float(vb[i]-ve[i]),ic_a=float(ic[i]),ic_per_emitter_a=float(ic[i]/dev['nx']),
      avdd_v=float(v('avdd')[i])))
  assert measured==prior['device_checks']
  failed={n:x for n,x in details.items()if x['original_check']['minimum_active_vce_v']<.4}
  assert len(failed)==(6 if args.case=='nominal_early'else 2)
  assert all(sha(Path(n))==h for n,h in frozen.items())
  r.update(status='COMPLETE_ORIGINAL_REJECTED_HBT_CHECKS_AND_NATIVE_MACRO_MAPPING_NOT_ACCEPTANCE',
   waveform_source=proof,capture_source=cproof,source_unchanged=True,protected_inputs=frozen,
   all116original_hbt_checks_reproduced=True,all_hbt_checks=measured,failed_hbts=failed,
   worst16_hbts=dict(sorted(details.items(),key=lambda kv:kv[1]['original_check']['minimum_active_vce_v'])[:16]),
   scope='Original full native waveform only; no interpolation, stimulus change or gate relaxation. Exact C/B/E samples and geometry ownership diagnose existing rejection; they do not prove a causal fix, recovered-clock operation, PVT, qualified PEX or fullPHY acceptance.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:save();print(json.dumps({k:r[k]for k in ('status','case','accepted')}),flush=True)
if __name__=='__main__':main()
