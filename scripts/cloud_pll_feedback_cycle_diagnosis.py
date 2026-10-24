#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe actual feedback-chain terminals; preserve the failed original PLL gate."""
import copy,hashlib,json,os,shutil,sys,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cloud_pll_rhi120_c8_delta_adapter as adapter
ROOT=Path(__file__).resolve().parents[1]
GROUP='pll-feedback-cycle-diagnosis'
OUT=ROOT/('cloud-'+GROUP)
MAP='docs/evidence/pll-rhi120-c8-diagnostic-node-selection-20261024.json'
MAP_SHA='31b0f4b6b4708850e166d057fb8de96bbaa7921634605bbee23367e39190c321'
METHOD='scripts/pll-feedback-cycle-diagnosis-method.json'
EXPECTED='REJECTED_ORIGINAL_FULL_RHI120_ACQUISITION_GATES'
SOURCE=dict(run=40071288423,attempt=1,stage='sparse',transport='native-lossless-prefix-delta-v1',
 summary_sha256='a9906f7c7314b527e05ce71eadf9fa267f73c346ffa4edea81931d67a09f64df',
 parts_sha256='bc71e55d3707af88dc19290ff1792b64fc39d849062805cb601c7e97872983ea')
def digest(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def methods():
 record=json.loads((ROOT/METHOD).read_text())
 for p,h in record['protected'].items():assert file_sha(ROOT/p)==h,p
 assert file_sha(ROOT/MAP)==MAP_SHA
 adapter.methods()
 return record
def selection(mapping,table):
 assert mapping['status']=='VERIFIED_NATIVE_GRAPH_DIAGNOSTIC_NODE_SELECTION_NOT_ACCEPTANCE'
 assert not any(mapping[k]for k in ('accepted','acquisition_accepted','full_phy_accepted','qualified_pex'))
 assert len(mapping['differential_pairs'])==25 and len(mapping['single_ended'])==29
 names=[r[1]for r in table]
 assert len(names)==5106 and len(set(names))==5106 and names[0]=='time'
 assert all(str(i)==r[0]for i,r in enumerate(table))
 selected=['time']+sorted({r[k]for r in mapping['differential_pairs']for k in ('p_vector','n_vector')}|
                         {r['vector']for r in mapping['single_ended']})
 assert len(selected)==80
 units={r[1]:r[2]for r in table}
 assert all(n in units and units[n]=='voltage'for n in selected[1:])
 assert len({r['name']for r in mapping['differential_pairs']+mapping['single_ended']})==54
 return selected
class SelectedCache:
 def __init__(self,names,selected,rows,path):
  assert len(names)==len(set(names)) and len(selected)==len(set(selected))
  assert selected[0]=='time' and set(selected)<=set(names) and type(rows)is int and rows>1
  self.names=names;self.selected=selected;self.rows=rows;self.done=0;self.finished=False
  self.path=Path(path);assert not self.path.exists()
  self.indices=[names.index(n)for n in selected]
  self.data=np.memmap(self.path,dtype='<f8',mode='w+',shape=(rows,len(selected)))
  self.digest=hashlib.sha256()
 def append(self,start,values):
  assert not self.finished and start==self.done
  assert values.dtype==np.dtype('<f8') and values.ndim==2 and values.shape[1]==len(self.names)
  end=start+len(values);assert len(values)>0 and end<=self.rows
  block=np.take(values,self.indices,axis=1);assert np.isfinite(block).all()
  self.data[start:end]=block
  assert np.array_equal(self.data[start:end].view('<u8'),block.view('<u8'))
  self.digest.update(block.tobytes(order='C'));self.done=end
 def finish(self):
  assert not self.finished and self.done==self.rows
  self.data.flush()
  expected=self.digest.hexdigest();assert file_sha(self.path)==expected,'Persisted selected bits changed'
  self.finished=True
  self.data=np.memmap(self.path,dtype='<f8',mode='r',shape=(self.rows,len(self.selected)))
  return {n:self.data[:,i]for i,n in enumerate(self.selected)},dict(
   rows=self.rows,columns=self.selected,bytes=self.path.stat().st_size,
   format='row-major little-endian binary64 without header',sha256=expected,
   all_sample_bits_checked=True,samples_removed=0,resampled=False,readonly=True)
def crossing(t,y,threshold=0.0,inclusive=False):
 assert len(t)==len(y)>1 and np.isfinite(y).all() and np.all(np.diff(t)>0)
 mask=((y[:-1]<threshold)&(y[1:]>=threshold))if inclusive else((y[:-1]<=threshold)&(y[1:]>threshold))
 i=np.flatnonzero(mask)
 return t[i]+(threshold-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i])
