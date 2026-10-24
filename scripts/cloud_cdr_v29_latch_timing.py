#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Diagnose real sampler data/clock terminal timing from rejected full CDR waves."""
import argparse,copy,hashlib,json,os
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import cloud_tx_stream as stream
import cloud_cdr_pd_vi as timing
import compare_cloud_routed_endpoints as reports
from cloud_cdr_source_access_headroom import rect,owner,measure,controls
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
PINS={"nominal_early":["f9418fb4bf9ac32a398aa51691536f95dd2d5fbf03894c6277d3539dbbba798a","3398065de43d7faa4dd2296d7bcdc09bcbca8c27f7d9ff7edd4c1ead8a54b5f1"],"nominal_late":["20f62cab499e59d3ad6d6a3b55e4c326756531de7dc92440b2128e923661df81","6801521d5ec03baa31076285012f5cec57e05553d19c9286829bd8c979df13d6"]}
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
def physical_pairs(positive,negative,terms):
 assert len(positive)==len(set(positive))and len(negative)==len(set(negative))and not set(positive)&set(negative)
 # Every physical positive/negative base combination on the same actual
 # emitter bank is retained. No arbitrary representative or averaged base.
 return [(p,n)for p in positive for n in negative if terms[p]['E']['native_cluster']==terms[n]['E']['native_cluster']]
def parallel_controls():
 terms={name:{'E':{'native_cluster':7}}for name in ('p0','p1','n0','n1')}
 expected=[('p0','n0'),('p0','n1'),('p1','n0'),('p1','n1')]
 assert physical_pairs(['p0','p1'],['n0','n1'],terms)==expected
 terms['n1']['E']['native_cluster']=8
 assert physical_pairs(['p0','p1'],['n0','n1'],terms)==[('p0','n0'),('p1','n0')]
 try:physical_pairs(['p0','p0'],['n0'],terms)
 except AssertionError:pass
 else:raise AssertionError('Duplicate physical device accepted')
 return dict(two_by_two_bank_keeps_all_four_combinations=True,different_emitter_not_paired=True,duplicate_device_rejected=True)
def latch_graph(members,terms,qp_node,qn_node):
 assert len(members)==16 and set(members)==set(terms)
 by_emitter=defaultdict(list)
 for name in members:by_emitter[terms[name]['E']['native_cluster']].append(name)
 assert sorted(map(len,by_emitter.values()))==[2,2,2,2,4,4]
 banks=defaultdict(list)
 for emitter,names in by_emitter.items():
  if len(names)!=2:continue
  output=tuple(sorted(terms[n]['C']['native_cluster']for n in names))
  assert len(set(output))==2
  banks[output].append(dict(emitter=emitter,members=names))
 assert len(banks)==2 and all(len(v)==2 for v in banks.values())
 classified={}
 for output,groups in banks.items():
  holds=[g for g in groups if {terms[n]['B']['native_cluster']for n in g['members']}==set(output)]
  assert len(holds)==1,'Cross-coupled hold pair is not unique'
  hold=holds[0];data=next(g for g in groups if g is not hold)
  assert all(terms[n]['B']['native_cluster']!=terms[n]['C']['native_cluster']for n in hold['members'])
  classified[output]=dict(data=data,hold=hold)
 def collector(node):
  names=[n for n,d in members.items()if d['nodes'][0]==node];assert len(names)==1
  return terms[names[0]]['C']['native_cluster']
 qplus,qminus=collector(qp_node),collector(qn_node);assert qplus!=qminus
 slave_key=tuple(sorted([qplus,qminus]));assert slave_key in classified
 slave_data=classified[slave_key]['data']['members']
 sp=next(n for n in slave_data if terms[n]['C']['native_cluster']==qminus)
 sn=next(n for n in slave_data if terms[n]['C']['native_cluster']==qplus)
 mp,mn=terms[sp]['B']['native_cluster'],terms[sn]['B']['native_cluster']
 master_key=tuple(sorted([mp,mn]));assert master_key in classified and master_key!=slave_key
 result={}
 for tag,key,pos,neg in [('master',master_key,mp,mn),('slave',slave_key,qplus,qminus)]:
  bank=classified[key];dp=next(n for n in bank['data']['members']if terms[n]['C']['native_cluster']==neg)
  dn=next(n for n in bank['data']['members']if terms[n]['C']['native_cluster']==pos)
  track=[n for n in members if terms[n]['C']['native_cluster']==bank['data']['emitter']]
  hold=[n for n in members if terms[n]['C']['native_cluster']==bank['hold']['emitter']]
  assert len(track)==len(hold)==2 and not set(track)&set(hold)
  assert len({terms[n]['E']['native_cluster']for n in track+hold})==1
  assert len({terms[n]['B']['native_cluster']for n in track})==len({terms[n]['B']['native_cluster']for n in hold})==1
  assert terms[track[0]]['B']['native_cluster']!=terms[hold[0]]['B']['native_cluster']
  result[tag]=dict(data_positive=dp,data_negative=dn,hold_pair=bank['hold']['members'],
   track_selectors=track,hold_selectors=hold,positive_output_native=pos,negative_output_native=neg,
   positive_input_native=terms[dp]['B']['native_cluster'],negative_input_native=terms[dn]['B']['native_cluster'],
   input_nodes=[members[dp]['nodes'][1],members[dn]['nodes'][1]],
   output_nodes=[members[dn]['nodes'][0],members[dp]['nodes'][0]])
 assert result['slave']['output_nodes']==[qp_node,qn_node]
 assert [result['slave'][k]for k in ['positive_input_native','negative_input_native']]==[result['master'][k]for k in ['positive_output_native','negative_output_native']]
 return result
