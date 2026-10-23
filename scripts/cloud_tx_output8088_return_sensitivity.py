#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Map measured failed TX terminals onto the exact archived physical wire graph."""
import copy,hashlib,io,json,os,subprocess,tarfile,traceback
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-return-sensitivity'
REPO='repos/Melihakbulut221/nssoc/'
def sha(b):return hashlib.sha256(b).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def asset(a,h):
 b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a),'-H','Accept: application/octet-stream'])
 assert sha(b)==h
 return b
def bind(failed,record):
 assert record['model'].lower()==failed['device']['model']=='npn13g2'
 assert [t['terminal']for t in record['terminals']]==['C','B','E','S']
 assert [t['node'].lower()for t in record['terminals']]==[n.removeprefix('xtree.')for n in failed['device']['terminals']]
 params={k.lower():v for k,v in record['parameters'].items()}
 assert float(params['nx'])==failed['device']['nx']
def path_and_resistance(resistors,targets):
 import heapq,math
 import numpy as np
 from scipy.sparse import coo_matrix
 from scipy.sparse.linalg import splu
 graph=defaultdict(list)
 for name,a,b,value in resistors:
  value=float(value);assert math.isfinite(value)and value>0
  graph[a].append((b,value,name));graph[b].append((a,value,name))
 start='avss';assert start in graph
 dist={start:0.};prev={};queue=[(0.,start)]
 while queue:
  value,node=heapq.heappop(queue)
  if value!=dist[node]:continue
  for nxt,res,name in graph[node]:
   new=value+res
   if new<dist.get(nxt,math.inf):dist[nxt]=new;prev[nxt]=(node,res,name);heapq.heappush(queue,(new,nxt))
 assert targets and all(t in dist and t!=start for t in targets)
 nodes=sorted(set(dist)-{start});index={n:i for i,n in enumerate(nodes)}
 ii=[];jj=[];vv=[];edge_count=0
 for name,a,b,res in resistors:
  if a not in dist:continue
  assert b in dist
  g=1/float(res);edge_count+=1
  for n in (a,b):
   if n!=start:ii.append(index[n]);jj.append(index[n]);vv.append(g)
  if a!=start and b!=start:
   ii.extend((index[a],index[b]));jj.extend((index[b],index[a]));vv.extend((-g,-g))
 matrix=coo_matrix((vv,(ii,jj)),shape=(len(nodes),len(nodes))).tocsc()
 matrix.sum_duplicates()
 rhs=np.zeros((len(nodes),len(targets)))
 for j,t in enumerate(targets):rhs[index[t],j]=1.
 lu=splu(matrix);voltage=lu.solve(rhs)
 residual=float(np.max(abs(matrix@voltage-rhs)))
 assert np.isfinite(voltage).all()and residual<1e-7 and voltage.min()>-1e-8
 imped=voltage[[index[t]for t in targets],:]
 assert np.allclose(imped,imped.T,rtol=1e-8,atol=1e-8),'DC reciprocity failed'
 output=[]
 for j,t in enumerate(targets):
  trace=[];at=t
  while at!=start:
   before,res,name=prev[at];trace.append(dict(name=name,a=before,b=at,resistance_ohm=res));at=before
  effective=float(voltage[index[t],j])
  assert 0<effective<=dist[t]*(1+1e-8)
  assert abs(sum(e['resistance_ohm']for e in trace)-dist[t])<1e-8
  energy=[]
  for name,a,b,res in resistors:
   if a not in dist:continue
   res=float(res)
   va=0. if a==start else float(voltage[index[a],j])
   vb=0. if b==start else float(voltage[index[b],j])
   current=(va-vb)/res;power=current*current*res
   energy.append(dict(name=name,a=a,b=b,resistance_ohm=res,unit_injection_current_a=current,
    self_resistance_contribution_ohm=power,d_self_resistance_d_segment_resistance=current*current))
  power_sum=sum(e['self_resistance_contribution_ohm']for e in energy)
  assert abs(power_sum-effective)<1e-7*max(1.,effective),'Resistive energy identity failed'
  output.append(dict(target=t,effective_self_resistance_ohm=effective,shortest_path_sum_ohm=dist[t],
   path_edges=len(trace),largest_path_resistors=sorted(trace,key=lambda x:x['resistance_ohm'],reverse=True)[:20],
   full_path=trace,power_identity_sum_ohm=power_sum,
   dominant_unit_injection_segments=sorted(energy,key=lambda x:x['self_resistance_contribution_ohm'],reverse=True)[:30]))
 return dict(ground=start,component_nodes=len(nodes)+1,resistors=edge_count,max_kcl_residual_a=residual,
  unit_injection_transfer_ohm=imped.tolist(),targets=output,
  interpretation='Linear DC resistance of original extracted metal only, unit current at one terminal at a time. Not total loaded IR drop, transient timing, device-access/substrate resistance or RF-qualified extraction.')
