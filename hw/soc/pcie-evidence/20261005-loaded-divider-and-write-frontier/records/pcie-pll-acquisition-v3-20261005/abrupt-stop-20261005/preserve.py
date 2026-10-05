"""Preserve abrupt PLL disappearance, retaining stale originals verbatim."""
from pathlib import Path
import datetime,hashlib,json,lzma,struct,tarfile,re
R=Path.cwd();B=Path(__file__).resolve().parent;P=Path('/dev/shm/nssoc-pll-acquisition-v3-step25-after-reboot-01')
def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def dump(name,obj):
 with (B/name).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
for pid,start in [(38669,'383026'),(38676,'383153')]:
 q=Path('/proc')/str(pid)/'stat'
 if q.exists():assert q.read_text().rsplit(') ',1)[1].split()[19]!=start
parts=json.loads((P/'capture/parts/parts.json').read_text())['parts'];assert len(parts)==128
receipts=[];cursor=0
for i,row in enumerate(parts):
 assert row['index']==i and row['first_row']==cursor;cursor+=row['rows']
 p=P/'capture/parts'/f'publication-{i:05}.json';j=json.loads(p.read_text());assert j['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(j['assets'])==1
 a=j['assets'][0];assert all(a[k]==row[k] for k in ['name','bytes','sha256']) and a['authenticated_roundtrip'] and a['anonymous_roundtrip'];receipts.append(dict(index=i,receipt=dict(path=str(p),**pin(p)),asset=a,first_row=row['first_row'],rows=row['rows']))
last=parts[-1];path=P/'capture/parts'/last['name'];assert pin(path)=={k:last[k] for k in ['bytes','sha256']}
raw=lzma.decompress(path.read_bytes());assert len(raw)==last['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==last['uncompressed_sha256'];width=len(raw)//last['rows'];assert width==826*8
first_t=struct.unpack_from('<d',raw,0)[0];last_t=struct.unpack_from('<d',raw,len(raw)-width)[0]
log=(P/'run.log').read_bytes().decode(errors='replace');times=re.findall(r'Reference value\s*:\s*([0-9.eE+-]+)',log)
observation=dict(status='ABRUPT_PROCESS_DISAPPEARANCE_INCOMPLETE_NOT_ANALOG_OR_TRANSPORT_FAILURE',observed_utc=datetime.datetime.now(datetime.UTC).isoformat(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),missing_original_births=[dict(pid=38669,start_ticks='383026'),dict(pid=38676,start_ticks='383153')],native_last_reported_seconds=float(times[-1]),published_parts=128,published_rows=cursor,last_public_part_first_seconds=first_t,last_public_part_last_seconds=last_t,last_part_uncompressed_verified=True,solver_checkpoint_available=False,operating_point_only='op.raw Plotname Operating Point, one point; bench.control writes only initial op then runFIFO. No transient integrator checkpoint exists.',native_terminal_record_available=False,original_stale_status=json.loads((P/'result.json').read_text())['status'],original_last_part_state=last['status'],last_publication_status=json.loads((P/'capture/parts/publication-00127.json').read_text())['status'],interruption_cause='Unclassified abrupt process disappearance. Journal confirms system suspend18:31:09–18:32:19UTC; native continueduntil18:33:55 and lastpublisher completed18:34:11. NoOOMkill/segfault inqueriedkernelinterval. Appscope launched18:33:31. Temporalassociation alone doesnot prove cause.',scope='No1uscompletion or analogacquisitionPASS. All128publishedparts andfullremainingregularRAMfiles preserved; missingin-memory/FIFOpending samples cannotbe reconstructed as solver state. Fresh time0 native run withseparateprefix required ifcontinued; no constraints/physics changes.')
dump('interruption-observation.json',observation);dump('reconciled-public-part-receipts.json',dict(status='PASS_ALL128_IMMUTABLE_PART_RECEIPTS_BOUND_NOT_SOLVER_COMPLETION',parts=receipts))
files={'capture/'+str(p.relative_to(P)):p for p in P.rglob('*') if p.is_file() and not p.is_symlink()}
for p in B.glob('*.json'):files['review/'+p.name]=p
files['method/preserve.py']=Path(__file__)
for n in ['launch_acquisition25.py','command-runtime.json','launcher-source-review.json','native-start-receipt.json','launch.log','supervisor.log']:
 p=B.parent/'launch01'/n;files['launch/'+n]=p
for name in ['characterize_pcie_pll_acquisition_v3.py','characterize_pcie_pll_acquisition_v2.py','characterize_pcie_pll_acquisition_v1.py','publish_pcie_native_capture_v3.py','characterize_pcie_clock_trim_stream_v2.py','characterize_pcie_clock_trim_stream_v1.py']:
 files['source/scripts/'+name]=R/'scripts'/name
members={n:dict(original_path=str(p),**pin(p)) for n,p in files.items()};mp=B/'members.json';dump(mp.name,members)
a=B/'pcie-pll-acquisition-v3-abrupt-stop-20261005.tar.xz'
with tarfile.open(a,'x:xz',preset=1) as t:
 for n,p in files.items():t.add(p,arcname=n,recursive=False)
 t.add(mp,arcname='members.json',recursive=False)
with tarfile.open(a,'r:xz') as t:
 assert set(t.getnames())==set(members)|{'members.json'}
 for m in t.getmembers():
  e=pin(mp) if m.name=='members.json' else members[m.name];assert m.isfile() and m.size==e['bytes']
  with t.extractfile(m) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==e['sha256']
for n,p in files.items():assert pin(p)=={k:members[n][k] for k in ['bytes','sha256']}
dump('preservation-validation.json',dict(status='PASS_ALL_REMAINING_REGULAR_FILES_SSD_FULL_MEMBER_READBACK_INCOMPLETE_RUN',observation=pin(B/'interruption-observation.json'),public_receipts=pin(B/'reconciled-public-part-receipts.json'),archive=dict(path=str(a),**pin(a),members=len(members)+1),all_originals_unchanged=True,full_member_readback=True));print(json.dumps(dict(archive=pin(a),members=len(members)+1,last_public_seconds=last_t)))
