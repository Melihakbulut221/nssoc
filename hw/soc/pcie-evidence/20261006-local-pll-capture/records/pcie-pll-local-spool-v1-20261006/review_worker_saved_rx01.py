# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure saved-byte XML, raw part, receipt and process-identity recount."""
from pathlib import Path
import hashlib,json,struct,lzma,gzip,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent
j=lambda p:json.loads(p.read_text())
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=j(B/'source-freeze01.json');pins={};campaigns=[]
for row in f['actual_fixture_files']:
 if 'nssoc-spool-publisher-controls'not in row['path']:continue
 p=Path(row['path']);h={k:row[k]for k in('bytes','sha256')};assert pin(p)==h,p;pins[str(p)]=h
for row in f['controls']:
 if not row['name'].startswith('publisher-'):continue
 for key in('xml','log'):
  r=row[key];assert pin(r['path'])=={k:r[k]for k in('bytes','sha256')};pins[r['path']]=pin(r['path'])
 cases=list(ET.parse(row['xml']['path']).iter('testcase'))
 passed=sum(not any(c.find(t)is not None for t in('failure','error','skipped'))for c in cases)
 failed=sum(any(c.find(t)is not None for t in('failure','error'))for c in cases)
 assert len(cases)==row['cases']and passed==row['passed']and failed==row['failed']
 campaigns.append(dict(name=row['name'],passed=passed,failed=failed,cases=[x.attrib for x in cases]))
assert [(x['passed'],x['failed'])for x in campaigns]==[(12,2),(14,0),(17,0),(2,0)]
root=Path('/dev/shm/nssoc-spool-publisher-controls03');records=[];births=[]
expected_raw=b''.join(struct.pack('<dd',i*1.25e-12,.5)for i in range(3))
for index in range(2):
 p=root/f'test_actual_offline_worker_sto{index}';spool=p/'ssd'
 failed=j(p/'publication/publication.json');recovery=j(p/'recovered-publication/publication.json');ledger=j(spool/'parts.json');terminal=j(spool/'native-terminal.json')
 assert failed['status']=='ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'and failed['explicit_stop']
 assert recovery['status']=='PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC'and len(recovery['assets'])==1
 assert len(failed['attempts'])==len(recovery['attempts'])==1
 assert terminal['canonical_manifest']==pin(spool/'parts.json')and recovery['native_terminal']==dict(path=str(spool/'native-terminal.json'),**pin(spool/'native-terminal.json'))
 assert ledger['status']=='LOCAL_CAPTURE_COMPLETE'and ledger['rows']==ledger['committed_rows']==3 and len(ledger['parts'])==1
 row=ledger['parts'][0];part=spool/'committed/00000'/row['name'];raw=lzma.decompress(part.read_bytes())
 assert raw==expected_raw and row['uncompressed_sha256']==hashlib.sha256(raw).hexdigest()and row['uncompressed_bytes']==48
 assert j(part.parent/'record.json')==row and pin(part)=={k:row[k]for k in('bytes','sha256')}
 asset=recovery['assets'][0];assert asset['row']==row and asset['receipt_pin']==pin(asset['receipt'])
 assert asset['asset']['anonymous_roundtrip']and asset['asset']['authenticated_roundtrip']
 transfer=Path(asset['receipt']).with_suffix('.transport')
 for kind in('authenticated','anonymous'):
  match=list(transfer.glob(f'*-{kind}-attempt1/stdout.bin.gz'));assert len(match)==1
  assert gzip.decompress(match[0].read_bytes())==part.read_bytes()
 for ownerfile in [*p.glob('publication/*.owner.json'),*p.glob('recovered-publication/*.owner.json'),*p.glob('**/owned-processes.json')]:
  owner=j(ownerfile)
  for process in owner.get('processes',[]):
   identity=process['identity'];proc=Path('/proc')/str(identity['pid'])/'stat'
   if proc.exists():
    fields=proc.read_text().rsplit(')',1)[1].split();assert int(fields[19])!=int(identity['start_ticks'])or fields[0]=='Z'
   births.append(identity)
 records.append(dict(case=p.name,failed=pin(p/'publication/publication.json'),recovered=pin(p/'recovered-publication/publication.json'),raw_samples=3,raw_bytes=48,compressed=pin(part),actual_local_http_dual_readback=True))
for i in range(5):
 s=j(root/f'test_nontransport_or_ambiguous{i}/publication/publication.json');assert len(s['attempts'])==1 and 'Non-transport publication failure'in s['error']and not s['assets']
for i in range(4):
 s=j(root/f'test_real_modified_part_or_suc{i}/publication/publication.json');assert len(s['attempts'])==1 and not s['assets']
s=j(root/'test_finite_offline_budget_doe0/publication/publication.json');assert len(s['attempts'])==2 and 'Finite publication attempt'in s['error']
s=j(root/'test_worker_transient_then_suc0/publication/publication.json');assert [x['status']for x in s['attempts']]==['TRANSPORT_PENDING_LOCAL_BYTES_RETAINED','PUBLIC_VERIFIED']
for i in range(2):
 p=Path('/dev/shm/nssoc-spool-publisher-controls04')/f'test_terminal_error_record_sur{i}'/'publication/publication.json';s=j(p);assert s['attempts']==[] and 'Publication 'in s['error']
record=dict(status='SAVED_WORKER_CONTROLS_RECOUNTED_SOURCE_HANDOFF_FINDING_PENDING',freeze=pin(B/'source-freeze01.json'),method=pin(Path(__file__)),campaigns=campaigns,fixture_pins=pins,actual_offline_stop_recovery=records,owned_births_closed= len(births),finding=pin(B/'source-saved-worker-findings-rx01.json'),scope='Read only existing bytes/XML/proc. Seventeen current predicates plus two actual resource refinements; first12PASS2FAIL retained. Local fake gh and localhost HTTP only, not public GitHub availability or new native.' )
with (B/'worker-saved-controls-review-rx01.json').open('x')as out:json.dump(record,out,indent=2);out.write('\n')
print(json.dumps(dict(result=pin(B/'worker-saved-controls-review-rx01.json'),fixture_files=len(pins),owned_births=len(births))))
