"""Independent bounded full saved-archive/control recount; no producer imports."""
from pathlib import Path
import ast,hashlib,json,lzma,os,resource,struct,tarfile,time,xml.etree.ElementTree as ET
R=Path.cwd();F=Path(__file__).resolve().parent;B=F.parent
os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
archive=F/'pcie-local-spool-publisher-v2-controls-20261006.tar.xz'
expected_archive=dict(bytes=1149780,sha256='58d7a4ec515fa8c06a32b1057c421a87fba6c9afed9547a12b2e4e07c8acbf1c')
assert pin(archive)==expected_archive
manifest=read(F/'members.json');files=manifest['files'];assert len(files)==1456
expected={n:{k:r[k] for k in ('bytes','sha256')} for n,r in files.items()};expected['members.json']=pin(F/'members.json')
seen=set();total=0;large=[];start=time.monotonic()
with lzma.open(archive,'rb') as decoded:
 with tarfile.open(fileobj=decoded,mode='r|',bufsize=1024**2) as tar:
  for member in tar:
   assert member.isfile() and member.name not in seen and member.name in expected
   assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
   h=hashlib.sha256();count=0;zero=True
   with tar.extractfile(member) as stream:
    while chunk:=stream.read(1024**2):
     h.update(chunk);count+=len(chunk)
     if member.size>100000000:zero=zero and chunk==bytes(len(chunk))
   assert dict(bytes=count,sha256=h.hexdigest())==expected[member.name]
   assert count==member.size
   if member.size>100000000:large.append(dict(member=member.name,bytes=count,all_zero=zero));assert zero
   seen.add(member.name);total+=count
 while chunk:=decoded.read(1024**2):assert chunk==bytes(len(chunk))
assert seen==set(expected) and len(seen)==1457 and total==5723954578
cache={}
def checked(p,expected):
 p=Path(p)
 if str(p) not in cache:cache[str(p)]=pin(p)
 assert cache[str(p)]==expected,str(p)
for name,row in files.items():
 assert not name.startswith(str((B/'publication01').relative_to(R)))
 checked(row['path'],{k:row[k] for k in ('bytes','sha256')})
