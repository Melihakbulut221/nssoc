#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Map measured failed TX terminals onto the exact archived physical wire graph."""
import copy,hashlib,io,json,os,subprocess,tarfile,traceback
from collections import defaultdict,Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-failure-topology'
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
  r['status']='COMPLETE_PHYSICAL_GRAPH_FAILURE_LOCALIZATION_NOT_REPAIR'
  r['scope']='Exact terminal and native resistor connectivity. Connected nodes retain their separate measured voltages; no zero-resistance assumption, new simulation, causal attribution or acceptance.'
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:save()
if __name__=='__main__':main()
