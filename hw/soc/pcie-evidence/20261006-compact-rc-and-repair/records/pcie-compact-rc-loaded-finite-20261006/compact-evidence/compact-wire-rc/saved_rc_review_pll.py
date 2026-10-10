# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-byte graph and capacitance readback, without producer imports."""
import hashlib,json,math,shlex
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
B=Path(__file__).resolve().parent
O=Path('/dev/shm/nssoc-div4-v7-compact-v2-wire-rc-01')
G=B.parent/'pcie-divider-v7-compact-v2-wire-v1-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def rows(p):return [shlex.split(s) for s in p.read_text().splitlines() if s.strip()]
def edge(a,b):return tuple(sorted((a,b)))
def close(a,b):return math.isclose(a,b,rel_tol=3e-6,abs_tol=1e-4)
native=json.loads((B/'native-execution.json').read_text())
assert native['status']=='PASS_NATIVE_WIRE_RC_GRAPH_AND13_RAW_CONTROLS_ONLY'
assert [(s['name'],s['execution']['returncode']) for s in native['steps']]==[('native',0),('audit',0),('mutations',0)]
for p,h in native['outputs'].items():assert pin(p)==h,p
assert json.loads((B/'native-wire-audit.json').read_text())['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
mutations=json.loads((B/'native-mutations-v2.json').read_text());assert len(mutations['cases'])==13 and len({r['control'] for r in mutations['cases']})==13
for p,h in mutations['inputs'].items():assert pin(p)==h
anchors=json.loads((G/'anchors.json').read_text());anchor={a['label']:a for a in anchors['anchors']};assert len(anchor)==205
source=rows(O/'bank_wires.ext');replacement=rows(O/'bank_wires.res.ext');export=rows(O/'wires.spice');baseline=rows(O/'baseline.spice')
for contents in (source,replacement):assert [r for r in contents if r[0]=='scale']==[['scale','1000','1','0.5']]
ports=[]
for r in export:
 if r[0]=='.subckt':assert not ports;ports+=r[2:]
 elif r[0]=='+':ports+=r[1:]
assert len(ports)==205 and set(ports)==set(anchor)
rs=[r for r in export if r[0].startswith('R')];cs=[r for r in export if r[0].startswith('C')]
assert len(rs)==382 and len(cs)==649
assert not [r for r in export if r[0][0].upper() in 'XQM']
graph=defaultdict(set)
for r in rs:
 assert len(r)==4 and r[1]!=r[2] and math.isfinite(float(r[3])) and float(r[3])>0
 graph[r[1]].add(r[2]);graph[r[2]].add(r[1])
remaining=set(graph)|set(anchor);owners={};components=[]
while remaining:
 seen={remaining.pop()};stack=list(seen)
 while stack:
  for n in graph[stack.pop()]:
   if n not in seen:seen.add(n);stack.append(n);remaining.discard(n)
 ids={anchor[n]['wire_component'] for n in seen if n in anchor};assert len(ids)==1 and len(seen)>1
 ident=next(iter(ids));owners.update({n:ident for n in seen});components.append({'wire':ident,'nodes':len(seen),'anchors':len(seen&set(anchor))})
assert len(components)==37 and {c['wire'] for c in components}==set(range(1,38))
assert Counter((edge(r[1],r[2]),float(r[3])) for r in rs)==Counter((edge(r[1],r[2]),float(r[3])) for r in replacement if r[0]=='resist')
owners['sub']=0
expected=defaultdict(float);actual=defaultdict(float);base=defaultdict(float)
for r in source:
 if r[0]=='node':assert r[1] in anchor;expected[edge(anchor[r[1]]['wire_component'],0)]+=float(r[3])
 elif r[0]=='cap':expected[edge(anchor[r[1]]['wire_component'],anchor[r[2]]['wire_component'])]+=float(r[3])
for dest,data in [(actual,cs),(base,[r for r in baseline if r[0].startswith('C')])]:
 for r in data:
  v=float(r[3])*1e18;assert v>=0 and math.isfinite(v)
  i,j=owners[r[1]],owners[r[2]];assert i!=j or v==0
  if v:dest[edge(i,j)]+=v
expected={k:v for k,v in expected.items() if v}
assert len(expected)==300 and expected.keys()==actual.keys()==base.keys()
for k,v in expected.items():assert close(v,actual[k]) and close(v,base[k]),(k,v,actual[k],base[k])
point=defaultdict(float);expoint=defaultdict(float);mutual=defaultdict(float);exmutual=defaultdict(float)
for r in replacement:
 if r[0]=='rnode':assert float(r[2])==0;point[r[1]]+=float(r[3])
for r in source:
 if r[0]=='cap':mutual[edge(r[1],r[2])]+=float(r[3])
for r in cs:
 if 'sub' in r[1:3]:expoint[r[2] if r[1]=='sub' else r[1]]+=float(r[3])*1e18
 else:exmutual[edge(r[1],r[2])]+=float(r[3])*1e18
assert set(expoint)<=set(point) and all(close(v,expoint.get(n,0)) for n,v in point.items())
assert mutual.keys()==exmutual.keys() and all(close(v,exmutual[k]) for k,v in mutual.items())
assert anchors['body_well_terminals']==85 and len(anchors['unmodeled_body_well_terminals'])==85
assert all(a['wire_component'] for a in anchor.values())
# Re-read every complete native input and compare all thirteen retained diagnostic outcomes.
for p,h in native['inputs'].items():assert pin(p)==h,p
old_controls=json.loads((B.parent/'pcie-divider-v7-wire-rc-v1-20261005/native-mutations-v2.json').read_text())
assert [(x['control'],x['rejected_by']) for x in mutations['cases']]==[(x['control'],x['rejected_by']) for x in old_controls['cases']]
bridge=mutations['actual_open_control'];assert bridge['original_components']==37 and bridge['mutated_components']==38
left_node,right_node=bridge['endpoints'];assert graph[left_node].__contains__(right_node)
assert sum(edge(r[1],r[2])==edge(left_node,right_node) for r in rs)==1
seen={left_node};queue=[left_node]
while queue:
 node=queue.pop()
 for neighbor in graph[node]:
  if edge(node,neighbor)==edge(left_node,right_node):continue
  if neighbor not in seen:seen.add(neighbor);queue.append(neighbor)
assert right_node not in seen
assert set(bridge['left_real_probes'])==seen&set(anchor)
assert set(bridge['right_real_probes'])=={n for n in anchor if owners[n]==owners[left_node]}-seen
assert bridge['left_real_probes'] and bridge['right_real_probes']
reference=json.loads((G/'terminal-reference-planes.json').read_text())['rows']
assert anchors['unmodeled_body_well_terminals']==[x for x in reference if x['disposition']!='ACTUAL_METAL_POINT_REFERENCE']
files=[Path(__file__),B/'native-execution.json',B/'native-wire-audit.json',B/'native-mutations-v2.json',B/'source-freeze.json',B/'source-only-peer.json',G/'anchors.json',*[O/n for n in ('bank_wires.ext','bank_wires.res.ext','baseline.spice','wires.spice','native.log')]]
r={'status':'PASS_INDEPENDENT_SAVED_COMPACT_V2_DIVIDER_WIRE_GRAPH_AND_CAPACITANCE','utc':datetime.now(timezone.utc).isoformat(),'findings':[],'inputs':{str(p):pin(p) for p in files},'method':'Independent stdlib literal rows and BFS; no producer or NetworkX imports; all raw native output hashes and exact thirteen-control terminal result revalidated.','resistors':len(rs),'capacitors':len(cs),'actual_anchors':len(anchor),'components':components,'conductor_capacitance_edges':len(expected),'matrix_entries':38**2,'complete_native_export_resistor_multiset_equal':True,'complete_source_baseline_export_capacitance_matrix_equal_with_declared_native_rounding':True,'each_native_point_and_mutual_attachment_preserved':True,'original85_body_terminals_preserved_unmodeled':True,'fresh_all_three_native_stages_exit0':True,'native_rerun':False,'full_pex_qualified':False,'loaded_division_simulated':False,'main_chip_integrated':False}
assert not (B/'saved-rc-peer-pll.json').exists();(B/'saved-rc-peer-pll.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(B/'saved-rc-peer-pll.json'))
