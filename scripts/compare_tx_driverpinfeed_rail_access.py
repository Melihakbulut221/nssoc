#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only exact DC access comparison of real original and repaired native rails."""
import argparse,copy,hashlib,json,os,subprocess,traceback
from collections import Counter,defaultdict
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_output8088_return_sensitivity as solver
REPO='repos/Melihakbulut221/nssoc/'
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def asset(a,h):
 b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a),'-H','Accept: application/octet-stream'])
 assert hashlib.sha256(b).hexdigest()==h
 return json.loads(b)
def dataset(comp,anchors,model):
 counts=comp['counts'];assert counts['devices']==8088 and counts['physical_ports']==165 and counts['external_ports']==166
 assert counts['terminals']==28620 and counts['metal_reference_planes']==13370 and counts['body_nets']==65 and counts['conductors']==703
 refs={a['label']:a for a in anchors['anchors']};assert len(refs)==13370
 records={r['native_id']:r for r in comp['device_records']};assert len(records)==8088
 public={a['name'].lower():refs[a['reference_label']]['native_cluster']for a in anchors['public']}
 rows=anchors['rows'];assert len(rows)==28620
 clusters={public[rail]:rail for rail in ('avdd','avss','dvdd')};assert len(clusters)==3
 indexed=defaultdict(list)
 def geom(label):
  a=refs[label];return [a['metal'],*a['point_dbu']]
 # Body nets are identified by the full geometry/parameter signatures of
 # their attached native devices, not extraction cluster numbering.
 body_members=defaultdict(list)
 for d in records.values():
  signature=dict(model=d['model'].lower(),parameters=d['parameters'],metal_terminals=[
   [t['terminal'],t['disposition'],geom(t['reference_label'])]for t in d['terminals']if t['reference_label']is not None])
  for t in d['terminals']:
   if t['reference_label']is None:body_members[t['native_cluster']].append([t['terminal'],signature])
 assert len(body_members)==65
 body_identity={cluster:hashlib.sha256(json.dumps(sorted(json.dumps(v,sort_keys=True)for v in members)).encode()).hexdigest()
  for cluster,members in body_members.items()}
 assert len(set(body_identity.values()))==65
 def fingerprint(d):
  return dict(model=d['model'].lower(),parameters=d['parameters'],terminals=[
   dict(terminal=t['terminal'],disposition=t['disposition'],
    identity=geom(t['reference_label'])if t['reference_label']is not None else ['retained_full_body_topology',body_identity[t['native_cluster']]])
   for t in d['terminals']])
 for row in rows:
  if 'reference_label'not in row:continue
  a=refs[row['reference_label']];d=records[row['device']]
  assert a['native_cluster']==row['native_cluster']
  key=(row['model'].lower(),row['terminal'],a['metal'],*a['point_dbu'])
  indexed[key].append(dict(row=row,anchor=a,record=d,fingerprint=fingerprint(d),rail=clusters.get(a['native_cluster'])))
 edges=[];actual=Counter()
 for line in model.read_text().splitlines():
  f=line.lower().split()
  if not f or f[0][0]in ('.','*'):continue
  actual[f[0][0]]+=1
  if f[0].startswith('r'):assert len(f)==4 and float(f[3])>0;edges.append(f)
 assert actual==dict(x=8088,r=counts['R'],c=counts['C'])
 parent={}
 def root(n):
  parent.setdefault(n,n)
  while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
  return n
 for _,a,b,_ in edges:parent[root(a)]=root(b)
 assert len({root(n)for n in parent})==703
 for a in anchors['public']:
  assert comp['wire_node_map'][a['reference_label']].lower()==a['name'].lower()
 return dict(comp=comp,refs=refs,index=indexed,edges=edges,root=root,records=records)
def bind(data,target,expected=None):
 key=(target['model'].lower(),target['terminal'],target['metal'],*target['point_dbu'])
 matches=[r for r in data['index'].get(key,[])if r['rail']==target['rail']]
 assert len(matches)==1,('Ambiguous or missing actual native terminal geometry',target,len(matches))
 row=matches[0]
 if expected is not None:assert row['fingerprint']==expected['fingerprint'],'Full original native device geometry/parameter fingerprint changed'
 node=data['comp']['wire_node_map'][row['anchor']['label']].lower()
 assert data['root'](node)==data['root'](target['rail'])
 return dict(row,node=node)
