#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Diagnose the original physical wire network without changing the native circuit."""
import json,os,subprocess,math
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
import build_pcie_local_vco_hybrid_v6 as parser
import compare_cloud_routed_endpoints as reports
import cloud_tx_power128feed32_native_failure_map as mapping
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-power128feed32-return-network'
MODEL_SHA='2572406e76c5db277acaf2a50d95c6a1b476e26e44f9a1fb388537e95bec3177'
HEADROOM_SHA='54e930e1c001a7441a945f9804898b7b59a54c40cdb8ba91ccaa50ae3d1e73d3'
MAP_SHA='a1ca3a2c04e63b7d9aad0149a46fe166d90e698b9471ced21c1b46af04f86a11'
def get(aid,name,digest):
 b=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
 p=OUT/name;p.write_bytes(b);assert sha(p)==digest
 return json.loads(b)
def resistor_graph(rows):
 names=set();adj=defaultdict(list);edges=[]
 for row in rows:
  assert len(row)==4
  name,a,b,value=row
  assert name not in names and a!=b
  value=float(parser.number(value));assert math.isfinite(value)and value>0
  names.add(name);i=len(edges);edges.append((name,a,b,value));adj[a].append((b,i));adj[b].append((a,i))
 return edges,adj
def component(adj,node):
 assert node in adj
 seen={node};stack=[node]
 while stack:
  a=stack.pop()
  for b,_ in adj[a]:
   if b not in seen:seen.add(b);stack.append(b)
 return seen
def solver(edges,adj,ground):
 nodes=component(adj,ground);unknown=sorted(nodes-{ground});index={n:i for i,n in enumerate(unknown)}
 chosen=sorted({i for n in nodes for _,i in adj[n]})
 rr=[];cc=[];vv=[]
 for i in chosen:
  _,a,b,r=edges[i];g=1/r
  for x,y in [(a,b),(b,a)]:
   if x!=ground:
    rr.append(index[x]);cc.append(index[x]);vv.append(g)
    if y!=ground:rr.append(index[x]);cc.append(index[y]);vv.append(-g)
 mat=sp.coo_matrix((vv,(rr,cc)),shape=(len(unknown),len(unknown))).tocsc()
 lu=spla.splu(mat)
 def solve(source):
  assert source in nodes and source!=ground
  current=np.zeros(len(unknown));current[index[source]]=1
  voltage=lu.solve(current)
  assert np.all(np.isfinite(voltage))
  residual=float(np.max(np.abs(mat@voltage-current)))
  assert residual<1e-7,('KCL residual',residual)
  v=lambda n:0. if n==ground else float(voltage[index[n]])
  resistance=v(source);assert resistance>0 and min(voltage)>-1e-8
  allrows=[]
  for i in chosen:
   name,a,b,r=edges[i];drop=v(a)-v(b);amps=drop/r
   allrows.append(dict(name=name,a=a,b=b,resistance_ohm=r,unit_injection_current_a=amps,unit_injection_drop_v=drop,unit_injection_power_w=amps*amps*r))
  power=sum(x['unit_injection_power_w']for x in allrows)
  assert math.isclose(power,resistance,rel_tol=1e-7,abs_tol=1e-8),(power,resistance)
  assert math.isclose(sum((v(n)/edges[i][3])for n,i in adj[ground]),1.,rel_tol=1e-7,abs_tol=1e-8)
  ordered=sorted(allrows,key=lambda x:x['unit_injection_power_w'],reverse=True)
  for row in ordered:row['fraction_of_effective_resistance']=row['unit_injection_power_w']/resistance
  return dict(source=source,ground=ground,effective_resistance_ohm=resistance,component_nodes=len(nodes),component_resistors=len(chosen),maximum_kcl_residual_a=residual,energy_identity_w=power,dominant_edges=ordered[:80])
 return solve,nodes
