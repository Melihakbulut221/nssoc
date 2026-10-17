"""Preserve two completed native finite screens, full replays and failed frozen pair predicate."""
from pathlib import Path
import hashlib,json,tarfile,datetime
B=Path(__file__).resolve().parent;R=Path.cwd()
A=Path('/dev/shm/nssoc-pll-acquisition-v1-step5-01');C=Path('/dev/shm/nssoc-pll-acquisition-v3-step25-detached-02')
Q=Path('/dev/shm/nssoc-pll-acquisition-v1-step5-full-review-01/result.json');DECL=Path('/dev/shm/nssoc-pll-acquisition-v1-evidence/pair-screen-declaration.json')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def dump(p,d):
 with Path(p).open('x')as f:json.dump(d,f,indent=2);f.write('\n')
q=json.loads((B/'result.json').read_text());e=json.loads((B/'execution.json').read_text());pair=json.loads((B/'pair-result.json').read_text());qa=json.loads(Q.read_text())
assert e['status']=='PASS_COMPLETED_PUBLIC_REPLAY'and e['returncode']==0
assert pin(B/'result.json')==e['result']and pin(B/'review.log')==e['log']
assert q['status']==qa['status']=='PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC'
assert len(q['parts'])==159 and q['rows']==401607 and q['values']==331727382 and q['all539_author_safety_records_exact']
assert pair['status']=='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN'and pair['passed']is False
for p,v in pair['inputs'].items():assert pin(p)==v
for row in pair['windows']:
 assert row['checks']==dict(both_individual_windows_pass=True,frequency_difference_100ppm=True,matched_phase_difference_50ps=False)
for native,review in [(A,qa),(C,q)]:
 r=json.loads((native/'result.json').read_text());assert r['status']=='PASS_NATIVE_STREAM_FINITE_SCREEN';assert review['native_result']==pin(native/'result.json')
 for p,v in review['inputs'].items():assert pin(p)==v
 for n,v in r['outputs'].items():assert pin(native/n)==v
for pid in [196570,196571,107895,107905]:assert not Path('/proc',str(pid)).exists()
# Preserve actual tool outcome, never infer a success from individual windows.
dump(B/'pair-execution-observation.json',dict(status='COMPLETED_PAIR_PREDICATE_REJECTED',observed_returncode=1,method=pin(R/'scripts/compare_pcie_pll_acquisition_pair_v1.py'),result=pin(B/'pair-result.json'),log=pin(B/'pair-comparison.log'),elapsed_seconds=None,elapsed_note='Tool invocation returned exit1 after0.430223946seconds; no separate native run.',native_restarted=False,declared_phase_limit_ps=50,declared_frequency_limit_ppm=100))
files={}
for prefix,root in [('native5ps',A),('native2p5ps',C),('review2p5ps',B)]:
 for p in root.rglob('*'):
  if p.is_file()and not p.is_symlink()and '__pycache__'not in p.parts and p.name not in ['seal-replay-pair01.log']:
   files[prefix+'/'+str(p.relative_to(root))]=p
for n,p in [('review5ps/result.json',Q),('declaration.json',DECL)]:files[n]=p
for name in ['scripts/review_pcie_pll_acquisition_v1.py','scripts/compare_pcie_pll_acquisition_pair_v1.py','scripts/run_pcie_pll_acquisition_v1.py','scripts/publish_pcie_native_capture_v3.py']:
 p=R/name
 if p.exists():files['source/'+name]=p
manifest={n:dict(original_path=str(p),**pin(p))for n,p in sorted(files.items())};mp=B/'replay-pair-members.json';dump(mp,manifest)
a=B/'pcie-pll-step25-public-replay-and-failed-pair-20261006.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as t:
 for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz')as t:
 assert set(t.getnames())==set(manifest)|{'members.json'}
 for m in t.getmembers():
  v=pin(mp)if m.name=='members.json'else manifest[m.name];assert m.isfile()and m.size==v['bytes']
  with t.extractfile(m)as s:assert hashlib.file_digest(s,'sha256').hexdigest()==v['sha256']
for n,p in files.items():assert pin(p)=={k:manifest[n][k]for k in ['bytes','sha256']}
x=dict(status='SEALED_COMPLETE_PUBLIC_REPLAY_AND_REAL_TIMESTEP_PHASE_FAILURE',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive=dict(path=str(a),**pin(a),members=len(manifest)+1),full_member_readback=True,all_original_files_rehashed=True,native5ps=pin(A/'result.json'),native2p5ps=pin(C/'result.json'),first_review=pin(Q),second_review=pin(B/'result.json'),replay_execution=pin(B/'execution.json'),replay_parts=159,rows=q['rows'],values=q['values'],all539_author_safety_records_exact=True,failed_pair=pair,full_nominal_timestep_convergence=False,physical_acceptance=False,scope='No new simulation. Both individual1us nominal finite screens and their complete public raw replay pass. Frozen100ppm/50ps pair predicates fail matched phase by~695ps in both declared windows. Do not remove phase offset or relax limits. No PVT/jitter/thermal/layout/foundry/fullPLL/fullPHY qualification.')
v=B/'pcie-pll-step25-public-replay-pair-validation-20261006.json';dump(v,x);print(json.dumps(dict(archive=x['archive'],validation=pin(v))))