def resistance(data,targets,bound):
 output={}
 for rail in ('avdd','avss'):
  names=[name for name,t in targets.items()if t['rail']==rail]
  component=[e for e in data['edges']if data['root'](e[1])==data['root'](rail)]
  def alias(n):return 'avss'if n==rail else'node:'+n
  edges=[[name,alias(a),alias(b),value]for name,a,b,value in component]
  assert len({alias(n)for e in component for n in e[1:3]})==len({n for e in component for n in e[1:3]})
  report=solver.path_and_resistance(edges,[alias(bound[name]['node'])for name in names])
  reverse={v.lower():k for k,v in data['comp']['wire_node_map'].items()}
  for name,item in zip(names,report['targets'],strict=True):
   item['actual_target']=bound[name]['node'];item['actual_reference_label']=bound[name]['anchor']['label']
   item['actual_ground']=rail
   for key in ('dominant_unit_injection_segments','largest_path_resistors','full_path'):
    for e in item[key]:
     for k in ('a','b'):e[k]=rail if e[k]=='avss'else e[k].removeprefix('node:')
     e['original_extractor_nodes']=[reverse[e['a']],reverse[e['b']]]
   output[name]=item
  report['target_order']=names;report['actual_ground']=rail
  report['scope']='Injective naming of unchanged native R nodes for the existing solver. No resistor, geometry or circuit parameter changed.'
  output['_'+rail]=report
 return output
