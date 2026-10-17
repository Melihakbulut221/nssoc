"""Seal closed V25 source/functional/native evidence; never starts HDL or EDA."""
from pathlib import Path
import hashlib,io,json,lzma,resource,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def save(p,r):
 with Path(p).open('x')as f:json.dump(r,f,indent=2);f.write('\n')
def audit(archive,manifest):
 seen=set();logical=0;drifts=[]
 with lzma.open(archive,'rb')as src,tarfile.open(fileobj=src,mode='r|',bufsize=1024**2)as t:
  for m in t:
   assert m.isfile()and m.name not in seen;seen.add(m.name)
   expected=pin(manifest)if m.name=='members.json'else data[m.name]
   assert m.size==expected['bytes'];s=t.extractfile(m)
   assert hashlib.file_digest(s,'sha256').hexdigest()==expected['sha256'];logical+=m.size
 assert seen==set(data)|{'members.json'}
 for n,h in data.items():
  p=Path(h.get('original',h.get('original_path')));old={k:h[k]for k in('bytes','sha256')}
  actual=pin(p)if p.is_file()else None
  if actual!=old:drifts.append(dict(member=n,original=str(p),archived=old,current=actual))
 return dict(full_member_readback=True,member_count=len(seen),logical_bytes=logical,original_path_drifts=drifts)
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
freeze=read(B/'source-freeze04.json');products=freeze['product_sources']
for p,h in products.items():assert pin(R/p)==h,p
assert read(B/'saved-controls-peer-vco04.json')['status']=='PASS_INDEPENDENT_SAVED_V25_CURRENT_43_FUNCTIONAL_PREDICATES'
np=read(B/'native-saved-peer-vco.json');assert np['status']=='PASS_SAVED_V25_FINITE_NATIVE_RECOUNT_TIMING_REJECTED'and np['findings']==[]
for n in ['status02.json','continuation-status01.json']:
 st=read(B/n)
 for key in ['controller','pytest']:
  if key not in st:continue
  x=st[key];p=Path('/proc',str(x['pid']),'stat')
  if p.exists():
   fields=p.read_text().rsplit(') ',1)[1].split();assert fields[19]!=str(x['start_ticks'])or fields[0]=='Z'
for n,count,fail in [('controls01.xml',42,2),('controls02.xml',43,0)]:
 cases=list(ET.parse(B/n).getroot().iter('testcase'));assert len(cases)==count
 assert sum(c.find('failure')is not None or c.find('error')is not None for c in cases)==fail
 assert all(c.find('skipped')is None for c in cases)
specs=[('historical_failed','failed-controls01/validation.json','failed-controls01/members.json'),('current_functional','pcie-integrity-v25-current-controls02-validation-20261006.json','current-controls02-members.json'),('native','pcie-integrity-v25-native-validation-20261006.json','native-members.json')]
archives={}
for label,vn,mn in specs:
 v=read(B/vn);ar=v['archive'];a=Path(ar['path']);assert pin(a)=={k:ar[k]for k in('bytes','sha256')}
 data=read(B/mn);result=audit(a,B/mn);assert result['member_count']==ar['members']
 archives[label]=dict(path=str(a),**pin(a),**result,validation=dict(path=str(B/vn),**pin(B/vn)),manifest=dict(path=str(B/mn),**pin(B/mn)))
 print(label,result['member_count'],'full members; current origin drifts',len(result['original_path_drifts']),flush=True)
assert not archives['native']['original_path_drifts'],'Native capsule origins must remain exact'
scope='Closed finite V25 evidence. Current43PASS and previous40PASS2FAIL are separate campaigns;1MAX4118excluded. Nominal+1 latency only, no generalcycleequivalence. Same4ns SS setup -3.421986ns is230.304ps worse thanV23: rejected, stableV11 unchanged. No mappedfunctional/CTS/routeRC/fullchip/PHY adoption. Old original-path drifts explicitly recorded; archived snapshot bytes remain exact. No active PLL/analog/RX/native observation admitted.'
audit_record=dict(status='PASS_CLOSED_V25_THREE_ARCHIVE_READBACK_CURRENT_SOURCE_EXACT',archives=archives,source_allowlist=products,source_freeze=pin(B/'source-freeze04.json'),saved_controls_peer=pin(B/'saved-controls-peer-vco04.json'),native_saved_peer=pin(B/'native-saved-peer-vco.json'),scope=scope,method=pin(__file__))
save(B/'delivery-archive-audit01.json',audit_record)
# Compact records are explicitly closed and smaller than128KiB. Full larger
# source/bridge/diagnostic records go in the supplement, not silently omitted.
paths=[]
for p in sorted(B.rglob('*')):
 if not p.is_file()or p.is_symlink()or '__pycache__'in p.parts:continue
 if p.suffix in('.xz','.gz','.pyc','.vvp'):continue
 if 'checkpoint'in p.name or p.name.startswith('observation-'):continue
 if p.name in ('prepare-delivery01.log','publication01.log'):continue
 assert 'publication'not in p.name,'Publication must not yet exist'
 paths.append(p)
evidence={str(p.relative_to(R)):pin(p)for p in paths if p.stat().st_size<=128*1024}
members={'evidence/'+str(p.relative_to(B)):dict(original=str(p),**pin(p))for p in paths}
members.update({'sources/'+p:dict(original=str(R/p),**h)for p,h in products.items()})
mp=B/'delivery-supplement-members01.json';save(mp,members)
archive=B/'pcie-integrity-v25-finite-peer-supplement-20261006.tar.xz'
with archive.open('xb')as sink,tarfile.open(fileobj=sink,mode='w:xz',preset=1)as t:
 for n,h in members.items():t.add(h['original'],arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
data=members;result=audit(archive,mp);assert not result['original_path_drifts']
archives['peer_supplement']=dict(path=str(archive),**pin(archive),**result,manifest=dict(path=str(mp),**pin(mp)))
record=dict(status='SEALED_V25_CURRENT43_AND_REJECTED_NATIVE_FINITE_PACKAGE',source_freeze=pin(B/'source-freeze04.json'),source_allowlist=products,archives=archives,archive_total_members=sum(x['member_count']for x in archives.values()),evidence=evidence,
 functional=dict(current=dict(passed=43,failed=0,excluded_MAX4118=1),historical=dict(passed=40,failed=2),total_executions=85,public_direct=19,public_instrumented=19,nominal_plus_one_cases=2,component_relations=4102,component_faults=12,public_mutants=12,architecture_mutants=8,block_mutants=2,cache_fault_epochs=[8,8,8],ring16_MAX18_is_explicit_override=True,general_cycle_equivalence=False),
 native=read(B/'candidate-decision.json'),functional_validation=pin(B/specs[1][1]),native_validation=pin(B/specs[2][1]),saved_controls_peer=pin(B/'saved-controls-peer-vco04.json'),native_saved_peer=pin(B/'native-saved-peer-vco.json'),adopted=False,scope=scope)
save(B/'pcie-integrity-v25-finite-package-20261006.json',record)
print(json.dumps(dict(archives=len(archives),members=record['archive_total_members'],compact_records=len(evidence),sources=len(products),package=pin(B/'pcie-integrity-v25-finite-package-20261006.json'))))
