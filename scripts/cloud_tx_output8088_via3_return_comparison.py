#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure via3 return resistance from independently verified native RC graphs."""
import copy,hashlib,json,os,shlex,traceback
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_output8088_return_paths as solver
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-via3-return-comparison'
PINS={
 'return64':dict(run=39901168356,group='tx-output8088-power128return64-native-rc',
  head='eab4cea794ef2b27d693b0deb92ca7f6dc2b1361',
  summary='2b19f65083554c59fc5a171eb89e25ce51bcc5f8f3f31de42024a554e049d729',
  parts='95dcea693149c27b869c4bab5dea47424b4d7fffa5503df930705e2ac58b8a3f'),
 'via3':dict(run=39991332843,group='tx-output8088-power128return64via3-native-rc',
  head='b321d505ab8dcb63224a282ae7ce2ce3d0cce3b0',
  summary='0045abe297e091cb91c9233caa158460236d180515d7c510dc263250336cf848',
  parts='7c1dba647216c993b3aa6e9aac7a4532b2bf9bfefed589827408e39602fa6555')}
DEVICES=[5644,5667,5674]
def sha(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def endpoints(data):
 anchors={a['label']:a for a in data['anchors']}
 assert len(anchors)==len(data['anchors'])==13370
 public=[p for p in data['public']if p['name']=='avss'];assert len(public)==1
 ground=public[0]['reference_label'];assert ground=='P_avss'
 source=anchors[ground];selected=[]
 for did in DEVICES:
  rows=[r for r in data['rows']if r['device']==did and r['terminal']=='E']
  assert len(rows)==1;row=rows[0]
  assert row['model'].lower()=='npn13g2'and row['native_cluster']==source['native_cluster']
  a=anchors[row['reference_label']]
  for k in ['native_cluster','metal','point_dbu','wire_component']:assert a[k]==row[k],('Wrong physical endpoint',did,k)
  selected.append(dict(device=did,terminal='E',reference_label=row['reference_label'],
   native_cluster=row['native_cluster'],metal=row['metal'],point_dbu=row['point_dbu']))
 assert len({r['reference_label']for r in selected})==3
 return ground,selected
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert sha(ROOT/'scripts/cloud_tx_output8088_return_paths.py')=='787d722f90540bf764d2bcd88932444b2bb91a0651d4897376ec72cafac801b5'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
  electrical_accepted=False,qualified_pex=False,
  scope='Unit-current linear DC return resistance of actual extracted metal. No total loaded IR-drop, RF, device-access, body spreading, transient or full PHY acceptance.')
 def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  result['solver_controls']=solver.resistance_controls()
  variants={};edge_sets={}
  for label,pin in PINS.items():
   run=solver.api('actions/runs/'+str(pin['run']))
   assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==pin['head']
   directory=OUT/label
   prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary'],pin['parts'],directory,
    ['rc01/wires.spice','anchors03.json'])
   assert prior['source_head']==pin['head']and prior['sources_unchanged']
   assert prior['status'].startswith('PASS_FRESH_TX_OUTPUT8088_')
   assert prior['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
   assert len(prior['controls']['cases'])==13
   data=json.loads((directory/'anchors03.json').read_text())
   assert data['counts']==dict(devices=8088,terminals=28620,metal_terminals=20532,body_terminals=8088,public_ports=165,unique_reference_planes=13370,wire_components=703)
   ground,bound=endpoints(data);rejected=[]
   for fault in ['missing-emitter','wrong-reference','wrong-cluster']:
    bad=copy.deepcopy(data);row=next(r for r in bad['rows']if r['device']==DEVICES[0]and r['terminal']=='E')
    if fault=='missing-emitter':bad['rows'].remove(row)
    elif fault=='wrong-reference':row['reference_label']=bound[1]['reference_label']
    else:row['native_cluster']=-998
    try:endpoints(bad)
    except (AssertionError,KeyError):rejected.append(fault)
    else:raise AssertionError('Accepted corrupted physical terminal: '+fault)
   edges=[];capacitors=[];seen=set()
   for line in (directory/'rc01/wires.spice').read_text().splitlines():
    fields=shlex.split(line)
    if not fields or fields[0][0]not in 'RC':continue
    assert len(fields)==4 and fields[0]not in seen
    seen.add(fields[0])
    if fields[0][0]=='R':
     assert float(fields[3])>0
     edges.append([fields[0],*['avss'if n==ground else n for n in fields[1:3]],fields[3]])
    else:capacitors.append(fields)
   assert len(edges)==prior['audit']['actual_exported_resistors']
   assert len(capacitors)==prior['audit']['actual_exported_capacitors']
   dc=solver.path_and_resistance(edges,[r['reference_label']for r in bound])
   variants[label]=dict(source=proof,terminals=bound,dc=dc,actual_R=len(edges),actual_C=len(capacitors),
    actual_terminal_controls=rejected)
   edge_sets[label]={r[0]:r for r in edges}
   for name in ['rc01/wires.spice','anchors03.json']:assert sha(directory/name)==prior['outputs'][name]
  a=variants['return64'];b=variants['via3']
  assert a['terminals']==b['terminals'],'Physical observation planes changed'
  expected=[10.326486441861093,6.286958767402294,6.275982084626535]
  for row,value in zip(a['dc']['targets'],expected,strict=True):
   assert abs(row['effective_self_resistance_ohm']-value)<1e-7,'Native graph fails to reproduce original composed-graph DC result'
  changes=[]
  for did,old,new in zip(DEVICES,a['dc']['targets'],b['dc']['targets'],strict=True):
   before=old['effective_self_resistance_ohm'];after=new['effective_self_resistance_ohm']
   changes.append(dict(device=did,before_ohm=before,after_ohm=after,delta_ohm=after-before,
    relative_reduction=(before-after)/before))
  witness='R139947'
  assert witness in edge_sets['return64']and witness in edge_sets['via3']
  result.update(status='COMPLETE_SOURCE_BOUND_VIA3_RETURN_RESISTANCE_COMPARISON_NOT_ELECTRICAL_ACCEPTANCE',
   variants=variants,changes=changes,bottleneck_witness={k:v[witness]for k,v in edge_sets.items()},
   common_resistor_names=len(set(edge_sets['return64'])&set(edge_sets['via3'])),
   identical_resistor_records=sum(v==edge_sets['via3'].get(k)for k,v in edge_sets['return64'].items()),
   source_rc_records_unchanged=True)
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  save()
if __name__=='__main__':main()
