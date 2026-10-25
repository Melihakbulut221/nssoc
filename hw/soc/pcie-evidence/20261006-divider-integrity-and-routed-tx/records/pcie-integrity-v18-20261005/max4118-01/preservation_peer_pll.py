"""Independent source review of closed MAX4118 sealing and owned publication."""
from pathlib import Path
import ast,datetime,hashlib,json
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=json.loads((B/'preservation-policy.json').read_text())
assert pin(B/'preservation-policy.json')==dict(bytes=3086,sha256='3ff308f88d214d2866b9c2a1948f75a516b929176dabe29afe15a38ae44153ff')
for name,value in p['pins'].items():assert pin(name)==value,name
s=(B/'continue_preservation.py').read_text();z=(B/'seal.py').read_text();ast.parse(s);ast.parse(z)
assert 'os.kill' not in s and 'signal.' not in s
assert "current['start_ticks'] == policy['controller']['start_ticks']" in s
assert "terminal['boot_id'] == policy['boot_id']" in s
assert "terminal['controller'] == policy['controller']" in s
assert "all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in release['assets'])" in s
assert "for a in release['assets']} == expected" in s
for name in ['source_peer_pll.py','source-peer-pll.log','preservation-source-peer.json','preservation-policy.json','continue_preservation.py']:
 assert repr(name) in z,name
assert "assert p.is_file(), ('Mandatory completed evidence', name)" in z
assert 'len(cases) == 13' in z and 'dict(passed=13, failed=0, skipped=0)' in z
assert "'CLOSED_MAX4118_FUNCTIONAL_FAILURES_RETAINED'" in z
assert "'x:xz'" in z and "assert all(pin(p) == members[n] for n, p in files.items())" in z
runtime=json.loads((B/'runtime-targets-observed01.json').read_text())
for name,value in runtime['files'].items():assert pin(name)==value,name
identity=p['controller'];q=Path('/proc')/str(identity['pid'])/'stat';observed=None
if q.exists():
 fields=q.read_text().rsplit(') ',1)[1].split();observed=dict(pid=identity['pid'],state=fields[0],start_ticks=fields[19],matches_original_birth=fields[19]==identity['start_ticks'])
r=dict(status='PASS_SOURCE_ONLY_V18_MAX4118_PRESERVATION',utc=datetime.datetime.now(datetime.UTC).isoformat(),policy=pin(B/'preservation-policy.json'),method=pin(Path(__file__)),files={n:pin(B/n) for n in ['seal.py','continue_preservation.py']},rehashes=dict(policy=len(p['pins']),observed_runtime=len(runtime['files'])),original_controller_readonly_observation=observed,findings=[],reviewed=['Observer binds currentboot and exactstoredcontroller PID/start, never adopts/signals/waits onoriginal viaowner; only observationalpoll untiloriginalbirth gone/Z.','Sealing requires terminaltwo-stage receipt, matchingboot/controller/policy and no descendants; own newstage commands alone enterProcessOwner.','Sealer rehashes frozen110 originalpins and actualobservedruntime targets, checks bothcompletedpytest returns withownerreapstatus, exact4118/R2048/2GiB helper records and inputs/outputs/runtime.','PASSrequires13+13 unskipped actualcocotb cases and bothpytestPASS; failures retain FAIL/helper/XML evidence and cannot countasPASS. Miter scope validatesmaximum/sourcepins.','All rawfunctional/lifecycle captures and mandatoryactualpeer methods/logs included; uniqueexclusivearchivecreation, complete memberbyte/hash readback and immutableoriginalrecheck. Firstsourcecandidate omitted actualpeerfilename and was corrected beforefreeze, preservedbyRX.','OnlypublisherV3 authenticated+anonymous roundtrips of exactthree filenames/sizes/SHAs countaspublication. Ownership checks followingcompletion andafterownerexit preventstop misclassification ascomplete.','Ownstage2GiB andscratch/diskfloors; nohealthyelapsedwatchdog. Explicitstop/error cancels onlyownednewstages,15secondoutergrace accommodatesfrozenpublishercleanup.'],scope='Source-only review withpolicy/runtime rehashes andoriginalcontroller readonlybirth observation. No MAX4118/nativetest executed orsignaled, no XMLresults claimed whileoriginalrun islive; future independent finite-review stillrequired.')
with (B/'preservation-source-peer.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(pin(B/'preservation-source-peer.json')))
