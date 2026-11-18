#!/usr/bin/env python3
"""Qualify indexed exact contacts on native parent geometry; not core signoff."""
import os,json,hashlib,subprocess,tempfile,time,resource
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-routed-geometry-baseline'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,current_eco_checked=False,full_gds_lvs=False,manufacturing_approved=False)
 try:
  assert sha(ROOT/'scripts/audit_native_signal_geometry.py')=='1dff792cfc90b6c8fbeb80df547aad824a2e768b1ff50336c31af04358940312'
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/native_geometry_contact_index.py';native=ROOT/'scripts/audit_native_signal_geometry_indexed.py'
  protected={str(p):sha(p)for p in [Path(__file__),helper,native,ROOT/'scripts/audit_native_signal_geometry.py']}
  with (OUT/'index-controls.json').open('w')as log:subprocess.run(['python3',str(helper)],stdout=log,stderr=subprocess.STDOUT,check=True)
  controls=json.loads((OUT/'index-controls.json').read_text());assert controls['passed']and controls['comparisons']==1624
  for p,h in [('scripts/native_geometry_contact_index.py','0423bd8ec0941d761f7594100f2e3be84f6cc6b2c67a2d55c951d69b86b7a26f'),('scripts/audit_native_signal_geometry_indexed.py','3baed05b7cbad6c03991d783fc7ad772e3b68e1534031ad07735750d7e79dabd')]:assert sha(ROOT/p)==h,p
  run=completed(44263061910,'921f49a0c7becd72e58177e19404b45e91575e63');z,m=archive(run,'core-only-detailed-route-native-44263061910');assert m['id']==14427036835 and m['digest']=='sha256:2d59e124653acb0529d73435857e701463d8db29e9bd9520ed38b9054d693b7b'
  sz,sm=archive(run,'core-only-detailed-route-summary-44263061910');assert sm['id']==14426887166 and sm['digest']=='sha256:6c7f4c49e439ac50958033f84fb23c14fda86a41d05bc3142ebb10670b8be6d8'
  assert z.read('result.json')==sz.read('result.json');source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['returncode']==0
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in source['protected_inputs'].items():
   rel=p.removeprefix('/home/runner/work/nssoc/nssoc/');assert not rel.startswith('/')
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,p
  metrics=source['routing_metrics']['values'];assert metrics['design__instance__count']==104885 and metrics['route__drc_errors']==0 and metrics['antenna__violating__nets']==0
  name='routing/1-nssoc-coreonlydetailedrouting/soc_top.odb';assert source['outputs'][name]=='eb3ed6dc3921b8b8584e455856615c5e64372650b638f9edfa2cf4e674b391c4'
  r.update(status='CHECKING_ORIGINAL_CORE_GEOMETRY',source_artifacts=[m,sm],protected_inputs=protected,scope='Original pre-ECO routed core visible native/LEF geometry, not current ECO or full transistor LVS')
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  with tempfile.TemporaryDirectory(prefix='nssoc-native-parent-')as tmp:
   odb=Path(tmp)/'source.odb';odb.write_bytes(z.read(name));env=dict(os.environ,NSSOC_PHYSICAL_ROUTE_OUT=str(OUT),NSSOC_PHYSICAL_ROUTE_ODB=str(odb))
   started=time.monotonic()
   with (OUT/'native.log').open('w')as log:
    process=subprocess.Popen([str(app),'openroad','-exit','-python',str(native)],env=env,stdout=log,stderr=subprocess.STDOUT)
    while process.poll()is None:
     print('Native core geometry PID',process.pid,'elapsed_seconds',round(time.monotonic()-started),flush=True);time.sleep(30)
   r.update(returncode=process.returncode,elapsed_seconds=time.monotonic()-started,child_maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
   if process.returncode:raise RuntimeError('Native core geometry audit failed; inspect preserved logs/reports')
   assert sha(odb)==source['outputs'][name]
  report=json.loads((OUT/'physical-route-audit.json').read_text())
  assert report['source_odb_sha256']==source['outputs'][name]and report['source_unchanged']and report['actual_route_removal_control']
  assert not report['signal_nets_with_disconnected_geometry']and not report['terminals_without_geometry']and report['inter_net_contact_pairs']==0
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='PASS_ORIGINAL_CORE_VISIBLE_GEOMETRY_REQUIRES_FINAL_ECO_AND_GDS_LVS',sources_unchanged=True,protected_inputs=protected,controls=controls,source_artifact=m,geometry=report)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
