# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Saved terminal feedback and physical wire loading; no native simulation."""
from pathlib import Path
import collections,gzip,hashlib,heapq,json,os,resource
import numpy as np
os.sched_setaffinity(0,{10});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();B=Path(__file__).resolve().parent;F=R/'sw/tests/fixtures/pcie_clock_div4_v9_bias8_v1_hybrid_v1';N=Path('/dev/shm/nssoc-vco-v6-divider-bias8-v1-wire-06-01')
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
r=json.loads((N/'result.json').read_text());assert r['status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'
raw=gzip.decompress((N/'wave.raw.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256'];header,payload=raw.split(b'Binary:\n',1);names=[l.decode().split()[1]for l in header.split(b'Variables:\n')[1].splitlines()];assert len(names)==957
size=r['rows']*957*8;assert payload[size:]==str(r['rows']).encode();a=np.frombuffer(payload[:size],'<f8').reshape(r['rows'],957);assert np.isfinite(a).all();d=dict(zip(names,a.T));t=d['time']
c=json.loads((F/'composition.json').read_text());b=json.loads((F/'source-native-bijection.json').read_text());records={v['native_id']:v for v in c['records']};dev={v['source_name']:v for v in b['devices']}
for p in [F/'composition.json',F/'source-native-bijection.json',F/'hybrid-open.spice']:assert pin(p)==r['inputs'][str(p)]
def node(name,term):
 z=dev[name];i=z['terminal_order'].index(term);return records[z['native_id']]['terminals'][i]['node']
def volt(n):return d['v(xchain.xdiv.'+n.lower()+')']
def ic(name):return d[f'i(@q.xchain.xdiv.xd{dev[name]["native_id"]:04d}.qnpn13g2[ic])']
res=[];caps=[];adj=collections.defaultdict(list)
for line in (F/'hybrid-open.spice').read_text().splitlines():
 f=line.split()
 if not f:continue
 if f[0].startswith('R'):
  assert len(f)==4;val=float(f[3]);res.append((f[0],f[1],f[2],val));adj[f[1]].append((f[2],val));adj[f[2]].append((f[1],val))
 elif f[0].startswith('C'):
  assert len(f)==4;caps.append((f[0],f[1],f[2],float(f[3])))
assert len(res)==382 and len(caps)==649
components=[];index={}
for n in adj:
 if n in index:continue
 i=len(components);pending=[n];nodes=set()
 while pending:
  x=pending.pop()
  if x in nodes:continue
  nodes.add(x);index[x]=i;pending.extend(y for y,_ in adj[x]if y not in nodes)
 components.append(nodes)
assert len(components)==37

def wire_pair(p,n):
 assert index[p]==index[n]
 dist={p:0.};queue=[(0.,p)]
 while queue:
  cost,x=heapq.heappop(queue)
  if cost!=dist[x]:continue
  for y,v in adj[x]:
   if cost+v<dist.get(y,float('inf')):dist[y]=cost+v;heapq.heappush(queue,(cost+v,y))
 comp=components[index[p]];edges=[v for _,a,b,v in res if a in comp and b in comp]
 assert len(edges)==len(comp)-1,'Shortest sum is actual path resistance only for tree'
 ground=sum(v for _,a,b,v in caps if (a in comp and b=='WIRE_CREF')or(b in comp and a=='WIRE_CREF'))
 mutual=sum(v for _,a,b,v in caps if (a in comp)!=(b in comp) and 'WIRE_CREF'not in (a,b))
 return {'nodes':[p,n],'path_ohm':dist[n],'component':index[p],'ground_C_F':ground,'incident_mutual_C_F':mutual,'wire_tree_nodes':len(comp)}
loops=[];witnesses={}
for stage,prefix in [('FIRST','DIV__XFIRST__XCORE'),('SECOND','DIV__XSECOND')]:
 for side in ('XM','XS'):
  z=prefix+'__'+side
  # QP collector node drives positive regenerative base, QN the other base.
  pairs=[(node(z+'__XDN','C'),node(z+'__XLP','B')),(node(z+'__XDP','C'),node(z+'__XLN','B'))]
  source=volt(pairs[0][0])-volt(pairs[1][0]);feedback=volt(pairs[0][1])-volt(pairs[1][1])
  clock=volt(node(z+'__XCH','B'))-volt(node(z+'__XCS','B'))
  currenthold=ic(z+'__XCH');sample=ic(z+'__XCS');currentreg=ic(z+'__XLP')-ic(z+'__XLN')
  rows=[]
  for lo,hi in [(4,8),(12,16),(20,22),(22,23.5),(24,26),(30,34)]:
   mask=(t>=lo*1e-9)&(t<hi*1e-9);hold=mask&(currenthold>sample*4)
   rms=lambda x:float(np.sqrt(np.mean(x[mask]**2)))
   # B voltages are real distributed endpoint voltages, not ideal net aliases.
   rows.append({'window_ns':[lo,hi],'collector_rms_v':rms(source),'feedback_base_rms_v':rms(feedback),'feedback_attenuation':rms(feedback)/rms(source),
    'collector_feedback_zero_lag_correlation':float(np.corrcoef(source[mask],feedback[mask])[0,1]),'hold_fraction':float(hold.sum()/mask.sum()),
    'hold_tail_a':float((currenthold+sample)[hold].mean()),'hold_regen_differential_current_rms_a':float(np.sqrt(np.mean(currentreg[hold]**2))),
    'clock_diff_rms_v':rms(clock)})
  loops.append({'stage':stage,'latch':side,'source_names':[z+'__XDN.C',z+'__XDP.C',z+'__XLP.B',z+'__XLN.B'], 'wire_paths':[wire_pair(*p)for p in pairs],'windows':rows})
out={'status':'SAVED_BIAS8_REGENERATION_AND_WIRE_TREE_DIAGNOSIS','method':pin(Path(__file__)),'inputs':{str(p):pin(p)for p in [N/'result.json',N/'wave.raw.gz',F/'composition.json',F/'source-native-bijection.json',F/'hybrid-open.spice']},'loops':loops,'scope':'Actual distributed collector-to-regenerative-base voltage/current measurements, native wire tree path resistance and incident wire capacitances. Capacitance excludes intrinsic devices and is not effective driven AC capacitance; no small-signal stability proof. Full34ns failed acceptance retained; no simulation rerun.'}
(B/'regeneration-diagnosis06.json').write_text(json.dumps(out,indent=2)+'\n')
for loop in loops:
 print(loop['stage'],loop['latch'],'wire',loop['wire_paths'])
 for row in loop['windows']:print(row)