def resistance_controls():
 # Series and parallel graphs have analytic solutions; no physical acceptance.
 tests=[([['r1','avss','a','2'],['r2','a','b','3']],['a','b'],[2.,5.]),
        ([['r1','avss','a','2'],['r2','avss','a','2']],['a'],[1.])]
 for edges,targets,expected in tests:
  report=path_and_resistance(edges,targets)
  assert all(abs(row['effective_self_resistance_ohm']-want)<1e-10 for row,want in zip(report['targets'],expected,strict=True))
 try:path_and_resistance(tests[0][0],['missing'])
 except AssertionError:pass
 else:raise AssertionError('Accepted disconnected target')
 return dict(series_and_parallel_analytic_cases_passed=2,disconnected_target_rejected=True)

def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False);r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  run=api('actions/runs/39973764125')
  assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='9756efaacc1f8d98e0290915bcfff42868a42f5e'
  raw=asset(669469545,'188a64b46a908def7814edcfd8a0faa1b54cece005ffc793bd84d33b747234b1')
  diag=json.loads(raw)
  assert diag['original_review_exactly_reproduced'] and diag['status']=='COMPLETE_REJECTED_FULL_TX_DIAGNOSIS_NOT_REPAIR_OR_PHY_ACCEPTANCE'
  prepraw=asset(668092138,'54d9c58c007e4a8fb4e770bc3fc847a6f2d6417ae5c10639ce2c1b36cd52a032')
  prep=json.loads(prepraw)
  assert prep['source_head']=='f5eb7b05d98fda7c99540dbbe1d9309c3995160e' and prep['source_unchanged']
  assert prep['status']=='READY_ACTUAL8088_POWER128RETURN64_PHYSICAL_WIRE_DECK_NOT_SIMULATED'
  packed=asset(668092409,'99e9815c487be3fefd6045da307dda5f0e9c0b0f0e50773276c29797096059d9')
  assert len(packed)==72670216
  wanted={'whole8088/source/composed/composition.json','whole8088/source/composed/output8088-wire.spice'}
  found={};seen=set();embedded=False
  with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz')as archive:
   for member in archive:
    p=Path(member.name);assert not p.is_absolute()and '..'not in p.parts
    assert member.name not in seen;seen.add(member.name)
    assert member.isdir()or member.isfile()
    if not member.isfile():continue
    name=str(Path(*p.parts[1:]))
    if name in wanted or name=='result.json':
     b=archive.extractfile(member).read()
     if name=='result.json':assert b==prepraw;embedded=True
     else:assert sha(b)==prep['outputs'][name];found[name]=b
  assert embedded and set(found)==wanted
  r['verified_sources']=dict(diagnosis_run=39973764125,diagnosis_sha256=sha(raw),prepared_run=39906382209,
   prepared_summary_sha256=sha(prepraw),prepared_archive_sha256=sha(packed),selected={p:sha(b)for p,b in found.items()})
  composition=json.loads(found['whole8088/source/composed/composition.json'])
  model=found['whole8088/source/composed/output8088-wire.spice'].decode()
  assert composition['counts']==dict(devices=8088,R=140222,C=99906,external_ports=166,physical_ports=165,metal_reference_planes=13370,body_nets=65,conductors=703,terminals=28620)
  records={d['instance'].lower():d for d in composition['device_records']}
  assert len(records)==8088
  parent={}
  def root(n):
   parent.setdefault(n,n)
   while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
   return n
  counts=Counter();resistors=[]
  for line in model.splitlines():
   f=line.lower().split()
   if not f or f[0][0]in ('.','*'):continue
   counts[f[0][0]]+=1
   if f[0].startswith('r'):
    assert len(f)==4 and float(f[3])>0
    parent[root(f[1])]=root(f[2]);resistors.append(f)
  assert counts==dict(x=8088,r=140222,c=99906)
  ports=[p.lower()for p in composition['interface']]
  public=defaultdict(list)
  for p in ports:
   if p in parent:public[root(p)].append(p)
  terminals=defaultdict(list);clusters=defaultdict(set)
  for instance,d in records.items():
   for term in d['terminals']:
    n=term['node'].lower()
    if n not in parent:
     assert n.startswith('body')
     continue
    component=root(n);clusters[component].add(term['native_cluster'])
    terminals[component].append(dict(instance=instance,model=d['model'],terminal=term['terminal'],node=n))
  assert all(len(x)==1 for x in clusters.values()),'Wire graph shorts physical native clusters'
  r['graph']=dict(R=counts['r'],C=counts['c'],devices=counts['x'],
   resistor_components=len({root(n)for n in parent}),terminal_components=len(clusters),
   original_physical_clusters_preserved=True)
  def neighborhood(node):
   n=node.removeprefix('xtree.').lower()
   assert n in parent,'Expected actual metal terminal'
   k=root(n)
   return dict(node=n,native_cluster=next(iter(clusters[k])),public_ports=sorted(public[k]),device_terminals=terminals[k])
  failing=diag['failed_hbts_at_native_times'];assert len(failing)==85
  mapped={}
  for name,f in failing.items():
   instance=name.removeprefix('xtree.');record=records[instance];bind(f,record)
   nets={t:neighborhood(n)for t,n in zip(('C','B','E'),f['device']['terminals'][:3],strict=True)}
   mapped[name]=dict(measured=f,physical_device=record,wire_neighborhoods=nets)
  r['all85_failed_device_neighborhoods']=mapped
  r['resistance_controls']=resistance_controls()
  ground_failures={name:row for name,row in mapped.items()if row['wire_neighborhoods']['E']['public_ports']==['avss']}
  assert set(ground_failures)=={'xtree.xd5644','xtree.xd5667','xtree.xd5674'}
  targets=[row['wire_neighborhoods']['E']['node']for row in ground_failures.values()]
  r['ground_failure_order']=list(ground_failures)
  r['exact_avss_dc_resistance']=path_and_resistance(resistors,targets)
  reverse={v.lower():k for k,v in composition['wire_node_map'].items()}
  assert len(reverse)==len(composition['wire_node_map'])
  for target in r['exact_avss_dc_resistance']['targets']:
   for edge in target['dominant_unit_injection_segments']:
    edge['original_extractor_nodes']=[reverse[edge['a']],reverse[edge['b']]]
    edge['fraction_of_self_resistance']=edge['self_resistance_contribution_ohm']/target['effective_self_resistance_ohm']


  r['all62_interface_neighborhoods']=[dict(input=row['input'],stage=row['stage'],
   minimum_margin_v=row['minimum_margin_v'],wrong_sign_samples=row['wrong_sign_samples'],
   below_150mv_samples=row['below_150mv_samples'],
   common_mode_outside_original_1p8_2p05_samples=row['common_mode_outside_original_1p8_2p05_samples'],
   endpoints={leg:[neighborhood(e['node'])for e in es]for leg,es in row['endpoints'].items()})
   for row in diag['all62_interface_pairs']]
  # Reject changes to the actual failed device's identity; no synthetic circuit repair.
  name=next(iter(failing));record=records[name.removeprefix('xtree.')];f=failing[name];faults=[]
  for label in ('swap-cb','missing-terminal','wrong-model','wrong-area'):
   bad=copy.deepcopy(record)
   if label=='swap-cb':bad['terminals'][0]['node'],bad['terminals'][1]['node']=bad['terminals'][1]['node'],bad['terminals'][0]['node']
   elif label=='missing-terminal':bad['terminals'].pop()
   elif label=='wrong-model':bad['model']='other'
   else:
    key=next(k for k in bad['parameters']if k.lower()=='nx');bad['parameters'][key]='999'
   try:bind(f,bad)
   except (AssertionError,KeyError):faults.append(label)
   else:raise AssertionError('Accepted '+label)
  r['actual_binding_faults_rejected']=faults
  r['status']='COMPLETE_ORIGINAL_AVSS_DC_SENSITIVITY_NOT_PHYSICAL_REPAIR'
  r['scope']='Exact terminal and native resistor connectivity. Connected nodes retain their separate measured voltages; no zero-resistance assumption, new simulation, causal attribution or acceptance.'
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:save()
if __name__=='__main__':main()
