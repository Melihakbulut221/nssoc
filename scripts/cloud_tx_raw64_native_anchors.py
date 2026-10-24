#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind every actual raw64/core terminal to the fresh full-parent native graph."""
import json,os,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-raw64-native-anchors'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/tx-raw64-native-wires-pass-20261020.json').read_text())
  assert pin['run']==39467260490 and pin['summary_sha256']=='8b0dc962fbd7bd98044eed205fe0e5fdbe19c3ea11433e32e0d2f699bcf81af6'
  names=['native01/wires.l2n','native01/wires.gds','native01/result.json','source/layout/layout.gds','source/flat_lvs/result.lvsdb','source/flat_lvs/audit.json']
  prior,proof=reports.restore_report('tx-raw64-native-wires',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
  assert prior['status']=='PASS_RAW64_CORE8074_METAL_VIA_GRAPH_BOUND_TO_ALL_NATIVE_DEVICES_NO_RC'and prior['sources_unchanged']
  g=prior['geometry'];assert g['native_device_count']==8074 and g['native_terminal_count']==28582 and g['wire_component_count']==698 and g['native_electrical_net_count']==763
  method=ROOT/'scripts/bind_tx_raw64_native_anchors.py'
  protected={p:sha(p)for p in [Path(__file__),method,*[OUT/'source'/n for n in names]]}
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  r['wire_source']=proof;save()
  with(OUT/'native.log').open('w')as f:code=subprocess.call([str(app),'python',str(method)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r['native_returncode']=code;save()
  if code:print((OUT/'native.log').read_text(errors='replace')[-16000:],flush=True)
  assert code==0
  b=json.loads((OUT/'anchors.json').read_text());r['binding']=b;save()
  assert b['status']=='PASS_ALL28582_FULL_PARENT_TERMINALS_WITH20508_METAL8074_BODY_AND_FOUR_FAULTS_NOT_RC_ACCEPTANCE'
  assert b['counts']['devices']==8074 and b['counts']['terminals']==28582
  assert b['counts']['metal_terminals']==20508 and b['counts']['body_terminals']==8074 and b['counts']['public_ports']==163 and b['counts']['wire_components']==698
  assert len(b['negative_controls'])==4 and all(x['rejected']for x in b['negative_controls'])
  assert all(sha(p)==v for p,v in protected.items());r['sources_unchanged']=True;r['status']=b['status']
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
