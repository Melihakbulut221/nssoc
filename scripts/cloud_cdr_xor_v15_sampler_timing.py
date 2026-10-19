#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Diagnose real sampler data/clock terminal timing from rejected full CDR waves."""
import argparse,hashlib,json,os
from collections import defaultdict
from pathlib import Path
import numpy as np
import cloud_tx_stream as stream
import cloud_cdr_pd_vi as timing
import compare_cloud_routed_endpoints as reports
from cloud_cdr_source_access_headroom import rect,owner,measure,controls
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
PINS={
 'nominal_early':('59dbb9e3c2f5efa3d2703820c3e5c2885dd1559ad62ef284a47c1aba4e36cfc8','81a915eb06d6411e11dd2937001d225c5c280876653823924334493dd8ca9a7d'),
 'nominal_late':('3a442c0d2351bb238670389eb52ae4c5e7d2b7dc5f8e569427835bfd9c21825c','5d269e64c2a05518c31d1968486643cd99f1e61969f631d062ff903d2921e5e7')}
def crossing(t,delta,up):
 a,b=delta[:-1],delta[1:];ids=np.flatnonzero((a<0)&(b>=0)if up else(a>0)&(b<=0))
 assert np.all(b[ids]!=a[ids])
 return t[ids]+(-a[ids])*(t[ids+1]-t[ids])/(b[ids]-a[ids])
