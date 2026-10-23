#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Review preserved native PLL RC; never repeat CAD merely to inspect a result."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import check_pll845_whole_rc_capture as checks
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-rc-review'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_CAD_repeated=False,
  accepted=False,qualified_pex=False,full_phy_accepted=False,raw_rc_audit_passed=False,
  controller_sha256=sha(Path(__file__)),checker_sha256=sha(Path(checks.__file__)))
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  names=['wire/anchors08.json','source/source/native-mim-geometry.json','native-inputs.json',
   'wire/rc03/wires.spice','wire/rc03/baseline.spice','wire/rc03/pump_wires.ext',
   'wire/rc03/pump_wires.res.ext','wire/rc03/native.log','wire/rc03/result.json',
   'wire/run-rc01.py','wire/native05/wires.gds']
  prior,proof=reports.restore_report('pll-rhi120-c8-rc',39916625651,
   'c13eb417f3c9a8cfe4dc2260dd58233f171a410314209f5a2952643c1e3d57fd',
   'c55f4dd64cff7b31647a343036ec4d62f8c7324463b8c591d6dfddea8cad7b18',OUT/'capture',names)
  assert prior['source_head']=='23e41e8d55aa42a3f4456af5ac75f806605f529d'
  assert prior['status']=='PASS_PLL845_WHOLE_MIM_NATIVE_CAPTURE_AND8_CONTROLS_REQUIRES_RAW_RC_AUDIT'and prior['sources_unchanged']
  assert prior['capture']['returncode']==0 and prior['capture']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
  assert {v['label']:v['returncode']for v in prior['commands']}=={'native-whole-geometry-and-points':0,'native-whole-pll-mim-rc':0}
  r['capture_source']=proof;r['original_capture_status']=prior['status']
  r['native_capture']=dict(returncode=prior['capture']['returncode'],seconds=prior['capture']['seconds'])
  anchors=json.loads((OUT/'capture/wire/anchors08.json').read_text())
  mim=json.loads((OUT/'capture/source/source/native-mim-geometry.json').read_text())
  text=(OUT/'capture/wire/rc03/wires.spice').read_text()
  r['intrinsic_capture_binding']=checks.check_capture(text,anchors,mim,OUT/'mim-comparison.json')
  r['capture_controls']=checks.fault_controls(text,anchors,mim)
  r['dimension_controls']=checks.dimension_controls(mim)
  assert all(sha(OUT/'capture'/n)==prior['outputs'][n]for n in names)
  assert sha(Path(__file__))==r['controller_sha256']and sha(Path(checks.__file__))==r['checker_sha256']
  r.update(status='PASS_PLL845_PRESERVED_NATIVE_CAPTURE_AND10_CONTROL_FAMILIES_REQUIRES_RAW_RC_AUDIT',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  if(OUT/'mim-comparison.json').exists():r['mim_comparison']=json.loads((OUT/'mim-comparison.json').read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
