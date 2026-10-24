#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose whole845 native models with audited RC and exact native MIM nodes."""
import json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import compose_pll845_body_rc as compose
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-composition'
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
  audit,proof=reports.restore_report('pll-rhi120-c8-body-audit',39919694972,
   'bfb12bb12fb38ccead4a7a026eab1f3f1cde1c74f3c4f87de98f42aa3f95ca16',
   '4d39ef3f1334716fd8785b2df109d1fb6f97ab2bc10628509617fbaca3690c4a',OUT/'audit',names)
  assert audit['source_head']=='77421080e0e25df82f3a460ba683bbc500b29ad6'
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
  bound,bproof=reports.restore_report('pll-rhi120-c8-binding',39916625647,
   'e0be95566badf2909b157ceddf9b892a76d961c2f8185e975f494af81891bcc4',
   '708b0baadfc89a389ea0f60dce7f91df595c3cbbb96447c9f8a393a12a2d0cb5',OUT/'binding',selected)
  assert bound['source_head']=='23e41e8d55aa42a3f4456af5ac75f806605f529d'
  assert bound['status']=='PASS_PLL845_ALL_NATIVE_MODELS_AND35_CONTROLS_REQUIRES_WIRE_COMPOSITION_AND_LOADED_WAVES'
  assert bound['sources_unchanged']and len(bound['controls'])==35 and all(x['rejected']for x in bound['controls'])
  binding=json.loads((OUT/'binding/binding.json').read_text());assert binding==bound['binding']
  capture=json.loads((OUT/'audit/capture/result.json').read_text())
  assert capture['terminal_reference_source']['run']==bound['physical_source']['run']==39915871064
  assert capture['terminal_reference_source']['summary_sha256']==bound['physical_source']['summary_sha256']
  r['native_model_source']=bproof
  geometry_names=['source/wire/native05/result.json']
  planes,gproof=reports.restore_report('pll-rhi120-c8-terminals',39915871064,
   '558a1d37cb69163ed67d4641b91d56467a8fb998f378e9d2dec6e6370beebe0a',
   '29844ac319e058685a56248eff381a224b14686d83327b85e3a0099129a4ea74',OUT/'planes',geometry_names)
  assert planes['sources_unchanged']and planes['native_returncode']==0 and not planes['binding']['unresolved']
  assert gproof['summary_sha256']==bound['physical_source']['summary_sha256']
  r['physical_source']=gproof;save()
  anchors=json.loads((OUT/'audit/capture/wire/anchors08.json').read_text())
  geometry=json.loads((OUT/'planes/source/wire/native05/result.json').read_text())
  assert capture['sources_unchanged']and capture['intrinsic_capture_binding']['all_mim_identities_unique']
  assert sha(OUT/'audit/capture/result.json')==audit['capture_source']['summary_sha256']
  assert capture['source_head']=='fff80cfb71ea5b43445f9a224a3e64dd18de7c5c'
  mim_groups=capture['intrinsic_capture_binding']['mim_groups']
  body_names=['regular-body-access.json']
  body,bodyproof=reports.restore_report('pll-rhi120-c8-body-access',39918715172,
   '3ad2fb167b455eb93df5c64c125802d2e48c11b7b49f0328247e581a916f6def',
   '86498acd8d058a443d868b249f5bd269d27aec9c58e8325b4ac58906e406172a',OUT/'body',body_names)
  assert body['source_head']=='4e64885879eb392bcea9d8eca1ca38b72e0ce801'and body['sources_unchanged']
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
