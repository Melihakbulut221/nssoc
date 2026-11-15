"""DC effective resistance of extracted passive conductors only."""
import math,hashlib
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from cdr_mos650_spice_syntax import statements,number,Union
def factor(edges,ref):
 nodes=sorted({n for a,b,r in edges for n in(a,b)}-{ref});ix={n:i for i,n in enumerate(nodes)}
 rr=[];cc=[];vv=[]
 for a,b,r in edges:
  assert math.isfinite(r) and r>0
  for n in(a,b):
   if n!=ref:rr.append(ix[n]);cc.append(ix[n]);vv.append(1/r)
  if a!=ref and b!=ref:rr.extend([ix[a],ix[b]]);cc.extend([ix[b],ix[a]]);vv.extend([-1/r,-1/r])
 matrix=coo_matrix((vv,(rr,cc)),shape=(len(nodes),len(nodes))).tocsc();solver=splu(matrix)
 def solve(sink):
  if sink==ref:return 0.
  rhs=np.zeros(len(nodes));rhs[ix[sink]]=1;v=solver.solve(rhs)
  assert float(np.max(np.abs(matrix@v-rhs)))<1e-7
  value=float(v[ix[sink]]);assert math.isfinite(value) and value>0
  return value
 return solve
def measure(text,anchors):
 parsed=statements(text);edges=[];union=Union()
 for row in parsed:
  if row[0].upper().startswith('R'):
   assert len(row)==4
   u,v=row[1:3];r=float(number(row[3]));assert u!=v and r>0
   edges.append((u,v,r));union.join(u,v)
 groups={}
 for edge in edges:groups.setdefault(union.find(edge[0]),[]).append(edge)
 physical={a['label']:a for a in anchors['anchors']};assert set(parsed[0][2:])==set(physical)
 result={}
 for device in (277,280,281,286,301,304,305,310):
  for terminal in ('C','E'):
   name='T%03d_%s'%(device,terminal)
   hits=[a for a in physical.values()if name==a['label']or name in a.get('logical_labels',[])]
   assert len(hits)==1,(name,len(hits))
   ref=hits[0]['label'];root=union.find(ref)
   sinks=sorted(n for n in physical if union.find(n)==root);assert len(sinks)>1
   solve=factor(groups[root],ref);result[name]=dict(reference=ref,resistance_ohm={n:solve(n)for n in sinks})
 return result
def compare(oldtext,oldanchors,newtext,newanchors):
 for edges,expected in [([('a','b',2.),('b','c',3.)],5.),([('a','c',2.),('a','c',2.)],1.)]:
  assert abs(factor(edges,'a')('c')-expected)<1e-12
 before=measure(oldtext,oldanchors);after=measure(newtext,newanchors);rows=[]
 for key in before:
  a,b=before[key],after[key]
  assert a['reference']==b['reference']and a['resistance_ohm'].keys()==b['resistance_ohm'].keys()
  for sink,old in a['resistance_ohm'].items():
   new=b['resistance_ohm'][sink]
   if old==0:assert new==0;continue
   rows.append(dict(terminal=key,reference=a['reference'],sink=sink,old_ohm=old,new_ohm=new,ratio=new/old))
 assert rows
 return dict(scope='Isolated passive metal DC effective resistance only; no intrinsic devices, capacitance, gate R or full PEX acceptance.',
 old_wire_sha256=hashlib.sha256(oldtext.encode()).hexdigest(),new_wire_sha256=hashlib.sha256(newtext.encode()).hexdigest(),
 before=before,after=after,comparisons=rows,minimum_ratio=min(x['ratio']for x in rows),maximum_ratio=max(x['ratio']for x in rows),
 analytic_series_parallel_controls_passed=True,full_phy_accepted=False)