def controls():
 result=[]
 for name,rows,expected in [
  ('series',[['R1','s','m','2'],['R2','m','g','3']],5.),
  ('parallel',[['R1','s','g','2'],['R2','s','g','3']],1.2),
  ('bridge',[['R1','s','a','1'],['R2','a','g','1'],['R3','s','b','1'],['R4','b','g','1'],['R5','a','b','100']],1.),
  ('dangling_branch',[['R1','s','g','5'],['R2','s','unused','100']],5.)]:
  e,a=resistor_graph(rows);f,_=solver(e,a,'g');v=f('s')
  assert math.isclose(v['effective_resistance_ohm'],expected,rel_tol=1e-10)
  result.append(dict(name=name,passed=True,expected_ohm=expected))
 for name,rows in [
  ('duplicate',[['R1','s','g','1'],['R1','s','g','2']]),
  ('negative',[['R1','s','g','-1']]),
  ('self_loop',[['R1','s','s','1']]),
  ('zero',[['R1','s','g','0']])]:
  try:resistor_graph(rows)
  except AssertionError:result.append(dict(name=name,rejected=True))
  else:raise AssertionError('Invalid graph accepted: '+name)
 e,a=resistor_graph([['R1','s','g','1'],['R2','q','z','2']]);f,_=solver(e,a,'g')
 for node in ['q','absent']:
  try:f(node)
  except AssertionError:result.append(dict(name='disconnected_'+node,rejected=True))
  else:raise AssertionError('Disconnected terminal accepted')
 return result
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,nominal_electrical_passed=False,native_model_modified=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['controls']=controls()
  normal=get(664616996,'normal-summary.json',mapping.NORMAL_SHA)
  mapped=get(665176254,'map-summary.json',MAP_SHA)
  headroom=get(665208696,'headroom-summary.json',HEADROOM_SHA)
  assert normal['sources_unchanged']and not normal['electrical_screen_passed']
  assert headroom['sources_unchanged']and headroom['all604_original_hbt_checks_reproduced']
  assert headroom['source']['summary_sha256']==mapping.NORMAL_SHA and headroom['source']['mapping_sha256']==MAP_SHA
  temporary=Path(os.environ['RUNNER_TEMP'])/'tx-return-native';temporary.mkdir(exist_ok=False);reports.OUT=temporary
  selected=['native/contract.json','whole8088/source/composed/composition.json','whole8088/source/interfaces.json','whole8088/source/composed/output8088-wire.spice']
  prepared,proof=reports.restore_report(mapping.PREP['group'],mapping.PREP['run'],mapping.PREP['summary_sha256'],mapping.PREP['parts_sha256'],temporary/'prepared',selected)
  for name in selected:
   assert sha(temporary/'prepared'/name)==prepared['outputs'][name]
   assert normal['preparation_source']['restore']['selected_files'][name]['sha256']==prepared['outputs'][name]
  root=temporary/'prepared';model=root/'whole8088/source/composed/output8088-wire.spice'
  assert sha(model)==MODEL_SHA
  composition=json.loads((root/'whole8088/source/composed/composition.json').read_text())
  contract=json.loads((root/'native/contract.json').read_text())
  interfaces=json.loads((root/'whole8088/source/interfaces.json').read_text())
  recomputed=mapping.mapped(normal['review'],composition,interfaces,contract)
  # The original Counter includes the remaining output stage key None; JSON stores that key as 'null'.
  assert json.loads(json.dumps(recomputed))==mapped['mapping'],'Exact JSON mapping differs'
  rows=parser.statements(model.read_text())
  assert rows[0]==['.subckt','nssoc_tx_output8088_wire_v1',*composition['interface']] and rows[-1]==['.ends','nssoc_tx_output8088_wire_v1']
  counts=Counter(x[0][0]for x in rows[1:-1]);assert counts==dict(X=8088,R=140222,C=99906)
  edges,adj=resistor_graph([x for x in rows[1:-1]if x[0].startswith('R')])
  records={'xtree.'+x['instance'].lower():x for x in composition['device_records']}
  term=lambda name,t:next(x for x in records[name]['terminals']if x['terminal']==t)
  bywire={}
  for name,d in records.items():
   for t in d['terminals']:
    if t['disposition']=='ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R':
     assert bywire.setdefault(t['node'],t['native_cluster'])==t['native_cluster']
  # Infer the remaining output HBT roles from conductor identity independently.
  remaining=[n for n,v in mapped['mapping']['native_topology_roles'].items()if v['stage']is None]
  assert len(remaining)==4
  references=[n for n in remaining if term(n,'B')['native_cluster']==term(n,'C')['native_cluster']]
  assert len(references)==1;reference=references[0]
  tails=[n for n in remaining if n!=reference and term(n,'B')['native_cluster']==term(reference,'B')['native_cluster']and term(n,'E')['native_cluster']==term(reference,'E')['native_cluster']]
  assert tails==['xtree.xd5644'];tail=tails[0]
  data=set(remaining)-{reference,tail}
  assert len(data)==2 and all(term(n,'E')['native_cluster']==term(tail,'C')['native_cluster']for n in data)
  avss_solve,avss_nodes=solver(edges,adj,'avss')
  clusters={bywire[n]for n in avss_nodes if n in bywire};assert clusters=={term(tail,'E')['native_cluster']}=={2}
  public=set(composition['interface'])&avss_nodes;assert public=={'avss'},public
  inverse={v:k for k,v in composition['wire_node_map'].items()};assert len(inverse)==len(composition['wire_node_map'])
  targets={'output_tail':tail}
  for stage,d in headroom['stages'].items():
   ns=d['native_devices']['tail'];assert len(ns)==2
   for i,n in enumerate(ns):targets[stage+'_tail'+str(i)]=n
  result={}
  for label,name in targets.items():
   emitter=term(name,'E');assert emitter['native_cluster']==2
   row=avss_solve(emitter['node'])
   for edge in row['dominant_edges']:
    edge['raw_wire_a']=inverse[edge['a']];edge['raw_wire_b']=inverse[edge['b']]
   obs=headroom['device_observations'][name]
   assert obs['terminals'][2]=='xtree.'+emitter['node']
   row.update(device=name,actual_native_terminal=emitter,observed_original_waveform=obs,
    unit_current_scope='Linear passive wire-only DC unit-current sensitivity to actual avss port. Capacitors are open only for this diagnostic; original native R/C/model and waveform remain unchanged. It is not a replacement transient simulation, total operating voltage prediction, or qualified PEX.')
   result[label]=row
  assert len(result)==63
  r.update(status='PASS_ORIGINAL_NATIVE_TX_RETURN_NETWORK_DIAGNOSIS_NOT_ELECTRICAL_ACCEPTANCE',sources_unchanged=True,source=dict(prepared=mapping.PREP,model_sha256=MODEL_SHA,normal_summary_sha256=mapping.NORMAL_SHA,headroom_summary_sha256=HEADROOM_SHA,mapping_sha256=MAP_SHA,restore=proof),original_counts=dict(counts),output_roles=dict(tail=tail,reference=reference,data=sorted(data)),actual_avss_component=dict(nodes=len(avss_nodes),native_cluster=2,public_ports=sorted(public)),targets=result,scope='Locate actual return-network resistance contributions. Any repair requires changed physical geometry, DRC/LVS, fresh RC and complete original loaded electrical checks.')
  assert sha(model)==MODEL_SHA
 except BaseException as error:
  import traceback
  r.update(status='FAIL_NATIVE_RETURN_NETWORK_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc());raise
 finally:save();print(r['status'],flush=True)
if __name__=='__main__':main()
