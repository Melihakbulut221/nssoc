#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read only already measured rail events and bind them to original native anchors."""
import copy,hashlib,json,os,traceback
from pathlib import Path
from collections import defaultdict
import compare_cloud_routed_endpoints as reports
import cloud_tx_output8088_return64via3_diagnosis as source
import cloud_tx_output8088_return_paths as solver
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-return64via3-rail-targets'
def sha(p):return source.sha(p)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,no_new_simulation=True)
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  methods=json.loads((ROOT/'scripts/tx-output8088-return64via3-rail-targets-methods.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in methods.items())
  run=source.api('actions/runs/40068199314')
  assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='4e1a9165eb9b1ec09a47aa8c482f8516d53a624e'
  selected=['all-rail-plane-statistics.json','failed84-rail-events.json','failed32-cmos-cm-rail-events.json',
   'physical/composed/composition.json','physical/composed/output8088-wire.spice']
  prior,proof=reports.restore_report('tx-output8088-return64via3-rails',40068199314,
   '542991b89019f352bf1efc3f19466cde6a8c23998eac8f76fbb431089cb85b33',
   'a46d1aaa2b6ba99aa33cd4dd273f15d35afc2035ef1221d9cfd6d2ddbef274f3',OUT/'observation',selected)
  assert prior['status']=='COMPLETE_EXACT_FULL_TX_RAIL_BODY_AND_FAILED_ENDPOINT_DIAGNOSIS_NOT_REPAIR'
  assert prior['original_review_exactly_reproduced']and prior['sources_unchanged']
  anchor_names=['composed/intrinsic/source/anchors.json']
  physical,physical_proof=reports.restore_report('tx-output8088-power128return64via3-interfaces',40003582105,
   '48aa3b39422955f78d94749252eb8a545153979141d1bb7cd7f9f207c6e3949b',
   '8ecda0d1aca0a3afae744bf0ce826746ac016c4571f65b0f167e5e007eba6cb5',OUT/'native',anchor_names)
  assert physical['source_head']=='59868b07b123933168a9e5b201236480fb67827c'and physical['sources_unchanged']
  comp=json.loads((OUT/'observation/physical/composed/composition.json').read_text())
  rails=json.loads((OUT/'observation/all-rail-plane-statistics.json').read_text())
  failures=json.loads((OUT/'observation/failed84-rail-events.json').read_text())
  cm=json.loads((OUT/'observation/failed32-cmos-cm-rail-events.json').read_text())
  anchors=json.loads((OUT/'native/composed/intrinsic/source/anchors.json').read_text())
  ar={a['label']:a for a in anchors['anchors']};assert len(ar)==13370
  records={d['instance'].lower():d for d in comp['device_records']};assert len(records)==8088
  bynode=defaultdict(list)
  def terminal(n):return n.removeprefix('xtree.')
  for d in records.values():
   for term in d['terminals']:
    if term['reference_label']is not None:
     a=ar[term['reference_label']]
     assert a['native_cluster']==term['native_cluster']
     assert comp['wire_node_map'][term['reference_label']]==term['node']
     bynode[term['node']].append(dict(instance=d['instance'],terminal=term['terminal'],native_id=d['native_id'],
      model=d['model'],reference_label=term['reference_label'],native_cluster=term['native_cluster'],
      metal=a['metal'],point_dbu=a['point_dbu']))
  def location(n):
   assert terminal(n)in bynode
   return bynode[terminal(n)]
  result['source']=proof;result['physical_source']=physical_proof
  result['rail_extreme_locations']={}
  for rail,r in rails.items():
   result['rail_extreme_locations'][rail]={k:dict(node=r[k],statistics=r['planes'][r[k]],locations=location(r[k]))for k in ('lowest','highest')}
  result['final_failed_device_rail_events']={}
  for name in ['xtree.xd5667','xtree.xd5674','xtree.xd5668','xtree.xd5669','xtree.xd5675','xtree.xd5676']:
   row=copy.deepcopy(failures[name])
   for entry in row['rail_neighborhood']:entry['locations']=location(entry['node'])
   result['final_failed_device_rail_events'][name]=row
  result['worst_cmos_local_rails']={}
  for name in ['d0','d1','d7','d31']:
   row=copy.deepcopy(cm[name])
   for event in ('rail_before','rail_after'):
    for entry in row[event]:entry['locations']=location(entry['node'])
   result['worst_cmos_local_rails'][name]=row
  # Exact unchanged physical resistance graph. The solver's historical 'avss'
  # root is renamed injectively for each selected rail; no circuit record changes.
  model=OUT/'observation/physical/composed/output8088-wire.spice'
  assert sha(model)=='218d5e41762cf7dfca7e57ad88def18cfd2fbd045a57a249e3789f6c38059649'
  edges=[]
  for line in model.read_text().splitlines():
   fields=line.lower().split()
   if fields and fields[0].startswith('r'):
    assert len(fields)==4 and float(fields[3])>0;edges.append(fields)
  assert len(edges)==140222
  parent={}
  def root(n):
   parent.setdefault(n,n)
   while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
   return n
  for _,a,b,_ in edges:parent[root(a)]=root(b)
  result['resistance_controls']=solver.resistance_controls()
  result['target_dc_resistance']={}
  reverse={v.lower():k for k,v in comp['wire_node_map'].items()}
  for rail in ('avdd','avss','dvdd'):
   candidates=[terminal(rails[rail]['lowest'if rail!='avss'else'highest'])]
   if rail=='avss':candidates+=['w0003496','w0003517']
   # Include direct first-device-hop CMOS driver power planes, without treating
   # the surrounding next-stage network as a physically nearest conductor.
   for label in ('d0','d31'):
    same=[x for x in cm[label]['rail_before']if x['rail']==rail and len(x['path'])==1]
    candidates += [terminal(x['node'])for x in same]
   candidates=list(dict.fromkeys(candidates))
   assert all(root(n)==root(rail)for n in candidates)
   subset=[e for e in edges if root(e[1])==root(rail)]
   def alias(n):return 'avss'if n==rail else 'node:'+n
   modified=[[name,alias(a),alias(b),value]for name,a,b,value in subset]
   assert len({alias(n)for e in subset for n in e[1:3]})==len({n for e in subset for n in e[1:3]})
   result_dc=solver.path_and_resistance(modified,[alias(n)for n in candidates])
   for n,row in zip(candidates,result_dc['targets'],strict=True):
    row['actual_target']=n;row['locations']=location(n)
    for key in ('dominant_unit_injection_segments','largest_path_resistors','full_path'):
     for e in row[key]:
      for terminal_key in ('a','b'):
       old=e[terminal_key];e[terminal_key]=rail if old=='avss'else old.removeprefix('node:')
      e['original_extractor_nodes']=[reverse[e['a']],reverse[e['b']]]
   result_dc['actual_ground']=rail
   result_dc['alias_scope']='Injective naming for the selected unchanged native R component only; no model or resistor value modified.'
   result['target_dc_resistance'][rail]=result_dc
  assert all(sha(OUT/'observation'/p)==prior['outputs'][p]for p in selected)
  assert all(sha(ROOT/p)==h for p,h in methods.items())
  result.update(status='COMPLETE_MEASURED_RAIL_TARGETS_BOUND_TO_ACTUAL_NATIVE_ANCHORS_NOT_REPAIR',
   sources_unchanged=True,scope='Existing full-wave measurements and exact native linear DC resistance only. No new simulation, modified physical RC, fitted data/clock or electrical acceptance.')
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save()
if __name__=='__main__':main()
