#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh full-parent native metal/via graph, prerequisite to8074-device RC."""
import json,os,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
from cloud_tx_exact_external_ports import compare as compare_ports
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64-native-wires'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64-physical-pass-20261023.json').read_text())
  assert pin['run']==39895931760 and pin['summary_sha256']=='11cc148299aa8c3363de4d25f0f326944e56b2bf08a7618ec7da7a85dbf9770d'
  names=['layout/layout.gds','layout/schematic.cir','flat_lvs/result.lvsdb','flat_lvs/audit.json','flat_lvs/extracted.cir']
  prior,proof=reports.restore_report('tx-output8088-power128return64-physical',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
  assert prior['status']=='PASS_ACTUAL_TX_OUTPUT8088_POWER128RETURN64_PARENT_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC_FULLWAVE'
  assert prior['source_head']=='432ee05bb5eda42c5298d2cbe936470529945d92'
  assert all(v['expected_verdict_observed']for v in prior['steps'].values())
  assert prior['steps']['drc']['measurement']['category_count']==560 and prior['steps']['drc']['measurement']['markers']==0
  for name in ('deep_lvs','flat_lvs'):
   a=prior['steps'][name]['audit'];assert a['status']=='PASS within comparison scope'and not a['extraction_diagnostics']
   assert a['circuits'][0]['layout_devices_recursive']==a['circuits'][0]['schematic_devices_recursive']==8088
   assert prior['steps'][name]['external_ports']['passed']and prior['steps'][name]['external_ports']['actual_count']==165
  assert compare_ports((OUT/'source/layout/schematic.cir').read_text(),(OUT/'source/flat_lvs/extracted.cir').read_text(),'nssoc_tx_output8088_parent_v1',expected_count=165)['passed']
  m=json.loads((ROOT/'scripts/tx-output8088-power128return64-wire-method.json').read_text())
  baseline=ROOT/m['baseline_path'];assert sha(baseline)==m['baseline_sha256'];source=baseline.read_text()
  for e in m['edits']:
   assert source.count(e['before'])==e['count'];source=source.replace(e['before'],e['after'])
  method=ROOT/m['candidate_path'];assert source==method.read_text()and sha(method)==m['candidate_sha256']
  native=OUT/'probe.py';native.write_text(source)
  protected={p:sha(p)for p in [Path(__file__),method,baseline,native,*[OUT/'source'/n for n in names]]}
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  r['physical_source']=proof;r['method']=m;save()
  with(OUT/'native.log').open('w')as f:code=subprocess.call([str(app),'python',str(native)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r['native_returncode']=code;save()
  if code:print((OUT/'native.log').read_text(errors='replace')[-12000:],flush=True)
  assert code==0
  g=json.loads((OUT/'native01/result.json').read_text());r['geometry']=g;save()
  assert g['status']=='PASS_TX_OUTPUT8088_POWER128RETURN64_METAL_VIA_GRAPH_BOUND_TO_ALL_NATIVE_DEVICES_NO_RC'
  assert g['native_device_count']==8088 and len(g['native_ports'])==165
  assert g['native_terminal_count']==28620
  assert g['wire_component_count']==703 and g['native_electrical_net_count']==768,('Unexpected whole-parent conductor/body census',g['wire_component_count'],g['native_electrical_net_count'])
  assert all(sha(p)==v for p,v in protected.items());r['sources_unchanged']=True
  r['status']=g['status']
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
