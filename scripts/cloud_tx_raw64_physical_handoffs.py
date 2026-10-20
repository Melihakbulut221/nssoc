#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only native driver/core physical handoff construction and obstruction evidence."""
import json,os,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_input_driver_localpins as driver
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-raw64-physical-handoffs'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/tx-p4-drive3-physical-pass-20261020.json').read_text())
  assert pin['run']==39447746971 and pin['summary_sha256']=='f351c3ab008b764155594fe395f83b319ca384c32073c1106d7bebbb508319cc'
  names=[n for n in pin['outputs']if n.startswith('layout/')]
  prior,proof=reports.restore_report('tx-p4-drive3-physical',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'core',names)
  assert prior==pin['report']and prior['physical']['steps']['drc']['measurement']['markers']==0
  r['core_source']=proof
  source=dict(run=38905613449,group='tx-input-driver-localpins',root='cloud-tx-input-driver-localpins',bytes=1289952,sha='d7e7ebb196bf22170df9a5e8fef996a7eddcfb0742300c4dabc128f684fbabdf',summary='b98c6c3f73aad4eb7b00c898ea6f158252b871f17bdb1ecce67eee72a0b164df')
  driver.OUT=OUT/'driver';driver.OUT.mkdir()
  dr,report=driver.restore(source)
  assert report['status']=='PASS_FULL_DRIVER_NATIVE_PHYSICAL_GATES_NOT_EXTRACTED_ELECTRICAL_OR_PHY_ACCEPTANCE'
  assert report['steps']['drc']['measurement']['markers']==0
  assert all(v['expected_verdict_observed']for v in report['steps'].values()if 'expected_verdict_observed'in v)
  r['driver_source']=source
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime-source.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  protected={p:sha(p)for p in [Path(__file__),ROOT/'scripts/generate_tx_raw64_physical_handoffs.py',*[OUT/'core'/n for n in names],*[dr/n for n in report['outputs']]]}
  with(OUT/'native-generation.log').open('w')as f:
   code=subprocess.call([str(app),'python',str(ROOT/'scripts/generate_tx_raw64_physical_handoffs.py'),str(OUT)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r['generation_returncode']=code;save()
  if code:print((OUT/'native-generation.log').read_text(errors='replace')[-14000:],flush=True)
  assert code==0
  r['handoffs']=json.loads((OUT/'handoff-result.json').read_text())
  assert r['handoffs']['placed_count']==64 and r['handoffs']['original_native_geometry_preserved']
  assert r['handoffs']['routed_count']+r['handoffs']['blocked_count']==64
  assert all(sha(p)==v for p,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  r['sources_unchanged']=True
  r['status']='MEASURED_NATIVE_RAW64_HANDOFF_CANDIDATE_REQUIRES_POWER_ROUTING_DRC_LVS_RC_AND_ORIGINAL_FULLWAVE'
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
