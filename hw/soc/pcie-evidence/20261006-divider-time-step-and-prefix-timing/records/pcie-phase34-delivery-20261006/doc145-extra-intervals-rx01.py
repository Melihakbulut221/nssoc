# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved raw recount of every reported edge interval; no native."""
import os,resource,hashlib,gzip,json,re
from pathlib import Path
os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
import numpy as np
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent
pin=lambda p:dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest())
records=[];inputs={}
for name,peername in [('wire','wave'),('halfstep','halfstep-wave'),('quarterstep','quarterstep-wave')]:
 n=Path('/dev/shm')/f'nssoc-vco-v6-divider-tail115-v1-{name}-06-01';peerpath=R/f'hw/soc/out/pcie-tail115-{peername}-peer-rx-20261006/result.json';peer=json.loads(peerpath.read_text())
 assert peer['findings']==[]
 for p in [peerpath,n/'result.json',n/'wave.raw.gz']:
  inputs[str(p)]=pin(p)
  if p!=peerpath:assert inputs[str(p)]==peer['inputs'][str(p)]
 r=json.loads((n/'result.json').read_text());raw=gzip.decompress((n/'wave.raw.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256'];header,payload=raw.split(b'Binary:\n',1)
 names=[line.decode().split()[1]for line in header.split(b'Variables:\n')[1].splitlines()];assert len(names)==957
 a=np.frombuffer(payload[:r['rows']*957*8],dtype='<f8').reshape(r['rows'],957);col={k:a[:,i]for i,k in enumerate(names)};t=col['time'];left,right=r['config']['window_s']
 def cross(x,level):
  values=[]
  for i in np.flatnonzero((x[:-1]<level)&(x[1:]>=level)):
   i=int(i);when=float(t[i])+(float(t[i+1])-float(t[i]))*(level-float(x[i]))/(float(x[i+1])-float(x[i]))
   if left<=when<right:values.append(when)
  return values
 edge={'cml':cross(col['v(qp)']-col['v(qn)'],0),'feedback':cross(col['v(fb)'],1.25)}
 for label,node in [('received','clk'),('fast0','f0'),('fast1','f1'),('count','count')]:edge[label]=cross(col[f'v(xchain.xfb.{node})'],.6)
 for label,e in edge.items():assert e==r['measurement']['edge_times'][label],label
 osc=cross(col['v(clkp)']-col['v(clkn)'],0)
 bucket=lambda fast,slow:[sum(lo<=x<hi for x in fast)for lo,hi in zip(slow[:-1],slow[1:])]
 actual={key:bucket(osc,edge[e])for key,e in [('native_hbt_div4','cml'),('whole_native_div80','feedback')]};assert actual==r['measurement']['actual_vco_period_counts']and actual['whole_native_div80']==[80,80]
 ratios={fast+'_'+slow:bucket(edge[fast],edge[slow])for fast,slow in [('cml','received'),('received','fast0'),('fast0','fast1'),('fast1','count'),('count','feedback'),('received','feedback')]}
 assert ratios==r['measurement']['edge_ratios']
 records.append(dict(capture=name,status=r['status'],edge_counts={k:len(v)for k,v in edge.items()},actual_vco_period_counts=actual,all_six_intermediate_stage_ratios=ratios))
 del raw,payload,a,col,t
record=dict(status='PASS_INDEPENDENT_SAVED_ALL_REPORTED_INTERVALS_NO_VERDICT_CHANGE',findings=[],inputs=inputs,method=pin(Path(__file__)),captures=records,scope='Pure full saved raw hash/read and independent linear crossing plus half-open interval arithmetic. No native or producer import; firsttwo FAIL and quarter finitePASS unchanged. Complements earlier all-value/64HBT/nativebinding peers.')
with(B/'doc145-extra-intervals-rx01.json').open('x')as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(result=pin(B/'doc145-extra-intervals-rx01.json'),captures=3,whole_div80_counts=[r['actual_vco_period_counts']['whole_native_div80']for r in records])))
