#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read full saved physical v54 failures and measure losses without rerunning SPICE."""
import argparse,hashlib,json,os,traceback
from collections import defaultdict
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_tx_stream as stream
import build_pcie_local_vco_hybrid_v6 as parser
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
METHOD=ROOT/'scripts/cdr-active-levelshift-v54-losses-method.json'
PIN=ROOT/'docs/evidence/cdr-active-levelshift-v54-extracted-results-20261024.json'
def check():
 m=json.loads(METHOD.read_text())
 for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
 return m
def effective_resistance(rows,a,b):
 """DC equivalent of every physical resistor in the connected wire component."""
 assert a!=b
 graph=defaultdict(set)
 for name,x,y,value in rows:
  resistance=float(parser.number(value))
  assert x!=y and np.isfinite(resistance) and resistance>0
  graph[x].add(y);graph[y].add(x)
 reached=set();todo=[a]
 while todo:
  node=todo.pop()
  if node in reached:continue
  reached.add(node);todo.extend(graph[node]-reached)
 assert b in reached,'Disconnected physical terminal'
 edges=[(name,x,y,float(parser.number(value)))for name,x,y,value in rows if x in reached]
 nodes=sorted(reached-{b});index={n:i for i,n in enumerate(nodes)}
 matrix=np.zeros((len(nodes),len(nodes)));rhs=np.zeros(len(nodes));rhs[index[a]]=1
 for name,x,y,r in edges:
  g=1/r
  for n in (x,y):
   if n!=b:matrix[index[n],index[n]]+=g
  if x!=b and y!=b:
   matrix[index[x],index[y]]-=g;matrix[index[y],index[x]]-=g
 volts=np.linalg.solve(matrix,rhs);assert np.isfinite(volts).all()
 potential={b:0.,**dict(zip(nodes,map(float,volts)))}
 kcl={n:0. for n in reached};energy=0.
 for name,x,y,r in edges:
  current=(potential[x]-potential[y])/r
  kcl[x]+=current;kcl[y]-=current;energy+=current*current*r
 residual=max(abs(value-(1 if n==a else -1 if n==b else 0))for n,value in kcl.items())
 req=potential[a]
 assert req>0 and residual<1e-8 and abs(energy-req)<=1e-8*max(1,req)
 return dict(equivalent_resistance_ohm=req,method='All physical branches; one-amp nodal solution with KCL and power identity',
             branch_count=len(edges),node_count=len(reached),edge_names=[e[0]for e in edges],
             maximum_kcl_residual_a=residual,dissipated_power_at_one_amp_w=energy)
