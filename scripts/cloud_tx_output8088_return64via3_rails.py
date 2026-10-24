#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe original full TX rail/body planes and exact failed-terminal neighborhoods."""
import argparse,copy,hashlib,json,os,traceback
from collections import defaultdict
from pathlib import Path
import numpy as np
import cloud_tx_output8088_return64via3_diagnosis as original
import compare_cloud_routed_endpoints as reports
from cloud_tx_stream import read_streamed_wave
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-return64via3-rails'
DIAG=dict(run=40066102059,head='213b5a6a2dd684b50c5bfa23ec7736f7e79469ed',
 asset=671380895,sha256='14dea460a650fe79a94874fb72ba54c4985543427823a308d43e68dfd9f9466f')
PHYS=dict(run=40003582105,head='59868b07b123933168a9e5b201236480fb67827c',
 group='tx-output8088-power128return64via3-interfaces',
 summary='48aa3b39422955f78d94749252eb8a545153979141d1bb7cd7f9f207c6e3949b',
 parts='8ecda0d1aca0a3afae744bf0ce826746ac016c4571f65b0f167e5e007eba6cb5')
def sha(p):return original.sha(p)
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def binding(comp,native,interfaces,contract):
 assert comp['counts']==dict(devices=8088,R=140222,C=99906,external_ports=166,physical_ports=165,metal_reference_planes=13370,body_nets=65,conductors=703,terminals=28620)
 assert native['counts']==dict(devices=8088,terminals=28620,ports=165,body_nets=65,wire_nets=703,mos_fingers=5376)
 assert interfaces['modes']['wire']==contract['interface_probes']
 records={d['instance'].lower():d for d in comp['device_records']}
 byid={d['id']:d for d in native['devices']}
 assert len(records)==len(byid)==8088
 ports={p['name'].lower():p['cluster']for p in native['ports']}
 assert len(ports)==165 and set(ports)==set(comp['interface'])-{'wire_cref'}
 body=set(native['body_clusters']);assert len(body)==65
 assert set(map(int,comp['body_node_map']))==body
 public=set(comp['interface'])
 def logical(n):
  n=n.lower();return '0'if n in ('avss','sub','wire_cref')else n if n in public else 'xtree.'+n
 count=0;hbt=0;mos=0
 for key,d in records.items():
  n=byid[d['native_id']];assert d['model'].lower()==n['model'].lower()
  assert set(t['terminal']for t in d['terminals'])==set(n['terminals'])
  for term in d['terminals']:
   actual=n['terminals'][term['terminal']]
   assert term['native_cluster']==actual['cluster'] and term['disposition']==actual['disposition']
   if term['native_cluster']in body:
    assert term['node']==comp['body_node_map'][str(term['native_cluster'])]
    assert term['reference_label']is None
   else:
    assert term['reference_label']==actual['reference_label']
    assert term['node']==comp['wire_node_map'][term['reference_label']]
   count+=1
  name='xtree.'+key
  if d['model'].lower()=='npn13g2':
   assert [x['terminal']for x in d['terminals']]==['C','B','E','S']
   want=dict(model='npn13g2',terminals=[logical(x['node'])for x in d['terminals']],nx=int(d['parameters']['nx']))
   assert contract['hbt'][name]==want;hbt+=1
  elif d['model'].lower()in ('sg13_lv_nmos','sg13_lv_pmos','sg13_hv_nmos'):
   assert [x['terminal']for x in d['terminals']]==['D','G','S','B']
   assert contract['mos'][name]==dict(model=d['model'].lower(),terminals=[logical(x['node'])for x in d['terminals']]);mos+=1
 assert count==28620 and hbt==593 and mos==5376
 assert len(contract['hbt'])==604 and len(contract['mos'])==5376
 return records,ports,body,logical
def binding_controls(comp,native,interfaces,contract):
 binding(comp,native,interfaces,contract);rejected=[]
 for fault in ('changed-native-cluster','missing-device','changed-body-node','changed-reference-plane',
               'changed-hbt-emitter-count','swapped-hbt-cb','changed-interface'):
  cc=copy.deepcopy(comp);ii=copy.deepcopy(interfaces)
  target=next(d for d in cc['device_records']if d['model'].lower()=='npn13g2'and d['terminals'][0]['node']!=d['terminals'][1]['node'])
  if fault=='changed-native-cluster':target['terminals'][0]['native_cluster']=-12345
  elif fault=='missing-device':cc['device_records'].pop()
  elif fault=='changed-body-node':target['terminals'][-1]['node']='avss'
  elif fault=='changed-reference-plane':target['terminals'][0]['reference_label']='P_avss'
  elif fault=='changed-hbt-emitter-count':target['parameters']['nx']='999'
  elif fault=='swapped-hbt-cb':target['terminals'][0],target['terminals'][1]=target['terminals'][1],target['terminals'][0]
  else:ii['modes']['wire'][next(iter(ii['modes']['wire']))]=['0']
  try:binding(cc,native,ii,contract)
  except (AssertionError,KeyError):rejected.append(fault)
  else:raise AssertionError('Accepted binding fault '+fault)
 return rejected
