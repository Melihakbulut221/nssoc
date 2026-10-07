# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full saved-byte replay plus independently summed current integrals."""
import pathlib,sys,json,gzip,hashlib,math,resource
import numpy as np
B=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(B));import characterize_pump13_02 as m
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
campaign=json.loads((B/'campaign01.json').read_text());assert campaign['status']=='CLOSED_TWELVE_PUMP13_DIAGNOSTICS_NOT_LOADED_FORCE_ACCEPTANCE' and campaign['all_twelve_cases_passed']
rows=[];maximum_error=0.
for point in campaign['points']:
 p=pathlib.Path(point['result_path']);assert m.pin(p)==point['result_pin'];r=json.loads(p.read_text());out=p.parent
 for name,v in r['outputs'].items():assert m.pin(out/name)==v,name
 for name,v in r['inputs'].items():assert m.pin(name)==v,name
 raw=gzip.decompress((out/'wave.raw.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256'] and len(raw)==r['raw_bytes']
 offset=raw.index(b'Binary:\n')+len(b'Binary:\n');nbytes=r['rows']*28*8
 payload=raw[offset:offset+nbytes];assert raw[offset+nbytes:]==str(r['rows']).encode();assert hashlib.sha256(payload).hexdigest()==r['payload_sha256']
 a=np.frombuffer(payload,'<f8').reshape(r['rows'],28);assert np.isfinite(a).all() and np.all(np.diff(a[:,0])>0)
 meter=m.Meter(r['columns'],r['devices'],r['config']);meter.push(a);safety,data,grid=meter.finish();assert safety==r['safety'];assert len(safety['all_device_bounds'])==13 and safety['passed']
 means=[]
 for window in r['measurement']['windows']:
  lo,hi=window['interval_s'];inside=(a[:,0]>lo)&(a[:,0]<hi);times=np.r_[lo,a[inside,0],hi]
  result={}
  for name,current in window['currents'].items():
   col=r['columns'].index(name);values=np.r_[np.interp(lo,a[:,0],a[:,col]),a[inside,col],np.interp(hi,a[:,0],a[:,col])]
   integral=math.fsum(float((y0+y1)*.5*(t1-t0)) for t0,t1,y0,y1 in zip(times[:-1],times[1:],values[:-1],values[1:]))
   mean=integral/(hi-lo);error=abs(mean-current['mean_a']);maximum_error=max(maximum_error,error)
   assert error<=1e-15,'Summation-rounding guard only, no physical criterion change';result[name]=mean
  means.append(dict(interval_s=[lo,hi],mean_current_a=result))
 rows.append(dict(case=point['case'],result_pin=m.pin(p),native_rows=r['rows'],safety_records=13,current_windows=means))
result=dict(status='PASS_ALL_TWELVE_SAVED_RAW_REPLAYS_AND_CURRENT_INTEGRALS',reviewer='root',external_independent_review=False,rows=rows,total_native_rows=sum(r['native_rows']for r in rows),all_sample_safety_formula_replay=True,independent_math_fsum_integrals=240,maximum_mean_current_rounding_difference_a=maximum_error,matched570_boundary_proven=False,loaded_force_accepted=False,loop_polarity_selected=False,pll_lock_accepted=False)
(B/'closed-review.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['total_native_rows'],maximum_error)
