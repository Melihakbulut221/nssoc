import hashlib,json,os,subprocess,tempfile,sys
import mainchip_two_signal_internal_witness as observer
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
scanner=root/'docs/evidence/openroad-find-messages-dcf36133.py'
assert hashlib.sha256(scanner.read_bytes()).hexdigest()=='21dcb1a4a4916c9a429bf1aa7d6444a75c1bbf0851a4d156e97d86678bf994fe'
with tempfile.TemporaryDirectory(prefix='nssoc-guide-messages-')as folder:
 folder=Path(folder)
 (folder/'FlexDR.cpp').write_bytes(derived)
 (folder/'TritonRoute.cpp').write_bytes(observer.derive((root/observer.PRIMARY).read_bytes()))
 (folder/'MainchipInternalWitness.h').write_bytes((root/observer.HEADER).read_bytes())
 argv=[sys.executable,str(scanner),'--dir',str(folder)]
 valid=subprocess.run(argv,capture_output=True,text=True,timeout=30)
 assert valid.returncode==0,(valid.stdout,valid.stderr)
 assert 'DRT 10000'in valid.stdout and 'DRT 9999'in valid.stdout and 'DRT 9998'in valid.stdout
 assert derived.count(b'utl::DRT, 10000,')==1
 (folder/'FlexDR.cpp').write_bytes(derived.replace(b'utl::DRT, 10000,',b'utl::DRT, 9999,',1))
 collision=subprocess.run(argv,capture_output=True,text=True,timeout=30)
 assert collision.returncode==1 and 'DRT 9999 used 2 times'in collision.stderr
 message_controls=dict(actual_upstream_scanner=True,combined_derived_sources=3,corrected_IDs_passed=True,original_collision_rejected=True,
   collision_stderr=collision.stderr,whole_DRT_module_checked=False,full_module_preflight_required_before_native_build=True)
print(json.dumps(dict(message_controls=message_controls,status='PASS_BOUND_GUIDE_WORKER_LIFETIME_SOURCE_CONTROLS',upstream_sha256=p.UPSTREAM_SHA256,derived_sha256=p.DERIVED_SHA256,
 complete_source_reversal=True,upstream_refusals=refused,compiled_lifetime_cases=9,maximum_live_workers=2,
 fixture_compiled=True,complete_engine_compiled=False,native_chip_routing_executed=False,physical_acceptance=False,timing_accepted=False),sort_keys=True,indent=2))
