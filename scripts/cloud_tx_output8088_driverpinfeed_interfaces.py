#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reprobe every real repaired TX interface; source-only until parent review."""
import ast,hashlib,json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-driverpinfeed-interfaces'
REPO='repos/Melihakbulut221/nssoc/'
BASE='scripts/bind_tx_output8088_power128return64via3_interfaces.py'
BASE_SHA='3bc0c4c9a65b5ee929cbe51be2fed008b19ff5a412ad9524178a08f8016cb94b'
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
 locked=json.loads((ROOT/'scripts/tx-driverpinfeed-interface-methods.json').read_text())
 assert all(sha(ROOT/p)==h for p,h in locked.items())
 assert sha(ROOT/BASE)==BASE_SHA
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,electrical_accepted=False,full_phy_accepted=False,
  qualified_pex=False,no_new_simulation=True,scope='Fresh native endpoint readback of the repaired GDS/LVS. Original coordinate metadata is separately preserved, never treated as a fresh physical test.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 protected={ROOT/p:h for p,h in locked.items()};loaded={}
 save()
 try:
  # Root supplies these four exact immutable fields only after reviewing
  # passing precision/composition and measured before/after rail resistance.
  pin=json.loads(os.environ['NSSOC_TX_COMPOSITION_SOURCE'])
  assert set(pin)=={'run','source_head','summary_sha256','parts_sha256'}
  q=api('actions/runs/'+str(pin['run']))
  assert q['status']=='completed'and q['conclusion']=='success'and q['head_sha']==pin['source_head']and q['run_attempt']==1
  assert q['head_branch']=='codex/tx-via3-rail-diagnosis'and q['path']=='.github/workflows/tx-output8088-driverpinfeed-composition-cloud.yml'
  inputs=[
   ('tx-output8088-driver-pinfeed',40070667147,
    'b6680151c8741fb11a4a5c6fbbe24815850a7de510dd6d72dc38fbf0625662d9','de46b737608b3065d60970518695a6c35de952b5e269b6b79c9ab424c2b199a4',
    'physical',['layout/layout.gds','flat_lvs/result.lvsdb','integration-result.json']),
   ('tx-output8088-power128return64via3-physical',39986288644,
    'beb59b25341649a13da73cead0e64c5dfaf8fda43b5214838ee6b8c4adda054d','268091ef768795110448ebbd0008c6113ca1e8e6f4bea54a9647ee5a269f256b',
    'original-physical',['integration-result.json']),
   ('tx-raw64-powered-physical',39466552523,
    'f5fcdbdee650f3c7868e671a9a05b0f3a7db3c78a0be76fe4afb828a1cd73d53','2a3431b7a2cae61f6b9edcbce8edeef23963bc62c170332064a5ab779ac58404',
    'core-metadata',['source/core/layout/result.json','source/handoff-result.json']),
   ('tx-output8088-driver-pinfeed-wires-anchors',40071267004,
    'b40767d0a3dc77124ff0ae6ebf4f11f5c79fd4241492cbabc6b52ee30ffe4f8b','823af2aa83ea8cc284b21f9513233cbe8ab5e792628f01af7c23eebb99aaf74f',
    'wires',['source/native01/result.json']),
   ('tx-output8088-driverpinfeed-composition',pin['run'],pin['summary_sha256'],pin['parts_sha256'],
    'composed',['composition.json','output8088-wire.spice','intrinsic/native.json','intrinsic/source/anchors.json','rail-comparison/result.json'])]
  for group,run,summary,parts,folder,names in inputs:
   d,proof=reports.restore_report(group,run,summary,parts,OUT/folder,names)
   assert d['sources_unchanged']and d['status'].startswith('PASS_')
   loaded[folder]=d;r.setdefault('sources',{})[folder]=proof
   protected.update({OUT/folder/n:d['outputs'][n]for n in names});save()
  physical=loaded['physical'];original=loaded['original-physical']
  assert physical['source_head']=='74bc46d2e9518821a12c66b6a071add579ccf2df'
  assert physical['status']=='PASS_ACTUAL128_DRIVER_PINFEEDS_NATIVE_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC'
  current_steps=('drc','deep_lvs','flat_lvs','source_access_open','body_supply_short','wrong_width','offgrid')
  assert set(physical['steps'])==set(current_steps)and all(physical['steps'][n]['expected_verdict_observed']for n in current_steps)
  assert physical['steps']['drc']['measurement']['category_count']==560 and physical['steps']['drc']['measurement']['markers']==0
  for name in ('deep_lvs','flat_lvs'):
   step=physical['steps'][name]
   assert step['external_ports']['passed']and step['external_ports']['actual_count']==165
   assert step['audit']['status']=='PASS within comparison scope'and not step['audit']['extraction_diagnostics']
   assert step['audit']['circuits'][0]['layout_devices_recursive']==step['audit']['circuits'][0]['schematic_devices_recursive']==8088
  g=physical['geometry']
  assert g['route_count']==128 and g['reference_devices']==8088
  assert g['all_original_material_preserved']and g['intrinsic_layers_and_all_port_shapes_unchanged']and g['serialized_geometry_verified']
  assert original['source_head']=='438d6e842b8cea5f5d561d6d333480580ddabad6'
  assert g['source_gds_sha256']==original['outputs']['layout/layout.gds']=='853fcb891bad225640d3f37a1cd234f9a3ad82923ad56d6dbeeded523ea95a4e'
  historical_steps=('drc','deep_lvs','flat_lvs','handoff_open','output_return_open','wrong_width','body_supply_short','wrong_output_Nx','internal_port_alias','offgrid','swap_output_inputs')
  assert all(original['steps'][n]['expected_verdict_observed']for n in historical_steps)
  assert original['geometry']['native_material_preserved']and original['geometry']['serialized_geometry_verified']
  assert original['geometry']['source_core_gds_sha256']==loaded['core-metadata']['outputs']['layout/layout.gds']=='9583c6cf7f70d4dad4736b808535ef564bed11d0730ce4674314025d0beaebdb'
  assert sha(OUT/'original-physical/integration-result.json')=='4e6bfef0b32c90e9ddcc57c382566aa75ab01bf070f58587f161f6739ef3e48a'
  r['physical_control_scope']=dict(current_repaired_geometry=list(current_steps),historical_predecessor_only=list(historical_steps),
   original_semantic_coordinates_reprobed_on_new_geometry=True)
  wires=loaded['wires']
  assert wires['source_head']=='737bef27ae4bd8ddb0b2740f2e0562cb51f8991b'and len(wires['anchor_controls'])==6
  assert wires['binding_counts']==dict(devices=8088,terminals=28620,metal_terminals=20532,body_terminals=8088,public_ports=165,unique_reference_planes=13370,wire_components=703)
  composed=loaded['composed']
  assert composed['source_head']==pin['source_head']and composed['status']=='PASS_ACTUAL_FULL8088_DRIVERPINFEED_PARENT_WIRE_COMPOSITION_AND25_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
  assert len(composed['controls'])==25 and all(c['rejected']for c in composed['controls'])
  assert composed['followthrough']['status']=='PASS_EXACT_PRECISION_COMPOSITION_AND_RAIL_ACCESS_REQUIRES_PARENT_REVIEW'
  assert composed['launcher']['generated_sources_unchanged']
  assert sha(OUT/'composed/output8088-wire.spice')==composed['model_sha256']
  assert sha(OUT/'composed/composition.json')==composed['composition_sha256']
  rail=json.loads((OUT/'composed/rail-comparison/result.json').read_text())
  assert rail['status']=='COMPLETE_EXACT128_DRIVER_AND2_TAIL_RAIL_RESISTANCE_COMPARISON_NOT_ELECTRICAL_ACCEPTANCE'
  assert rail['sources_unchanged']and rail['all8088_intrinsic_and_complete_terminal_body_fingerprints_equal']
  assert rail['counts']==dict(drivers=128,final_tails=2,identity_controls=6)
  counts=composed['counts'];nr=counts['R'];nc=counts['C'];assert type(nr)is type(nc)is int and nr>0 and nc>0
  assert counts==dict(devices=8088,R=nr,C=nc,external_ports=166,physical_ports=165,metal_reference_planes=13370,body_nets=65,conductors=703,terminals=28620)
  base=(ROOT/BASE).read_text()
  edits=[dict(before='R=140222,C=99906',after='R='+str(nr)+',C='+str(nc),count=1),
   dict(before="P/'wires/native01/result.json'",after="P/'wires/source/native01/result.json'",count=1),
   dict(before="physical/'integration-result.json'",after="P/'original-physical/integration-result.json'",count=1)]
  code=base
  for edit in edits:
   assert code.count(edit['before'])==edit['count'];code=code.replace(edit['before'],edit['after'])
  ast.parse(code)
  candidate=OUT/'bind-native-interfaces.py';candidate.write_text(code);protected[candidate]=sha(candidate)
  (OUT/'native-method.json').write_text(json.dumps(dict(baseline=BASE,baseline_sha256=BASE_SHA,candidate_sha256=sha(candidate),edits=edits,
   scope='Only exact fresh R/C census and explicit restored metadata paths. Actual new GDS/LVS probes, all28620 terminals,124legs/372bases/64drivers/four outputs and every original control unchanged.'),indent=2)+'\n')
  topology=ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json'
  p=json.loads(topology.read_text());assert p['run']==39304550527 and p['summary_sha256']=='03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d'
  (OUT/'topology.json').write_text(json.dumps(p['report'],indent=2)+'\n');protected[topology]=sha(topology)
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  with (OUT/'native-interface-binding.log').open('w')as log:
   code=subprocess.call([str(app),'python',str(candidate),str(OUT),str(OUT/'interfaces.json')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r['native_returncode']=code;save()
  assert code==0,'Fresh native interface/geometry/identity control rejected'
  interfaces=json.loads((OUT/'interfaces.json').read_text())
  assert interfaces['status']=='PASS_ACTUAL8088_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_FOUR_OUTPUT_PORTS_REQUIRES_LOADED_WAVES'
  assert len(interfaces['references'])==124 and len(interfaces['drivers'])==64 and len(interfaces['output_ports'])==4
  assert sum(len(x['terminals'])for x in interfaces['references'].values())==372 and interfaces['all_native_terminals_checked']==28620
  assert len(interfaces['controls'])==8 and len(interfaces['actual_endpoint_faults'])==2 and len(interfaces['output_port_controls'])==2
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status=interfaces['status'],sources_unchanged=True,counts=dict(input_legs=124,data_bases=372,driver_handoffs=64,output_ports=4,native_terminals=28620),
   controls=interfaces['controls'],actual_endpoint_faults=interfaces['actual_endpoint_faults'],output_port_controls=interfaces['output_port_controls'],
   interfaces_sha256=sha(OUT/'interfaces.json'),protected_inputs={str(p):h for p,h in protected.items()},
   next_action='Prepare a fresh immutable native trajectory from this new model only after parent review. No transient has run.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