def statistics(matrix,indices,t,first):
 # Visit every native active row once in bounded blocks; no column/sample decimation.
 indices=np.asarray(indices);n=len(indices)
 lows=np.full(n,np.inf);highs=np.full(n,-np.inf);sums=np.zeros(n);lowi=np.zeros(n,dtype=np.int64);highi=lowi.copy()
 for a in range(first,len(t),512):
  block=np.asarray(matrix[a:min(a+512,len(t)),indices]);assert block.ndim==2 and block.shape[1]==n
  assert np.isfinite(block).all()
  il=block.argmin(axis=0);ih=block.argmax(axis=0);cols=np.arange(n)
  lv=block[il,cols];hv=block[ih,cols];take=lv<lows;lowi[take]=a+il[take];lows=np.minimum(lows,lv)
  take=hv>highs;highi[take]=a+ih[take];highs=np.maximum(highs,hv);sums+=block.sum(axis=0)
 return [dict(minimum_v=float(lows[i]),maximum_v=float(highs[i]),mean_v=float(sums[i]/(len(t)-first)),
  minimum_time_s=float(t[lowi[i]]),maximum_time_s=float(t[highi[i]]),native_rows=int(len(t)-first))for i in range(n)]
def statistic_controls():
 t=np.array([0.,1.,2.,3.]);m=np.array([[99.,99.],[4.,2.],[1.,5.],[3.,-1.]])
 got=statistics(m,[1,0],t,1)
 assert got[0]==dict(minimum_v=-1.,maximum_v=5.,mean_v=2.,minimum_time_s=3.,maximum_time_s=2.,native_rows=3)
 assert got[1]==dict(minimum_v=1.,maximum_v=4.,mean_v=8/3,minimum_time_s=2.,maximum_time_s=1.,native_rows=3)
 bad=m.copy();bad[2,0]=np.nan
 try:statistics(bad,[0],t,1)
 except AssertionError:pass
 else:raise AssertionError('Accepted nonfinite rail sample')
 return dict(all_native_rows_and_reordered_columns_verified=True,nonfinite_rejected=True,synthetic_only=True)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(exist_ok=False);original.OUT=OUT;reports.OUT=OUT
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
  electrical_accepted=False,no_new_simulation=True,source_capture=original.SPEC)
 def save():write(OUT/'result.json',result)
 save()
 try:
  methods=json.loads((ROOT/'scripts/tx-output8088-return64via3-rails-methods.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in methods.items());result['methods']=methods
  result['source_controls']=original.controls();result['statistics_controls']=statistic_controls()
  report=original.restore(result);save()
  diag_run=original.api('actions/runs/'+str(DIAG['run']))
  assert diag_run['head_sha']==DIAG['head'] and diag_run['status']=='completed' and diag_run['conclusion']=='success' and diag_run['run_attempt']==1
  previous=json.loads(original.small(DIAG['asset'],DIAG['sha256']))
  assert previous['status']=='COMPLETE_REJECTED_FULL_TX_DIAGNOSIS_NOT_REPAIR_OR_PHY_ACCEPTANCE'
  assert previous['source']==original.SPEC and previous['original_review_exactly_reproduced']
  case=OUT/'capture/work';contract=json.loads((case/'contract.json').read_text())
  assert original.tree.review(case,contract)==report['review'],'Original complete engineering gates changed'
  result['original_review_exactly_reproduced']=True
  run=original.api('actions/runs/'+str(PHYS['run']))
  assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==PHYS['head']
  selected=['interfaces.json','composed/output8088-wire.spice','composed/composition.json','composed/intrinsic/native.json']
  physical,proof=reports.restore_report(PHYS['group'],PHYS['run'],PHYS['summary'],PHYS['parts'],OUT/'physical',selected)
  assert physical['source_head']==PHYS['head']and physical['sources_unchanged']
  assert physical['status']=='PASS_ACTUAL8088_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_FOUR_OUTPUT_PORTS_REQUIRES_LOADED_WAVES'
  assert all(sha(OUT/'physical'/p)==physical['outputs'][p]for p in selected)
  assert physical['outputs']['composed/output8088-wire.spice']=='218d5e41762cf7dfca7e57ad88def18cfd2fbd045a57a249e3789f6c38059649'
  comp=json.loads((OUT/'physical/composed/composition.json').read_text())
  native=json.loads((OUT/'physical/composed/intrinsic/native.json').read_text())
  interfaces=json.loads((OUT/'physical/interfaces.json').read_text())
  records,ports,body,logical=binding(comp,native,interfaces,contract)
  result['physical_binding_controls']=binding_controls(comp,native,interfaces,contract)
  result['physical_source']=proof
  t,values,transport=read_streamed_wave(case/'wave.raw',contract['vectors'],34e-9,contract['condition']['step_ps']*1e-12)
  assert transport==report['review']['capture_transport']
  assert transport['columns']==14182 and transport['header_rows']==77708
  result['capture_transport']={k:v for k,v in transport.items()if k!='logical_vector_order'}
  names=transport['logical_vector_order'];columns={n:i for i,n in enumerate(names)};first=int(np.searchsorted(t,2e-9))
  matrix=np.memmap(case/'wave.raw',mode='r',dtype='<f8',offset=transport['header_bytes'],shape=(len(t),len(names)))
  cluster_terms=defaultdict(list);by_node=defaultdict(list)
  for key,d in records.items():
   for term in d['terminals']:
    rec=dict(instance=key,model=d['model'],terminal=term['terminal'],native_cluster=term['native_cluster'],
     reference_label=term['reference_label'],node=logical(term['node']))
    cluster_terms[term['native_cluster']].append(rec);by_node[rec['node']].append(rec)
  rail_names=['avdd','avss','dvdd','tvdd','sub'];rail_clusters={ports[name]:name for name in rail_names}
  assert len(rail_clusters)==len(rail_names)and not(set(rail_clusters)&body)
  selected_nodes=sorted({r['node']for k in [*rail_clusters,*body]for r in cluster_terms[k]}-{'0'})
  assert selected_nodes and all('v('+n+')'in columns for n in selected_nodes)
  rows=statistics(matrix,[columns['v('+n+')']for n in selected_nodes],t,first)
  stats=dict(zip(selected_nodes,rows,strict=True))
  zero=dict(minimum_v=0.,maximum_v=0.,mean_v=0.,minimum_time_s=float(t[first]),maximum_time_s=float(t[first]),native_rows=len(t)-first)
  stats['0']=zero
  def voltage(node,index):return 0. if node=='0'else float(matrix[index,columns['v('+node+')']])
  rails={}
  for cluster,name in rail_clusters.items():
   entries={row['node'] for row in cluster_terms[cluster]}
   assert entries
   ordered=sorted(entries,key=lambda n:stats[n]['minimum_v'])
   rails[name]=dict(native_cluster=cluster,terminal_planes=len(entries),
    lowest=ordered[0],highest=max(entries,key=lambda n:stats[n]['maximum_v']),
    planes={n:dict(**stats[n],terminals=by_node[n])for n in ordered})
  write(OUT/'all-rail-plane-statistics.json',rails)
  result['rail_summary']={name:dict(native_cluster=r['native_cluster'],terminal_planes=r['terminal_planes'],
   lowest=dict(node=r['lowest'],**stats[r['lowest']]),highest=dict(node=r['highest'],**stats[r['highest']]))for name,r in rails.items()}
  bodies={str(cluster):dict(nodes={n:stats[n]for n in sorted({r['node']for r in cluster_terms[cluster]})},
   device_terminals=len(cluster_terms[cluster]))for cluster in sorted(body)}
  result['body_planes']=bodies
  # Topological neighborhoods retain native clusters, finite wire planes and separate voltages.
  # Traversing an intrinsic device does not claim conductance or physical distance.
  def nearest_rail_paths(starts,max_hops=2):
   frontier={k:[]for k in starts if k not in body};seen=set(frontier);found={}
   for depth in range(max_hops+1):
    following={}
    for cluster,path in frontier.items():
     if cluster in rail_clusters:
      # Existing rail endpoints can contain thousands of remote terminals; callers
      # already report their exact starting plane and the whole rail statistics.
      continue
     if depth==max_hops:continue
     for attached in cluster_terms[cluster]:
      d=records[attached['instance']]
      if d['model'].lower()in ('ptap1','ntap1'):continue
      for end in d['terminals']:
       target=end['native_cluster']
       if target==cluster or target in body:continue
       edge=dict(instance=attached['instance'],from_terminal=attached['terminal'],to_terminal=end['terminal'],
        from_cluster=cluster,to_cluster=target)
       route=path+[edge]
       if target in rail_clusters:
        n=logical(end['node']);key=(rail_clusters[target],n)
        if key not in found or len(route)<len(found[key]['path']):
         found[key]=dict(rail=key[0],node=n,reference_label=end['reference_label'],path=route)
       elif target not in seen:
        following.setdefault(target,route)
    seen.update(following);frontier=following
   return list(found.values())
  def rail_event(paths,index):
   return [dict(**p,voltage_v=voltage(p['node'],index),active_statistics=stats[p['node']])for p in paths]
  failure={}
  for name,old in previous['failed_hbts_at_native_times'].items():
   d=records[name.removeprefix('xtree.')];assert old['device']==contract['hbt'][name]
   peak=old['violation_times']['min_post_vce']['peak'];at=peak['time_s'];index=int(np.searchsorted(t,at));assert float(t[index])==at
   terminals={x['terminal']:dict(node=logical(x['node']),native_cluster=x['native_cluster'],reference_label=x['reference_label'],
    voltage_v=voltage(logical(x['node']),index))for x in d['terminals']}
   assert terminals['C']['voltage_v']-terminals['E']['voltage_v']==peak['vce']
   assert terminals['B']['voltage_v']-terminals['E']['voltage_v']==peak['vbe']
   starts={x['native_cluster']for x in d['terminals']if x['terminal']!='S'}
   paths=nearest_rail_paths(starts)
   failure[name]=dict(time_s=at,nx=old['device']['nx'],minimum_vce_v=peak['vce'],terminals=terminals,
    body_active_statistics=stats[terminals['S']['node']],rail_neighborhood=rail_event(paths,index),
    path_scope='All first-discovered shortest paths within two intrinsic-device hops; not a conductance/causality model.')
  assert len(failure)==84
  write(OUT/'failed84-rail-events.json',failure)
  result['failed84_summary']={name:dict(time_s=x['time_s'],minimum_vce_v=x['minimum_vce_v'],
   collector_v=x['terminals']['C']['voltage_v'],emitter_v=x['terminals']['E']['voltage_v'],
   body_v=x['terminals']['S']['voltage_v'],rail_endpoints=len(x['rail_neighborhood']))for name,x in failure.items()}
  cm={}
  for row in previous['all62_interface_pairs']:
   failed=[s for s in row['failed_samples']if not 1.8<=s['common_mode_v']<=2.05]
   if not failed:continue
   worst=min(failed,key=lambda s:s['common_mode_v'])
   lo=max(0,int(np.searchsorted(t,worst['time_s']))-1);hi=lo+1
   assert t[lo]<=worst['time_s']<=t[hi]
   pn,nn=worst['pnode'],worst['nnode']
   pv=float(np.interp(worst['time_s'],t,values['v('+pn+')']));nv=float(np.interp(worst['time_s'],t,values['v('+nn+')']))
   assert (pv+nv)/2==worst['common_mode_v']
   cluster_p={x['native_cluster']for x in by_node[pn]};cluster_n={x['native_cluster']for x in by_node[nn]}
   assert len(cluster_p)==len(cluster_n)==1
   paths=nearest_rail_paths(cluster_p|cluster_n)
   cm[row['input']]=dict(original_sample=worst,exact_native_bracket_s=[float(t[lo]),float(t[hi])],
    endpoints={pn:by_node[pn],nn:by_node[nn]},rail_before=rail_event(paths,lo),rail_after=rail_event(paths,hi))
  assert len(cm)==32
  write(OUT/'failed32-cmos-cm-rail-events.json',cm)
  result['failed32_cmos_summary']={n:dict(common_mode_v=x['original_sample']['common_mode_v'],
   time_s=x['original_sample']['time_s'],native_bracket_s=x['exact_native_bracket_s'],rail_endpoints=len(x['rail_before']))for n,x in cm.items()}
  assert sha(case/'wave.raw')==original.SPEC['raw_sha256']
  assert all(sha(OUT/'physical'/p)==physical['outputs'][p]for p in selected)
  assert all(sha(ROOT/p)==h for p,h in methods.items())
  result.update(status='COMPLETE_EXACT_FULL_TX_RAIL_BODY_AND_FAILED_ENDPOINT_DIAGNOSIS_NOT_REPAIR',
   sources_unchanged=True,all_original_engineering_gates_unchanged=True,
   scope='Full original 34ns waveform, every native active row for all original rail/body terminal planes. Finite-contact body voltage retained; no substrate-spreading/RF claim, fitted phase, altered clocks, circuit edit, new transient or electrical acceptance.')
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  # Existing immutable source release remains authoritative; never republish the large raw capture.
  for p in (OUT/'source.tar.gz',OUT/'capture/work/wave.raw'):
   if p.exists():p.unlink()
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');args=p.parse_args()
 if args.controls:print(json.dumps(dict(original=original.controls(),statistics=statistic_controls())))
 else:main()
