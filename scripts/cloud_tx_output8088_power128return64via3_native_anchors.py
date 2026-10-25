#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind every actual raw64/core terminal to the fresh full-parent native graph."""
import json,os,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64via3-native-anchors'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64via3-native-wires-pass-20261023.json').read_text())
  assert pin['run']==39987745998 and pin['summary_sha256']=='f348e701bddb909351b03f9af63f781bfdd5f45f8ac603a42c36ea8d70cca788'
  names=['native01/wires.l2n','native01/wires.gds','native01/result.json','source/layout/layout.gds','source/flat_lvs/result.lvsdb','source/flat_lvs/audit.json']
  prior,proof=reports.restore_report('tx-output8088-power128return64via3-native-wires',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
  assert prior['status']=='PASS_TX_OUTPUT8088_POWER128RETURN64VIA3_METAL_VIA_GRAPH_BOUND_TO_ALL_NATIVE_DEVICES_NO_RC'and prior['sources_unchanged']
  g=prior['geometry'];assert g['native_device_count']==8088 and g['native_terminal_count']==28620 and g['wire_component_count']==703 and g['native_electrical_net_count']==768
  method=ROOT/'scripts/bind_tx_output8088_power128return64via3_native_anchors.py'
  m=json.loads((ROOT/'scripts/tx-output8088-power128return64via3-anchor-method.json').read_text())
  baseline=ROOT/m['baseline_path'];assert sha(baseline)==m['baseline_sha256']and sha(method)==m['candidate_sha256']
  original=baseline.read_text();pieces=[];cursor=0
  for e in m['changes']:
   assert cursor<=e['start']<=e['end']<=len(original)
   pieces.extend([original[cursor:e['start']],e['replacement']]);cursor=e['end']
  pieces.append(original[cursor:]);assert ''.join(pieces)==method.read_text()
  leaf,leafproof=reports.restore_report('tx-output14-physical',39564026768,'8f434b1368bcf613ca2f32c4eeebc528d3e131a243299bf6df09f609c293f9fa','82076d156f767b5c9caf35f9fea9f13e7953022abec73f6814bb473c1de452c4',OUT/'output_leaf_proof',['layout/result.json'])
  assert leaf['status']=='PASS_ACTUAL_TX_OUTPUT14_NATIVE_PHYSICAL_AND_PARENT_ENDPOINT_BINDING_REQUIRES_FRESH_RC_AND_PARENT_ROUTE'
  r['output_leaf_source']=leafproof
  pcell=OUT/'npn13G2_code.py'
  fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py','634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729',pcell)
  protected={p:sha(p)for p in [Path(__file__),method,baseline,pcell,OUT/'output_leaf_proof/layout/result.json',*[OUT/'source'/n for n in names]]}
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  r['wire_source']=proof;save()
  with(OUT/'native.log').open('w')as f:code=subprocess.call([str(app),'python',str(method)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r['native_returncode']=code;save()
  if code:print((OUT/'native.log').read_text(errors='replace')[-16000:],flush=True)
  assert code==0
  b=json.loads((OUT/'anchors.json').read_text());r['binding']=b;save()
  assert b['status']=='PASS_ALL28620_FULL_PARENT_TERMINALS_WITH20532_METAL8088_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
  assert b['counts']['devices']==8088 and b['counts']['terminals']==28620
  assert b['counts']['metal_terminals']==20532 and b['counts']['body_terminals']==8088 and b['counts']['public_ports']==165 and b['counts']['wire_components']==703
  assert len(b['negative_controls'])==6 and all(x['rejected']for x in b['negative_controls'])
  assert all(sha(p)==v for p,v in protected.items());r['sources_unchanged']=True;r['status']=b['status']
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
