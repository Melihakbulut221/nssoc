#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact full-capture first-latch sink-voltage observer; no new PLL simulation."""
import copy,hashlib,json,os,shutil,sys,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cloud_pll_feedback_cycle_diagnosis as old
import cloud_pll_feedback_event_review as events
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-first-latch-sinks'
METHOD='scripts/pll-first-latch-sinks-methods.json'
MAP='docs/evidence/pll-first-divider15-terminal-column-map-20261024.json'
MAP_SHA='d405e7125ae9b838dc258d65ccfc91c03d0f3e9e03ccaed59a741dfb75058df5'
def digest(b):return hashlib.sha256(b).hexdigest()
def methods():
 old.methods();events.methods()
 m=json.loads((ROOT/METHOD).read_text())
 for p,h in m['protected'].items():assert old.file_sha(ROOT/p)==h,p
 assert old.file_sha(ROOT/MAP)==MAP_SHA
 return m
def choose(mapping,table,chain):
 assert mapping['schema']=='pll-first-divider15-native-terminal-column-map-v1'
 assert mapping['status']=='VERIFIED_EXISTING_METADATA_ONLY_NO_NEW_WAVEFORM_OR_NATIVE_EXECUTION'
 assert not any(mapping[k]for k in ('accepted','acquisition_accepted','full_device_safety_accepted','full_phy_accepted','native_execution','waveform_samples_read','local_files_written'))
 prior=old.selection(chain,table)
 assert len(prior)==80 and len(mapping['terminal_voltage_columns'])==54
 assert len(mapping['aggregate_branch_currents'])==3
 devices=mapping['devices']
 assert {d['native_id']for d in devices}==set(range(386,401))|set(range(493,497))
 hbts=[d for d in devices if d['native_id']<401];assert len(hbts)==15
 assert all({t['terminal']for t in d['terminals']}=={'C','B','E','S'}for d in hbts)
 rows=mapping['terminal_voltage_columns']+mapping['aggregate_branch_currents']
 assert len({r['vector']for r in rows})==len(rows)==57
 assert len({r['raw_column']for r in rows})==57
 for r in rows:
  i=r['raw_column'];assert type(i)is int and 0<i<len(table)
  assert table[i]==[str(i),r['vector'],r['unit']],('Changed exact native column',r)
 assert all(r['unit']=='voltage'for r in mapping['terminal_voltage_columns'])
 assert all(r['unit']=='current'and r['vector'].startswith('i(v')for r in mapping['aggregate_branch_currents'])
 absent=mapping['absent_device_currents']
 assert not any(absent[k]for k in ('HBT_Ic_saved','HBT_Ib_saved','HBT_Ie_saved'))
 actual=[dict(raw_column=i,vector=r[1],unit=r[2])for i,r in enumerate(table)if r[2]=='current']
 assert actual==absent['all_actual_current_columns']and len(actual)==17
 assert set(mapping['existing_cache_overlap'])==set(prior)&{r['vector']for r in mapping['terminal_voltage_columns']}
 selected=['time']+sorted(set(prior[1:])|{r['vector']for r in rows})
 assert len(selected)==131 and len(set(selected))==131
 return selected,prior
def controls():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 methods();original=old.controls();bad=[]
 def reject(label,fn):
  try:fn()
  except (AssertionError,KeyError,ValueError,IndexError):bad.append(label)
  else:raise AssertionError('Accepted fault '+label)
 with tempfile.TemporaryDirectory(prefix='first-latch-source-')as d:
  ref=old.adapter.reference.load_reference(Path(d));mapping=json.loads((ROOT/MAP).read_text())
  chain=json.loads((ROOT/old.MAP).read_text());table=ref['contract']['raw_table']
  selected,prior=choose(mapping,table,chain)
  for label,mutate in [
   ('lost-terminal',lambda m,t:m['terminal_voltage_columns'].pop()),
   ('wrong-column-index',lambda m,t:m['terminal_voltage_columns'][0].__setitem__('raw_column',24)),
   ('wrong-column-unit',lambda m,t:m['terminal_voltage_columns'][0].__setitem__('unit','current')),
   ('wrong-column-name',lambda m,t:m['terminal_voltage_columns'][0].__setitem__('vector','v(invented)')),
   ('lost-device',lambda m,t:m['devices'].pop()),
   ('lost-body',lambda m,t:m['devices'][0]['terminals'].pop()),
   ('invented-device-current',lambda m,t:m['absent_device_currents'].__setitem__('HBT_Ic_saved',True)),
   ('dropped-aggregate-current',lambda m,t:m['aggregate_branch_currents'].pop()),
   ('accepted-source-map',lambda m,t:m.__setitem__('accepted',True)),
   ('renamed-original-header',lambda m,t:t[985].__setitem__(1,'v(renamed)')),
   ('wrong-original-current-unit',lambda m,t:t[3903].__setitem__(2,'voltage')),
   ('lost-shared-sink',lambda m,t:m['existing_cache_overlap'].pop())]:
   m,t=copy.deepcopy((mapping,table));mutate(m,t);reject(label,lambda:choose(m,t,chain))
  assert len(selected)==131 and len(prior)==80
 # Exact bit comparison includes current columns and does not treat them as HBT currents.
 t=np.array([0.,1.,2.,3.]);y=np.array([-1.,1.,-1.,1.])
 assert np.array_equal(old.crossing(t,y),[.5,2.5])
 assert np.array_equal(old.crossing(t,-y),[1.5])
 rows=events.relation([0.,2.,3.],old.crossing(t,y),old.crossing(t,-y))
 assert [r['output_transitions']for r in rows]==[2,1]
 return dict(original_observer=original,exact_native_column_faults=bad,count=len(bad),
  actual_original_contract_positive=True,native_started=False)
