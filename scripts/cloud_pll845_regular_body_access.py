#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native geometry proof for previously implicit standard-cell n-well contacts."""
import json,os,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pll845_native_models as models
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll845-regular-body-access'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 helper=ROOT/'scripts/pll845_regular_body_access_native.py'
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_phy_accepted=False,
  composition_accepted=False,loaded_simulation_passed=False,controller_sha256=sha(Path(__file__)),
  helper_sha256=sha(helper),model_converter_sha256=sha(Path(models.__file__)))
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  names=['composition.json','audit/capture/wire/anchors08.json']
  failed,proof=reports.restore_report('pll845-native-composition',39355410610,
   'b26504a02876c5c4e33e94e70c9fd16a67af5d971ed8ea709a10621fe19bdb38',
   '54513b74859303bd6390561d0fa1f12637b41890a4055c1189543a181933e628',OUT/'composition',names)
  assert failed['status']=='FAIL_OR_ERROR'and failed['source_head']=='8aef441d948ed54ae0e82276dcbbb19852578a41'
  assert failed['composition']['uncontacted_body_groups']==[dict(native_cluster=203,net='body_203',native_net='core_vdd')]
  r['rejected_composition_source']=proof
  selected=['source/parent/integrated/nssoc_pll845_divider3p2_c8_v2_development.gds',
   'source/parent/physical/lvs_flat/result.lvsdb','source/wire/native05/result.json','source/wire/native05/wires.l2n']
  prior,pproof=reports.restore_report('pll845-terminal-references',39350440897,
   '73e731a6f5f0b426170163a8ecd7f790e23364e6877747a32487fdeb1e97254d',
   'baab8d27c8b8de2390018ebb3e2d2aa369a6c4402cf797ed43e1187256a1e94d',OUT/'planes',selected)
  assert prior['sources_unchanged']and prior['native_returncode']==0 and not prior['binding']['unresolved']
  assert pproof['summary_sha256']==failed['physical_source']['summary_sha256']
  r['physical_source']=pproof
  rel='libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json'
  fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/'+rel,models.MODEL_PINS[rel],OUT/'sg13g2_tech.json')
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  save()
  log=OUT/'native-body-access.log'
  with log.open('w')as stream:rc=subprocess.call([str(app),'python',str(helper),str(OUT)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  r['native_returncode']=rc;r['native_log_sha256']=sha(log)
  if(OUT/'regular-body-access.json').exists():r['body_access']=json.loads((OUT/'regular-body-access.json').read_text())
  save()
  if rc:print(log.read_text(errors='replace')[-15000:],flush=True)
  assert rc==0
  data=r['body_access'];assert data['plan']['native_pmos_body_terminals']==125
  assert len(data['controls'])==5 and all(x['rejected']for x in data['controls'])
  assert data['plan']['existing_audited_wire_points_only']
  assert all(sha(OUT/'composition'/n)==failed['outputs'][n]for n in names)
  assert all(sha(OUT/'planes'/n)==prior['outputs'][n]for n in selected)
  assert all(sha(Path(n))==digest for n,digest in data['inputs'].items())
  assert sha(Path(__file__))==r['controller_sha256']and sha(helper)==r['helper_sha256']and sha(Path(models.__file__))==r['model_converter_sha256']
  r.update(status=data['status'],sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
