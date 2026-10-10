# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual mapped critical enable branch; never run native or rewrite reports."""
from pathlib import Path
import json,re,hashlib,collections
B=Path(__file__).resolve().parent
raw=Path('/dev/shm/nssoc-integrity-v23-balanced-sta-01/rx/repaired.v').read_text()
cells={};drivers={};users=collections.defaultdict(list)
for typ,name,body in re.findall(r'\b(sg13g2_\w+)\s+(\S+)\s*\((.*?)\);',raw,re.S):
 c={p:re.sub(r'\s+','',v).lstrip('\\') for p,v in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)};cells[name]={'type':typ,'pins':c}
 for p,w in c.items():
  if p in ['X','Y','Q']:assert w not in drivers;drivers[w]=name
  else:users[w].append((name,p))
def root_buffer(w):
 seen=[]
 while w in drivers and cells[drivers[w]]['type'].startswith('sg13g2_buf_'):
  c=drivers[w];seen.append(c);w=cells[c]['pins']['A']
 return w,seen
def buffer_fanout(w):
 pending=[w];visited=set();leaf=[];buffers=[]
 while pending:
  n=pending.pop();assert n not in visited;visited.add(n)
  for c,p in users[n]:
   if cells[c]['type'].startswith('sg13g2_buf_'):
    buffers.append(c);pending.append(cells[c]['pins']['X'])
   else:leaf.append((c,p))
 return {'buffers':buffers,'leaf_loads':leaf}
selected=['_086723_','_087052_','_162326_','_162352_','_175190_'];data={n:cells[n] for n in selected}
for n in ['_162326_','_162352_']:
 for p,w in cells[n]['pins'].items():
  if p in ['X','Y','Q']:continue
  r,chain=root_buffer(w);data[n].setdefault('input_buffer_roots',{})[p]={'wire':r,'chain':chain,'driver':cells.get(drivers.get(r))}
f=root_buffer('net908')[0];assert f==root_buffer('net926')[0]=='_013724_'
fan=buffer_fanout(f);kinds=collections.Counter(cells[n]['type'] for n,p in fan['leaf_loads'])
p=lambda v:{'bytes':v.stat().st_size,'sha256':hashlib.sha256(v.read_bytes()).hexdigest()}
d={'status':'MEASURED_SHARED_VERDICT_ENABLE_BUFFER_FANOUT_DIAGNOSIS','inputs':{str(v):p(v) for v in [Path(__file__),Path('/dev/shm/nssoc-integrity-v23-balanced-sta-01/rx/repaired.v'),B/'slow-critical-path.txt']},'cells':data,'shared_enable_root':f,'buffer_count':len(fan['buffers']),'leaf_load_count':len(fan['leaf_loads']),'leaf_cell_types':dict(kinds),'buffer_tree':fan,'exact_endpoint_equation':'D = not((L or u) and not(d and L)); L = net908 = net926 through noninverting buffers, u=_080759_, d=net18324. Therefore binary D=L?d:!u; late measured signal participates in write/hold selection, not merely verdict data.','scope':'Read-only actual repaired netlist. Binary algebra only; no HDL equivalence or source mapping inferred. Remaining comparator/control feeds shared qualified write/hold network. Need independently verified source repair and same4ns native screen; timing still failed.'}
v=B/'measured-control-fanout01.json';assert not v.exists();v.write_text(json.dumps(d,indent=2)+'\n');print(d['buffer_count'],d['leaf_load_count'],dict(kinds),p(v))