def main():
 p=argparse.ArgumentParser();p.add_argument('--composition',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 out=a.output;out.mkdir(parents=True,exist_ok=False);reports.OUT=out
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,electrical_accepted=False,full_phy_accepted=False,no_new_simulation=True)
 def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 protected={}
 try:
  physical=asset(671499822,'b6680151c8741fb11a4a5c6fbbe24815850a7de510dd6d72dc38fbf0625662d9')
  assert physical['source_head']=='74bc46d2e9518821a12c66b6a071add579ccf2df'and physical['sources_unchanged']
  assert physical['status']=='PASS_ACTUAL128_DRIVER_PINFEEDS_NATIVE_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC'
  assert physical['geometry']['route_count']==128
  names=['composed/composition.json','composed/output8088-wire.spice','composed/intrinsic/source/anchors.json']
  previous,proof=reports.restore_report('tx-output8088-power128return64via3-interfaces',40003582105,
   '48aa3b39422955f78d94749252eb8a545153979141d1bb7cd7f9f207c6e3949b',
   '8ecda0d1aca0a3afae744bf0ce826746ac016c4571f65b0f167e5e007eba6cb5',out/'before',names)
  assert previous['source_head']=='59868b07b123933168a9e5b201236480fb67827c'and previous['sources_unchanged']
  protected.update({out/'before'/n:previous['outputs'][n]for n in names})
  oldroot=out/'before/composed';assert digest(oldroot/'output8088-wire.spice')=='218d5e41762cf7dfca7e57ad88def18cfd2fbd045a57a249e3789f6c38059649'
  fresh=json.loads((a.composition/'result.json').read_text())
  assert fresh['status']=='PASS_ACTUAL_FULL8088_DRIVERPINFEED_PARENT_WIRE_COMPOSITION_AND25_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
  assert fresh['sources_unchanged']and len(fresh['controls'])==25
  selected=['composition.json','output8088-wire.spice','intrinsic/source/anchors.json']
  protected.update({a.composition/n:fresh['outputs'][n]for n in selected})
  assert all(digest(p)==h for p,h in protected.items())
  before=dataset(json.loads((oldroot/'composition.json').read_text()),json.loads((oldroot/'intrinsic/source/anchors.json').read_text()),oldroot/'output8088-wire.spice')
  after=dataset(json.loads((a.composition/'composition.json').read_text()),json.loads((a.composition/'intrinsic/source/anchors.json').read_text()),a.composition/'output8088-wire.spice')
  targets={}
  for route in physical['geometry']['routes']:
   t=route['terminal'];anchor=route['anchor'];assert t['reference_label']==anchor['label']
   name=route['driver']+':'+route['rail']
   assert name not in targets
   targets[name]=dict(model=t['model'],terminal=t['terminal'],metal=anchor['metal'],point_dbu=anchor['point_dbu'],rail=route['rail'],old_reference_label=anchor['label'],original_native_id=t['device'])
  assert len(targets)==128 and Counter(t['rail']for t in targets.values())==dict(avdd=64,avss=64)
  for name,label in [('final_tail_xd5667','A0856'),('final_tail_xd5674','A0877')]:
   anchor=before['refs'][label]
   targets[name]=dict(model='npn13g2',terminal='E',metal=anchor['metal'],point_dbu=anchor['point_dbu'],rail='avss',old_reference_label=label)
  old={name:bind(before,t)for name,t in targets.items()}
  assert all(row['anchor']['label']==targets[n]['old_reference_label']for n,row in old.items())
  new={name:bind(after,t,old[name])for name,t in targets.items()}
  controls=[]
  original=targets['d0p:avdd']
  for fault in ('wrong_model','wrong_terminal','wrong_point','wrong_metal','wrong_rail'):
   t=copy.deepcopy(original)
   if fault=='wrong_model':t['model']='missing_model'
   elif fault=='wrong_terminal':t['terminal']='missing_terminal'
   elif fault=='wrong_point':t['point_dbu'][0]+=1
   elif fault=='wrong_metal':t['metal']=-1
   else:t['rail']='avss'
   try:bind(after,t,old['d0p:avdd'])
   except AssertionError:controls.append(dict(name=fault,rejected=True))
   else:raise AssertionError('Accepted corrupt original terminal identity '+fault)
  bad=copy.deepcopy(old['d0p:avdd']);bad['fingerprint']['parameters']['wrong_parameter']='1'
  try:bind(after,original,bad)
  except AssertionError:controls.append(dict(name='wrong_intrinsic_parameter',rejected=True))
  else:raise AssertionError('Accepted corrupt full-device fingerprint')
  result['identity_controls']=controls;result['analytic_controls']=solver.resistance_controls();save()
  measured_before=resistance(before,targets,old);measured_after=resistance(after,targets,new)
  historical=asset(671444609,'96d047e42afc94dd8b976aa5b95bab44ee4a9ac6a62c42dbbecdf181660ccba5')
  # The historical saved-wave target diagnosis is independently reproduced at
  # its eight selected driver ports and two final-tail emitter points.
  checked=[]
  lookup={row['anchor']['label']:name for name,row in old.items()}
  for rail in ('avdd','avss'):
   for row in historical['target_dc_resistance'][rail]['targets']:
    label=row['locations'][0]['reference_label'];assert label in lookup
    name=lookup[label];got=measured_before[name]['effective_self_resistance_ohm'];want=row['effective_self_resistance_ohm']
    assert abs(got-want)<1e-7*max(1.,want)
    checked.append(dict(name=name,original_reference_label=label,expected_ohm=want,recomputed_ohm=got))
  assert len(checked)==10
  changes={}
  for name in targets:
   b=measured_before[name]['effective_self_resistance_ohm'];n=measured_after[name]['effective_self_resistance_ohm']
   changes[name]=dict(target=targets[name],before_ohm=b,after_ohm=n,delta_ohm=n-b,reduction_percent=(b-n)/b*100,
    before_native_id=old[name]['record']['native_id'],after_native_id=new[name]['record']['native_id'],
    before_reference_label=old[name]['anchor']['label'],after_reference_label=new[name]['anchor']['label'],
    full_original_device_fingerprint=old[name]['fingerprint'])
  summary={}
  for rail in ('avdd','avss'):
   selected=[v for n,v in changes.items()if n.endswith(':'+rail)]
   summary[rail]=dict(driver_terminals=len(selected),before_min_ohm=min(v['before_ohm']for v in selected),before_max_ohm=max(v['before_ohm']for v in selected),
    after_min_ohm=min(v['after_ohm']for v in selected),after_max_ohm=max(v['after_ohm']for v in selected),min_reduction_percent=min(v['reduction_percent']for v in selected),
    reduced_count=sum(v['after_ohm']<v['before_ohm']for v in selected))
  summary['final_tails']={n:v for n,v in changes.items()if n.startswith('final_tail')}
  for name,data in [('before-resistance',measured_before),('after-resistance',measured_after),('terminal-comparison',changes)]:
   (out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
  assert all(digest(p)==h for p,h in protected.items())
  result.update(status='COMPLETE_EXACT128_DRIVER_AND2_TAIL_RAIL_RESISTANCE_COMPARISON_NOT_ELECTRICAL_ACCEPTANCE',
   sources_unchanged=True,source=proof,summary=summary,original_ten_results_reproduced=checked,counts=dict(drivers=128,final_tails=2,identity_controls=6),
   scope='Exact native metal DC effective resistance only. No intrinsic/device-access/substrate/RF equivalence, transient improvement or PHY acceptance claimed.')
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  result['outputs']={str(p.relative_to(out)):digest(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
