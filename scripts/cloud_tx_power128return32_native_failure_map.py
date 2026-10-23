#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Map retained full TX failures to actual native devices; no new electrical pass."""
import copy,json,os,subprocess
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-power128return32-native-failure-map'
PREP=dict(group='tx-output8088-power128return32-prepared-wire-nominal-none',run=39770384053,
 summary_sha256='449e933d18b43a0fa425ee37277637f482eb5db37b6ead06c0df2e057803c6ff',
 parts_sha256='1de738fe5961fda70fa4e321d90aa32ef729dc4ff0dc18e2b87e978bdf610511')
NORMAL_SHA='0ecc3dc388c00cc05dac72ae349db19f935e970180ea149e6bb495ceac14aa66'
def mapped(review,composition,interfaces,contract):
 records=composition['device_records']
 assert len(records)==8088 and len({d['native_id']for d in records})==8088
 byname={'xtree.'+d['instance'].lower():d for d in records}
 assert len(byname)==8088
 hbts={n:d for n,d in byname.items()if d['model'].lower()=='npn13g2'}
 assert len(hbts)==593
 assert len(review['hbt_devices'])==len(contract['hbt'])==604
 assert set(review['hbt_devices'])==set(contract['hbt'])
 assert set(hbts).issubset(review['hbt_devices'])
 failed={n:v for n,v in review['hbt_devices'].items()if not v['passed']}
 assert failed==review['failed_hbts']and len(failed)==85
 assert set(failed).issubset(hbts),'Failure has no actual parent-device identity'
 refs=interfaces['references'];assert len(refs)==124
 roles={}
 for label,ref in refs.items():
  assert len(ref['terminals'])==3
  for t in ref['terminals']:
   name='xtree.'+t['instance'].lower();d=hbts[name]
   assert t['native_id']==d['native_id']and t['terminal']=='B'
   base=next(x for x in d['terminals']if x['terminal']=='B')
   assert base['node']==t['node']and base['native_cluster']==t['native_cluster']
   assert name not in roles
   roles[name]=dict(input_leg=label,endpoints=ref['endpoints'],physical_base=t)
 assert len(roles)==372
 # Derive stage roles from actual native conductor identity, not instance-number
 # ranges: data emitter -> selector collector -> selector emitter -> tail collector.
 stages={}
 for name,role in roles.items():
  stage=role['endpoints'][-1]['endpoint'].split('.')[0]
  stages.setdefault(stage,[]).append(name)
 assert len(stages)==31 and all(len(v)==12 for v in stages.values())
 def cluster(name,terminal):
  return next(t['native_cluster']for t in hbts[name]['terminals']if t['terminal']==terminal)
 topology={n:dict(kind='data',stage=role['endpoints'][-1]['endpoint'].split('.')[0])for n,role in roles.items()}
 for stage,data in stages.items():
  emitters={cluster(n,'E')for n in data};assert len(emitters)==2
  selectors=[n for n in hbts if cluster(n,'C')in emitters]
  assert len(selectors)==4 and not set(selectors)&set(topology),(stage,selectors)
  selector_emitters={cluster(n,'E')for n in selectors};assert len(selector_emitters)==1
  tails=[n for n in hbts if cluster(n,'C')in selector_emitters]
  assert len(tails)==2 and not set(tails)&set(topology)and not set(tails)&set(selectors),(stage,tails)
  for n in selectors:topology[n]=dict(kind='selector',stage=stage)
  for n in tails:topology[n]=dict(kind='tail',stage=stage)
  tail_bases={cluster(n,'B')for n in tails};tail_emitters={cluster(n,'E')for n in tails}
  assert len(tail_bases)==len(tail_emitters)==1
  references=[n for n in hbts if cluster(n,'C')==cluster(n,'B')and cluster(n,'B')in tail_bases and cluster(n,'E')in tail_emitters]
  assert len(references)==1 and not set(references)&set(topology),(stage,references)
  topology[references[0]]=dict(kind='reference',stage=stage)
 assert len(topology)==589
 remaining=set(hbts)-set(topology);assert len(remaining)==4
 for n in remaining:topology[n]=dict(kind='remaining_parent_hbt',stage=None)
 assert Counter(v['kind']for v in topology.values())==dict(data=372,selector=124,tail=62,reference=31,remaining_parent_hbt=4)
 rows=[]
 for name,value in sorted(failed.items(),key=lambda x:x[1]['min_post_vce_v']):
  d=hbts[name]
  assert [t['terminal']for t in d['terminals']]==['C','B','E','S']
  rows.append(dict(name=name,measurement=value,native_device=d,
   native_bench_record=contract['hbt'][name],physical_input_role=roles.get(name),native_topology_role=topology[name]))
 return dict(failures=rows,native_topology_roles=topology,failed_roles=dict(Counter(x['native_topology_role']['kind']for x in rows)),failed_stages=dict(Counter(x['native_topology_role']['stage']for x in rows)),failed_data_pair_devices=sum(x['physical_input_role']is not None for x in rows),
  failed_other_hbts=sum(x['physical_input_role']is None for x in rows),
  data_leg_counts=dict(Counter(x['physical_input_role']['input_leg']for x in rows if x['physical_input_role'])),
  all593_parent_hbts_bound=True,external_clock_hbts=11,all_failed_hbts_physically_identified=True)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,
  new_electrical_simulation=False,nominal_electrical_passed=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/667636656','-H','Accept: application/octet-stream'])
  (OUT/'normal-summary.json').write_bytes(raw);assert sha(OUT/'normal-summary.json')==NORMAL_SHA
  normal=json.loads(raw)
  assert normal['run_id']==39882244224and normal['full_capture']and not normal['electrical_screen_passed']
  assert normal['sources_unchanged']and normal['native_exit_code']==0
  assert normal['preparation_source']['run']==PREP['run']
  assert normal['preparation_source']['summary_sha256']==PREP['summary_sha256']
  assert normal['preparation_source']['manifest_sha256']==PREP['parts_sha256']
  selected=['native/contract.json','whole8088/source/composed/composition.json','whole8088/source/interfaces.json','whole8088/source/composed/output8088-wire.spice']
  prepared,proof=reports.restore_report(PREP['group'],PREP['run'],PREP['summary_sha256'],PREP['parts_sha256'],OUT/'prepared',selected)
  assert prepared['source_unchanged']and prepared['core_counts']==dict(devices=8088,R=140222,C=99906)
  assert prepared['model_sha256']=='a9faee6c09dbaa599e8fac3051c0f778c5939479c6bc3c4769cff6763662168f'
  for name in selected:
   assert sha(OUT/'prepared'/name)==prepared['outputs'][name]
   assert normal['preparation_source']['restore']['selected_files'][name]['sha256']==prepared['outputs'][name]
  contract=json.loads((OUT/'prepared/native/contract.json').read_text())
  composition=json.loads((OUT/'prepared/whole8088/source/composed/composition.json').read_text())
  interfaces=json.loads((OUT/'prepared/whole8088/source/interfaces.json').read_text())
  review=normal['review'];r['mapping']=mapped(review,composition,interfaces,contract)
  r['source']=dict(run=39882244224,summary_sha256=NORMAL_SHA,prepared=PREP,restoration=proof)
  r['interfaces']=review['interfaces'];r['signals']=review['signals']
  r['controls']=[]
  for label in ['duplicate_native_id','wrong_hbt_model','missing_failed_measurement','wrong_physical_base','wrong_bench_identity','wrong_selector_connection','wrong_tail_connection']:
   c=copy.deepcopy(composition);i=copy.deepcopy(interfaces);v=copy.deepcopy(review);b=copy.deepcopy(contract)
   if label=='duplicate_native_id':c['device_records'][1]['native_id']=c['device_records'][0]['native_id']
   elif label=='wrong_hbt_model':
    next(d for d in c['device_records']if d['model'].lower()=='npn13g2')['model']='cap_cmim'
   elif label=='missing_failed_measurement':v['failed_hbts'].pop(next(iter(v['failed_hbts'])))
   elif label=='wrong_physical_base':next(iter(i['references'].values()))['terminals'][0]['node']='0'
   elif label=='wrong_bench_identity':b['hbt']['wrong_identity']=b['hbt'].pop(next(iter(b['hbt'])))
   else:
    role='selector'if label=='wrong_selector_connection'else'tail'
    name=next(n for n,x in r['mapping']['native_topology_roles'].items()if x['kind']==role)
    d=next(d for d in c['device_records']if 'xtree.'+d['instance'].lower()==name)
    next(t for t in d['terminals']if t['terminal']=='C')['native_cluster']=-1
   try:mapped(v,c,i,b)
   except (AssertionError,KeyError,StopIteration):r['controls'].append(dict(name=label,rejected=True))
   else:raise AssertionError('Accepted '+label)
  assert len(r['controls'])==7
  assert all(sha(OUT/'prepared'/name)==prepared['outputs'][name]for name in selected)
  assert sha(OUT/'normal-summary.json')==NORMAL_SHA
  r['sources_unchanged']=True;r['status']='PASS_EXISTING_FULL_TX_FAILURES_MAPPED_TO_ACTUAL_NATIVE_DEVICES_NOT_ELECTRICAL_ACCEPTANCE'
 except BaseException as e:
  import traceback
  r.update(status='FAIL_NATIVE_FAILURE_MAPPING',error=repr(e),traceback=traceback.format_exc());raise
 finally:save();print(r['status'],flush=True)
if __name__=='__main__':main()