def nearest_edges(a,b):
 assert len(a)and len(b)
 out=[]
 for x in a:
  i=int(np.searchsorted(b,x));candidates=[j for j in (i-1,i)if 0<=j<len(b)]
  j=min(candidates,key=lambda j:abs(float(b[j]-x)));out.append(float(x-b[j]))
 return dict(count=len(out),minimum_s=min(out),maximum_s=max(out),median_s=float(np.median(out)),
  scope='Nearest observed reference edge only; no ordinal-lock or causal-delay acceptance',values_s=out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=tuple(PINS),required=True);args=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 out=ROOT/('cloud-cdr-xor-v15-sampler-timing-'+args.case);out.mkdir(exist_ok=False)
 inputs=ROOT/('cdr-xor-v15-sampler-inputs-'+args.case);inputs.mkdir(exist_ok=False);reports.OUT=inputs
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,full_phy_accepted=False,no_new_simulation=True)
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['controls']=controls()
  tx=np.array([0.,1.,2.,3.]);dx=np.array([-1.,1.,-1.,1.])
  assert list(crossing(tx,dx,True))==[.5,2.5]and list(crossing(tx,dx,False))==[1.5]
  pin=json.loads((ROOT/('docs/evidence/cdr-xor-collector-v15-fullwave-'+args.case+'-20261019.json')).read_text())
  sh,ph=PINS[args.case];assert pin['run']==39320016317 and pin['summary_sha256']==sh and pin['parts_sha256']==ph
  prior,proof=reports.restore_report('cdr-xor-collector-v15-mim-streamed-'+args.case,pin['run'],sh,ph,inputs/'wave',['native/wave.raw','composed/composition.json','planes/native-planes.json'])
  assert prior==pin['report']and prior['status']=='REJECTED_WHOLE_MIM_PD484_LOADED'
  assert prior['case']==args.case and prior['source_head']=='cb5959ee34233dd5c1c99b767bc53e587d4c8186'
  assert prior['returncode']==0 and not prior['diagnostics']and prior['sources_unchanged']and prior['devices_passed']
  cp=json.loads((ROOT/'docs/evidence/cdr-xor-collector-v15-mim-parent-capture-pass-20261019.json').read_text())
  assert cp['run']==39318436586 and cp['summary_sha256']=='4c73ec0f23af85bc5d9dcae34c49358bd9dd01417ee6b98e6072f27170fa49e5'
  names=['source/wire/device-locations01.json','source/parent/layout/result.json']
  captured,cproof=reports.restore_report('cdr-xor-collector-v15-mim-parent-rc',cp['run'],cp['summary_sha256'],cp['parts_sha256'],inputs/'geometry',names)
  assert captured==cp['report']and captured['sources_unchanged']
  contract=json.loads((inputs/'wave/composed/composition.json').read_text())
  planes=json.loads((inputs/'wave/planes/native-planes.json').read_text())
  locations=json.loads((inputs/'geometry/source/wire/device-locations01.json').read_text())
  layout=json.loads((inputs/'geometry/source/parent/layout/result.json').read_text())
  devices={d['native_id']:d for d in locations['devices']};records={d['native_id']:d for d in contract['device_records']}
  assert len(devices)==484 and devices.keys()==records.keys()
  placements={n:rect(p['bbox_um'])for n,p in layout['placements'].items()};assert len(placements)==16
  frozen={str(q):sha(q)for q in [Path(__file__),Path(stream.__file__),Path(timing.__file__),ROOT/'scripts/cloud_cdr_source_access_headroom.py',*[q for q in inputs.rglob('*')if q.is_file()]]}
  t,w,capture=stream.read_streamed_wave(inputs/'wave/native/wave.raw',prior['vectors'],timing.STOP,timing.STEP)
  assert capture==prior['raw_capture'];active=t>=timing.START
  aliases=prior['binding']['aliases']
  def v(n):
   n=aliases.get(n,n);return np.zeros(len(t))if n=='0'else w['v('+n+')']
  owned={};checked={}
  for name,dev in prior['devices'].items():
   vc,vb,ve,_=map(v,dev['nodes']);ic=w['@q.'+name+'.qnpn13g2[ic]']
   checked[name]=measure(vc,vb,ve,ic,dev['nx'],active);assert checked[name]==prior['device_checks'][name]
   d=devices[dev['native_id']];card=records[dev['native_id']]
   assert d['model'].lower()==card['model']=='npn13g2'and 'xpd.'+card['instance'].lower()==name
   assert card['parameters']==dev['parameters']
   owned[name]=owner(rect(d['pcell']['bbox']),placements)
  assert len(checked)==116 and min(x['minimum_active_vce_v']for x in checked.values())>=.4
  logical={}
  for a in planes['anchors']:
   value=(a['native_cluster'],a['native_name']);assert logical.setdefault(a['logical_net'],value)==value
  assert len(logical)==51
  bits=prior['source_bits'];assert len(bits)==256 and hashlib.sha256(bytes(bits)).hexdigest()==prior['source_bits_sha256']
  indices=range(1,256);current=[bits[i]for i in indices];previous=[bits[i-1]for i in indices]
  edge_bits=current if prior['data_offset_s']<0 else previous
  expected=dict(a=current,b=edge_bits,c=previous,d=edge_bits);assert expected==prior['expected_samples']
  UI=timing.UI;rising=[timing.START+(i+.5)*UI for i in indices];falling=[timing.START+i*UI for i in indices]
  def rebuild(tag):
   delta=v('xpd.'+tag+'qp')-v('xpd.'+tag+'qn');signed=[];delays=[];events=[]
   for k,(bit,edge)in enumerate(zip(expected[tag],falling if tag=='b'else rising,strict=True)):
    sign=2*bit-1
    for phase in (.3,.6,.9):
     when=edge+phase*UI;margin=float(np.interp(when,t,delta))*sign;signed.append(margin)
     events.append(dict(bit_index=k+1,expected=bit,phase_ui=phase,time_s=when,signed_margin_v=margin,
      expected_changed=None if k==0 else bit!=expected[tag][k-1]))
    ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
    delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+timing.STEP))
   result=dict(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),
    below_100mv_samples=sum(x<.1 for x in signed),maximum_clock_to_valid_s=max(delays),clock_to_valid_by_bit_s=delays,
    passed=min(signed)>=.1 and max(delays)<=.3*UI)
   assert result==prior['sampler_checks'][tag],('Original sampler result does not reproduce',tag)
   return events
  reference_delta=v('cp')-v('cn')
  refs={direction:crossing(t,reference_delta,direction=='rising')for direction in ('rising','falling')}
  refs={k:x[x>=timing.START]for k,x in refs.items()}
  allpairs=[('cp','cn'),('s0p','s0n'),('s1p','s1n'),('adp','adn'),('cdp','cdn'),('dp','dn')]
  stages={}
  for tag in 'abcd':
   point=prior['binding']['sampler_points'][tag+'qp']
   matches=[name for name,dev in prior['devices'].items()if dev['nodes'][0]==point]
   assert len(matches)==1;macro=owned[matches[0]]
   members={n:d for n,d in prior['devices'].items()if owned[n]==macro};assert members
   terms={}
   for name,dev in members.items():
    card=records[dev['native_id']]
    terms[name]={x['terminal']:x for x in card['terminals']}
   pairs=[]
   for lp,ln in allpairs:
    if lp not in logical or ln not in logical:continue
    positive=[n for n in members if terms[n]['B']['native_cluster']==logical[lp][0]]
    negative=[n for n in members if terms[n]['B']['native_cluster']==logical[ln][0]]
    for pn in positive:
     ns=[nn for nn in negative if terms[nn]['E']['native_cluster']==terms[pn]['E']['native_cluster']]
     assert len(ns)<=1,('Ambiguous shared-emitter differential pair',tag,lp,pn,ns)
     if not ns:continue
     nn=ns[0];pv=v(members[pn]['nodes'][1]);nv=v(members[nn]['nodes'][1]);delta=pv-nv
     edges={direction:crossing(t,delta,direction=='rising')for direction in ('rising','falling')}
     edges={k:x[x>=timing.START]for k,x in edges.items()}
     pairs.append(dict(logical_pair=[lp,ln],positive_device=pn,negative_device=nn,
      native_shared_emitter=terms[pn]['E']['native_cluster'],positive_base_node=members[pn]['nodes'][1],negative_base_node=members[nn]['nodes'][1],
      differential_range_v=[float(delta[active].min()),float(delta[active].max())],
      commonmode_range_v=[float(((pv+nv)/2)[active].min()),float(((pv+nv)/2)[active].max())],
      edges={k:list(map(float,x))for k,x in edges.items()},
      nearest_external_edges={dk:{rk:nearest_edges(ds,rs)for rk,rs in refs.items()if len(rs)}for dk,ds in edges.items()if len(ds)}))
   assert any(p['logical_pair'][0]in ('cp','s0p','s1p')for p in pairs),('No real sampler clock pair bound',tag,macro)
   events=rebuild(tag);summaries=[]
   for phase in (.3,.6,.9):
    part=[e for e in events if e['phase_ui']==phase]
    summaries.append(dict(phase_ui=phase,samples=len(part),wrong=sum(e['signed_margin_v']<=0 for e in part),
     below_100mv=sum(e['signed_margin_v']<.1 for e in part),minimum_signed_margin_v=min(e['signed_margin_v']for e in part),
     wrong_on_changed_expected=sum(e['signed_margin_v']<=0 and e['expected_changed']is True for e in part),
     wrong_on_unchanged_expected=sum(e['signed_margin_v']<=0 and e['expected_changed']is False for e in part)))
   snapshots=[]
   for event in sorted(events,key=lambda e:e['signed_margin_v'])[:8]:
    i=int(np.argmin(abs(t-event['time_s'])));state={}
    for name,dev in members.items():
     vc,vb,ve,_=map(lambda n:float(v(n)[i]),dev['nodes'])
     state[name]=dict(vc_v=vc,vb_v=vb,ve_v=ve,vce_v=vc-ve,vbe_v=vb-ve,ic_a=float(w['@q.'+name+'.qnpn13g2[ic]'][i]),native_terminals=terms[name])
    snapshots.append(dict(event=event,native_sample_index=i,native_sample_time_s=float(t[i]),
     source_data_difference_v=float(v('dp')[i]-v('dn')[i]),source_clock_difference_v=float(v('cp')[i]-v('cn')[i]),
     sampler_difference_v=float(v('xpd.'+tag+'qp')[i]-v('xpd.'+tag+'qn')[i]),devices=state))
   stages[tag]=dict(physical_macro=macro,physical_kind=layout['placements'][macro]['kind'],hbt_count=len(members),
     original_sampler_check=prior['sampler_checks'][tag],phase_breakdown=summaries,real_shared_emitter_base_pairs=pairs,worst_native_snapshots=snapshots)
  assert all(sha(Path(n))==h for n,h in frozen.items())
  r.update(status='COMPLETE_REJECTED_CDR_SAMPLER_TIMING_REPLAY_AND_NATIVE_INPUT_CLOCK_PAIR_DIAGNOSIS_NOT_ACCEPTANCE',
   waveform_source=proof,capture_source=cproof,source_unchanged=True,protected_inputs=frozen,
   all116original_hbt_checks_reproduced=True,all4original_sampler_checks_reproduced=True,
   original_rejection_preserved=True,original_devices_passed=prior['devices_passed'],
   original_phase_passed=prior['phase_passed'],original_vi_passed=prior['vi']['passed'],stages=stages,
   scope='Same complete native waveform and original sample/window/gates. Physical sampler ownership and common-emitter HBT base pairs are measured, not ideal data regeneration. Edge interpolation only locates existing crossings; no clock realignment or new acceptance claim.')
 except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
 finally:save();print(json.dumps({k:r[k]for k in ('status','case','accepted')}),flush=True)
if __name__=='__main__':main()
