# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Post-completion raw comparison. Descriptive metrics never alter acceptance."""
from pathlib import Path
import gzip,hashlib,json,os,resource
import numpy as np
os.sched_setaffinity(0,{10});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();B=Path(__file__).resolve().parent
OLD=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-wire-06-01')
NEW=Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-halfstep-06-01')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def crossings(t,v):
 ans=[]
 for i in range(1,len(t)):
  if v[i-1]<0<=v[i]:
   ans.append(dict(time_s=float(t[i-1]+(t[i]-t[i-1])*(0-v[i-1])/(v[i]-v[i-1])),rows=[i-1,i],times_s=[float(t[i-1]),float(t[i])],volts=[float(v[i-1]),float(v[i])]))
 return ans
controller=json.loads((B/'native06-controller.json').read_text());assert controller['status']=='CLOSED_FINITE_NATIVE_RESULT'
owner=json.loads((NEW/'owned-processes.json').read_text());assert all(p['status']=='REAPED_NO_LIVE_MEMBERS'for p in owner['processes'])
for p,v in json.loads((B/'source-freeze01.json').read_text())['pins'].items():assert pin(p)==v
assert pin(OLD/'result.json')==dict(bytes=426335,sha256='04f18138303887b2755c09b08afb47c2c5e6c830a40c810578f069f6ecfc2ab7')
results=[]
for root,step in [(OLD,5e-12),(NEW,2.5e-12)]:
 r=json.loads((root/'result.json').read_text());assert r['status']in('PASS_NATIVE_LOADED_FEEDBACK_SCREEN','FAIL_NATIVE_LOADED_FEEDBACK_SCREEN')
 assert len(r['devices'])==455 and r['config']['step_s']==step and r['config']['stop_s']==34e-9 and r['config']['window_s']==[4e-9,34e-9]
 for p,v in r['inputs'].items():assert pin(p)==v
 for p,v in r['outputs'].items():assert pin(root/p)==v
 raw=gzip.decompress((root/'wave.raw.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256']
 header,payload=raw.split(b'Binary:\n',1);names=[s.decode().split()[1]for s in header.split(b'Variables:\n')[1].splitlines()];assert len(names)==957 and len(set(names))==957
 size=r['rows']*957*8;assert payload[size:]==str(r['rows']).encode();assert hashlib.sha256(payload[:size]).hexdigest()==r['payload_sha256']
 a=np.frombuffer(payload[:size],'<f8').reshape(r['rows'],957);assert np.isfinite(a).all();d=dict(zip(names,a.T));t=d['time'];assert np.all(np.diff(t)>0)and t[-1]==34e-9
 ce=[e for e in crossings(t,d['v(qp)']-d['v(qn)'])if 4e-9<=e['time_s']<34e-9]
 ve=[e for e in crossings(t,d['v(clkp)']-d['v(clkn)'])if 4e-9<=e['time_s']<34e-9]
 ct=np.array([e['time_s']for e in ce]);vt=np.array([e['time_s']for e in ve]);assert ct.tolist()==r['measurement']['edge_times']['cml']
 counts=[int(sum(x<=e<y for e in vt))for x,y in zip(ct[:-1],ct[1:])];assert counts==r['measurement']['actual_vco_period_counts']['native_hbt_div4']
 first=int(np.argmin(abs(vt-ct[0])));nearest=[int(np.argmin(abs(vt-e)))for e in ct];rows=[]
 for i,e in enumerate(ct):
  fixed=first+4*i;z=dict(cml_index=i,cml_edge=ce[i],nearest_vco_index=nearest[i],nearest_vco_edge=ve[nearest[i]],nearest_phase_ps=float((e-vt[nearest[i]])*1e12),fixed_vco_index=fixed)
  if fixed<len(vt):z['fixed_phase_ps']=float((e-vt[fixed])*1e12)
  if i<len(counts):
   z.update(bucket_count=counts[i],cml_period_ps=float((ct[i+1]-e)*1e12),nearest_ordinal_advance=nearest[i+1]-nearest[i])
   if fixed+4<len(vt):z['fixed_four_vco_period_ps']=float((vt[fixed+4]-vt[fixed])*1e12)
  rows.append(z)
 results.append(dict(step_s=step,native_status=r['status'],source_inputs={str(root/p):pin(root/p)for p in ['result.json','wave.raw.gz']},full_values=int(a.size),electrical_pass=r['safety']['passed'],unchanged_all_checks=r['measurement']['checks'],cml_edges=len(ce),vco_edges=len(ve),bucket_counts=counts,bad_bucket_indices=[i for i,v in enumerate(counts)if v!=4],nearest_ordinal_advances=[b-a for a,b in zip(nearest[:-1],nearest[1:])],cml_boundaries=rows))
 del raw,payload,a,d
# This is numerical evidence, not an alternative pass predicate.
summary=dict(status='SAVED_COMPLETE_34NS_STEP_COMPARISON_ORIGINAL_VERDICTS_RETAINED',method=pin(__file__),source_freeze=pin(B/'source-freeze01.json'),captures=results,all_acceptance_unchanged=True,scope='Exact complete34ns native records. Original455 safety and strict half-open count flags preserved. Fixed-ordinal tracking, phase and CML/four-VCO periods are descriptive convergence diagnostics; neither counts nor thresholds nor windows are shifted. A pass of either run alone is not pairwise numerical, PVT, extended-time, PLL, or fullPHY qualification.')
(B/'step-comparison01.json').write_text(json.dumps(summary,indent=2)+'\n')
print([(x['step_s'],x['native_status'],x['bad_bucket_indices'])for x in results])
