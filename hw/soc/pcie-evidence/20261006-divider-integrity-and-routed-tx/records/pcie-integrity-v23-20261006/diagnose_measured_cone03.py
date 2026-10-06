# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only correlation of exact saved native graphs, buffers, and reported paths."""
from pathlib import Path
import collections,hashlib,json,re
R=Path.cwd();B=Path(__file__).resolve().parent
LIB=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib')
allinputs=[Path(__file__),LIB]
def groups(text, kind):
 for match in re.finditer(r'\b'+kind+r'\s*\(\s*([^()]+)\s*\)\s*\{',text):
  start=match.end();i=start;depth=1
  while depth:
   if text[i]=='{':depth+=1
   if text[i]=='}':depth-=1
   i+=1
  yield match.group(1).strip().strip('"'),text[start:i-1]
libdirs={typ:{name:re.search(r'\bdirection\s*:\s*"?(input|output|inout)"?\s*;',part).group(1) for name,part in groups(body,'pin')} for typ,body in groups(LIB.read_text(),'cell')}
def pin(p):
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def parse(p):
 text=p.read_text();ans=[]
 for typ,name,body in re.findall(r'\b(sg13g2_\w+)\s+(\S+)\s*\((.*?)\);',text,re.S):
  ans.append((name,typ,{n:re.sub(r'\s+','',w).lstrip('\\') for n,w in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)}))
 return ans
results=[]
for version,date in [(17,'20261005'),(21,'20261005'),(22,'20261006')]:
 base=R/f'hw/soc/out/pcie-integrity-v{version}-{date}'
 imported=Path(f'/dev/shm/nssoc-integrity-v{version}-balanced-import-01')
 repaired=Path(f'/dev/shm/nssoc-integrity-v{version}-balanced-sta-01/rx/repaired.v')
 mp=imported/'mapped.json';vp=imported/'mapped.v';path=base/'critical-path-attribution.json'
 allinputs.extend([mp,vp,repaired,path])
 m=json.loads(mp.read_text())['modules'][f'soc_pcie_gen3_continuous_rx_integrity_v{version}']
 original=parse(vp);assert len(original)==len(m['cells'])
 wb={};mapping={};directions={};checked=0
 for (n,t,ps),(jn,c) in zip(original,m['cells'].items()):
  assert t==c['type'] and ps.keys()==c['connections'].keys()
  mapping[n]=jn;directions[t]=c['port_directions']
  for p,w in ps.items():
   assert len(c['connections'][p])==1
   bit=c['connections'][p][0]
   assert w not in wb or wb[w]==bit,(version,w)
   wb[w]=bit;checked+=1
 # Every emitted semantic wire that has a live cell pin must retain its exact
 # Yosys bit; unused debug netnames are not treated as actual driven signals.
 semantic=0
 for name,rec in m['netnames'].items():
  if name.startswith('$'):continue
  for i,bit in enumerate(rec['bits']):
   w=name+(f'[{i+rec.get("offset",0)}]' if len(rec['bits'])>1 or rec.get('upto') else '')
   if w in wb:assert wb[w]==bit,(version,w);semantic+=1
 for name,p in m['ports'].items():
  for i,bit in enumerate(p['bits']):
   w=name+(f'[{i}]' if len(p['bits'])>1 else '')
   if w in wb:assert wb[w]==bit,(version,w)
 op={n:ps for n,t,ps in original};ot={n:t for n,t,ps in original};oc=collections.defaultdict(list)
 for n,t,ps in original:
  for p,w in ps.items():
   if directions[t][p]=='input':oc[w].append((n,p))
 rp={};rt={};rc=collections.defaultdict(list)
 for n,t,ps in parse(repaired):
  rp[n]=ps;rt[n]=t
  if t in directions:assert directions[t]==libdirs[t]
  directions[t]=libdirs[t]
  assert ps.keys()==directions[t].keys()
  for p,w in ps.items():
   if directions[t][p]=='input':rc[w].append((n,p))
 assert set(op)<=set(rp)
 assert all(rt[n].rsplit('_',1)[0]==ot[n].rsplit('_',1)[0] for n in op)
 resized={n:{'before':ot[n],'after':rt[n]} for n in op if rt[n]!=ot[n]}
 report=json.loads(path.read_text());rows=report['rows'];detail=[]
 for i,row in enumerate(rows):
  n=row['cell'];w=row['output'];entry={k:row[k] for k in ['cell','type','output','arrival_ns','delay_ns']}
  if i:
   previous=rows[i-1]['output'];entry['path_input_ports']=[p for p,x in rp[n].items() if x==previous and directions[rt[n]][p]=='input'];assert entry['path_input_ports']
  if n in op:
   entry['json_cell']=mapping[n];entry['original_direct_fanout']=len(oc[w]);entry['source_attributes']=m['cells'][mapping[n]].get('attributes',{})
   stack=[(w,0)];leaves=[];buffers=set();maxdepth=0
   while stack:
    nw,depth=stack.pop();maxdepth=max(maxdepth,depth)
    for sn,port in rc[nw]:
     if sn not in op:
      assert '_buf_' in rt[sn] and port=='A';assert sn not in buffers;buffers.add(sn);stack.append((rp[sn]['X'],depth+1))
     else:leaves.append((sn,port))
   assert sorted(leaves)==sorted(oc[w]),(version,n,len(leaves),len(oc[w]))
   entry['inserted_buffer_tree']={'buffers':len(buffers),'maximum_depth':maxdepth,'original_sink_pins_reconnected_exactly':len(leaves)}
  detail.append(entry)
 results.append({'version':version,'emitted_original_cells':len(original),'resized_original_cells':len(resized),'all_cell_pin_correspondence_checks':checked,'live_semantic_alias_checks':semantic,'startpoint':report['startpoint_q_wire'],'endpoint':report['endpoint_q_wire'],'reported_arrival_ns':rows[-1]['arrival_ns'],'delay_by_family':report['delay_by_cell_family'],'path':detail,'largest_original_fanouts_on_path':sorted([x for x in detail if 'original_direct_fanout' in x],key=lambda x:x['original_direct_fanout'],reverse=True)[:5]})
out={'status':'PASS_SAVED_WHOLE_GRAPH_ALIAS_AND_ACTUAL_PATH_BUFFER_ATTRIBUTION','inputs':{str(p):pin(p) for p in allinputs},'versions':results,'scope':'Read-only saved graph/path analysis. Ordered emitted/Yosys cell correspondence is checked through every type/pin and every live semantic alias; inserted buffer leaves match original sink pins exactly. Optimized stale debug netnames are not identified as live signals. Structural support is not Boolean sensitivity or physical signoff; no EDA/test rerun.'}
(B/'measured-cone-diagnosis03.json').write_text(json.dumps(out,indent=2)+'\n')
for x in results:print(x['version'],x['reported_arrival_ns'],[(y['output'],y['original_direct_fanout'],y['inserted_buffer_tree']) for y in x['largest_original_fanouts_on_path']])
