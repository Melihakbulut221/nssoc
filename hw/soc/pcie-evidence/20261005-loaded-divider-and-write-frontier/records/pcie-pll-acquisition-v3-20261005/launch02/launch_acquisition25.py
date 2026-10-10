# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restart unchanged2.5ps1us circuit from time0 after explicit user shutdown."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
import numpy as np
import numpy._core._multiarray_umath as compiled
ROOT=Path.cwd();B=Path(__file__).resolve().parent;OLD=Path('/dev/shm/nssoc-pll-acquisition-v1-evidence')
sys.path.insert(0,str(ROOT/'scripts'))
import characterize_pcie_pll_acquisition_v3 as m

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
assert sys.version_info[:3]==(3,12,3) and np.__version__=='2.5.3' and callable(np.trapezoid)
assert m.sha(m.__file__)=='d3b6706d0b8feb1c6a5c66bb434df29fe792b621200eae8fc593ea5e4faa9b8d'
assert m.sha(ROOT/'sw/tests/test_pcie_pll_acquisition_v3.py')=='ff9749a66818bbc29f403f9b17c13625dae927a9b2839c9f12c03222e4c34a83'
peer=ROOT/'hw/soc/out/pcie-phase16-delivery-20261005/pll-publication-v2-root-peer.json';q=json.loads(peer.read_text());assert q['status']=='PASS_BOUNDED_ROOT_PUBLICATION_BRIDGE_PEER'
for p,v in q['pins'].items():assert pin(ROOT/p)==v
failure=ROOT/'hw/soc/out/pcie-pll-acquisition-20261004/publication-limit-failure';q=json.loads((failure/'release.json').read_text());assert q['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assert len(q['assets'])==2 and all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in q['assets'])
validation=failure/'pcie-pll-acquisition-publication-failure-validation-20261005.json';v=json.loads(validation.read_text());assert v['status']=='PRESERVED_PUBLICATION_RESOURCE_FAILURE_NOT_ANALOG_VERDICT'
assert pin(v['archive']['path'])=={k:v['archive'][k] for k in ['bytes','sha256']}
for row in q['files']:assert pin(row['path'])=={k:row[k] for k in ['bytes','sha256']}
proof_path=Path('/dev/shm/nssoc-pll-acquisition-v1-step5-full-review-01/result.json');assert m.sha(proof_path)=='960ca00987717903f773516fecc75b3a207d027f8c7b7df860ba17dfba3241eb'
proof=json.loads(proof_path.read_text());first=Path('/dev/shm/nssoc-pll-acquisition-v1-step5-01/result.json');assert m.sha(first)=='38e2bc21a0995b6ceafd136b61c2a554476701369cefe8ef59245d0f99f237f4'
assert proof['status']=='PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC'
assert proof['native_result']==pin(first) and proof['native_authoritative_status']=='PASS_NATIVE_STREAM_FINITE_SCREEN'
assert proof['all539_author_safety_records_exact'] and proof['agreement']['all_predicates_exact'] and proof['parts']==80 and proof['rows']==202716
for p,value in proof['inputs'].items():assert pin(p)==value
gate=OLD/'second1us-prerequisites.json';assert m.sha(gate)=='b3e59bd79d68ad2a712f445773977da9bc0a8482a3520bef72aa950ef947e631'
validated=m.prerequisites(gate,m.sha(gate),2.5e-12,m.verify_parent())
ref=Path('/dev/shm/nssoc-pll-loop-stream-v1-evidence/original-public-replay-v2.json');assert m.sha(ref)=='27bd5f99f3ee3660ce567e4bcc4af4eaa018cfa44193975713ff8e13854acb35'
ready=ROOT/'hw/soc/out/pcie-agent-resume-second-20261005/publisher-v3-ready-finite.json'
assert m.sha(ready)=='549c58a7f7dbafd6532894cbbd9960387e7fb2f2db85ee4e58747b6cab3ae056'
pr=json.loads(ready.read_text());assert pr['status']=='READY_FINITE_TRANSPORT_RETRY_PUBLISHER_NATIVE_PRODUCER_BRIDGE_PENDING'
assert pr['controls']['final_passed']==31 and pr['controls']['skipped']==0
for row in pr['source_allowlist']:assert pin(ROOT/row['repository_path'])=={k:row[k] for k in ['bytes','sha256']}
failed=Path('/dev/shm/nssoc-pll-acquisition-v2-step25-after-shutdown-01/result.json')
assert json.loads(failed.read_text())['status']=='ERROR_NATIVE_OR_STREAM_CAPTURE'
# The exact new source peer pin is inserted only after its independent review.
peer3=ROOT/'hw/soc/out/pcie-pll-acquisition-v3-20261005/source-only-peer.json'
assert m.sha(peer3)=='badef7b0d0e2fab64e34873129d193e4b87f369113b0b08991f97043225d6f68'
assert json.loads(peer3.read_text())['status']=='PASS_PRODUCER_SOURCE_AND_SAVED_CONTROLS_WITH_TEST_PORTABILITY_FINDING'
portable=peer3.with_name('source-only-peer02-portable.json')
assert m.sha(portable)=='4e60de6862277ec27db4429ff67deaed9006a5acd83718fcfdab5518f9d4587c'
assert json.loads(portable.read_text())['status']=='PASS_TEST_FIXTURE_PORTABILITY_FINDING_CLOSED'
freeze=peer3.with_name('source-freeze02.json')
assert m.sha(freeze)=='a3d94ff1223739762e37fa257254adc35e917ed0e45142ed53e443b00f18f153'
for p,v in json.loads(freeze.read_text())['files'].items():assert pin(ROOT/p)==v
release=json.loads(subprocess.check_output(['gh','api',f'repos/{m.publication.REPO}/releases/tags/{m.RELEASE_TAG}']));assert release['tag_name']==m.RELEASE_TAG and len(release['assets'])+200<=1000
# Prior abruptly lost run is fully preserved, never resumed from initial OP.
interruption=ROOT/'hw/soc/out/pcie-pll-acquisition-v3-20261005/abrupt-stop-20261005'
preservation=json.loads((interruption/'preservation-validation.json').read_text())
assert preservation['status']=='PASS_ALL_REMAINING_REGULAR_FILES_SSD_FULL_MEMBER_READBACK_INCOMPLETE_RUN'
assert preservation['full_member_readback'] and preservation['all_originals_unchanged']
assert pin(Path(preservation['archive']['path']))=={k:preservation['archive'][k] for k in ['bytes','sha256']}
oldrelease=json.loads((interruption/'release01.json').read_text())
assert oldrelease['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(oldrelease['assets'])==2
assert all(a['authenticated_roundtrip'] and a['anonymous_roundtrip'] for a in oldrelease['assets'])
observation=json.loads((interruption/'interruption-observation.json').read_text())
assert observation['published_parts']==128 and not observation['solver_checkpoint_available']
for birth in observation['missing_original_births']:
 proc=Path('/proc')/str(birth['pid'])/'stat'
 if proc.exists():assert proc.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
for proc in Path('/proc').iterdir():
 if proc.name.isdigit():
  try:argv=(proc/'cmdline').read_bytes().split(b'\0')
  except (FileNotFoundError,ProcessLookupError):continue
  assert os.fsencode(str(ROOT/'scripts/characterize_pcie_pll_acquisition_v3.py')) not in argv, 'No duplicate native producer'
free=shutil.disk_usage('/dev/shm').free;assert free>=562*1024**2
out=Path('/dev/shm/nssoc-pll-acquisition-v3-step25-detached-02');assert not out.exists()
command=[sys.executable,str(ROOT/'scripts/characterize_pcie_pll_acquisition_v3.py'),'--out',str(out),'--prefix','pcie-pll-acquisition-v3-step25-detached02-20261005','--step-ps','2.5','--reference',str(ref),'--reference-sha',m.sha(ref),'--prerequisites',str(gate),'--prerequisites-sha',m.sha(gate)]
record=dict(command=command,python=sys.executable,python_version=sys.version,numpy_version=np.__version__,numpy_path=np.__file__,numpy_extension={'path':compiled.__file__,**pin(compiled.__file__)},launcher=pin(__file__),prerequisite_manifest=pin(gate),validated_prerequisite_paths=len(validated['paths']),producer=pin(m.__file__),publisher=pin(m.publication.__file__),root_source_peer=pin(peer),full_first_replay=pin(proof_path),old_failed_capture=pin('/dev/shm/nssoc-pll-acquisition-v1-step25-01/result.json'),old_failure_validation=pin(validation),old_failure_release=pin(failure/'release.json'),free_at_launch=free,release_tag=m.RELEASE_TAG,release_asset_count_at_launch=len(release['assets']),reserved_part_count=200,declaration='Full time0 restart2.5ps1us: unchanged539devices/100ppm/50ps/fixed800–900/900–1000ns windows, original runtime/numerics and50MiB/512MiB resources. Only bounded transport publication implementation and input pins changed; previous379ns resourceERROR,594ns interruption,50.5816ns TLS failure and both400nsFAILs remain immutable. Full capture/raw review/pair agreement required. No healthy elapsed watchdog.')
assert os.sched_getaffinity(0)=={12}, 'Dedicated PLL CPU12 required'
record.update(user_resume_authorized=True,controller_affinity=sorted(os.sched_getaffinity(0)),shutdown_checkpoint=pin(ROOT/'hw/soc/out/pcie-agent-shutdown-20261005/shutdown-checkpoint.json'),interrupted_v2_result=pin('/dev/shm/nssoc-pll-acquisition-v2-step25-01/result.json'),failed_v2_after_shutdown_result=pin(failed),publisher_controls=pin(ready),producer_peer=pin(peer3),producer_portability_peer=pin(portable),producer_source_freeze=pin(freeze),resume_scope='Fresh time0 restart in new output/prefix after31 publisher controls and15 exact bridge/integration controls. Existing594ns interruption and50.5816ns TLS capture remain immutable. Same539devices, fixed acquisition windows,100ppm/50ps acceptance and paired review requirements. No physics or resource-limit change.')
(B/'command-runtime.json').write_text(json.dumps(record,indent=2)+'\n');print('acquisition_v3_restart_pid',os.getpid(),flush=True)
fd=os.open(B/'launch.log',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.dup2(fd,1);os.dup2(fd,2);os.close(fd);os.execv(command[0],command)
