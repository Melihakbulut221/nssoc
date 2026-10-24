#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh full-parent native conductor/terminal extraction after physical pass."""
import json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha,fetch
from cloud_tx_exact_external_ports import compare as compare_ports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-output8088-driver-pinfeed-wires-anchors'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False,no_new_simulation=True)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  methods=json.loads((ROOT/'scripts/tx-output8088-driver-pinfeed-wires-anchors-methods.json').read_text())
  assert all(sha(ROOT/p)==h for p,h in methods['locked'].items())
  for candidate,record in methods['derivations'].items():
   baseline=ROOT/record['baseline'];assert sha(baseline)==record['baseline_sha256']
   text=baseline.read_text()
   for e in record['edits']:
    assert text.count(e['before'])==e['count'];text=text.replace(e['before'],e['after'])
   assert text==(ROOT/candidate).read_text()
  names=['layout/layout.gds','layout/schematic.cir','flat_lvs/result.lvsdb','flat_lvs/audit.json','flat_lvs/extracted.cir']
  prior,proof=reports.restore_report('tx-output8088-driver-pinfeed',40070667147,
   'b6680151c8741fb11a4a5c6fbbe24815850a7de510dd6d72dc38fbf0625662d9',
   'de46b737608b3065d60970518695a6c35de952b5e269b6b79c9ab424c2b199a4',OUT/'source/source',names)
  assert prior['status']=='PASS_ACTUAL128_DRIVER_PINFEEDS_NATIVE_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC'
  assert prior['source_head']=='74bc46d2e9518821a12c66b6a071add579ccf2df'and prior['sources_unchanged']
  assert prior['geometry']['route_count']==128 and all(s['expected_verdict_observed']for s in prior['steps'].values())
  assert prior['steps']['drc']['measurement']['category_count']==560 and prior['steps']['drc']['measurement']['markers']==0
  for name in ('deep_lvs','flat_lvs'):
   step=prior['steps'][name];assert step['external_ports']['passed']and step['external_ports']['actual_count']==165
   assert step['audit']['status']=='PASS within comparison scope'and not step['audit']['extraction_diagnostics']
   assert step['audit']['circuits'][0]['layout_devices_recursive']==step['audit']['circuits'][0]['schematic_devices_recursive']==8088
  assert compare_ports((OUT/'source/source/layout/schematic.cir').read_text(),(OUT/'source/source/flat_lvs/extracted.cir').read_text(),'nssoc_tx_output8088_parent_v1',expected_count=165)['passed']
  protected={OUT/'source/source'/n:prior['outputs'][n]for n in names}
  r['physical_source']=proof;save()
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  probe=OUT/'source/probe.py';probe.write_bytes((ROOT/'scripts/tx_output8088_driver_pinfeed_wire_native.py').read_bytes());protected[probe]=sha(probe)
  def execute(script,log):
   with(OUT/log).open('w')as f:code=subprocess.call([str(app),'python',str(script)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   if code:print((OUT/log).read_text(errors='replace')[-16000:],flush=True)
   assert code==0,('Native extraction failed',log,code)
  execute(probe,'wires.log')
  g=json.loads((OUT/'source/native01/result.json').read_text());r['geometry']=g;save()
  assert g['status']=='PASS_TX_OUTPUT8088_DRIVER_PINFEED_METAL_VIA_GRAPH_BOUND_TO_ALL_NATIVE_DEVICES_NO_RC'
  assert g['native_device_count']==8088 and g['native_terminal_count']==28620
  assert g['wire_component_count']==703 and g['native_electrical_net_count']==768 and len(g['native_ports'])==165
  leaf,lp=reports.restore_report('tx-output14-physical',39564026768,
   '8f434b1368bcf613ca2f32c4eeebc528d3e131a243299bf6df09f609c293f9fa',
   '82076d156f767b5c9caf35f9fea9f13e7953022abec73f6814bb473c1de452c4',
   OUT/'output_leaf_proof',['layout/result.json'])
  assert leaf['status']=='PASS_ACTUAL_TX_OUTPUT14_NATIVE_PHYSICAL_AND_PARENT_ENDPOINT_BINDING_REQUIRES_FRESH_RC_AND_PARENT_ROUTE'
  pcell=OUT/'npn13G2_code.py'
  fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py',
   '634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729',pcell)
  protected[pcell]=sha(pcell);protected[OUT/'output_leaf_proof/layout/result.json']=leaf['outputs']['layout/result.json']
  protected.update({OUT/'source/native01'/p:h['sha256']for p,h in g['outputs'].items()})
  protected[OUT/'source/native01/result.json']=sha(OUT/'source/native01/result.json')
  r['output_leaf_source']=lp;save()
  execute(ROOT/'scripts/bind_tx_output8088_driver_pinfeed_native_anchors.py','anchors.log')
  b=json.loads((OUT/'anchors.json').read_text());r['binding_counts']=b['counts'];r['anchor_controls']=b['negative_controls'];save()
  assert b['status']=='PASS_ALL28620_FULL_PARENT_TERMINALS_WITH20532_METAL8088_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
  assert b['counts']['devices']==8088 and b['counts']['terminals']==28620 and b['counts']['metal_terminals']==20532
  assert b['counts']['body_terminals']==8088 and b['counts']['public_ports']==165 and b['counts']['wire_components']==703
  assert len(b['negative_controls'])==6 and all(x['rejected']for x in b['negative_controls'])
  assert all(sha(p)==h for p,h in protected.items())and all(sha(ROOT/p)==h for p,h in methods['locked'].items())
  r.update(status='PASS_FRESH_DRIVER_PINFEED_NATIVE_WIRE_GRAPH_AND_ALL_TERMINAL_ANCHORS_REQUIRES_FRESH_RC',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
