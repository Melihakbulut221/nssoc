#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict native physical gates on128 actual branch and2 actual tail feeds."""
import json,os,subprocess,sys,tarfile,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from cloud_tx_exact_external_ports import compare as compare_ports,controls as port_controls
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-output8088-branch-tail-feed'
TOP='nssoc_tx_output8088_parent_v1'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,no_new_simulation=True,steps={})
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  methods=json.loads((ROOT/'scripts/tx-output8088-branch-tail-feed-methods.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in methods.items())
  protected={ROOT/p:h for p,h in methods.items()}
  r['geometry_readback']=dict(run=40075242137,source_head='f9dfeee4ebdd1970109eee34b9289bc29fd0eef1',
   summary_sha256='b8327a78d088a97d4d4864b552d5e9084d2b79b022088a49456e70908cc1f8eb',
   status='COMPLETE_EXACT_FRESH_RAIL_SEGMENTS_AND_NATIVE_ACCESS_GEOMETRY_NOT_REPAIR')
  inputs=[
   ('tx-output8088-driver-pinfeed-wires-anchors',40071267004,
    'b40767d0a3dc77124ff0ae6ebf4f11f5c79fd4241492cbabc6b52ee30ffe4f8b','823af2aa83ea8cc284b21f9513233cbe8ab5e792628f01af7c23eebb99aaf74f','native',
    ['source/native01/result.json','source/source/layout/layout.gds','source/source/flat_lvs/result.lvsdb']),
   ('tx-output8088-driverpinfeed-composition',40072977220,
    '5ce97973544098520f93a8dbdc6c56d63b63151ef98dc804334e93cf1b0d3baf','20edb394ae2f6c734ca8f7907602a2212eee67f09c24d887e9ce28f62d459894','anchors',
    ['intrinsic/source/anchors.json']),
   ('tx-output8088-driver-pinfeed',40070667147,
    'b6680151c8741fb11a4a5c6fbbe24815850a7de510dd6d72dc38fbf0625662d9','de46b737608b3065d60970518695a6c35de952b5e269b6b79c9ab424c2b199a4','parent',
    ['layout/schematic.cir','integration-result.json'])]
  for group,run,summary,parts,folder,names in inputs:
   prior,proof=reports.restore_report(group,run,summary,parts,OUT/folder,names)
   assert prior['sources_unchanged']and prior['status'].startswith('PASS_')
   r.setdefault('sources',{})[folder]=proof
   protected.update({OUT/folder/n:prior['outputs'][n]for n in names});save()
   if folder=='parent':
    assert all(s['expected_verdict_observed']for s in prior['steps'].values())
    assert prior['steps']['drc']['measurement']['category_count']==560 and prior['steps']['drc']['measurement']['markers']==0
    for name in ('deep_lvs','flat_lvs'):
     step=prior['steps'][name];assert step['external_ports']['passed']and step['external_ports']['actual_count']==165
     assert step['audit']['status']=='PASS within comparison scope'and not step['audit']['extraction_diagnostics']
  r['external_port_controls']=port_controls(expected_count=165)
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  sys.path.insert(0,str(ROOT/'hw/soc/flow'))
  from check_pcie_rx_cell import execute
  from prepare_ihp_drc import validate_lock,verify
  from check_ihp_drc import record_result
  for typ in ('drc','lvs'):
   lock=json.loads((ROOT/f'hw/soc/pnr/ihp-{typ}.lock.json').read_text());validate_lock(lock)
   assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6'
   for row in lock['files']:
    p=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);protected[p]=row['sha256']
  generation=execute([app,'python',ROOT/'scripts/generate_tx_output8088_branch_tail_feed.py',OUT],OUT,'generation')
  r['generation']=generation;save()
  if generation['returncode']:print((OUT/'generation.log').read_text(errors='replace')[-16000:],flush=True)
  assert generation['returncode']==0
  r['geometry']=json.loads((OUT/'integration-result.json').read_text());save()
  assert r['geometry']['route_count']==130 and not r['geometry']['blocked']
  jobs=[('drc','layout/layout.gds',None,'deep',True),
        ('deep_lvs','layout/layout.gds','layout/schematic.cir','deep',True),
        ('flat_lvs','layout/layout.gds','layout/schematic.cir','flat',True),
        ('source_access_open','faults/source_access_open.gds','layout/schematic.cir','flat',False),
        ('tail_access_open','faults/tail_access_open.gds','layout/schematic.cir','flat',False),
        ('body_supply_short','faults/body_supply_short.gds','layout/schematic.cir','deep',False),
        ('wrong_width','layout/layout.gds','faults/wrong_width.cir','deep',False),
        ('offgrid','faults/offgrid.gds',None,'deep',False)]
  results=[]
  for name,geometry,reference,mode,positive in jobs:
   d=OUT/name;d.mkdir();drc=reference is None;typ='drc'if drc else'lvs'
   entry=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/('drc/ihp-sg13g2.drc'if drc else'lvs/sg13g2.lvs')
   options=['input='+str(OUT/geometry),'topcell='+TOP,'log='+str(d/'deck.log'),'run_mode='+mode]
   options+=['report='+str(d/'drc.lyrdb'),'threads=2','no_recommended=False','precheck_drc=False']if drc else[
    'schematic='+str(OUT/reference),'report='+str(d/'result.lvsdb'),'target_netlist='+str(d/'extracted.cir'),'thr=2','no_simplify=true','top_lvl_pins=true','combine_devices=false']
   cmd=[app,'klayout','-b','-zz','-r',entry]
   for op in options:cmd+=['-rd',op]
   step=dict(execution=execute(cmd,d,'run'),positive=positive,mode=mode,combine_devices=False);r['steps'][name]=step;save()
   assert step['execution']['returncode']==0,('Native deck execution failed',name)
   if drc:
    step['measurement']=record_result(d,TOP,0,protected);v=step['measurement']
    ok=v['category_count']==560 and v['status']==('PASS'if positive else'FAIL')
    if not positive:ok=ok and any('Offgrid'in c for c in v['categories'])
   else:
    step['audit_execution']=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',d/'result.lvsdb','--top',TOP,'--deck-log',d/'deck.log','--output',d/'audit.json'],d,'audit')
    a=json.loads((d/'audit.json').read_text());step['audit']=a
    step['external_ports']=compare_ports((OUT/'layout/schematic.cir').read_text(),(d/'extracted.cir').read_text(),TOP,expected_count=165)
    ok=a['status']==('PASS within comparison scope'if positive else'FAIL')and step['audit_execution']['returncode']==(0 if positive else 1)
    if positive:
     tops=[c for c in a['circuits']if c['layout']==TOP]
     ok=ok and len(tops)==1 and not a['extraction_diagnostics']and all(tops[0][k]==8088 for k in('layout_devices_recursive','schematic_devices_recursive'))
    else:ok=ok and 'Deck explicitly reported a mismatch'in a['reasons']
    if positive:ok=ok and step['external_ports']['passed']
    if name=='internal_port_alias':
     # Native circuit matching tolerates this extra port. Preserve that result,
     # and require the stronger explicit external-interface contract to reject it.
     step['native_circuit_comparison_passed']=a['status']=='PASS within comparison scope'
     ok=(not step['external_ports']['passed']and step['external_ports'].get('actual_count')==166
      and step['external_ports'].get('extra')==['MP']and not step['external_ports'].get('missing')
      and step['native_circuit_comparison_passed']and not a['extraction_diagnostics'])
     step['fault_rejection_gate']='EXACT_EXTERNAL_INTERFACE_165_NAMES'
   step['expected_verdict_observed']=bool(ok);results.append(bool(ok));save();print(name,'expected verdict',bool(ok),flush=True)
  assert all(sha(p)==v for p,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  r['sources_unchanged']=True
  r['status']='PASS_ACTUAL128_BRANCH_AND2_TAIL_FEEDS_NATIVE_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC'if all(results)else'REJECTED_ACTUAL128_BRANCH_AND2_TAIL_FEEDS_NATIVE_PHYSICAL_GATES'
  save();assert all(results),'Native physical rejection preserved'
 except BaseException as e:
  if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
  r['error']=repr(e);raise
 finally:
  progress=OUT/'candidate-progress.json'
  if progress.exists():
   value=json.loads(progress.read_text());r['candidate_progress']=dict(route_count=len(value['routes']),blocked=value['blocked'])
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