freeze=read(B/'source-freeze01.json')
for path,value in freeze['pins'].items():checked(path,value)
for path,value in freeze['sources'].items():checked(R/path,value)
peer=read(B/'source-saved-peer-vco02.json')
assert peer['status']=='PASS_SOURCE_SAVED_PUBLISHER_V2_AND_LAUNCH' and peer['findings']==[]
assert peer['freeze']==pin(B/'source-freeze01.json') and peer['policy']==pin(B/'launch01/policy.json')
assert peer['reviewer_metadata_correction']['original_peer']==pin(B/'source-saved-peer-vco01.json')
assert peer['reviewer_metadata_correction']['original_peer_and_method_preserved']
assert manifest['active_journals_excluded'] and not manifest['native_completion'] and not manifest['full_phy_acceptance']
assert all('/pcie-pll-local-captures/' not in n for n in files)
method=R/'sw/tests/test_pcie_local_spool_publisher_v2.py';tree=ast.parse(method.read_text())
names={n.name for n in tree.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
campaigns=[];sets=[]
for n,wanted in [(1,4),(2,1),(3,0)]:
 xml=B/f'controls0{n}.xml';cases=list(ET.parse(xml).getroot().iter('testcase'))
 assert len(cases)==31 and all(c.find('error') is None and c.find('skipped') is None for c in cases)
 assert all(c.get('name').split('[',1)[0] in names for c in cases)
 failed=[c.get('name') for c in cases if c.find('failure') is not None];assert len(failed)==wanted
 nameset={c.get('name') for c in cases};assert len(nameset)==31;sets.append(nameset)
 campaigns.append(dict(xml=pin(xml),executions=len(cases),passed=len(cases)-len(failed),failed=failed))
assert sets[0]==sets[1]==sets[2]
assert campaigns==peer['historical_campaigns']
assert sum(c['executions'] for c in campaigns)==93 and sum(c['passed'] for c in campaigns)==88
assert all('31 passed' in (B/'controls03.log').read_text() for _ in [0])
terminals=[];good=[];owners=[]
for n,row in files.items():
 if '/fixtures03/' not in n:continue
 p=Path(row['path'])
 if p.name=='publication.json':
  r=read(p);assert r['status'] in ('ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED','PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC')
  for asset in r['assets']:
   receipt=read(asset['receipt']);checked(asset['receipt'],asset['receipt_pin'])
   assert receipt['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and asset['asset'] in receipt['assets']
   a=asset['asset'];s=asset['row'];assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
   assert {k:a[k] for k in ('bytes','sha256','name')}=={k:s[k] for k in ('bytes','sha256','name')}
   source=Path(r['spool'])/'committed'/f"{s['index']:05d}"/s['name'];checked(source,{k:s[k] for k in ('bytes','sha256')})
   raw=lzma.decompress(source.read_bytes());assert len(raw)==s['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==s['uncompressed_sha256']
   assert len(raw)==48 and list(struct.iter_unpack('<dd',raw))==[(0.,.5),(1.25e-12,.5),(2.5e-12,.5)]
  terminals.append(dict(path=str(p),status=r['status'],attempts=len(r['attempts']),assets=len(r['assets']),explicit_stop=r.get('explicit_stop')))
  if r['status'].startswith('PASS_'):good.append(str(p))
 if p.name.endswith('.owner.json'):
  r=read(p);assert r['status'] in ('HEALTHY','CANCELLED','FAILURE_REAPED')
  owners.append(dict(path=str(p),pin=pin(p),status=r['status']))
assert len(terminals)==22 and len(good)==4
assert terminals==peer['saved_publication_terminals']
base=B/'fixtures03/test_recovery_reconciles_exist0'
u=read(base/'upload-state.json');assert u['uploads']==0
r=read(base/'recovery/publication.json');assert len(r['assets'])==1 and r['assets'][0]['asset']['asset_id']==1719
assert r['assets'][0]['asset']['authenticated_roundtrip'] and r['assets'][0]['asset']['anonymous_roundtrip']
old=R/'hw/soc/out/pcie-pll-local-spool-v1-20261006/publisher-failure01/reverified-failure-pll01.json'
checked(old,dict(bytes=1902,sha256='d832bbf62bb797011323e850f288e7c5b08f3ff6c8cdaa3565bc3f2c6d1dd6f2'))
assert read(old)['status']=='PASS_REVERIFIED_CLOSED_V1_PUBLISHER_FAILURE_ARCHIVE'
assert pin(archive)==expected_archive
result=dict(status='PASS_INDEPENDENT_SAVED_PUBLISHER_V2_FINITE_CONTROLS',reviewer='/root/pll_integrity_resume',findings=[],archive=dict(path=str(archive),**expected_archive),manifest=pin(F/'members.json'),members=len(seen),logical_bytes=total,original_member_paths=len(files),independently_rehashed_distinct_path_spellings=len(cache),large_zero_fixture_entries=large,freeze=pin(B/'source-freeze01.json'),source_peer=pin(B/'source-saved-peer-vco02.json'),historical_campaigns=campaigns,current_predicates=31,current_prior_worker=21,current_new_regression=10,historical_executions=93,historical_passed=88,historical_failed=5,closed_fixture_publications=terminals,owned_fixture_receipts=owners,existing_asset_recovery=dict(fixture_asset_id=1719,actual_fixture_uploads=0,authenticated_roundtrip=True,anonymous_roundtrip=True,raw_rows=3),old_failure_reverification=pin(old),old_failure_classification='Primary host FileNotFoundError during non-atomic moving-log stat; outer explicit_stop=false. Child explicit-stop receipt is owned cleanup, not user cancellation. Old local part61 is bound to actual uploaded asset614811208 but old V1 cutoff did not finish both readbacks. Current live V2 publication progress is excluded from this finite receipt.',scope='Full saved bytes, source pins, actual XML/control evidence and immutable startup only. No producer imports/tests/native/network reruns or live journals. No PLL 1us completion, physical acceptance, empirical power-loss claim, or original sealer completion assumption. Duplicate historical fixture path spellings are counted as archived entries, not unique physical data.',preparatory_schema_notes=['Exploratory metadata query initially assumed original key; actual closed manifest uses files/name/path. A separate exploratory source read used a guessed test filename and found no file; exact frozen source path was then read. Neither produced a review verdict or modified evidence.'],method=pin(__file__),runtime=dict(tarfile=pin(tarfile.__file__),lzma=pin(lzma.__file__)),elapsed_seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
(F/'saved-finite-peer-pll01.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('status','members','logical_bytes','current_predicates','historical_executions','elapsed_seconds','peak_rss_kib')}))
