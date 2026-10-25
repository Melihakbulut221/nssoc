#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose whole845 native models with audited RC and exact native MIM nodes."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import compose_pll845_native_rc as compose
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll845-native-composition'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,
  full_phy_accepted=False,loaded_simulation_passed=False,closed_loop_accepted=False,accepted=False,
  controller_sha256=sha(Path(__file__)),composer_sha256=sha(Path(compose.__file__)))
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  names=['capture/wire/anchors08.json','capture/wire/rc03/wires.spice','capture/wire/audit.json',
   'capture/result.json','review/result.json','capture/source/source/native-mim-geometry.json']
  audit,proof=reports.restore_report('pll845-whole-raw-audit',39353209044,
   '2ac5579638869d9099c868d91d48d1ac676459c0830e2b8ff66022cea1bfc25b',
   '8b26b49da6f69a6af22fde32509c6491eef38831f2dd2c3761f9b2d4485d912a',OUT/'audit',names)
  assert audit['source_head']=='2add3d6d68a43e058e9de9d55fee7307e69de4d2'
  assert audit['sources_unchanged']and audit['raw_rc_audit_passed']
  assert audit['status']=='PASS_PLL845_WHOLE_RAW_RC_AND22_CONTROLS_REQUIRES_INTRINSIC_COMPOSITION_AND_LOADED_WAVES'
  assert len(audit['wire_controls']['cases'])==13 and len(audit['intrinsic_controls'])==9
  assert all(x['rejected']for x in audit['intrinsic_controls'])
  assert audit['audit']['actual_exported_resistors']==3380 and audit['audit']['actual_exported_capacitors']==5104
  assert audit['audit']['native_mim_intrinsic']['devices']==26
  r['audited_source']=proof
  selected=['binding.json','pll845-compact.spice','native-devices.json']
  bound,bproof=reports.restore_report('pll845-native-binding',39354573228,
   '9fbc69fbbc9a3c1b826c1c95e790ab741e1a8d466baf5aca56cfc4b6360bb031',
   'e97209d2414ee8d25c66f45a0cb3465fe3d627381f16c044f496091f3e4c7109',OUT/'binding',selected)
  assert bound['source_head']=='0e9cfd53cb8562f0b27ac09add5ede1f164ab37d'
  assert bound['status']=='PASS_PLL845_ALL_NATIVE_MODELS_AND35_CONTROLS_REQUIRES_WIRE_COMPOSITION_AND_LOADED_WAVES'
  assert bound['sources_unchanged']and len(bound['controls'])==35 and all(x['rejected']for x in bound['controls'])
  binding=json.loads((OUT/'binding/binding.json').read_text());assert binding==bound['binding']
  capture=json.loads((OUT/'audit/capture/result.json').read_text())
  assert capture['terminal_reference_source']['run']==bound['physical_source']['run']==39350440897
  assert capture['terminal_reference_source']['summary_sha256']==bound['physical_source']['summary_sha256']
  r['native_model_source']=bproof
  geometry_names=['source/wire/native05/result.json']
  planes,gproof=reports.restore_report('pll845-terminal-references',39350440897,
   '73e731a6f5f0b426170163a8ecd7f790e23364e6877747a32487fdeb1e97254d',
   'baab8d27c8b8de2390018ebb3e2d2aa369a6c4402cf797ed43e1187256a1e94d',OUT/'planes',geometry_names)
  assert planes['sources_unchanged']and planes['native_returncode']==0 and not planes['binding']['unresolved']
  assert gproof['summary_sha256']==bound['physical_source']['summary_sha256']
  r['physical_source']=gproof;save()
  anchors=json.loads((OUT/'audit/capture/wire/anchors08.json').read_text())
  geometry=json.loads((OUT/'planes/source/wire/native05/result.json').read_text())
  review=json.loads((OUT/'audit/review/result.json').read_text())
  assert review['sources_unchanged']and review['intrinsic_capture_binding']['all_mim_identities_unique']
  assert review['capture_source']['summary_sha256']==audit['capture_source']['summary_sha256']
  mim_groups=review['intrinsic_capture_binding']['mim_groups']
  wiretext=(OUT/'audit/capture/wire/rc03/wires.spice').read_text()
  text,contract=compose.assemble(binding,anchors,geometry,wiretext,mim_groups)
  assert compose.verify(text,binding,anchors,geometry,wiretext,mim_groups)==contract
  (OUT/'pll845-mim-wire.spice').write_text(text)
  (OUT/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
  r['composition']=contract;save()
  assert not contract['uncontacted_body_groups'],('Native body access requires actual tap extraction; no silently floating bulk nodes',contract['uncontacted_body_groups'])
  r['controls']=compose.faults(text,binding,anchors,geometry,wiretext,mim_groups)
  assert len(r['controls'])==46 and all(x['rejected']for x in r['controls'])
  assert contract['counts']==dict(devices=845,R=3380,C=5104,MIM=26)
  assert all(sha(OUT/'audit'/n)==audit['outputs'][n]for n in names)
  assert all(sha(OUT/'binding'/n)==bound['outputs'][n]for n in selected)
  assert all(sha(OUT/'planes'/n)==planes['outputs'][n]for n in geometry_names)
  assert sha(Path(__file__))==r['controller_sha256']and sha(Path(compose.__file__))==r['composer_sha256']
  r.update(status='PASS_PLL845_NATIVE_COMPOSITION_AND46_CONTROLS_REQUIRES_LOADED_CLOSED_LOOP',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
