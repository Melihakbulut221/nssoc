#!/usr/bin/env python3
"""Qualify indexed exact contacts on native parent geometry; not core signoff."""
import os,json,hashlib,subprocess,tempfile
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-indexed-geometry-audit'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,full_core_checked=False)
 try:
  assert sha(ROOT/'scripts/audit_native_signal_geometry.py')=='1dff792cfc90b6c8fbeb80df547aad824a2e768b1ff50336c31af04358940312'
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/native_geometry_contact_index.py';native=ROOT/'scripts/audit_native_signal_geometry_indexed.py'
  protected={str(p):sha(p)for p in [Path(__file__),helper,native,ROOT/'scripts/audit_native_signal_geometry.py']}
  with (OUT/'index-controls.json').open('w')as log:subprocess.run(['python3',str(helper)],stdout=log,stderr=subprocess.STDOUT,check=True)
  controls=json.loads((OUT/'index-controls.json').read_text());assert controls['passed']and controls['comparisons']==1624
  run=completed(44312962654,'650e309f79e1853b2169f79289816c374621699f');z,m=archive(run,'core-only-chip-gpio-repaired-route-native-44312962654');assert m['id']==14430474684 and m['digest']=='sha256:b096344f7e21a97e03e50864a4bc88ad8519583841e40ea64d407d10f2c5ade6'
  source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['native_drc_count']==0
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  name='chip-detailedroute.odb';assert name in source['outputs']
  with tempfile.TemporaryDirectory(prefix='nssoc-native-parent-')as tmp:
   odb=Path(tmp)/'source.odb';odb.write_bytes(z.read(name));env=dict(os.environ,NSSOC_PHYSICAL_ROUTE_OUT=str(OUT),NSSOC_PHYSICAL_ROUTE_ODB=str(odb))
   with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(native)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   assert sha(odb)==source['outputs'][name]
  report=json.loads((OUT/'physical-route-audit.json').read_text());prior=source['geometry_audit']
  for key in ['source_odb_sha256','signal_nets_with_disconnected_geometry','unwired_multi_terminal_nets','terminals_without_geometry','inter_net_contact_pairs','contact_counts','native_decoder_qualification','synthetic_controls']:
   assert report[key]==prior[key],key
  assert report['source_unchanged']and report['actual_route_removal_control']and not report['accepted']
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='PASS_INDEX_REFERENCE_AND_NATIVE_PARENT_GEOMETRY_REQUIRES_CORE_VALIDATION',sources_unchanged=True,protected_inputs=protected,controls=controls,source_artifact=m,geometry=report)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
