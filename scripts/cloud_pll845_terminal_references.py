#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only whole PLL terminal references before complete native RC."""
import json,os,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll845-terminal-references'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 helper=ROOT/'scripts/pll845_terminal_references_native.py'
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(Path(__file__)),generator_sha256=sha(helper),
  qualified_pex=False,wire_rc_extracted=False,full_phy_accepted=False,accepted=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/pll845-whole-mim-geometry-pass-20261019.json').read_text())
  assert pin['run']==39322420374 and pin['summary_sha256']=='4b688b6ccd28a3d220224c67c9d67164a41afcf5385d888023eb484a14fd48db'
  wanted=['parent/integrated/nssoc_pll845_divider3p2_c8_v2_development.gds','parent/integrated/result.json','parent/physical/lvs_flat/result.lvsdb','parent/physical/lvs_flat/audit.json','parent/physical/lvs_flat/extracted.cir','wire/native05/result.json','wire/native05/wires.l2n','wire/native05/wires.gds','native-mim-geometry.json','wire/whole-pll-mim-masks.gds']
  prior,proof=reports.restore_report('pll845-mim-full-geometry',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',wanted)
  assert prior==pin['report']and prior['sources_unchanged']
  assert prior['status']=='PASS_PLL845_WHOLE_GEOMETRY_AND26_MIM_PLANES_REQUIRES_COMPLETE_TERMINAL_RC'
  assert len(prior['geometry']['controls'])==5 and all(c['rejected']for c in prior['geometry']['controls'])
  assert json.loads((OUT/'source/native-mim-geometry.json').read_text())==prior['geometry']
  r['source']=proof
  pcell=OUT/'npn13G2_code.py'
  fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/npn13G2_code.py','634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729',pcell)
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  r['runtime_sha256']=sha(app);save()
  log=OUT/'native-references.log'
  with log.open('w')as f:rc=subprocess.call([str(app),'python',str(helper),str(OUT)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r['native_returncode']=rc;r['native_log_sha256']=sha(log)
  if (OUT/'anchors.json').exists():r['binding']=json.loads((OUT/'anchors.json').read_text())
  save()
  if rc:print(log.read_text(errors='replace')[-12000:],flush=True)
  assert rc==0,'Whole native terminal reference binding rejected; retain unresolved details'
  bound=r['binding']
  assert bound['status']=='PASS_ALL2737_PLL_TERMINAL_IDENTITIES_AND_ACTUAL_METAL_REFERENCES_REQUIRES_FULL_RC'
  assert len(bound['negative_controls'])==7 and all(c['rejected']for c in bound['negative_controls'])
  assert bound['counts']['terminals']==2737 and bound['counts']['covered_wire_components']==235
  assert not bound['unresolved']
  assert all(sha(Path(n))==v for n,v in bound['inputs'].items())
  assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in wanted)
  assert sha(Path(__file__))==r['controller_sha256']and sha(helper)==r['generator_sha256']
  r.update(status=bound['status'],sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
