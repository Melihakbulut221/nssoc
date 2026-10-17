# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import collections,copy,hashlib,json,os,pathlib,re,sys,time,gzip
sys.setrecursionlimit(20000)
ROOT=pathlib.Path(os.environ.get('NSSOC_EQUIVALENCE_CAPTURE','/dev/shm/nssoc-tx-path-v4-repair05-equivalence'))
TOP='soc_pcie_gen3_tx_path_v4'
ALLOWED={'$_AND_','$_OR_','$_NOT_','$_XOR_','$_DFF_PP0_','$scopeinfo'}
def read(name):
 d=json.loads(gzip.decompress((ROOT/(name+'.json.gz')).read_bytes()))
 assert set(d['modules'])=={TOP},'Unexpected nonflattened modules'
 m=d['modules'][TOP]
 assert not int(m['attributes'].get('blackbox','0'),2)
 assert set(x['type'] for x in m['cells'].values())<=ALLOWED
 return m
class Intern:
 def __init__(self): self.table={}; self.nodes={}
 def get(self, key):
  if key not in self.table:
   n=len(self.table); self.table[key]=n; self.nodes[n]=key
  return self.table[key]
 def op(self,t,args):
  if t=='$_NOT_':
   a=args[0]; n=self.nodes[a]
   if n[0]=='$_NOT_':return n[1]
   if n[0]=='const': return self.get(('const',1-n[1]))
   return self.get((t,a))
  if t in ('$_AND_','$_OR_','$_XOR_'):
   flat=[]
   for a in args:
    n=self.nodes[a]
    flat.extend(n[1:] if n[0]==t else [a])
   args=flat
  if t in ('$_AND_','$_OR_'):
   args=list(set(args))
  args=tuple(sorted(args))
  if len(args)==1:return args[0]
  return self.get((t,*args))
def state_name(name):
 match=re.fullmatch(r'(\$flatten.*)\.\$auto\$liberty\.cc:242:create_ff\$[0-9]+',name)
 assert match,('unexpected native ff expansion name',name)
 return match[1]
class Circuit:
 def __init__(self,m,intern):
  self.m,self.i=m,intern
  assert all(c["type"] in ALLOWED for c in m["cells"].values())
  assert not any("init" in n.get("attributes",{}) for n in m["netnames"].values()), "Unexpected initial-state restriction"
  self.ff={state_name(k):v for k,v in m['cells'].items() if v['type']=='$_DFF_PP0_'}
  assert len(self.ff)==sum(v['type']=='$_DFF_PP0_' for v in m['cells'].values())
  self.driver={}; self.memo={'0':intern.get(('const',0)),'1':intern.get(('const',1))}; self.active=set()
  for p,v in sorted(m['ports'].items()):
   assert v['direction'] in ('input','output')
   if v['direction']=='input':
    for ix,b in enumerate(v['bits']):
     assert isinstance(b,int) and b not in self.driver
     self.driver[b]=('input',p,ix)
  for name,c in sorted(m['cells'].items()):
   if c['type']=='$scopeinfo':continue
   assert not c['parameters']
   expected={'$_DFF_PP0_':{'C':'input','D':'input','R':'input','Q':'output'},'$_NOT_':{'A':'input','Y':'output'}}.get(c['type'],{'A':'input','B':'input','Y':'output'})
   assert c['port_directions']==expected and set(c['connections'])==set(expected)
   assert all(len(x)==1 for x in c['connections'].values())
   output='Q' if c['type']=='$_DFF_PP0_' else 'Y'
   b=c['connections'][output][0]
   assert isinstance(b,int) and b not in self.driver,('multiple driver',name,b)
   self.driver[b]=('state',state_name(name)) if output=='Q' else ('cell',name)
 def bit(self,b):
  if b in self.memo:return self.memo[b]
  assert isinstance(b,int) and b not in self.active,('unknown or combinational cycle',b)
  self.active.add(b)
  d=self.driver[b]
  if d[0]!='cell': value=self.i.get(d)
  else:
   c=self.m['cells'][d[1]]
   args=[self.bit(c['connections'][p][0]) for p in ('A','B') if p in c['connections']]
   value=self.i.op(c['type'],args)
  self.active.remove(b); self.memo[b]=value
  return value
 def boundaries(self):
  targets={}
  for name,c in sorted(self.ff.items()):
   for p in ('C','D','R'):targets['state:'+name+':'+p]=self.bit(c['connections'][p][0])
  for name,p in sorted(self.m['ports'].items()):
   if p['direction']=='output':
    for ix,b in enumerate(p['bits']):targets[f'output:{name}:{ix}']=self.bit(b)
  for b in self.driver:self.bit(b)
  return targets

def compare(a,b):
 assert {k:(v['direction'],len(v['bits'])) for k,v in a['ports'].items()}=={k:(v['direction'],len(v['bits'])) for k,v in b['ports'].items()}
 i=Intern(); x=Circuit(a,i);y=Circuit(b,i)
 assert set(x.ff)==set(y.ff),'Exact bijective native state instance map'
 ax=x.boundaries();by=y.boundaries()
 assert ax.keys()==by.keys()
 mismatch=[k for k in ax if ax[k]!=by[k]]
 return {'states':len(x.ff),'input_bits':sum(len(p['bits']) for p in a['ports'].values() if p['direction']=='input'),'output_bits':sum(len(p['bits']) for p in a['ports'].values() if p['direction']=='output'),'targets':len(ax),'canonical_nodes':len(i.table),'mismatches':mismatch,'matched':len(ax)-len(mismatch)}
if __name__=="__main__":
 start=time.monotonic();gold,gate=read('gold'),read('gate');result=compare(gold,gate)
 result['elapsed_seconds']=time.monotonic()-start
 result['logic_cell_census']={n:dict(collections.Counter(c['type'] for c in m['cells'].values())) for n,m in [('gold',gold),('gate',gate)]}
 result['status']='PASS_COMPLETE_STATE_TRANSITION_AND_OUTPUT_FUNCTION_EQUALITY' if not result['mismatches'] else 'INCOMPLETE_STRUCTURAL_COMPARISON'
 result['scope']='Native Liberty binary Boolean functions; bijective same-instance FF state map, all D/clock/reset and all external outputs. No blackboxes, unconstrained omitted cells, new assumptions or timing equivalence.'
 result['rules']=['exact primitive semantics','commutative binary operand order','double Boolean inversion','literal 0/1 negation','associative Boolean operator grouping','AND/OR idempotence','collision-free tuple interning']
 (ROOT/'equivalence.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:(v[:5] if k=='mismatches' else v) for k,v in result.items()},indent=2))
