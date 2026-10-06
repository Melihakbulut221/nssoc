"""Read-only actual saved wave and exported resistor-network diagnosis."""
from pathlib import Path
import hashlib,json,gzip,os,resource,math
import numpy as np
os.sched_setaffinity(0,{10});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();B=Path(__file__).resolve().parent;L=R/'hw/soc/out/pcie-vco-v6-divider-power-v2-wire-v1-20261006';W=R/'hw/soc/out/pcie-divider-v7-power-v2-wire-v2-20261006';P=Path('/dev/shm/nssoc-vco-v6-divider-power-v2-wire-06-01');raw=Path('/dev/shm/nssoc-div4-v7-power-v2-wire-rc-01/wires.spice')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
paths=[P/'result.json',P/'wave.raw.gz',W/'anchors.json',W/'source-native-bijection.json',L/'composed01/composition.json',raw]
inputs={str(p):pin(p) for p in paths};result=json.loads(paths[0].read_text());anchors=json.loads(paths[2].read_text())['anchors'];binding=json.loads(paths[3].read_text());comp=json.loads(paths[4].read_text());rec={r['native_id']:r for r in comp['records']}
with gzip.open(paths[1],'rb') as f:
 header=[]
 while True:
  line=f.readline();assert line;header.append(line)
  if line==b'Binary:\n':break
 blob=f.read()
header=b''.join(header);assert hashlib.sha256(header+blob).hexdigest()==result['raw_sha256'];cols=[]
for line in header.decode().split('Variables:\n')[1].split('Binary:')[0].splitlines():
 i,name,unit=line.split();assert int(i)==len(cols);cols.append(name)
assert len(cols)==957;rows=result['rows'];assert blob[rows*len(cols)*8:]==str(rows).encode();a=np.frombuffer(blob[:rows*len(cols)*8],'<f8').reshape(rows,len(cols));assert np.isfinite(a).all();data=dict(zip(cols,a.T));t=data['time'];mask=(t>=4e-9)&(t<34e-9)
bylabel={a['label']:a for a in anchors};terms={}
for item in binding['devices']:
 for net,node in zip(item['source_nets'],rec[item['native_id']]['terminals']):
  if node['anchor'] is None:continue
  label=node['anchor'];term=dict(label=label,source=item['source_name'],terminal=node['terminal'],point_dbu=bylabel[label]['point_dbu'],wire_component=bylabel[label]['wire_component'])
  terms.setdefault(net,[]).append(term)
edges=[];adj={}
for line in raw.read_text().splitlines():
 f=line.split()
 if not f or not f[0].startswith('R'):continue
 _,x,y,v=f;v=float(v);assert v>0 and math.isfinite(v);edges.append((x,y,v));adj.setdefault(x,set()).add(y);adj.setdefault(y,set()).add(x)
reports=[]
for net,ts in terms.items():
 if len(ts)<2:continue
 seen,pending={ts[0]['label']},[ts[0]['label']]
 while pending:
  for n in adj[pending.pop()]:
   if n not in seen:seen.add(n);pending.append(n)
 assert {z['label'] for z in ts}<=seen
 ground=min(seen);nodes=sorted(seen-{ground});index={n:i for i,n in enumerate(nodes)};mat=np.zeros((len(nodes),len(nodes)))
 for x,y,r in edges:
  if x not in seen:continue
  assert y in seen
  for n in [x,y]:
   if n!=ground:mat[index[n],index[n]]+=1/r
  if ground not in [x,y]:mat[index[x],index[y]]-=1/r;mat[index[y],index[x]]-=1/r
 inv=np.linalg.solve(mat,np.eye(len(nodes)));assert np.max(np.abs(mat@inv-np.eye(len(nodes))))<1e-6
 def element(x,y):return 0 if ground in [x,y] else inv[index[x],index[y]]
 pairs=[]
 for i,x in enumerate(ts):
  for y in ts[i+1:]:
   xx,yy=x['label'],y['label'];res=float(element(xx,xx)+element(yy,yy)-2*element(xx,yy));dv=data['v(xchain.xdiv.w_'+xx.lower()+')'][mask]-data['v(xchain.xdiv.w_'+yy.lower()+')'][mask]
   pairs.append(dict(a=x,b=y,effective_R_ohm=res,max_abs_voltage_difference=float(np.max(np.abs(dv))),mean_difference=float(np.mean(dv))))
 reports.append(dict(logical_net=net,terminals=ts,maximum_R_pair=max(pairs,key=lambda x:x['effective_R_ohm']),maximum_wave_drop_pair=max(pairs,key=lambda x:x['max_abs_voltage_difference']),all_pairs=pairs))
reports.sort(key=lambda x:x['maximum_wave_drop_pair']['max_abs_voltage_difference'],reverse=True)
out=dict(status='DESCRIPTIVE_SAVED_SIGNAL_CONDUCTOR_DIAGNOSIS',inputs=inputs,method=pin(__file__),raw_sha256=result['raw_sha256'],native_status=result['status'],native_unchanged=True,rows=rows,columns=len(cols),all_resistors=len(edges),nets=reports,scope='Actual saved terminal voltage differences and one-amp effective-resistance mathematical solves on actual multigraph; no new simulation, waveform threshold changes, RF prediction, or physical acceptance.')
assert inputs=={p:pin(p) for p in inputs};dest=B/'saved-signal-paths.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n')
for r in reports:
 if r['logical_net'] in ['DIV_AVDD','AVSS','SUB']:continue
 z=r['maximum_wave_drop_pair'];print(r['logical_net'],round(z['max_abs_voltage_difference']*1000,3),'mV',round(z['effective_R_ohm'],3),'ohm',z['a']['source']+':'+z['a']['terminal'],z['b']['source']+':'+z['b']['terminal'])
print(pin(dest))