def hysteresis(t,y,h):
 assert h>0 and len(t)==len(y)>1 and np.isfinite(y).all() and np.all(np.diff(t)>0)
 up=np.flatnonzero((y[:-1]<h)&(y[1:]>=h))
 low=np.flatnonzero((y[:-1]>-h)&(y[1:]<=-h))
 if y[0]<=-h:low=np.concatenate(([-1],low))
 before=np.searchsorted(low,up,side='left')-1
 last=np.full(len(up),-3,dtype=np.int64);ok=before>=0;last[ok]=low[before[ok]]
 previous=np.concatenate(([-2],up[:-1]))
 i=up[last>previous]
 return t[i]+(h-y[i])*(t[i+1]-t[i])/(y[i+1]-y[i])
def stats(x):
 x=np.asarray(x)
 if not len(x):return dict(count=0)
 assert np.isfinite(x).all()
 return dict(count=len(x),minimum=float(x.min()),maximum=float(x.max()),mean=float(x.mean()),
             median=float(np.median(x)))
def cycles(t,y,edges,crossings):
 result=[]
 for a,b in zip(edges[:-1],edges[1:]):
  lo,hi=np.searchsorted(t,[a,b])
  def boundary(x,i):
   if i<len(t)and t[i]==x:return float(y[i])
   assert 0<i<len(t)
   return float(np.interp(x,t[i-1:i+1],y[i-1:i+1]))
  v=np.concatenate(([boundary(a,lo)],y[lo:hi],[boundary(b,hi)]))
  row=dict(interval_s=[float(a),float(b)],minimum_v=float(v.min()),maximum_v=float(v.max()),
           mean_v=float(np.trapezoid(v,np.concatenate(([a],t[lo:hi],[b])))/(b-a)))
  row['rising_counts']={k:int(np.searchsorted(e,b,side='left')-np.searchsorted(e,a,side='left'))for k,e in crossings.items()}
  result.append(row)
 return result
def diagnose(data,mapping,analysis):
 t=np.array(data['time'],dtype='<f8',order='C',copy=True)
 assert np.array_equal(t.view('<u8'),data['time'].view('<u8'));t.flags.writeable=False
 assert len(t)>2 and np.isfinite(t).all() and np.all(np.diff(t)>0)
 fb=np.asarray(analysis['feedback_edges_s']);assert len(fb)>2 and np.all(np.diff(fb)>0)
 report=dict(scope='Diagnostic only. Original feedback intervals; no fitting, edge replacement, resampling or acceptance override.',
  original_feedback_edges_s=fb.tolist(),differential={},single_ended={},
  expected_nominal_cycle_ratios=mapping['expected_nominal_cycle_ratios'])
 for row in mapping['differential_pairs']:
  p=data[row['p_vector']];n=data[row['n_vector']];y=p-n
  assert np.isfinite(p).all()and np.isfinite(n).all()
  up=crossing(t,y);down=crossing(t,-y)
  es={'zero':up,'hysteresis_10mV':hysteresis(t,y,.01),'hysteresis_50mV':hysteresis(t,y,.05)}
  end=np.searchsorted(down,up,side='right');valid=end<len(down)
  widths=down[end[valid]]-up[valid]
  report['differential'][row['name']]=dict(p_vector=row['p_vector'],n_vector=row['n_vector'],
   nominal_frequency_hz=row['nominal_frequency_hz'],thresholds_are_not_acceptance=True,
   voltage=stats(y),common_mode=stats((p+n)/2),zero_rising_period_s=stats(np.diff(up)),
   zero_positive_width_s=stats(widths),rising_edges_s={k:e.tolist()for k,e in es.items()},
   cycles=cycles(t,y,fb,es))
 for row in mapping['single_ended']:
  y=data[row['vector']];threshold=row['diagnostic_threshold_v']
  es={}if threshold is None else{'fixed_threshold':crossing(t,y,threshold,True)}
  report['single_ended'][row['name']]=dict(vector=row['vector'],diagnostic_threshold_v=threshold,
   threshold_is_not_acceptance=True,voltage=stats(y),
   rising_edges_s={k:e.tolist()for k,e in es.items()},cycles=cycles(t,y,fb,es))
 # Actual different RC nodes on the same native conductor remain distinct.
 pairs=[
  ('div1_to_gain_p','v(qp)','v(xloop.w_t442_b)'),
  ('div1_to_gain_n','v(qn)','v(xloop.w_t443_b)'),
  ('gain_to_div2_p','v(xloop.w_t444_e)','v(xloop.w_t541_rppd_1)'),
  ('gain_to_div2_n','v(xloop.w_t445_e)','v(xloop.w_t540_rppd_1)'),
  ('div2_qp_two_terminals','v(xloop.w_t469_c)','v(xloop.w_t476_c)'),
  ('div2_to_rx_p','v(xloop.w_t476_c)','v(xloop.w_t528_rppd_1)'),
  ('div2_to_rx_n','v(xloop.w_t468_c)','v(xloop.w_t529_rppd_1)'),
  ('rx_to_counter','v(xloop.w_t6_d)','v(xloop.w_t77_g)'),
  ('release_to_reset','v(xloop.w_t105_d)','v(xloop.w_t9_g)'),
  ('count_to_level','v(xloop.w_t33_d)','v(xloop.w_t180_g)'),
  ('public_fb_to_pfd','v(fb)','v(xloop.w_t134_g)'),
  ('public_up_to_pump','v(up)','v(xloop.w_t189_g)'),
  ('public_down_to_pump','v(down)','v(xloop.w_t187_g)'),
  ('pump_to_vco','v(xloop.w_t187_d)','v(xloop.w_t320_g)')]
 report['source_minus_sink']={name:dict(source=a,sink=b,voltage=stats(data[a]-data[b]),
   cycles=cycles(t,data[a]-data[b],fb,{}))for name,a,b in pairs}
 return report
