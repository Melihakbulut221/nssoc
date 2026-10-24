#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native geometry proof for previously implicit standard-cell n-well contacts."""
import json,os,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pll845_native_models as models
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-body-access'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 helper=ROOT/'scripts/pll_rhi120_c8_body_access_native.py'
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_phy_accepted=False,
  composition_accepted=False,loaded_simulation_passed=False,controller_sha256=sha(Path(__file__)),
  helper_sha256=sha(helper),model_converter_sha256=sha(Path(models.__file__)))
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  names=['capture/wire/anchors08.json']
  apin=json.loads((ROOT/'docs/evidence/pll-rhi120-c8-raw-audit-pass-20261023.json').read_text())
  audited,proof=reports.restore_report('pll-rhi120-c8-raw-audit',apin['run'],apin['summary_sha256'],apin['parts_sha256'],OUT/'audit',names)
  assert audited==apin['report']and audited['raw_rc_audit_passed']and audited['sources_unchanged']
  assert len(audited['wire_controls']['cases'])==13 and len(audited['intrinsic_controls'])==9
  r['audited_wire_source']=proof
  bpin=json.loads((ROOT/'docs/evidence/pll-rhi120-c8-binding-pass-20261023.json').read_text())
  binding_names=['binding.json']
  bound,bproof=reports.restore_report('pll-rhi120-c8-binding',bpin['run'],bpin['summary_sha256'],bpin['parts_sha256'],OUT/'binding',binding_names)
  assert bound['status']==bpin['status']and bound['sources_unchanged']
  assert len(bound['controls'])==35 and all(c['rejected']for c in bound['controls'])
  r['native_binding_source']=bproof
  selected=['source/parent/integrated/nssoc_pll845_divider3p2_rhi120_c8_development.gds',
   'source/parent/physical/lvs_flat/result.lvsdb','source/wire/native05/result.json','source/wire/native05/wires.l2n']
  prior,pproof=reports.restore_report('pll-rhi120-c8-terminals',39915871064,
   '558a1d37cb69163ed67d4641b91d56467a8fb998f378e9d2dec6e6370beebe0a',
   '29844ac319e058685a56248eff381a224b14686d83327b85e3a0099129a4ea74',OUT/'planes',selected)
  assert prior['sources_unchanged']and prior['native_returncode']==0 and not prior['binding']['unresolved']
  assert pproof['summary_sha256']==bound['physical_source']['summary_sha256']
  assert audited['capture_source']['summary_sha256']=='c13eb417f3c9a8cfe4dc2260dd58233f171a410314209f5a2952643c1e3d57fd'
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
  assert data['plan']['original_audited_wire_points_preserved']and not data['plan']['wire_geometry_changed']
  assert data['plan']['fresh_wire_rc_required']==bool(data['plan']['new_reference_count'])
  assert sha(OUT/'extended-anchors.json')==data['extended_anchors_sha256']
  assert all(sha(OUT/'audit'/n)==audited['outputs'][n]for n in names)
  assert all(sha(OUT/'binding'/n)==bound['outputs'][n]for n in binding_names)
  assert all(sha(OUT/'planes'/n)==prior['outputs'][n]for n in selected)
  assert all(sha(Path(n))==digest for n,digest in data['inputs'].items())
  assert sha(Path(__file__))==r['controller_sha256']and sha(helper)==r['helper_sha256']and sha(Path(models.__file__))==r['model_converter_sha256']
  r.update(status=data['status'],sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