def summarize(t,y,fb):
 return dict(full=old.stats(y),per_feedback_cycle=old.cycles(t,y,fb,{}))
def analyze(data,mapping,chain,analysis):
 # Reproduce every old statistic/event exactly; all 79 old voltage bits are independently hashed during streaming.
 original=old.diagnose(data,chain,analysis)
 original_bytes=(json.dumps(original,indent=2)+'\n').encode()
 assert digest(original_bytes)==events.DIAG_SHA,'Changed original diagnostic events or statistics'
 (OUT/'original-feedback-diagnosis.json').write_bytes(original_bytes)
 t=np.array(data['time'],dtype='<f8',copy=True);assert np.array_equal(t.view('<u8'),data['time'].view('<u8'))
 assert np.isfinite(t).all()and np.all(np.diff(t)>0)and t[0]==0 and abs(t[-1]-1e-6)<1e-15
 fb=np.asarray(analysis['feedback_edges_s'])
 V=lambda i,terminal:data['v(xloop.w_t'+str(i)+'_'+terminal.lower()+')']
 signals={}
 for d in mapping['devices']:
  i=d['native_id']
  if i>=493:
   signals['load_'+str(i)+'_terminal_drop_v']=data['v(xloop.w_t'+str(i)+'_rppd_1)']-data['v(xloop.w_t'+str(i)+'_rppd_2)']
  else:
   for name,x,y in [('VCE','C','E'),('VBE','B','E'),('VBC','B','C')]:
    signals['HBT_'+str(i)+'_'+name+'_v']=V(i,x)-V(i,y)
 pairs={
  'master_clock_hold_minus_sample_sink_v':(392,'B',393,'B'),
  'slave_clock_sample_minus_hold_sink_v':(388,'B',387,'B'),
  'same_clock_p_slave_sink_minus_master_sink_v':(388,'B',392,'B'),
  'same_clock_n_slave_sink_minus_master_sink_v':(387,'B',393,'B'),
  'master_feedback_QP_source_minus_data_sink_v':(398,'C',395,'B'),
  'master_feedback_QN_source_minus_data_sink_v':(389,'C',396,'B'),
  'master_feedback_QN_minus_QP_at_data_sinks_v':(396,'B',395,'B'),
  'master_MP_minus_MN_producers_v':(394,'C',396,'C'),
  'master_MP_source_minus_hold_sink_v':(394,'C',400,'B'),
  'master_MN_source_minus_hold_sink_v':(396,'C',394,'B'),
  'slave_MP_source_minus_data_sink_v':(394,'C',390,'B'),
  'slave_MN_source_minus_data_sink_v':(396,'C',399,'B')}
 for name,(a,ta,b,tb)in pairs.items():signals[name]=V(a,ta)-V(b,tb)
 # These are external supply/body branch currents; no individual transistor current was saved.
 for r in mapping['aggregate_branch_currents']:signals['aggregate_only_'+r['vector']+'_a']=data[r['vector']]
 result=dict(scope='Exact native terminal-voltage observations over complete1us. Not individual HBT current or current-density evidence. Original acquisition rejection remains unchanged.',
  original_diagnostic_sha256=events.DIAG_SHA,signals={k:summarize(t,v,fb)for k,v in signals.items()},
  master_events={},device_current_observation_available=False,acquisition_accepted=False,full_phy_accepted=False)
 clock=original['differential']['div1_first_conditioned']
 master=original['differential']['div1_first_master']
 my=data[master['p_vector']]-data[master['n_vector']]
 for key,h in [('zero',0),('hysteresis_10mV',.01),('hysteresis_50mV',.05)]:
  rising=np.asarray(master['rising_edges_s'][key])
  falling=old.crossing(t,-my)if h==0 else old.hysteresis(t,-my,h)
  intervals=events.relation(clock['rising_edges_s'][key],rising,falling)
  anomalies=[]
  for row in intervals:
   if row['output_transitions']==1:continue
   a,b=row['interval_s'];snapshots=[]
   for kind,es in [('rising',rising),('falling',falling)]:
    for x in es[np.searchsorted(es,a,'left'):np.searchsorted(es,b,'left')]:
     hi=int(np.searchsorted(t,x,'left'));assert 0<hi<len(t)
     snapshots.append(dict(kind=kind,time_s=float(x),bracketing_rows=[hi-1,hi],
       native_times_s=[float(t[hi-1]),float(t[hi])],
       signals={k:float(np.interp(x,t[hi-1:hi+1],v[hi-1:hi+1]))for k,v in signals.items()}))
   anomalies.append(dict(**row,transition_snapshots=sorted(snapshots,key=lambda r:r['time_s'])))
  counts={}
  for row in intervals:
   n=str(row['output_transitions']);counts[n]=counts.get(n,0)+1
  result['master_events'][key]=dict(complete_input_intervals=len(intervals),transition_count_histogram=counts,
    anomalous_intervals=anomalies,threshold_is_diagnostic_only=True,all_edges_retained=True)
 return result
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
  native_activation_performed=False,acquisition_accepted=False,full_device_safety_accepted=False,full_phy_accepted=False,qualified_pex=False)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  result['method']=methods();result['controls']=controls()
  if sys.argv[1:]==['--controls']:
   result['status']='PASS_FIRST_LATCH_SINK_OBSERVER_CONTROLS_NOT_NATIVE_ACCEPTANCE';return
  assert sys.argv[1:]==['--review']
  mapping=json.loads((ROOT/MAP).read_text());chain=json.loads((ROOT/old.MAP).read_text())
  original=json.loads(events.small(671784463,events.OLD_SHA))
  assert original['status']==old.EXPECTED and original['source_checkpoint']==old.SOURCE
  original_observer=json.loads(events.small(672131330,events.SUMMARY_SHA));events.summary_valid(original_observer)
  prior=old.adapter.api('actions/runs/40076916467')
  assert prior['status']=='completed'and prior['conclusion']=='failure'and prior['head_sha']==chain['source_ref']and prior['run_attempt']==1
  os.environ['SOURCE_CHECKPOINT']=json.dumps(old.SOURCE)
  original_loader=old.adapter.reference.load_reference;original_cache=old.adapter.completed.AnalyzerCache;state={}
  def load_ref(out):
   ref=original_loader(out)
   assert digest((json.dumps(ref['contract'],indent=2)+'\n').encode())==mapping['proofs']['contract_sha256']
   state['selected'],state['prior']=choose(mapping,ref['contract']['raw_table'],chain)
   return ref
  class Observer(original_cache):
   def __init__(self,names,rows):
    assert rows==3201410 and len(names)==5106
    assert shutil.disk_usage(OUT).free>=2*rows*131*8+6*1024**3,'Insufficient cloud cache and publication reserve'
    super().__init__(names,rows)
    self.sinks=old.SelectedCache(names,state['selected'],rows,OUT/'selected-native.bin')
    self.prior_indices=[names.index(n)for n in state['prior']];self.prior_digest=hashlib.sha256()
   def append(self,start,values):
    super().append(start,values);self.sinks.append(start,values)
    self.prior_digest.update(np.take(values,self.prior_indices,axis=1).tobytes(order='C'))
   def finish(self):
    data,proof=super().finish();assert proof==original['analyzer_cache']
    assert self.prior_digest.hexdigest()==events.CACHE_SHA,'Changed previously qualified80-column sample bits'
    extra,receipt=self.sinks.finish();state.update(data=extra,cache=receipt)
    (OUT/'selected-native.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return data,proof
  expected=False
  with patch.object(old.adapter.reference,'load_reference',load_ref),patch.object(old.adapter.completed,'AnalyzerCache',Observer):
   try:old.adapter.review_complete()
   except AssertionError as error:
    assert str(error)=='Original full-duration acquisition gates failed';expected=True
  assert expected,'Original rejected capture unexpectedly accepted'
  path=ROOT/old.adapter.READER/'result.json';current=json.loads(path.read_text())
  result['original_reproduction']=old.reproduce(current,original)
  (OUT/'original-review.json').write_bytes(path.read_bytes())
  result['selected_cache']=state['cache'];result['prior80_column_sha256']=events.CACHE_SHA
  result['full5106_column_capture_verified']=True
  diagnostic=analyze(state['data'],mapping,chain,current['independent_acquisition'])
  (OUT/'first-latch-diagnosis.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
  result['diagnosis_sha256']=old.file_sha(OUT/'first-latch-diagnosis.json')
  result['signals']={k:v['full']for k,v in diagnostic['signals'].items()}
  result['master_transition_histograms']={k:{p:v[p]for p in ('complete_input_intervals','transition_count_histogram')}for k,v in diagnostic['master_events'].items()}
  methods();result['status']='PASS_EXACT_FULL_CAPTURE_FIRST_LATCH_SINK_DIAGNOSIS_ORIGINAL_PLL_REMAINS_REJECTED'
 except BaseException as error:
  result.update(status='FAIL_FIRST_LATCH_SINK_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
 finally:save();print(result['status'],flush=True)
if __name__=='__main__':main()
