# SPDX-License-Identifier: Apache-2.0
"""Identify MIM/divider connections after collapsing extracted wire R only."""
import hashlib,json,math,pathlib,re,zipfile
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'accepted':False,'new_layout':False,'scope':'Connectivity classification only. Collapse explicit numeric wire R, never PDK resistor instances. No RC accuracy, timing, device or PHY approval.'}
try:
 h=hashlib.sha256()
 with open('native.zip','rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 assert h.hexdigest()=='df95a0280336f6876e0308a4e7231e71f9d000f271398dcdad3d8eb89ae2f86a'
 z=zipfile.ZipFile('native.zip');matches=[n for n in z.namelist() if n.endswith('composition-n1/model.cir')];assert len(matches)==1
 raw=z.read(matches[0]);lines=[]
 for row in raw.decode().splitlines():
  row=row.strip()
  if not row or row.startswith('*'):continue
  if row.startswith('+'):assert lines;lines[-1]+=' '+row[1:]
  else:lines.append(row)
 blocks={};active=None
 for row in lines:
  tokens=row.lower().split()
  if tokens[0]=='.subckt':
   assert active is None and len(tokens)>=2, 'nested or invalid subcircuit'
   active=tokens[1];assert active not in blocks, 'duplicate subcircuit'
   blocks[active]=[]
  elif tokens[0]=='.ends':
   assert active is not None, 'unmatched ends'
   assert len(tokens)==1 or tokens[1]==active, 'mismatched ends'
   active=None
  elif active is not None:blocks[active].append(row)
 assert active is None, 'unterminated subcircuit'
 top='nssoc_cdr650_gate_n1';assert top in blocks, 'expected top missing'
 subckts=[top];lines=blocks[top]
 r['subcircuits_excluded_from_top_scope']=len(blocks)-1
 parent={};rank={}
 def find(n):
  n=n.lower();parent.setdefault(n,n);rank.setdefault(n,0);root=n
  while parent[root]!=root:root=parent[root]
  while parent[n]!=n:old=parent[n];parent[n]=root;n=old
  return root
 def union(a,b):
  a,b=find(a),find(b)
  if a==b:return
  if rank[a]<rank[b]:a,b=b,a
  parent[b]=a
  if rank[a]==rank[b]:rank[a]+=1
 wires=0;instances={}
 for row in lines:
  t=row.lower().split()
  if t[0].startswith('r'):
   assert len(t)==4,('unsupported wire R card',t[0])
   value=float(t[3]);assert math.isfinite(value) and value>=0
   union(t[1],t[2]);wires+=1
  elif t[0].startswith('x'):
   assert t[0] not in instances
   pos=[];params={}
   for token in t[1:]:
    if '=' in token:
     k,v=token.split('=',1);assert k not in params;params[k]=v
    else:pos.append(token)
   assert len(pos)>=3
   instances[t[0]]={'nodes':pos[:-1],'model':pos[-1],'params':params}
 assert wires>0
 resnames=['XD0377','XD0378','XD0379','XD0380','XD0384','XD0385','XD0386','XD0387','XD0388','XD0389','XD0390','XD0391']
 capnames=['XD0423','XD0424','XD0425','XD0426','XD0427','XD0428']
 def device(name,model):
  d=instances.get(name.lower())
  if d is None and model=='cap_cmim':
   node=('w_t'+name[3:]+'_mim_top').lower();hits=[v for v in instances.values() if node in v['nodes'] and model in v['model']];assert len(hits)==1;d=hits[0]
  assert d is not None and model in d['model'],(name,'model or identity differs')
  assert len(d['nodes'])>=2
  return d
 resistors={n:device(n,'rppd') for n in resnames};caps={n:device(n,'cap_cmim') for n in capnames}
 probes={'sampler_a_positive':'w_t239_c','sampler_a_negative':'w_t241_c','sampler_c_positive':'w_t255_c','sampler_c_negative':'w_t257_c','sampler_d_positive':'w_t203_c','sampler_d_negative':'w_t205_c','buffer_a_positive_input':'w_t273_b','buffer_a_negative_input':'w_t275_b','buffer_c_positive_input':'w_t278_b','buffer_c_negative_input':'w_t280_b','selector0_positive_input':'w_t281_b','selector0_negative_input':'w_t282_b','selector1_positive_input':'w_t299_b','selector1_negative_input':'w_t300_b','power':'avdd','ground':'avss'}
 def dimension(d):return {k:v for k,v in d['params'].items() if k in ['w','l','m']}
 records=[]
 for n,d in caps.items():
  roots=[find(x) for x in d['nodes'][:2]];assert roots[0]!=roots[1],(n,'MIM shorted after wire collapse')
  labels=[[label for label,node in probes.items() if find(node)==root] for root in roots]
  parallel=[rn for rn,rd in resistors.items() if set(find(x) for x in rd['nodes'][:2])==set(roots)]
  neighbors=[[rn for rn,rd in resistors.items() if root in [find(x) for x in rd['nodes'][:2]]] for root in roots]
  records.append({'capacitor':n,'dimensions':dimension(d),'endpoint_probe_labels':labels,'parallel_with_divider_resistors':parallel,'endpoint_neighbor_resistors':neighbors})
 r.update(status='DIVIDER_TOPOLOGY_CLASSIFIED',model_sha256=hashlib.sha256(raw).hexdigest(),subcircuit=subckts[0],collapsed_wire_resistors=wires,pdk_resistors_not_collapsed={n:dimension(d) for n,d in resistors.items()},capacitors=records)
 buffer_nodes={}
 for ident in (273,275,278,280):
  for terminal in ('b','c','e'):
   node=f'w_t{ident}_{terminal}';root=find(node)
   matches=[]
   for name,d in instances.items():
    positions=[i for i,n in enumerate(d['nodes']) if find(n)==root]
    if positions:matches.append({'device':name,'model':d['model'],'terminal_positions':positions,'parameters':d['params']})
   assert matches,('No physical device neighbor for buffer terminal',node)
   buffer_nodes[node]={'connected_devices':matches,'supply_aliases':[n for n in ('avdd','avss') if find(n)==root]}
 r['buffer_terminal_neighborhoods']=buffer_nodes
 r['scope']+=' Buffer neighborhoods identify model terminals and attached PDK components only; no RC or bias conclusion from wire collapse.'
except Exception as e:r.update(status='ERROR',error=type(e).__name__+': '+str(e))
(out/'divider-topology.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status']=='DIVIDER_TOPOLOGY_CLASSIFIED' else 1)
