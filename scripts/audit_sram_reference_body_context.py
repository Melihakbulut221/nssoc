# SPDX-License-Identifier: Apache-2.0
"""Resolve SRAM cell body ports through the independent macro hierarchy only."""
import collections,hashlib,io,json,pathlib,zipfile
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'manufacturing_approval':False,'layout_connectivity_proven':False}
def need(ok,msg):
 if not ok:raise ValueError(msg)
try:
 raw=pathlib.Path('reference.zip').read_bytes();need(hashlib.sha256(raw).hexdigest()=='124f6a92fa56346b1c471efb84750878180ef0c8056b2c940c5c6fce0e41e29b','archive SHA')
 z=zipfile.ZipFile(io.BytesIO(raw));names=[n for n in z.namelist() if n.endswith('reference.spice')];need(len(names)==1,'ambiguous reference')
 raw=z.read(names[0]);digest=hashlib.sha256(raw).hexdigest();need(digest=='64d041383d0ebee7b54dab0bc10d651d31262a2a41ccd15a9c0727dac06e0dd9','reference SHA')
 lines=[]
 for line in raw.decode().splitlines():
  line=line.strip().lower()
  if not line or line.startswith('*'):continue
  if line.startswith('+'):need(bool(lines),'orphan continuation');lines[-1]+=' '+line[1:]
  else:lines.append(line)
 subs={};active=None;globals_={'0'}
 for line in lines:
  t=line.split()
  if t[0]=='.subckt':
   need(active is None and t[1] not in subs,'nested/duplicate subcircuit');active=t[1]
   need(not any('=' in p or p=='params:' for p in t[2:]),'parameterized subcircuit requires explicit binding')
   subs[active]={'ports':t[2:],'rows':[]}
  elif t[0]=='.ends':need(active is not None,'orphan end');active=None
  elif t[0]=='.global':globals_.update(t[1:])
  elif active is not None:subs[active]['rows'].append(t)
 need(active is None,'unterminated subcircuit')
 top='dp8tsramdp256x16';leaf='dp8tcell';need(top in subs and leaf in subs,'missing macro/cell')
 topports=subs[top]['ports'];root={p:'PORT:'+p for p in topports};counts=collections.Counter();patterns=collections.Counter();calls=collections.Counter()
 def visit(name,env,path,ancestry):
  need(name not in ancestry and len(ancestry)<50,'recursive hierarchy')
  def node(n):return 'GLOBAL:'+n if n in globals_ else env.get(n,path+'/'+n)
  calls[name]+=1
  if name==leaf:
   need(all(p in env for p in ['substrate','nwell','vss','vdd']),'body/power formal absent')
   body={p:node(p) for p in ['substrate','nwell','vss','vdd']}
   counts['cells']+=1;counts['substrate_equals_vss']+=body['substrate']==body['vss'];counts['nwell_equals_vdd']+=body['nwell']==body['vdd']
   def label(v):return v if v.startswith(('PORT:','GLOBAL:')) else 'INTERNAL'
   patterns[tuple((p,label(body[p])) for p in ['substrate','nwell','vss','vdd'])]+=1
   return
  for t in subs[name]['rows']:
   if not t[0].startswith('x'):continue
   pos=[]
   for token in t[1:]:
    if '=' in token or token=='params:':break
    pos.append(token)
   need(bool(pos),'empty instance')
   child=pos[-1]
   if child not in subs:continue
   need(len(pos)-1==len(subs[child]['ports']),'hierarchical pin count differs: '+child)
   childenv={p:node(n) for p,n in zip(subs[child]['ports'],pos[:-1])}
   visit(child,childenv,path+'/'+t[0],ancestry+(name,))
 visit(top,root,top,())
 need(counts['cells']>0,'no SRAM cells reached')
 r.update(status='REFERENCE_HIERARCHY_RESOLVED',reference_spice_sha256=digest,top=top,top_ports=topports,cell_ports=subs[leaf]['ports'],counts=dict(counts),body_patterns=[{'binding':dict(k),'cells':v} for k,v in patterns.items()],hierarchical_instances=dict(calls),scope='Independent schematic hierarchy only. Resolves actual parent connections of leaf substrate/nwell ports. Does not prove extracted geometry, authorize aliases or establish macro LVS.')
except Exception as e:r.update(status='ERROR',error=type(e).__name__+': '+str(e))
(out/'reference-body-context.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status']=='REFERENCE_HIERARCHY_RESOLVED' else 1)
