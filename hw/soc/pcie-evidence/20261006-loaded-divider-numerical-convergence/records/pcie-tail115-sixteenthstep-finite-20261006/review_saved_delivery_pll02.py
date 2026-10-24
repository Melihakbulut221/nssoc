# SPDX-License-Identifier: Apache-2.0
"""Independent bounded archive/ordered publication audit. No native or network."""
from pathlib import Path
import collections,gzip,hashlib,json,lzma,math,os,resource,tarfile,time
R=Path.cwd();F=Path(__file__).resolve().parent;B=F.parent/'pcie-vco-v6-divider-tail115-v1-sixteenthstep-20261006';D=F.parent/'pcie-tail115-sixteenthstep-multipart-20261006'
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{2});started=time.monotonic()
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def wanted(r):return {k:r[k]for k in ('bytes','sha256')}
def readhash(s,count=None):
 h=hashlib.sha256();n=0
 while count is None or n<count:
  b=s.read(1024**2 if count is None else min(1024**2,count-n))
  if not b:break
  n+=len(b);h.update(b)
 if count is not None:assert n==count
 return {'bytes':n,'sha256':h.hexdigest()}
ready=F/'ready-finite01.json';assert pin(ready)=={'bytes':380986,'sha256':'af0757e05a1614f2fcbfb4f8d4c87b462e5fb0f6f3657dead3551b6739fd18cd'};f=json.loads(ready.read_text())
assert f['status']=='READY_FINITE_SIXTEENTHSTEP_FUNCTIONAL_AND_NUMERICAL_PASS_PUBLIC' and not f['physical_acceptance'] and f['future_integration_excluded'] and not f['independent_postnative_peer_pending']
assert f['method_files']==len(f['method_allowlist'])==7 and f['compact_files']==len(f['compact_evidence'])==len(f['original_evidence'])==592
checked={}
def check(p,v):
 p=str(p);assert pin(p)==v,p;checked[p]=v
for key in ('sources','method_allowlist','compact_evidence','original_evidence','public_receipts'):
 for p,v in f[key].items():check(p,v)
check(F/'finite-snapshot01.json',f['snapshot']);check(F/'complete_finite01.py',f['completion_method'])
archives=[];origins={}
for ai,a in enumerate(f['archives']):
 check(a['path'],wanted(a));check(a['manifest'],a['manifest_pin']);manifest=json.loads(Path(a['manifest']).read_text());seen={};logical=0
 with lzma.open(a['path'],'rb')as raw,tarfile.open(fileobj=raw,mode='r|',bufsize=1024**2)as t:
  for m in t:
   assert m.isfile() and m.name not in seen and m.name in manifest,m.name
   actual=readhash(t.extractfile(m));assert actual==manifest[m.name] and actual['bytes']==m.size,m.name;seen[m.name]=actual;logical+=m.size
   if ai==0:
    prefix,tail=m.name.split('/',1)
    origin={'native':Path('/dev/shm'),'project':R,'review':B,'licenses':R/'LICENSES'}[prefix]/tail
   else:origin=R/'LICENSES'/m.name.split('/',1)[1]if m.name.startswith('licenses/')else F/m.name
   check(origin,actual);origins[str(origin)]=actual
 assert seen==manifest and len(seen)==a['members'];archives.append({'path':a['path'],**wanted(a),'members':len(seen),'logical_bytes':logical,'all_member_bytes_and_current_origins_equal':True});print('archive',ai,len(seen),logical,flush=True)
assert sum(x['members']for x in archives)==f['all_archive_members']==968
# Public representation is complete ordered local bytes, not a different native capture.
rep=f['archives'][0]['public_representation'];mp=Path(rep['manifest']);check(mp,rep['manifest_pin']);partmanifest=json.loads(mp.read_text());assert len(partmanifest['parts'])==rep['parts']==24
assert wanted(partmanifest['archive'])==wanted(f['archives'][0])==rep['reconstructed_archive']
h=hashlib.sha256();offset=0
for i,row in enumerate(partmanifest['parts']):
 assert row['name']==Path(f['archives'][0]['path']).name+f'.part{i:04d}' and row['offset']==offset and 0<row['bytes']<=32*1024**2
 p=D/'parts01'/row['name'];check(p,wanted(row))
 with p.open('rb')as s:
  while b:=s.read(1024**2):offset+=len(b);h.update(b)
