#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose whole845 native models with audited RC and exact native MIM nodes."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import compose_pll845_body_rc as compose
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll845-body-composition'
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
   'capture/result.json','capture/body/regular-body-access.json','capture/source/source/native-mim-geometry.json']
  audit,proof=reports.restore_report('pll845-body-raw-audit',39358698811,
   '41b7ca6e47306db0cb1cfa0a1a03acc5dc35a92a079def0adad9a6e5823b3e9c',
   '12a90945cf50d121acede0cd96c419f9d5d5a25d5bb201d8540c3c1f742c8a9e',OUT/'audit',names)
  assert audit['source_head']=='9dd5bfdf0ed1d588282213f96b7e56851e90c75c'
  assert audit['sources_unchanged']and audit['raw_rc_audit_passed']
  assert audit['status']=='PASS_PLL845_BODY_RAW_RC_AND25_CONTROLS_REQUIRES_CONTACT_COMPOSITION_AND_LOADED_WAVES'
  assert len(audit['wire_controls']['cases'])==13 and len(audit['intrinsic_controls'])==9
  assert all(x['rejected']for x in audit['intrinsic_controls'])
  assert audit['audit']['actual_exported_resistors']==3381 and audit['audit']['actual_exported_capacitors']==5105
  assert audit['audit']['native_mim_intrinsic']['devices']==26
  assert audit['same_geometry_capacitance']['status']=='PASS_SAME_GEOMETRY_COMPLETE_COLLAPSED_C_MATRIX'
  assert len(audit['same_geometry_capacitance_controls'])==3 and all(x['rejected']for x in audit['same_geometry_capacitance_controls'])
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
  assert capture['sources_unchanged']and capture['intrinsic_capture_binding']['all_mim_identities_unique']
  assert sha(OUT/'audit/capture/result.json')==audit['capture_source']['summary_sha256']
  assert capture['source_head']=='ec86f33452dc9bb737e5b209f432013670e991bc'
  mim_groups=capture['intrinsic_capture_binding']['mim_groups']
  body_names=['regular-body-access.json']
  body,bodyproof=reports.restore_report('pll845-regular-body-access',39357065697,
   '78d5a79014ad0fb9197c312f074bc488152580a22529b4744674fc612b9c5c57',
   'c88f91f4b630fb5556efcec1369bcc3d53c083f21979684030320b1e0d90ace2',OUT/'body',body_names)
  assert body['source_head']=='bf687e183858e8cf29ae89a9f9e2e5890178939c'and body['sources_unchanged']
  assert body['status']=='PASS_ACTUAL_REGULAR_NWELL_CONTACT_GEOMETRY_REQUIRES_FRESH_RC_AND_COMPOSITION'
  assert bodyproof['summary_sha256']==capture['regular_body_geometry_source']['summary_sha256']
  assert body['physical_source']['summary_sha256']==gproof['summary_sha256']
  bodyrecord=json.loads((OUT/'body/regular-body-access.json').read_text())
  assert bodyrecord==body['body_access']==json.loads((OUT/'audit/capture/body/regular-body-access.json').read_text())
  assert len(bodyrecord['controls'])==5 and all(x['rejected']and x['cases']==4 for x in bodyrecord['controls'])
  body_plan=bodyrecord['plan'];r['body_geometry_source']=bodyproof
  wiretext=(OUT/'audit/capture/wire/rc03/wires.spice').read_text()
  text,contract=compose.assemble(binding,anchors,geometry,wiretext,mim_groups,body_plan)
  assert compose.verify(text,binding,anchors,geometry,wiretext,mim_groups,body_plan)==contract
  (OUT/'pll845-mim-wire.spice').write_text(text)
  (OUT/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
  r['composition']=contract;save()
  assert not contract['uncontacted_body_groups'],('Native body access requires actual tap extraction; no silently floating bulk nodes',contract['uncontacted_body_groups'])
  r['controls']=compose.faults(text,binding,anchors,geometry,wiretext,mim_groups,body_plan)
  assert len(r['controls'])==62 and all(x['rejected']for x in r['controls'])
  assert contract['counts']==dict(devices=845,auxiliary_contacts=4,total_model_instances=849,R=3381,C=5105,MIM=26)
  assert all(sha(OUT/'audit'/n)==audit['outputs'][n]for n in names)
  assert all(sha(OUT/'binding'/n)==bound['outputs'][n]for n in selected)
  assert all(sha(OUT/'planes'/n)==planes['outputs'][n]for n in geometry_names)
  assert all(sha(OUT/'body'/n)==body['outputs'][n]for n in body_names)
  assert sha(Path(__file__))==r['controller_sha256']and sha(Path(compose.__file__))==r['composer_sha256']
  r.update(status='PASS_PLL845_BODY_COMPOSITION_AND62_CONTROLS_REQUIRES_LOADED_CLOSED_LOOP',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
