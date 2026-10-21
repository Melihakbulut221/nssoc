#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify actual global/completed mainchip topology and fixed clock without rerouting."""
import json,os,re,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-postroute-geometry'
PREFIX='source/run/1-openroad-detailedrouting/'
CONTROLLER='02c29d2b896687e57d03e42f74a76e39f90bce4cc02a838ca907864afb259946'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,route_complete=False,
  final_timing_complete=False,full_phy_accepted=False,qualified_pex=False,
  scope='All152762 original instance masters, geometry, pins, net/NDR/port records and exact fixed PCIe clock wire. Not transistor LVS, full DRC, antenna/disconnection, RC or STA.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  methods=json.loads((ROOT/'scripts/mainchip-postroute-geometry-methods.json').read_text())
  assert all(sha(ROOT/p)==v for p,v in methods.items())
  pin=json.loads((ROOT/'docs/evidence/onehot-native-fanout-pass-20261020.json').read_text())
  assert pin['run']==39404356943 and pin['summary_sha256']=='400cc00f4a66d39d41a6e49c8c9d5077c8a6b02bdd14d74e17fa9b9c0e885ad0'
  before,bproof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'candidate',['candidate.odb','proof/result.json'])
  assert before['source_head']==pin['source_head']and before['sources_unchanged']
  assert before['proof']['status']=='PASS within scope'and before['actual_inversion_control_rejected']
  assert {k:before['proof'][k]for k in pin['proof']}==pin['proof']
  a=OUT/'candidate/candidate.odb'
  assert sha(a)==before['candidate_odb_sha256']=='c005764c949e088b96cea5583f3a86fe901772b5e0eafc9d93bba506a151f2b7'
  r['original_candidate']=bproof
  pp=json.loads((ROOT/'docs/evidence/mainchip-portable-runtime-pass-20261020.json').read_text())
  assert pp['run']==39494338440 and pp['summary_sha256']=='21e8f082931a30e8ae074d34843c828502a80e0719b778e6a8686a04fc976bc2'
  names=[PREFIX+'fresh-fanout-global.odb',PREFIX+'config.json']
  portable,pproof=reports.restore_report(pp['group'],pp['run'],pp['summary_sha256'],pp['parts_sha256'],OUT/'global',names)
  assert portable==pp['report']and portable['sources_unchanged']
  b=OUT/'global'/names[0];original_global=sha(b)
  assert original_global==portable['isolated_db_equivalence']['original_global_odb_sha256']
  cfg=json.loads((OUT/'global'/names[1]).read_text())
  assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
  assert float(cfg['CLOCK_PERIOD'])==20 and float(cfg['TIME_DERATING_CONSTRAINT'])==5
  r['global_source']=pproof
  descriptor=os.environ.get('NSSOC_COMPLETED_DRT','').strip()
  actual=None
  if descriptor:
   selected=json.loads(descriptor)
   assert set(selected)=={'run','attempt','group','source_head','controller_sha256','summary_sha256','parts_sha256'}
   assert selected['attempt']==1 and selected['group']=='mainchip-active-drt-cross'and selected['controller_sha256']==CONTROLLER
   assert type(selected['run'])is int and selected['run']>0
   assert re.fullmatch('[0-9a-f]{40}',selected['source_head'])
   assert all(re.fullmatch('[0-9a-f]{64}',selected[k])for k in ('summary_sha256','parts_sha256'))
   live=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(selected['run'])]))
   assert live['status']=='completed'and live['conclusion']=='success'and live['run_attempt']==1
   assert live['head_sha']==selected['source_head']and live['path']=='.github/workflows/mainchip-active-drt-continuation-cloud.yml'
   names=['work/detailed-route.odb','work/native.log','work/boots.log','work/before-guide-read.odb','work/drt-done']
   actual,aproof=reports.restore_report(selected['group'],selected['run'],selected['summary_sha256'],selected['parts_sha256'],OUT/'routed',names)
   assert actual['source_head']==selected['source_head']and actual['controller_sha256']==CONTROLLER
   assert actual['sources_unchanged']and actual['route_complete']and not actual.get('native_process_saved',False)
   assert actual['status']=='COMPLETE_NATIVE_DRT_REQUIRES_ALL_POSTROUTE_PHYSICAL_RC_STA_GATES'
   assert actual['image_id']==portable['image_id']
   assert actual['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
   assert actual['retained_timing_contract']['derating_percent']==5
   assert sha(OUT/'routed/work/before-guide-read.odb')==original_global
   b=OUT/'routed/work/detailed-route.odb';assert sha(b)==actual['routed_odb_sha256']
   r.update(route_complete=True,completed_route_source=aproof,completed_route_descriptor=selected,
    reported_native_drt_violation_counts=actual['native_log']['completed_violation_counts'])
  r['mode']='completed_route'if actual else'global_preflight'
  inputs={str(p):sha(p)for p in (a,b,Path(__file__),*[ROOT/p for p in methods])}
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  def native(method,label,extra):
   env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
   env.update(NSSOC_TOPOLOGY_BEFORE=str(a),NSSOC_TOPOLOGY_AFTER=str(b),**extra)
   with(OUT/(label+'.log')).open('w')as log:
    code=subprocess.call([str(app),'openroad','-exit','-python',str(ROOT/method)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
   r.setdefault('commands',[]).append(dict(method=method,returncode=code,log_sha256=sha(OUT/(label+'.log'))));save()
   if code:print((OUT/(label+'.log')).read_text(errors='replace')[-14000:],flush=True)
   assert code==0,('Native geometry rejection',label)
  native('scripts/check_onehot_native_fanout_routed_topology.py','topology',dict(NSSOC_TOPOLOGY_OUT=str(OUT/'topology.json')))
  topology=json.loads((OUT/'topology.json').read_text())
  assert topology['status']=='PASS_NATIVE_FANOUT_ROUTED_TOPOLOGY_AND_GEOMETRY_NOT_LVS'
  assert topology['proof']['retained_instances']==152762
  assert set(topology['rejected'])=={'changed_master','changed_pin','changed_location','non_diode_addition'}
  assert topology['proof']['added_diode_count']==0,'This native DRT controller does not run antenna cell insertion'
  r['topology']=topology;save()
  native('scripts/check_onehot_fixed_clock_route.py','fixed-clock',dict(NSSOC_CLOCK_ROUTE_PROOF_OUT=str(OUT/'fixed-clock.json')))
  fixed=json.loads((OUT/'fixed-clock.json').read_text())
  assert fixed['status']=='PASS_NATIVE_DRT_FIXED_CLOCK_GEOMETRY_EXACT'and fixed['original_physical_route_preserved']
  r['fixed_clock']=fixed
  assert all(sha(Path(p))==v for p,v in inputs.items())
  assert all(sha(OUT/'candidate'/p)==before['outputs'][p]for p in ('candidate.odb','proof/result.json'))
  r.update(status='PASS_COMPLETED_NATIVE_ROUTE_GEOMETRY_REQUIRES_DRC_ANTENNA_RC_STA'if actual else'PASS_ACTUAL_GLOBAL_GEOMETRY_PREFLIGHT_REQUIRES_COMPLETED_ROUTE',
   sources_unchanged=True,protected_inputs=inputs,
   next_action='For completed route require native DRC/antenna/disconnected pins, fresh RC, three-corner original-clock STA, final full-chip LVS/DRC; global preflight cannot satisfy those gates.')
 except BaseException as error:
  r.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