assert {'bytes':offset,'sha256':h.hexdigest()}==rep['reconstructed_archive']
# Every saved transport stdout/stderr full byte stream and each observed download
# is reconstructed from its immutable local prefix; failed partials remain failed.
assets=[];journalrows=[];successful_downloads=[];failures=[];transport_files={}
for path,pp in f['public_receipts'].items():
 check(path,pp);pub=json.loads(Path(path).read_text());assert pub['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and pub['tag']=='evidence-20261006-pcie-closure' and pub['explicit_stop']is False
 check(R/'scripts/publish_pcie_native_capture_v4.py',pub['source']);check(R/'scripts/characterize_pcie_clock_trim_stream_v2.py',pub['process_owner'])
 assetmap={a['name']:a for a in pub['assets']};assert len(assetmap)==len(pub['assets'])
 for row in pub['files']:
  check(row['path'],wanted(row));a=assetmap[row['name']];assert wanted(a)==wanted(row) and a['authenticated_roundtrip']is True and a['anonymous_roundtrip']is True
 j=pub['transport_journal'];check(j['path'],wanted(j));attempts=json.loads(Path(j['path']).read_text());roundtrips=collections.Counter()
 for row in attempts:
  assert row['status']in ('PASS','TRANSPORT_FAILURE')
  for stream in ('stdout','stderr'):
   info=row[stream];check(info['path'],wanted(info))
   with gzip.open(info['path'],'rb')as g:assert readhash(g)==info['uncompressed']
  if 'response'in row:check(row['response']['path'],wanted(row['response']))
  ownerpath=Path(row['owned_processes']);o=json.loads(ownerpath.read_text());transport_files[str(ownerpath)]=pin(ownerpath)
  assert o['processes']
  expected_status='REAPED_NO_LIVE_MEMBERS'if row['status']=='PASS'else 'FAILURE_REAPED'
  assert all(p['status']==expected_status and p['returncode']==row['returncode']for p in o['processes'])
  if row['status']=='TRANSPORT_FAILURE':
   assert row['deadline_triggered']is True and row['returncode']==-15
   assert o['status']=='CANCELLED'and o['reason']=='Bounded transport deadline exceeded'
   assert not o['cleanup']['recording_errors']and not o['cleanup']['observation_errors']
   assert all(not g['identity_reused']and g['term_sent']and not g['immediate_after_kill']for g in o['cleanup']['groups'])
  for p in o['processes']:
   q=Path('/proc')/str(p['identity']['pid'])/'stat'
   if q.exists():assert q.read_text().rsplit(')',1)[1].split()[19]!=str(p['identity']['start_ticks'])
  if row['status']=='PASS':assert row['returncode']==0 and not row['deadline_triggered']
  else:failures.append({'kind':row['kind'],'directory':row['directory'],'returncode':row['returncode'],'deadline_triggered':row['deadline_triggered']})
  if row['kind']in ('authenticated','anonymous'):
   src=row['retained_local_source'];check(src['path'],wanted(src));obs=row['observed_download'];assert obs['mismatching_chunk']is None and obs['bytes']==obs['matched_local_prefix_bytes']
   with Path(src['path']).open('rb')as s:assert readhash(s,obs['matched_local_prefix_bytes'])==wanted(obs)
   if row['status']=='PASS':
    a=assetmap[row['asset']['name']];assert a['asset_id']==row['asset']['id'] and wanted(obs)==wanted(a)==wanted(src)
    assert row['stdout_capture_complete']is True and row['stderr_capture_complete']is True
    if row['kind']=='anonymous':
     response=json.loads(Path(row['response']['path']).read_text());assert response.get('status')=='COMPLETE_HTTP_STREAM'and response.get('http_status')==200
    roundtrips[(a['name'],row['kind'])]+=1;successful_downloads.append({'name':a['name'],'kind':row['kind'],**wanted(obs)})
 for name in assetmap:assert roundtrips[(name,'authenticated')]>=1 and roundtrips[(name,'anonymous')]>=1
 journalrows.append({'path':j['path'],**wanted(j),'attempts':len(attempts),'successful_downloads':sum(roundtrips.values())});assets.extend(pub['assets'])
assert assets==f['assets'] and len(assets)==26 and len({a['name']for a in assets})==26
# Rebind existing independent full-wave reader, retaining its declared subset.
binding=json.loads((F/'independent-peer-binding01.json').read_text());assert not binding['findings']
for p,v in binding['files'].items():check(p,v)
peerpath=F.parent/'pcie-tail115-sixteenthstep-wave-peer-rx-20261006/result.json';peer=json.loads(peerpath.read_text());assert peer['status']=='PASS_INDEPENDENT_SAVED_TAIL115_SIXTEENTHSTEP_STREAMING_RECOUNT_FINITE_NUMERICAL_PASS' and not peer['findings']
n=json.loads((B/'numerical-convergence01.json').read_text());assert n['status']=='PASS_FINITE_OPEN_LOOP_NUMERICAL_SCREEN' and all(n['checks'].values()) and peer['numerical']['checks']==n['checks']
assert n['physical_acceptance']is False
for k in ('vco_frequency_delta_ppm','feedback_frequency_delta_ppm'):assert math.isclose(n['details'][k],peer['numerical']['details'][k],abs_tol=1e-6,rel_tol=0)
maxphase={k:max(abs(x)for x in n['details'][k+'_unaligned_delta_ps'])for k in ('vco','cml','feedback')};assert all(x<=50 for x in maxphase.values()) and all(n['details'][k]<=100 for k in ('vco_frequency_delta_ppm','feedback_frequency_delta_ppm'))
r={'status':'PASS_INDEPENDENT_SAVED_N16_FINITE_MULTIPART_AND_ADDITIVE','ready':pin(ready),'findings':[],'method':pin(__file__),'reviewer_attempts':{'retained_method':pin(F/'review_saved_delivery_pll01.py'),'retained_log':pin(F/'review-saved-delivery-pll01.log'),'correction':pin(F/'reviewer-schema-correction02.json')},'source_methods':7,'compact_records':592,'compact_originals':592,'archives':archives,'all_members':968,'archive_origins_rehashed':len(origins),'public_assets':26,'ordered_parts':24,'ordered_reconstruction':rep['reconstructed_archive'],'assets':assets,'closed_transport_journals':journalrows,'successful_full_readbacks':successful_downloads,'historical_failed_transport_attempts':failures,'all_saved_downloads_reconstructed_without_network':True,'source_and_record_files_rehashed':len(checked),'transport_owner_files':transport_files,'independent_saved_wave_peer':{'path':str(peerpath),**pin(peerpath),'scope':peer['scope']},'numerical':{'status':n['status'],'vco_frequency_delta_ppm':n['details']['vco_frequency_delta_ppm'],'feedback_frequency_delta_ppm':n['details']['feedback_frequency_delta_ppm'],'maximum_unaligned_phase_ps':maxphase,'original_failed_coarser_steps_unchanged':True},'elapsed_seconds':time.monotonic()-started,'maximum_resident_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'Independent finite delivery/source/archive/publication byte audit only. Full compressed wave archived bytes reread; no repeated native, raw numerical producer or tests and no downloads. Existing independent wave reader covers full finite values/64HBT subset as explicitly declared, not a new455-device electrical recomputation.52 complete saved auth/anonymous matches plus all9 partial transport failures retained. Finite34ns nominal openloop/adjacent-step screen only; no1usPLL/acquisition/PVT/CDR/qualifiedPEX/fullPHY/adoption.'}
p=F/'saved-delivery-peer-pll01.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'receipt':str(p),**pin(p),'seconds':r['elapsed_seconds'],'maxrss':r['maximum_resident_kib']},indent=2))