def resistance_controls():
 fixtures=[
  ('series',[('R1','a','x','1'),('R2','x','b','2')],3.),
  ('parallel',[('R1','a','b','4'),('R2','a','b','4')],2.),
  ('triangle',[('R1','a','b','1'),('R2','a','x','1'),('R3','x','b','1')],2/3)]
 passed=[]
 for name,rows,expected in fixtures:
  for a,b in [('a','b'),('b','a')]:
   r=effective_resistance(rows,a,b)
   assert abs(r['equivalent_resistance_ohm']-expected)<1e-12
  passed.append(name)
 for name,rows in [('open',[('R1','a','x','1')]),('negative',[('R1','a','b','-1')]),('zero',[('R1','a','b','0')])]:
  try:effective_resistance(rows,'a','b')
  except AssertionError:passed.append('rejected-'+name)
  else:raise AssertionError(name)
 return passed

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['nominal','hot_low','cold_high'],required=True);args=ap.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true';check()
 out=ROOT/('cloud-cdr-active-levelshift-v54-losses-'+args.case);out.mkdir();reports.OUT=out
 r=dict(status='RUNNING',case=args.case,source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,qualified_pex=False,scope='Analysis of the complete actual saved extracted leaf wave. No resimulation, changed wire values, or accepted physical fix.')
 def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  r['resistance_controls']=resistance_controls()
  pin=json.loads(PIN.read_text());p=pin['cases'][args.case]
  old,proof=reports.restore_report('cdr-active-levelshift-v54-extracted-'+args.case,pin['run'],p['summary_sha256'],p['parts_sha256'],out/'source',['native/wave.raw','composed/levelshift18-wire.spice','composed/composition.json'])
  assert old==p['report'] and old['sources_unchanged'] and old['status']in ('REJECTED_NATIVE_EXTRACTED_LEVELSHIFT_LEAF','PASS_NATIVE_EXTRACTED_LEVELSHIFT_LEAF_REQUIRES_PARENT_AND_FULL_CDR')
  c=json.loads((out/'source/composed/composition.json').read_text());assert c==old['physical_contract']
  t,w,capture=stream.read_streamed_wave(out/'source/native/wave.raw',old['vectors'],34.25e-9,.3125e-12)
  assert capture==old['raw_capture']
  window=t>=2e-9
  def physical(n):
   return '0'if n in ['avss','sub','wire_cref']else n if n in c['interface']else'xgain.'+n.lower()
  def v(n):
   n=physical(n);return np.zeros(len(t))if n=='0'else w['v('+n+')']
  def stats(x):
   a=x[window];return dict(minimum=float(a.min()),maximum=float(a.max()),mean=float(np.trapezoid(a,t[window])/(t[window][-1]-t[window][0])))
  rows=parser.statements((out/'source/composed/levelshift18-wire.spice').read_text())
  rs=[row for row in rows if row[0].startswith('R')]
  cs=[row for row in rows if row[0].startswith('C')]
  assert len(rs)==473 and len(cs)==350
  graph=defaultdict(list);losses=[]
  for name,a,b,value in rs:
   resistance=float(parser.number(value));assert resistance>0
   graph[a].append((b,resistance,name));graph[b].append((a,resistance,name))
   dv=v(a)-v(b)
   losses.append(dict(name=name,nodes=[a,b],resistance_ohm=resistance,drop_v=stats(dv),current_a=stats(dv/resistance),power_w=stats(dv*dv/resistance)))
  def path(a,b):return effective_resistance(rs,a,b)
  terminals=[]
  for d in c['device_records']:
   for term in d['terminals']:
    net=term['native_net']
    if term['anchor'] and net in c['interface']:
     terminals.append(dict(device=d['instance'],model=d['model'],terminal=term['terminal'],port=net,physical_node=term['node'],path=path(net,term['node']),port_minus_terminal_v=stats(v(net)-v(term['node'])),terminal_voltage_v=stats(v(term['node']))))
  caps=[dict(name=row[0],nodes=row[1:3],capacitance_f=float(parser.number(row[3])))for row in cs]
  r.update(source=proof,raw_capture=capture,terminal_paths=terminals,wire_resistor_losses=sorted(losses,key=lambda x:x['power_w']['mean'],reverse=True),all_wire_capacitors=caps,body_voltage_v=stats(v('body_1')),all_wave_nodes_saved=old['full_native_wire_and_body_nodes_saved'],native_device_checks=old['device_checks'],native_mos_checks=old['mos_checks'])

  # Measure actual node-to-node waveforms; never reconstruct internal data.
  import cloud_cdr_xor as primitive
  bits=primitive.prbs(0x7f)
  assert hashlib.sha256(bytes(bits)).hexdigest()==old['source_bits_sha256']
  hbts=[d for d in c['device_records']if d['model']=='npn13g2']
  assert len(hbts)==2
  def transistor_for_input(net):
   matches=[d for d in hbts if next(x['native_net']for x in d['terminals']if x['terminal']=='B')==net]
   assert len(matches)==1
   return {t['terminal']:t['node']for t in matches[0]['terminals']}
  xp=transistor_for_input('ip');xn=transistor_for_input('inn')
  stages={}
  for label,a,b,threshold in [
      ('external_input','ip','inn',.03),
      ('intrinsic_input',xp['B'],xn['B'],.03),
      ('intrinsic_collectors',xn['C'],xp['C'],.1),
      ('external_output','op','on',.1)]:
   delta=v(a)-v(b);signed=[];delays=[]
   for i,bit in enumerate(bits):
    edge=2e-9+i*125e-12;sign=2*bit-1
    for phase in (.3,.6,.9):signed.append(float(np.interp(edge+phase*125e-12,t,delta))*sign)
    ids=np.flatnonzero((t>=edge)&(t<=edge+.95*125e-12));bad=ids[delta[ids]*sign<threshold]
    delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+.3125e-12))
   stages[label]=dict(positive_node=a,negative_node=b,threshold_v=threshold,minimum_sampled_signed_v=min(signed),maximum_input_to_valid_s=max(delays),per_bit_input_to_valid_s=delays,active_differential_range_v=[float(delta[window].min()),float(delta[window].max())])
  assert abs(stages['external_output']['minimum_sampled_signed_v']-old['minimum_signed_margin_v'])<1e-14
  assert abs(stages['external_output']['maximum_input_to_valid_s']-old['maximum_input_to_valid_s'])<1e-18
  r['measured_waveform_stages']=stages

  check();r.update(status='PASS_COMPLETE_SAVED_WAVE_LOSS_DIAGNOSIS_NOT_A_FIX',sources_unchanged=True)
 except BaseException as e:
  r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'}
  save()
if __name__=='__main__':main()
