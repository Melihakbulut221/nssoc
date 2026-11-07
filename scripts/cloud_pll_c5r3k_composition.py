#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose whole845 native models with audited RC and exact native MIM nodes."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import compose_pll_c5r3k_body_rc as compose
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-c5r3k-composition'
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
  audit,proof=reports.restore_report('pll-c5r3k-body-audit',42402931505,
   '727646dd27b3dcf744acf587994aa432d891a164c2db3e5f84ca737998ea3f1b',
   '819d8a22ce45ca20cf23ddc970f741f401ac261dfb152447fd3032b2cab397e7',OUT/'audit',names)
  assert audit['source_head']=='600ef3a1aa20f7006b18c15672e18c20f759fef5'
  assert audit['sources_unchanged']and audit['raw_rc_audit_passed']
  assert audit['status']=='PASS_PLL845_BODY_RAW_RC_AND25_CONTROLS_REQUIRES_CONTACT_COMPOSITION_AND_LOADED_WAVES'
  assert len(audit['wire_controls']['cases'])==13 and len(audit['intrinsic_controls'])==9
  assert all(x['rejected']for x in audit['intrinsic_controls'])
  assert audit['audit']['actual_exported_resistors']==3391 and audit['audit']['actual_exported_capacitors']==5120
  assert audit['audit']['native_mim_intrinsic']['devices']==27
  assert audit['same_geometry_capacitance']['status']=='PASS_SAME_GEOMETRY_COMPLETE_COLLAPSED_C_MATRIX'
  assert len(audit['same_geometry_capacitance_controls'])==3 and all(x['rejected']for x in audit['same_geometry_capacitance_controls'])
  r['audited_source']=proof
  selected=['binding.json','pll845-compact.spice','native-devices.json']
  bound,bproof=reports.restore_report('pll-c5r3k-binding',42401324808,
   '1b56898f1b111c751fa163e5f5101b16690ba6ff1c274565eb7a740996ec4c94',
   '6f3a0643d4a5c8810f2dfb6d93f4cfec595a05513516e7179ad77366ef4799ac',OUT/'binding',selected)
  assert bound['source_head']=='c2dc688a525e88ef82c6da77e95c9a799ce33622'
  assert bound['status']=='PASS_PLL845_ALL_NATIVE_MODELS_AND35_CONTROLS_REQUIRES_WIRE_COMPOSITION_AND_LOADED_WAVES'
  assert bound['sources_unchanged']and len(bound['controls'])==35 and all(x['rejected']for x in bound['controls'])
  binding=json.loads((OUT/'binding/binding.json').read_text());assert binding==bound['binding']
  capture=json.loads((OUT/'audit/capture/result.json').read_text())
  assert capture['terminal_reference_source']['run']==bound['physical_source']['run']==42400729999
  assert capture['terminal_reference_source']['summary_sha256']==bound['physical_source']['summary_sha256']
  r['native_model_source']=bproof
  geometry_names=['source/wire/native05/result.json']
  planes,gproof=reports.restore_report('pll-c5r3k-terminals',42400729999,
   'a84c8bd1a293470747d67993738e4ba8bd0f166caede039b086751b8c95f93a7',
   '385c97636d21094a515c49ca0e984ed09d7134eeda80f687ded50989515b1e15',OUT/'planes',geometry_names)
  assert planes['sources_unchanged']and planes['native_returncode']==0 and not planes['binding']['unresolved']
  assert gproof['summary_sha256']==bound['physical_source']['summary_sha256']
  r['physical_source']=gproof;save()
  anchors=json.loads((OUT/'audit/capture/wire/anchors08.json').read_text())
  geometry=json.loads((OUT/'planes/source/wire/native05/result.json').read_text())
  assert capture['sources_unchanged']and capture['intrinsic_capture_binding']['all_mim_identities_unique']
  assert sha(OUT/'audit/capture/result.json')==audit['capture_source']['summary_sha256']
  assert capture['source_head']=='f3edc5bf6cc747bb0c1d5f26823a58576b9f6865'
  mim_groups=capture['intrinsic_capture_binding']['mim_groups']
  body_names=['regular-body-access.json']
  body,bodyproof=reports.restore_report('pll-c5r3k-body-access',42402230513,
   '395a5ee6be39be5db101cec72120ca351688f933c3dfc9a60a004667c48e0f5b',
   '093d252bb9a3501c40558a2331070a41a57bbd4c121fd43983041d96edef7668',OUT/'body',body_names)
  assert body['source_head']=='13325574ee461fb8a4e9833581d2b43ac77d1bad'and body['sources_unchanged']
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
  assert contract['counts']==dict(devices=849,auxiliary_contacts=4,total_model_instances=853,R=3391,C=5120,MIM=27)
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
