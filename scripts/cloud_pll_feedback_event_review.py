#!/usr/bin/env python3
"""Read-only event diagnosis from the exact cloud-resident native PLL cache."""
import hashlib,json,os,shutil,subprocess,sys,tarfile,tempfile,traceback
from pathlib import Path
import numpy as np
import cloud_pll_feedback_cycle_diagnosis as observer
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-feedback-event-review'
REPO='repos/Melihakbulut221/nssoc/'
SOURCE_HEAD='f520b2511b9dd00c98c1bff5491e87d232f11d21'
SUMMARY_SHA='9656bff3e87627c0529bdff52921f2d8278d48fe05cc76516b507200f9c67863'
PARTS_SHA='912d7f49e9b334f6579fd5f77cae89bbb2ca86302da597ee1bb08265df803449'
CACHE_SHA='18241b441de283bb6746198e0c8b49875eb959d4e17702ca60908e7736ac143c'
DIAG_SHA='b876a488ff086e045605544b3d6a3daeedd1ac0215b0b2a6c9df3ceeaa47a0b7'
OLD_SHA='04ae4ebfcdaa3696d686e6f3be68998183ba0f9c7eb937b9b96859835f6feebf'
def digest(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path]))
def small(aid,sha,size=None):
 b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
 assert digest(b)==sha and(size is None or len(b)==size)
 return b
def methods():
 observer.methods()
 m=json.loads((ROOT/'scripts/pll-feedback-event-review-methods.json').read_text())
 for p,s in m['protected'].items():assert file_sha(ROOT/p)==s,p
 return m
def summary_valid(s):
 assert s['status']=='PASS_EXACT_FEEDBACK_DIAGNOSIS_ORIGINAL_ACQUISITION_REMAINS_REJECTED'
 assert s['source_head']==SOURCE_HEAD and int(s['run_id'])==40084454916
 assert s['full_capture']and s['original_reproduction']==dict(original_rejection_reproduced=True,original_cache_bits_identical=True,full5106_column_capture_verified=True,acquisition_accepted=False)
 assert not any(s[k]for k in ('native_activation_performed','acquisition_accepted','full_phy_accepted','full_device_safety_accepted','qualified_pex'))
 c=s['selected_cache']
 assert c['rows']==3201410 and len(c['columns'])==80 and len(set(c['columns']))==80
 assert c['columns'][0]=='time'and c['bytes']==2048902400 and c['sha256']==CACHE_SHA
 assert c['all_sample_bits_checked']and c['samples_removed']==0 and not c['resampled']
 assert c['format']=='row-major little-endian binary64 without header'and c['readonly']
 assert s['diagnosis_sha256']==DIAG_SHA and s['diagnostic_counts']==dict(differential_pairs=25,single_ended=29,feedback_cycles=100)
def manifest_valid(m):
 assert m['format']=='ordered-tar-gzip-parts-v1'and m['stem']=='pll-feedback-cycle-diagnosis-40084454916-1'
 assert m['bytes']==1800659552 and m['sha256']=='5dcbdc1c05c662de4ff5bcf4dab918904b95da584101f08b66b9bb2c39457f01'
 expected=[
 ('pll-feedback-cycle-diagnosis-40084454916-1.tar.gz.part0000',1073741824,'6d36cc48353cabe40d36ce8a442556fe1d279693572521b55c41dccbb28eb31c'),
 ('pll-feedback-cycle-diagnosis-40084454916-1.tar.gz.part0001',726917728,'4b6079a45c6090b6fb1aa7d4ecfd059f64fe1cdb43b5e0661fbf83d48e4c9308')]
 assert len(m['parts'])==2
 for i,(r,e)in enumerate(zip(m['parts'],expected,strict=True)):
  assert r['index']==i and(r['name'],r['bytes'],r['sha256'])==e
 assert m['verification']==dict(parts=2,bytes=m['bytes'],sha256=m['sha256'],all_parts_and_combined_bytes_verified=True)
