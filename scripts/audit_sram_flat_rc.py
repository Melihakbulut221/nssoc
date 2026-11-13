# SPDX-License-Identifier: Apache-2.0
"""Flat CC/RC pair conservation and terminal connectivity, not physical PEX signoff.
Caller must supply the independently expected MOS count. Resistance collapse
uses iterative disjoint sets to support full macros without Python recursion.
"""
import collections, math, re
class Rejected(Exception):pass
def require(ok,message):
 if not ok:raise Rejected(message)
def scalar(s):
 m=re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)(meg|[tgkmunpf]?)',s.lower())
 require(m is not None,'unsupported passive value')
 value=float(m[1])*{'':1,'t':1e12,'g':1e9,'meg':1e6,'k':1e3,'m':1e-3,'u':1e-6,'n':1e-9,'p':1e-12,'f':1e-15}[m[2]]
 require(math.isfinite(value) and value>0,'nonpositive/nonfinite passive')
 return value
def parse(text):
 lines=[]
 for raw in text.splitlines():
  s=raw.strip()
  if not s or s.startswith('*'):continue
  if s.startswith('+'):
   require(bool(lines),'orphan continuation');lines[-1]+=' '+s[1:]
  else:lines.append(s)
 result=dict(mos={},R={},C={},ports=[]);names=set();sub=0
 for line in lines:
  t=line.lower().split();kind=t[0][0]
  if t[0]=='.subckt':
   sub+=1;result['ports']=t[2:];continue
  if t[0] in ['.ends','.end']:continue
  require(kind in ['r','c','m','x'],'unsupported SPICE statement '+t[0])
  require(t[0] not in names,'duplicate instance');names.add(t[0])
  if kind in ['r','c']:
   require(len(t)==4,'unsupported passive card shape');result[kind.upper()][t[0]]=(t[1],t[2],scalar(t[3]));continue
  params={};pos=[]
  for v in t[1:]:
   if '=' in v:
    k,val=v.split('=',1);require(k not in params,'duplicate device parameter');params[k]=val
   else:pos.append(v)
  require(len(pos)==5,'unsupported non-four-terminal MOS instance')
  result['mos'][t[0]]={'nodes':pos[:4],'model':pos[4],'params':params}
 require(sub==1,'requires one flat subcircuit')
 require(len(set(result['ports']))==len(result['ports']),'duplicate ports')
 return result
def audit(cc,rc,expected_mos):
 require(type(expected_mos) is int and expected_mos>0,"expected MOS count must be a positive integer")
 require(not cc['R'],'CC reference has resistors')
 require(cc['ports']==rc['ports'],'port order differs')
 require(set(cc['mos'])==set(rc['mos']) and len(cc['mos'])==expected_mos,'MOS identities or expected count differ')
 parent={};rank={}
 def find(n):
  parent.setdefault(n,n);rank.setdefault(n,0)
  root=n
  while parent[root]!=root:root=parent[root]
  while parent[n]!=n:
   nxt=parent[n];parent[n]=root;n=nxt
  return root
 def union(a,b):
  a,b=find(a),find(b)
  if a==b:return
  if rank[a]<rank[b]:a,b=b,a
  parent[b]=a
  if rank[a]==rank[b]:rank[a]+=1
 for a,b,v in rc['R'].values():union(a,b)
 mapping={};inverse=collections.defaultdict(set)
 def bind(n,ref):
  root=find(n);require(root not in mapping or mapping[root]==ref,'resistor short between reference nets')
  mapping[root]=ref;inverse[ref].add(root)
 for p in cc['ports']:bind(p,p)
 for name,a in cc['mos'].items():
  b=rc['mos'][name];require(a['model']==b['model'] and a['params']==b['params'],'device model/geometry changed')
  for n,ref in zip(b['nodes'],a['nodes']):bind(n,ref)
 require(all(len(roots)==1 for roots in inverse.values()),'reference net split across resistance components')
 missing_roots={find(n) for a,b,v in rc['C'].values() for n in [a,b]}-set(mapping)
 require(not missing_roots,'capacitor endpoint without port/device anchor')
 require(all(find(a) in mapping for a,b,v in rc['R'].values()),'unanchored resistor network')
 def caps(rows,mapper):
  pairs=collections.defaultdict(float);self_c=0
  for a,b,v in rows.values():
   a,b=mapper(a),mapper(b)
   if a==b:self_c+=1;continue
   pairs[tuple(sorted([a,b]))]+=v
  return pairs,self_c
 ref,_=caps(cc['C'],lambda x:x);got,self_c=caps(rc['C'],lambda x:mapping[find(x)])
 missing=set(ref)-set(got);extra=set(got)-set(ref)
 changed=[k for k in set(ref)&set(got) if abs(ref[k]-got[k])>1e-23+1e-5*abs(ref[k])]
 result=dict(mos=len(cc['mos']),rc_resistors=len(rc['R']),cc_capacitors=len(cc['C']),rc_capacitors=len(rc['C']),reference_pairs=len(ref),projected_pairs=len(got),missing_pairs=len(missing),extra_pairs=len(extra),changed_pairs=len(changed),reference_sum_f=sum(ref.values()),projected_sum_f=sum(got.values()),collapsed_intraconductor_capacitors=self_c,max_pair_difference_f=max([abs(ref.get(k,0)-got.get(k,0)) for k in set(ref)|set(got)],default=0))
 return result,not(missing or extra or changed)