def latch_graph_faults(members,terms,qp_node,qn_node):
 result=[]
 for label in ['missing_actual_parallel_selector','wrong_actual_slave_input','wrong_actual_collector_reference']:
  ms=copy.deepcopy(members);ts=copy.deepcopy(terms)
  good=latch_graph(ms,ts,qp_node,qn_node)
  if label=='missing_actual_parallel_selector':
   name=good['master']['track_selectors'][0];del ms[name];del ts[name]
  elif label=='wrong_actual_slave_input':
   name=good['slave']['data_positive'];ts[name]['B']['native_cluster']=-991
  else:qp_node='not_a_native_collector'
  try:latch_graph(ms,ts,qp_node,qn_node)
  except (AssertionError,StopIteration):result.append(dict(name=label,rejected=True))
  else:raise AssertionError('Corrupted native latch topology accepted: '+label)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=tuple(PINS),required=True);args=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 out=ROOT/('cloud-cdr-v29-latch-timing-'+args.case);out.mkdir(exist_ok=False)
 inputs=ROOT/('cdr-v29-latch-inputs-'+args.case);inputs.mkdir(exist_ok=False);reports.OUT=inputs
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,full_phy_accepted=False,no_new_simulation=True)
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['controls']=controls();r['parallel_bank_controls']=parallel_controls()
  tx=np.array([0.,1.,2.,3.]);dx=np.array([-1.,1.,-1.,1.])
  assert list(crossing(tx,dx,True))==[.5,2.5]and list(crossing(tx,dx,False))==[1.5]
  receipt=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-electrical-rejection-20261022.json').read_text())
  pin=receipt['cases'][args.case];assert receipt['run']==39695370523
  sh,ph=PINS[args.case];assert receipt['run']==39695370523 and pin['summary_sha256']==sh and pin['parts_sha256']==ph
  prior,proof=reports.restore_report('cdr-gain-headroom-v29-mim-streamed-'+args.case,receipt['run'],sh,ph,inputs/'wave',['native/wave.raw','composed/composition.json','planes/native-planes.json'])
  assert prior['status']=='REJECTED_WHOLE_MIM_PD476_LOADED'
  for key in ('case','source_head','status','validation_prerequisite','source_bits_sha256','data_offset_s','devices_passed','phase_passed','sources_unchanged'):
   assert prior[key]==pin[key],('Pinned native report mismatch',key)
  assert {key:prior['raw_capture'][key]for key in pin['raw_capture']}==pin['raw_capture']
  for tag,check in pin['sampler_checks'].items():
   assert {key:prior['sampler_checks'][tag][key]for key in check}==check
  assert prior['case']==args.case and prior['source_head']=='c875a4f6effbd936d054a58f22f90bdaaf27d3e3'
  assert prior['returncode']==0 and not prior['diagnostics']and prior['sources_unchanged']and prior['devices_passed']==pin['devices_passed']
  cp=json.loads((ROOT/'docs/evidence/cdr-gain-headroom-v29-mim-parent-capture-pass-20261022.json').read_text())
  assert cp['run']==39694160820 and cp['summary_sha256']=='ccfe6913daa977fe9de26cb413c993e408ba38ab53430cd6a24e74b3065da1a8'
  names=['source/wire/device-locations01.json','source/parent/layout/result.json']
  captured,cproof=reports.restore_report('cdr-gain-headroom-v29-mim-parent-rc',cp['run'],cp['summary_sha256'],cp['parts_sha256'],inputs/'geometry',names)
  assert captured==cp['report']and captured['sources_unchanged']
  assert captured['source_head']=='d4b48ffbf77a10a048166681a5054d9e1fbb4c12'
  assert prior['validation_prerequisite']['spec']['capture_summary_sha256']==cp['summary_sha256']
  contract=json.loads((inputs/'wave/composed/composition.json').read_text())
  planes=json.loads((inputs/'wave/planes/native-planes.json').read_text())
  locations=json.loads((inputs/'geometry/source/wire/device-locations01.json').read_text())
  layout=json.loads((inputs/'geometry/source/parent/layout/result.json').read_text())
  assert contract['counts']==dict(devices=476,R=17906,C=12834)
  devices={d['native_id']:d for d in locations['devices']};records={d['native_id']:d for d in contract['device_records']}
  assert len(devices)==476 and devices.keys()==records.keys()
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
  assert len(checked)==120
  violations={n:c for n,c in checked.items()if c['minimum_active_vce_v']<.4 or c['maximum_alltime_abs_vce_v']>1.6 or c['maximum_alltime_abs_vbe_v']>1 or c['maximum_alltime_abs_ic_per_emitter_a']>=.003}
  assert violations==pin['hbt_violations']
  assert set(violations)==(set() if args.case=='nominal_early' else {'xpd.xd0105'})
  r['original_hbt_violations_reproduced']={n:dict(measurements=c,physical_macro=owned[n],device=prior['devices'][n],native_record=records[prior['devices'][n]['native_id']])for n,c in violations.items()}
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
  def analyze_latches(tag,members,terms):
   qp=prior['binding']['sampler_points'][tag+'qp'];qn=prior['binding']['sampler_points'][tag+'qn']
   graph=latch_graph(members,terms,qp,qn);faults=latch_graph_faults(members,terms,qp,qn)
   signals={};currents={}
   for label,bank in graph.items():
    signals[label+'_input']=v(bank['input_nodes'][0])-v(bank['input_nodes'][1])
    signals[label+'_output']=v(bank['output_nodes'][0])-v(bank['output_nodes'][1])
    for side in ['track','hold']:
     names=bank[side+'_selectors']
     currents[label+'_'+side]=sum((w['@q.'+name+'.qnpn13g2[ic]']for name in names),np.zeros(len(t)))
    currents[label+'_track_minus_hold']=currents[label+'_track']-currents[label+'_hold']
   assert np.array_equal(signals['slave_output'],v('xpd.'+tag+'qp')-v('xpd.'+tag+'qn'))
   edges=falling if tag=='b'else rising;offsets=(-.5,-.3,-.1,0.,.1,.3,.6,.9)
   rows=[]
   for k,(bit,edge)in enumerate(zip(expected[tag],edges,strict=True)):
    sign=2*bit-1
    for offset in offsets:
     when=edge+offset*UI
     rows.append(dict(bit_index=k+1,expected=bit,offset_ui=offset,time_s=when,
      signed_differentials_v={key:float(np.interp(when,t,val))*sign for key,val in signals.items()},
      selector_currents_a={key:float(np.interp(when,t,val))for key,val in currents.items()}))
   summary=[]
   for offset in offsets:
    part=[r for r in rows if r['offset_ui']==offset]
    summary.append(dict(offset_ui=offset,samples=len(part),signals={name:dict(
     wrong_sign=sum(r['signed_differentials_v'][name]<=0 for r in part),
     below_100mv_marker=sum(r['signed_differentials_v'][name]<.1 for r in part),
     minimum_signed_v=min(r['signed_differentials_v'][name]for r in part))for name in signals}))
   at_edge={r['bit_index']:r for r in rows if r['offset_ui']==0}
   late={r['bit_index']:r for r in rows if r['offset_ui']==.9}
   contingency=Counter()
   for bit,row in at_edge.items():
    bad_input=row['signed_differentials_v']['master_input']<.1
    bad_output=late[bit]['signed_differentials_v']['slave_output']<.1
    contingency[str((bad_input,bad_output))]+=1
   steering={}
   for label in ['master','slave']:
    delta=currents[label+'_track_minus_hold']
    on=crossing(t,delta,True);off=crossing(t,delta,False)
    on=on[on>=timing.START];off=off[off>=timing.START]
    steering[label]=dict(minimum_track_a=float(currents[label+'_track'][active].min()),maximum_track_a=float(currents[label+'_track'][active].max()),
     minimum_hold_a=float(currents[label+'_hold'][active].min()),maximum_hold_a=float(currents[label+'_hold'][active].max()),
     positive_crossings_s=list(map(float,on)),negative_crossings_s=list(map(float,off)),
     track_on_nearest_expected_edge=nearest_edges(on,np.array(edges))if len(on)else None,
     track_off_nearest_expected_edge=nearest_edges(off,np.array(edges))if len(off)else None)
   both=(currents['master_track_minus_hold']>0)&(currents['slave_track_minus_hold']>0)&active
   dt=np.diff(t);left=both[:-1];right=both[1:]
   overlap=dict(sample_count=int(both.sum()),duration_lower_bound_s=float(dt[left&right].sum()),
    duration_upper_bound_s=float(dt[(left|right)&active[:-1]&active[1:]].sum()),
    scope='Observed simultaneous positive track-minus-hold collector currents, not proof of an actual data race')
   return dict(native_graph=graph,graph_faults=faults,original_expected_capture_edges_s=edges,
    input_output_observations=rows,phase_summary=summary,
    master_input_at_edge_vs_slave_output_at_09ui=dict(contingency),steering=steering,simultaneous_track_observation=overlap,
    full_original_sampler_check_unchanged=True,
    marker_scope='100mV at internal nodes is only a diagnostic marker, not a new input acceptance gate; original output gate remains unchanged.')
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
   latch_data=analyze_latches(tag,members,terms)
   selector_names={n for bank in latch_data['native_graph'].values()for key in ('track_selectors','hold_selectors')for n in bank[key]}
   assert len(selector_names)==8 and all(members[n]['nx']==2 for n in selector_names)
   assert len(members)==16 and all(members[n]['nx']==4 for n in set(members)-selector_names)
   latch_data['actual_selector_nx']={n:members[n]['nx']for n in sorted(selector_names)}
   latch_data['actual_data_hold_nx']={n:members[n]['nx']for n in sorted(set(members)-selector_names)}
   pairs=[]
   for lp,ln in allpairs:
    if lp not in logical or ln not in logical:continue
    positive=[n for n in members if terms[n]['B']['native_cluster']==logical[lp][0]]
    negative=[n for n in members if terms[n]['B']['native_cluster']==logical[ln][0]]
    for pn,nn in physical_pairs(positive,negative,terms):
     pv=v(members[pn]['nodes'][1]);nv=v(members[nn]['nodes'][1]);delta=pv-nv
     edges={direction:crossing(t,delta,direction=='rising')for direction in ('rising','falling')}
     edges={k:x[x>=timing.START]for k,x in edges.items()}
     pairs.append(dict(logical_pair=[lp,ln],positive_device=pn,negative_device=nn,
      native_shared_emitter=terms[pn]['E']['native_cluster'],
      parallel_positive_devices=[n for n in positive if terms[n]['E']['native_cluster']==terms[pn]['E']['native_cluster']],
      parallel_negative_devices=[n for n in negative if terms[n]['E']['native_cluster']==terms[pn]['E']['native_cluster']],positive_base_node=members[pn]['nodes'][1],negative_base_node=members[nn]['nodes'][1],
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
   stages[tag]=dict(latches=latch_data,physical_macro=macro,physical_kind=layout['placements'][macro]['kind'],hbt_count=len(members),
     original_sampler_check=prior['sampler_checks'][tag],phase_breakdown=summaries,real_shared_emitter_base_pairs=pairs,worst_native_snapshots=snapshots)
  assert all(sha(Path(n))==h for n,h in frozen.items())
  r.update(status='COMPLETE_REJECTED_CDR_NATIVE_MASTER_SLAVE_TOPOLOGY_AND_TRANSFER_TIMING_NOT_ACCEPTANCE',
   waveform_source=proof,capture_source=cproof,source_unchanged=True,protected_inputs=frozen,
   all120original_hbt_checks_reproduced=True,all4original_sampler_checks_reproduced=True,
   original_rejection_preserved=True,original_devices_passed=prior['devices_passed'],
   original_phase_passed=prior['phase_passed'],original_vi_passed=prior['vi']['passed'],stages=stages,
   scope='Same complete native waveform and original sample/window/gates. Physical sampler ownership and common-emitter HBT base pairs are measured, not ideal data regeneration. Edge interpolation only locates existing crossings; no clock realignment or new acceptance claim.')
 except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
 finally:save();print(json.dumps({k:r[k]for k in ('status','case','accepted')}),flush=True)
if __name__=='__main__':main()