def reproduce(current,old):
 assert current['status']==old['status']==EXPECTED
 assert current['full_capture']is True and current['all5106_columns_verified']is True
 assert current['all_original_native_bytes_retained']is True and current['native_activation_performed']is False
 assert not any(current[k]for k in ('acquisition_accepted','full_device_safety_accepted','full_phy_accepted','qualified_pex'))
 for k in ('source_checkpoint','analyzer_cache','independent_acquisition','cycle_diagnosis'):
  assert current[k]==old[k],('Original failed evidence changed',k)
 for k in ('rows','columns','bytes','header_bytes','raw_sha256','payload_sha256','start_s','end_s',
           'every_native_column_finite','all_recorded_columns_checked','dropped_columns',
           'all_source_bytes_checked','source_iterator_exhausted','payload_has_only_complete_rows'):
  assert current['capture'][k]==old['capture'][k],k
 assert current['error']=="AssertionError('Original full-duration acquisition gates failed')"
 return dict(original_rejection_reproduced=True,original_cache_bits_identical=True,
             full5106_column_capture_verified=True,acquisition_accepted=False)
def controls():
 assert os.environ.get('GITHUB_ACTIONS')=='true','Tests execute only on hosted runner'
 methods();rejects=[]
 def reject(name,fn):
  try:fn()
  except (AssertionError,KeyError,ValueError):rejects.append(name)
  else:raise AssertionError('Accepted fault '+name)
 with tempfile.TemporaryDirectory(prefix='pll-observer-')as d:
  v=np.arange(57,dtype='<f8').reshape(19,3);v[:,0]=np.arange(19,dtype='<f8')
  names=['time','v(a)','v(b)'];selected=['time','v(b)']
  c=SelectedCache(names,selected,19,Path(d)/'exact.bin')
  reject('skipped-first-row',lambda:c.append(1,v[:1]))
  reject('wrong-width',lambda:c.append(0,v[:1,:2]))
  reject('wrong-dtype',lambda:c.append(0,v[:1].astype('<f4')))
  bad=v[:1].copy();bad[0,2]=np.nan
  reject('nonfinite-selected',lambda:c.append(0,bad))
  reject('incomplete',lambda:c.finish())
  for a,b in [(0,1),(1,7),(7,18),(18,19)]:c.append(a,v[a:b])
  data,proof=c.finish()
  assert proof['sha256']==digest(v[:,[0,2]].tobytes())
  assert np.array_equal(data['v(b)'].view('<u8'),v[:,2].view('<u8'))
  reject('append-after-finish',lambda:c.append(19,v[:1]))
  reject('finish-twice',lambda:c.finish())
  reject('duplicate-selection',lambda:SelectedCache(names,['time','time'],19,Path(d)/'dup.bin'))
  reject('missing-column',lambda:SelectedCache(names,['time','v(c)'],19,Path(d)/'missing.bin'))
  corrupt=SelectedCache(names,selected,19,Path(d)/'corrupt.bin');corrupt.append(0,v)
  corrupt.data[8,1]=1000
  reject('persisted-bit-corruption',lambda:corrupt.finish())
  overflow=SelectedCache(names,selected,2,Path(d)/'overflow.bin')
  reject('row-overrun',lambda:overflow.append(0,v))
 mapping=json.loads((ROOT/MAP).read_text())
 vv=sorted({r[k]for r in mapping['differential_pairs']for k in ('p_vector','n_vector')}|{r['vector']for r in mapping['single_ended']})
 nn=['time']+vv+['v(synthetic_'+str(i)+')'for i in range(5106-1-len(vv))]
 table=[[str(i),n,'time'if i==0 else'voltage']for i,n in enumerate(nn)]
 assert selection(mapping,table)==['time']+vv
 for label,mutate in [
  ('missing-selected-vector',lambda m,t:t[1].__setitem__(1,'v(removed)')),
  ('wrong-selected-unit',lambda m,t:t[1].__setitem__(2,'current')),
  ('duplicate-table-name',lambda m,t:t[2].__setitem__(1,t[1][1])),
  ('reordered-table-index',lambda m,t:t[3].__setitem__(0,'4')),
  ('invented-map-acceptance',lambda m,t:m.__setitem__('accepted',True)),
  ('missing-pair',lambda m,t:m['differential_pairs'].pop())]:
  m,tb=copy.deepcopy((mapping,table));mutate(m,tb)
  reject(label,lambda:selection(m,tb))
 old=json.loads(adapter.completed.hosted_asset(671784463,mapping['capture_binding']['summary_sha256']))
 assert reproduce(old,old)['original_rejection_reproduced']
 for label,mutate in [
  ('changed-full-capture-hash',lambda r:r['capture'].__setitem__('raw_sha256','0'*64)),
  ('changed-original-cache-bits',lambda r:r['analyzer_cache'].__setitem__('selected_row_major_binary64_sha256','0'*64)),
  ('changed-original-cycle',lambda r:r.__setitem__('cycle_diagnosis',{})),
  ('accepted-failed-acquisition',lambda r:r.__setitem__('acquisition_accepted',True)),
  ('incomplete-original-capture',lambda r:r.__setitem__('full_capture',False)),
  ('unrelated-original-error',lambda r:r.__setitem__('error',"AssertionError('unrelated')"))]:
  changed=copy.deepcopy(old);mutate(changed);reject(label,lambda:reproduce(changed,old))
 # Known crossings span selected-cache append boundaries; no missed seam edge.
 t=np.arange(7,dtype='<f8');y=np.array([-2.,-1.,1.,2.,-1.,1.,2.])
 assert np.array_equal(crossing(t,y),[1.5,4.5])
 assert np.array_equal(hysteresis(t,y,.5),[1.75,4.75])
 assert np.array_equal(crossing(t,np.array([-1.,0.,1.,-1.,0.,1.,2.]),0,True),[1.,4.])
 # Extra sign-only ringing must remain visible, never silently removed.
 ring=np.array([-1.,.1,-.1,.1,1.,-1.,1.]);rt=np.arange(len(ring),dtype='<f8')
 assert len(crossing(rt,ring))==3 and len(hysteresis(rt,ring,.5))==2
 reject('zero-hysteresis',lambda:hysteresis(rt,ring,0))
 reject('reversed-time',lambda:crossing(t[::-1],y))
 yn=y.copy();yn[2]=np.nan;reject('nonfinite-edge',lambda:crossing(t,yn))
 yy=np.arange(7,dtype='<f8')
 rr=cycles(t,yy,np.array([.5,3.5,5.5]),{'x':np.array([.5,1.5,3.5,4.5,5.5])})
 assert [r['rising_counts']['x']for r in rr]==[2,2]
 assert np.allclose([r['mean_v']for r in rr],[2.,4.5])
 # Same endpoints, including exact native sample times, with strided cache views.
 st=np.zeros((7,3),dtype='<f8');st[:,0]=t;st[:,2]=yy
 for bounds in (np.array([.5,3.5,5.5]),np.array([0.,3.,6.])):
  rows=cycles(st[:,0],st[:,2],bounds,{})
  for row,a,b in zip(rows,bounds[:-1],bounds[1:]):
   lo,hi=np.searchsorted(t,[a,b]);grid=np.concatenate(([a],t[lo:hi],[b]))
   expected=float(np.trapezoid(np.interp(grid,t,yy),grid)/(b-a))
   assert row['mean_v']==expected
 return dict(rejected=rejects,count=len(rejects),exact_binary_cache=True,
  analytical_crossings_and_seams=True,ringing_retained=True,half_open_feedback_intervals=True,
  no_acceptance_override=True,native_started=False)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
  native_activation_performed=False,acquisition_accepted=False,full_phy_accepted=False,
  full_device_safety_accepted=False,qualified_pex=False)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  result['method']=methods();result['controls']=controls()
  if sys.argv[1:]==['--controls']:
   result['status']='PASS_FEEDBACK_OBSERVER_CONTROLS_NOT_NATIVE_ACCEPTANCE';return
  assert sys.argv[1:]==['--review']
  mapping=json.loads((ROOT/MAP).read_text());result['mapping_sha256']=MAP_SHA
  old=adapter.completed.hosted_asset(671784463,mapping['capture_binding']['summary_sha256'])
  old=json.loads(old);assert old['status']==EXPECTED and old['source_checkpoint']==SOURCE
  prior=adapter.api('actions/runs/40076916467')
  assert prior['status']=='completed' and prior['conclusion']=='failure'
  assert prior['head_sha']==mapping['source_ref'] and prior['run_attempt']==1
  result['original_failed_run']=40076916467
  os.environ['SOURCE_CHECKPOINT']=json.dumps(SOURCE)
  original_loader=adapter.reference.load_reference
  original_cache=adapter.completed.AnalyzerCache
  state={}
  def load_ref(out):
   ref=original_loader(out)
   assert digest((json.dumps(ref['contract'],indent=2)+'\n').encode())==mapping['column_binding']['contract_sha256']
   state['selected']=selection(mapping,ref['contract']['raw_table'])
   return ref
  class Observer(original_cache):
   def __init__(self,names,rows):
    assert rows==mapping['capture_binding']['rows']and len(names)==5106
    selected=state['selected'];nbytes=rows*len(selected)*8
    # Original capacity gate remains active; reserve for this exact cloud cache,
    # source staging and its subsequent publication without a full raw allocation.
    assert shutil.disk_usage(OUT).free>=2*nbytes+6*1024**3,'Insufficient observer disk reserve'
    super().__init__(names,rows)
    self.selected_cache=SelectedCache(names,selected,rows,OUT/'selected-native.bin')
   def append(self,start,values):
    super().append(start,values);self.selected_cache.append(start,values)
   def finish(self):
    data,proof=super().finish()
    assert proof==old['analyzer_cache']
    extra,receipt=self.selected_cache.finish()
    state.update(data=extra,cache=receipt)
    (OUT/'selected-native.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return data,proof
  expected_error=False
  with patch.object(adapter.reference,'load_reference',load_ref),patch.object(adapter.completed,'AnalyzerCache',Observer):
   try:adapter.review_complete()
   except AssertionError as error:
    assert str(error)=='Original full-duration acquisition gates failed','Unexpected original-reader failure'
    expected_error=True
  assert expected_error,'Original rejected record unexpectedly accepted'
  review_path=ROOT/adapter.READER/'result.json'
  current=json.loads(review_path.read_text());result['original_reproduction']=reproduce(current,old)
  (OUT/'original-review.json').write_bytes(review_path.read_bytes())
  result['selected_cache']=state['cache'];result['full_capture']=True
  analysis=diagnose(state['data'],mapping,current['independent_acquisition'])
  (OUT/'feedback-diagnosis.json').write_text(json.dumps(analysis,indent=2)+'\n')
  sequence=mapping['expected_nominal_cycle_ratios']['sequence']
  result['per_feedback_cycle_stage_counts']=[]
  for i,(a,b)in enumerate(zip(analysis['original_feedback_edges_s'][:-1],analysis['original_feedback_edges_s'][1:])):
   stages={}
   for name in sequence:
    section=analysis['differential']if name in analysis['differential']else analysis['single_ended']
    r=section[name]['cycles'][i]
    stages[name]={k:r[k]for k in ('rising_counts','minimum_v','maximum_v')}
   result['per_feedback_cycle_stage_counts'].append(dict(ordinal=i,interval_s=[a,b],stages=stages))
  result['stage_statistics']={name:{k:v for k,v in r.items()if k not in ('cycles','rising_edges_s')}
   for section in ('differential','single_ended')for name,r in analysis[section].items()}
  result['diagnosis_file']='feedback-diagnosis.json'
  result['diagnosis_sha256']=file_sha(OUT/'feedback-diagnosis.json')
  result['diagnostic_counts']=dict(differential_pairs=len(analysis['differential']),single_ended=len(analysis['single_ended']),
                                    feedback_cycles=len(analysis['original_feedback_edges_s'])-1)
  methods()
  result['status']='PASS_EXACT_FEEDBACK_DIAGNOSIS_ORIGINAL_ACQUISITION_REMAINS_REJECTED'
 except BaseException as error:
  result.update(status='FAIL_FEEDBACK_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
 finally:save();print(result['status'],flush=True)
if __name__=='__main__':main()
