import hashlib,json,os,subprocess,tempfile
from pathlib import Path
import mainchip_guide_worker_batch_patch as p
root=Path(__file__).resolve().parents[1]
assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
source=(root/'docs/evidence/mainchip-guide-batch-upstream-FlexDR.cpp').read_bytes()
derived=p.derive(source)
assert derived.decode().replace(p.NEW,p.OLD,1).encode()==source
refused=0
for bad in [source+b' ',source.replace(b'void FlexDR::guideTilesFlow',b'void FlexDR::otherGuideFlow',1),source.replace(b'workers_batches',b'changed_batches',1)]:
 try:p.derive(bad)
 except ValueError:refused+=1
 else:raise AssertionError('unbound upstream source')
assert refused==3
fixture=(root/'scripts/mainchip-guide-worker-lifetime-fixture.cpp').read_text()
assert fixture.count('__ACTUAL_PATCH_BODY__')==1
with tempfile.TemporaryDirectory(prefix='nssoc-guide-batch-')as folder:
 folder=Path(folder);cpp=folder/'fixture.cpp';exe=folder/'fixture'
 cpp.write_text(fixture.replace('__ACTUAL_PATCH_BODY__',p.NEW))
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],check=True,timeout=60)
 subprocess.run([str(exe)],check=True,timeout=30)
print(json.dumps(dict(status='PASS_BOUND_GUIDE_WORKER_LIFETIME_SOURCE_CONTROLS',upstream_sha256=p.UPSTREAM_SHA256,derived_sha256=p.DERIVED_SHA256,
 complete_source_reversal=True,upstream_refusals=refused,compiled_lifetime_cases=9,maximum_live_workers=2,
 fixture_compiled=True,complete_engine_compiled=False,native_chip_routing_executed=False,physical_acceptance=False,timing_accepted=False),sort_keys=True,indent=2))