def restore(work,s,m):
 run=api('actions/runs/40084454916')
 assert run['status']=='completed'and run['conclusion']=='success'and run['run_attempt']==1
 assert run['head_sha']==SOURCE_HEAD and run['head_branch']=='codex/pll-feedback-cycle-diagnosis'
 assert run['path']=='.github/workflows/pll-feedback-cycle-diagnosis-cloud.yml'
 assert shutil.disk_usage(work).free>=6*1024**3
 rel=api('releases/tags/cloud-results-40084454916-1-pll-feedback-cycle-diagnosis')
 byname={a['name']:a for a in rel['assets']};assert len(byname)==len(rel['assets'])
 archive=work/'source.tar.gz';combined=hashlib.sha256();total=0
 with archive.open('xb')as out:
  for part in m['parts']:
   a=byname[part['name']];assert a['size']==part['bytes']
   p=subprocess.Popen(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'],stdout=subprocess.PIPE)
   h=hashlib.sha256();n=0
   try:
    for b in iter(lambda:p.stdout.read(1048576),b''):
     n+=len(b);assert n<=part['bytes'];h.update(b);combined.update(b);out.write(b)
   finally:p.stdout.close()
   assert p.wait()==0 and n==part['bytes']and h.hexdigest()==part['sha256']
   total+=n;print('Verified original cloud part',part['index'],n,flush=True)
 assert total==m['bytes']and combined.hexdigest()==m['sha256']and file_sha(archive)==m['sha256']
 wanted={'selected-native.bin':2048902400,'selected-native.json':100000,'feedback-diagnosis.json':20000000,'original-review.json':20000000}
 found={}
 with tarfile.open(archive,mode='r|gz')as tar:
  for member in tar:
   name=Path(member.name).name
   if name not in wanted:continue
   assert name not in found and member.isfile()and member.size<=wanted[name]
   assert len(Path(member.name).parts)<=2 and '..'not in Path(member.name).parts and not Path(member.name).is_absolute()
   target=work/name
   with tar.extractfile(member)as inp,target.open('xb')as out:shutil.copyfileobj(inp,out,1048576)
   assert target.stat().st_size==member.size;found[name]=target
 assert set(found)==set(wanted)
 assert found['selected-native.bin'].stat().st_size==2048902400 and file_sha(found['selected-native.bin'])==CACHE_SHA
 assert json.loads(found['selected-native.json'].read_text())==s['selected_cache']
 assert file_sha(found['feedback-diagnosis.json'])==DIAG_SHA
 old=json.loads(small(671784463,OLD_SHA))
 proof=observer.reproduce(json.loads(found['original-review.json'].read_text()),old)
 return found,dict(source_run=40084454916,source_head=SOURCE_HEAD,summary_sha256=SUMMARY_SHA,parts_sha256=PARTS_SHA,
  combined_archive_sha256=m['sha256'],selected_cache_sha256=CACHE_SHA,original_reproduction=proof,
  native_started=False,original_archives_preserved=True)
def relation(clock,up,down):
 clock=np.asarray(clock,dtype=float);up=np.asarray(up,dtype=float);down=np.asarray(down,dtype=float)
 assert len(clock)>=2 and np.isfinite(clock).all()and np.all(np.diff(clock)>0)
 for e in (up,down):assert np.isfinite(e).all()and np.all(np.diff(e)>0)
 counts=np.diff(np.searchsorted(up,clock,side='left'))+np.diff(np.searchsorted(down,clock,side='left'))
 return [dict(interval_s=[float(a),float(b)],output_rises=int(np.searchsorted(up,b,'left')-np.searchsorted(up,a,'left')),
              output_falls=int(np.searchsorted(down,b,'left')-np.searchsorted(down,a,'left')),output_transitions=int(n))
         for a,b,n in zip(clock[:-1],clock[1:],counts,strict=True)]
def bounded_signal(t,y,a,b):
 assert t[0]<=a<b<=t[-1]
 lo,hi=np.searchsorted(t,[a,b])
 def at(x,i):
  if i<len(t)and t[i]==x:return float(y[i])
  assert 0<i<len(t);return float(np.interp(x,t[i-1:i+1],y[i-1:i+1]))
 grid=np.concatenate(([a],t[lo:hi],[b]));v=np.concatenate(([at(a,lo)],y[lo:hi],[at(b,hi)]))
 return dict(interval_s=[a,b],native_sample_count=int(hi-lo),minimum=float(v.min()),maximum=float(v.max()),time_mean=float(np.trapezoid(v,grid)/(b-a)))
def analyze(found,s):
 c=s['selected_cache'];raw=np.memmap(found['selected-native.bin'],dtype='<f8',mode='r',shape=(c['rows'],len(c['columns'])))
 data={n:raw[:,i]for i,n in enumerate(c['columns'])};t=np.array(data['time'],copy=True)
 assert np.array_equal(t.view('<u8'),data['time'].view('<u8'))and np.isfinite(t).all()and np.all(np.diff(t)>0)
 original=json.loads(found['feedback-diagnosis.json'].read_text())
 mapping=json.loads((ROOT/observer.MAP).read_text())
 pairs={r['name']:r for r in mapping['differential_pairs']}
 result=dict(scope='Read-only correlation; all events retained. No fitted threshold, phase correction, sample pruning, loop retune or acceptance override.',
  full_capture_rows=len(t),start_s=float(t[0]),end_s=float(t[-1]),stage_correlations={},boundary={},per_feedback_cycles=[])
 chain=[
 ('vco_public','div1_first_conditioned',1),
 ('div1_first_conditioned','div1_first_master',2),
 ('div1_first_master','div1_first_div2',1),
 ('div1_first_conditioned','div1_first_div2',2),
 ('div1_first_div2','div1_interstage_limiter',1),
 ('div1_interstage_limiter','div1_second_conditioned',1),
 ('div1_second_conditioned','div1_second_master',2),
 ('div1_second_master','div1_div4_producer',1),
 ('div1_second_conditioned','div1_div4_producer',2),
 ('div1_div4_producer','gain_follower_producer',1),
 ('gain_follower_producer','div2_input_sink',1),
 ('div2_input_sink','div2_first_conditioned',1),
 ('div2_first_conditioned','div2_first_master',2),
 ('div2_first_master','div2_first_div2',1),
 ('div2_first_conditioned','div2_first_div2',2),
 ('div2_first_div2','div2_interstage_limiter',1),
 ('div2_interstage_limiter','div2_second_conditioned',1),
 ('div2_second_conditioned','div2_second_master',2),
 ('div2_second_master','div2_div4_producer',1),
 ('div2_second_conditioned','div2_div4_producer',2)]
 # Existing native event lists are digest-bound; do not replace or recompute their thresholds.
 for src,dst,ratio in chain:
  si=original['differential'][src];so=original['differential'][dst]
  pair=pairs[dst];y=data[pair['p_vector']]-data[pair['n_vector']]
  down={'zero':observer.crossing(t,-y),'hysteresis_10mV':observer.hysteresis(t,-y,.01),'hysteresis_50mV':observer.hysteresis(t,-y,.05)}
  table={}
  for key in ('zero','hysteresis_10mV','hysteresis_50mV'):
   rows=relation(si['rising_edges_s'][key],so['rising_edges_s'][key],down[key])
   expected=2//ratio
   distributions={}
   for window,(a,b)in {'full':(float(t[0]),float(t[-1])),'last200ns':(800e-9,1e-6)}.items():
    rr=[r for r in rows if a<=r['interval_s'][0]and r['interval_s'][1]<=b]
    hist={str(n):sum(r['output_transitions']==n for r in rr)for n in sorted({r['output_transitions']for r in rr})}
    anomalies=[r for r in rr if r['output_transitions']!=expected]
    distributions[window]=dict(complete_input_intervals=len(rr),transition_count_histogram=hist,
      expected_only_for_ideal_division=expected,anomalous_intervals=anomalies)
   table[key]=distributions
  result['stage_correlations'][src+' -> '+dst]=table
 # Persist all 25 differential and 29 single-ended original per-FB cycle records compactly.
 for i,(a,b)in enumerate(zip(original['original_feedback_edges_s'][:-1],original['original_feedback_edges_s'][1:])):
  result['per_feedback_cycles'].append(dict(ordinal=i,interval_s=[a,b],
   differential={k:{q:r['cycles'][i][q]for q in ('minimum_v','maximum_v','mean_v','rising_counts')}for k,r in original['differential'].items()},
   single_ended={k:{q:r['cycles'][i][q]for q in ('minimum_v','maximum_v','mean_v','rising_counts')}for k,r in original['single_ended'].items()}))
 pair=pairs['div1_first_div2'];p=data[pair['p_vector']];n=data[pair['n_vector']]
 for label,(a,b)in {'full':(float(t[0]),float(t[-1])),'post100ns':(100e-9,1e-6),'last200ns':(800e-9,1e-6)}.items():
  result['boundary'][label]={key:bounded_signal(t,y,a,b)for key,y in {'p':p,'n':n,'common_mode':(p+n)/2,'differential':p-n}.items()}
 result['boundary']['nominal_fixture_is_not_actual_PLL']=True
 result['diagnostic_ideal_division_counts_are_not_acceptance_gates']=True
 result['acquisition_accepted']=False;result['full_phy_accepted']=False
 return result
def controls():
 import copy
 methods();faults=[]
 def reject(name,fn):
  try:fn()
  except (AssertionError,KeyError,ValueError):faults.append(name)
  else:raise AssertionError('Accepted '+name)
 s=json.loads(small(672131330,SUMMARY_SHA,288016));summary_valid(s)
 m=json.loads(small(672131430,PARTS_SHA,1093));manifest_valid(m)
 for name,fn in [
 ('changed_cache_hash',lambda q:q['selected_cache'].__setitem__('sha256','0'*64)),
 ('removed_rows',lambda q:q['selected_cache'].__setitem__('rows',3201409)),
 ('changed_native_source',lambda q:q.__setitem__('source_head','0'*40)),
 ('accepted_PLL',lambda q:q.__setitem__('acquisition_accepted',True)),
 ('resampled_cache',lambda q:q['selected_cache'].__setitem__('resampled',True)),
 ('weakened_original_failure',lambda q:q['original_reproduction'].__setitem__('original_rejection_reproduced',False))]:
  bad=copy.deepcopy(s);fn(bad);reject(name,lambda:summary_valid(bad))
 for name,fn in [('swapped_parts',lambda q:q['parts'].reverse()),('changed_part_bytes',lambda q:q['parts'][0].__setitem__('bytes',1)),('missing_part',lambda q:q['parts'].pop())]:
  bad=copy.deepcopy(m);fn(bad);reject(name,lambda:manifest_valid(bad))
 clock=np.array([0.,1.,2.,3.]);rr=relation(clock,[.25,2.25],[1.25])
 assert [r['output_transitions']for r in rr]==[1,1,1]
 rr=relation(clock,[.25,.75,2.25],[.5,1.25])
 assert [r['output_transitions']for r in rr]==[3,1,1]
 rr=relation(clock,[0.,1.,3.],[2.])
 assert [(r['output_rises'],r['output_falls'])for r in rr]==[(1,0),(1,0),(0,1)]
 assert [r['output_transitions']for r in relation(clock,[.25],[2.25])]==[1,0,1]
 reject('unordered_clock',lambda:relation([0.,2.,1.],[.2],[]))
 reject('duplicate_output_edge',lambda:relation(clock,[.2,.2],[]))
 reject('nonfinite_output_edge',lambda:relation(clock,[float('nan')],[]))
 t=np.arange(8,dtype=float);back=np.zeros((8,3));back[:,2]=2*t+1
 for a,b in [(.25,6.75),(0.,7.)]:
  q=bounded_signal(t,back[:,2],a,b);assert q['minimum']==2*a+1 and q['maximum']==2*b+1 and q['time_mean']==a+b+1
 reject('reversed_voltage_window',lambda:bounded_signal(t,back[:,2],4.,2.))
 return dict(rejected=faults,count=len(faults),all_edges_and_boundary_edges_retained=True,analytic_pulse_and_strided_time_mean_checks=True,native_started=False)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true','Cloud only'
 OUT.mkdir(exist_ok=False);report=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation_performed=False,acquisition_accepted=False,full_phy_accepted=False)
 try:
  report['method']=methods();report['controls']=controls()
  if sys.argv[1:]==['--controls']:report['status']='PASS_EVENT_REVIEW_CONTROLS_NOT_CIRCUIT_ACCEPTANCE';return
  assert sys.argv[1:]==['--review']
  s=json.loads(small(672131330,SUMMARY_SHA,288016));summary_valid(s)
  m=json.loads(small(672131430,PARTS_SHA,1093));manifest_valid(m)
  with tempfile.TemporaryDirectory(prefix='pll-existing-cache-',dir=os.environ.get('RUNNER_TEMP'))as temp:
   found,proof=restore(Path(temp),s,m);report['restored_original_evidence']=proof
   analysis=analyze(found,s);target=OUT/'event-diagnosis.json';target.write_text(json.dumps(analysis,indent=2)+'\n')
   report['analysis_sha256']=file_sha(target);report['analysis_file']=target.name
   report['boundary']=analysis['boundary']
   report['stage_transition_histograms']={k:{threshold:{window:{q:v[q]for q in ('complete_input_intervals','transition_count_histogram','expected_only_for_ideal_division')}for window,v in x.items()}for threshold,x in values.items()}for k,values in analysis['stage_correlations'].items()}
   report['per_feedback_cycles']=analysis['per_feedback_cycles']
  methods();report['status']='PASS_EXISTING_NATIVE_EVENT_DIAGNOSIS_ORIGINAL_PLL_STILL_REJECTED'
 except BaseException as error:
  report.update(status='FAIL_EVENT_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
 finally:
  (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)
if __name__=='__main__':main()
