# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source and saved-control review; no test, native or transport execution."""
from pathlib import Path
import sys,json,hashlib,gzip,lzma,struct,datetime
R=Path(__file__).resolve().parents[4];sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v3 as m
B=Path(__file__).parent; F=B/'source-freeze.json'; f=json.loads(F.read_text())
def pin(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for rows in [f['files'],f['frozen_dependencies']]:
 for p,expected in rows.items():assert pin(R/p)==expected,(p,'source mismatch')
assert pin(F)['sha256']=='31437ed0bb7bb8907a364b268df18313574f755912be00ed5fdfe3b573a9e18f'
for k in ['publisher','run']:
 s=getattr(m,k+'_source');bridge=f['exact_source_bridges'][k]
 assert hashlib.sha256(s.encode()).hexdigest()==bridge['modified_sha256']
 for old,new in reversed(bridge['exact_replacements']):assert s.count(new)==1;s=s.replace(new,old)
 assert s==getattr(m.previous,k+'_source')
 assert hashlib.sha256(s.encode()).hexdigest()==bridge['original_sha256']
assert m.main_source==m.previous.main_source
for k in ['stream_deck','measurements','startup_proof','acquisition','prerequisites','runtime']:assert getattr(m,k) is getattr(m.previous,k)
for k in ['capture','native_wait','Meter','guard','FLOOR','CAP','PART_BYTES','life']:assert m.namespace[k] is m.previous.namespace[k]
assert m.namespace is not m.previous.namespace and m.publisher_namespace is not m.previous.publisher_namespace
assert m.run.__globals__ is m.namespace and m.main.__globals__ is m.namespace
assert m.namespace['OwnedPublisherV3'] is m.OwnedPublisherV3
assert m.OwnedPublisherV3.__call__.__globals__ is m.publisher_namespace
assert m.publisher_namespace['publication'] is m.publication
assert m.previous.publisher_namespace['publication'] is m.previous.publication
assert m.namespace['verify_parent'] is m.verify_parent
assert m.STOP==1e-6 and m.namespace['FLOOR']==512*1024**2 and m.namespace['CAP']==50*1024**2
original=m.namespace['ORIGINAL']/'bench.cir'; deck=[]
for step in [5e-12,2.5e-12]:
 s=m.stream_deck(original.read_text(),step,1e-6)
 assert s==m.previous.stream_deck(original.read_text(),step,1e-6)
 deck.append(dict(step=step,bytes=len(s.encode()),sha256=hashlib.sha256(s.encode()).hexdigest()))
log=R/f['controls']['log'];assert pin(log)=={k:f['controls'][k] for k in ['bytes','sha256']}
assert '15 passed' in log.read_text()
raw=Path(f['controls']['raw']);cases={};rawbytes=struct.pack('<4d',0.,1.25,2.5e-12,1.3)
for name,mode in [('test_actual_nested_publisher_p0','transient'),('test_actual_nested_publisher_p1','mismatch'),('test_actual_outer_stop_reaps_n0','outer_SIGTERM')]:
 p=raw/name; packed=(p/'expected-compressed-fixture.bin').read_bytes();assert lzma.decompress(packed)==rawbytes
 ledger=json.loads((p/'parts/parts.json').read_text());receipt=json.loads((p/'parts/publication-00000.json').read_text());attempts=json.loads((p/'parts/publication-00000.transport/attempts.json').read_text());owned=json.loads((p/'outer-owner.json').read_text())
 assert receipt['source']==pin(m.publication.__file__)
 assert receipt['process_owner']==pin(m.publication.lifecycle.__file__)
 auth=[a for a in attempts if a['kind']=='authenticated']
 if mode=='transient':
  assert ledger['status']=='PASS_PUBLISHED_PARTS' and ledger['rows']==2
  assert ledger['payload_sha256']==hashlib.sha256(rawbytes).hexdigest()
  assert [a['status'] for a in auth]==['TRANSPORT_FAILURE','PASS']
  assert auth[0]['observed_download']['matched_local_prefix_bytes']==8
  assert hashlib.sha256(packed[:8]).hexdigest()==auth[0]['observed_download']['sha256']
  assert all(receipt['assets'][0][k] for k in ['authenticated_roundtrip','anonymous_roundtrip'])
  assert not (p/'parts/producer-control-part00000.bin.xz').exists()
 else:
  assert ledger['status']=='ERROR_PART_RETAINED' and receipt['status']=='FAIL'
  assert (p/'parts/producer-control-part00000.bin.xz').read_bytes()==packed
  assert len(auth)==1 and auth[0]['status']=='FATAL_NO_RETRY'
  assert not any(a['kind']=='anonymous' for a in attempts)
  if mode=='outer_SIGTERM':
   assert receipt['explicit_stop'] and owned['reason']=='Parent received SIGTERM'
   assert (p/'retained-pending.bin').read_bytes()==rawbytes
   assert owned['cleanup']['finished_monotonic']-owned['cleanup']['started_monotonic']<5
  else:assert 'IntegrityError' in receipt['error']
 count=0
 for a in attempts:
  for stream in ['stdout','stderr']:
   item=a[stream];path=Path(item['path']);assert pin(path)=={k:item[k] for k in ['bytes','sha256']}
   data=gzip.decompress(path.read_bytes());assert dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())==item['uncompressed'];count+=1
  owners=json.loads(Path(a['owned_processes']).read_text())
  for e in owners['processes']:assert not any(i['state']!='Z' for i in m.life.group_members(e['process_group']))
 for e in owned['processes']:assert not any(i['state']!='Z' for i in m.life.group_members(e['process_group']))
 cases[mode]=dict(ledger_status=ledger['status'],receipt_status=receipt['status'],authenticated_attempts=len(auth),all_gzip_members_read=count,owner=pin(p/'outer-owner.json'),receipt=pin(p/'parts/publication-00000.json'),ledger=pin(p/'parts/parts.json'),attempts=pin(p/'parts/publication-00000.transport/attempts.json'))
out=dict(status='PASS_PRODUCER_SOURCE_AND_SAVED_CONTROLS_WITH_TEST_PORTABILITY_FINDING',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='/root/rx_route_resume',source_freeze=pin(F),method=pin(__file__),reviewed_sources=f['files'],frozen_dependencies=f['frozen_dependencies'],source_bridges=f['exact_source_bridges'],pure_deck_byte_comparisons=deck,original_deck=dict(path=str(original),**pin(original)),saved_controls=dict(log=pin(log),reported_passed=15,rerun=False,critical_cases=cases),verified=['Full producer and inherited OwnedPublisher/run sources inspected; exact inverse bridges; private namespaces preserve old module globals','Only V3 publisher class routing and additional publisher/owner input pins change; main source and native electrical/numerical/capture/lifecycle aliases identical','Publisher source is frozen approved V3; parent5s grace exceeds nested1s failure cleanup; SIGTERM fixture retained 32B pending raw+84B part and reaped all groups','Immutable local original removed only after full metadata and authenticated+anonymous byte readbacks; saved TLS-prefix reconstructed and mismatch stays terminal'],findings=[dict(scope='test portability only',file='sw/tests/test_pcie_pll_acquisition_v3.py',function='test_actual_deck_generation_bytes_identical',reason='Reads volatile ORIGINAL/bench.cir with no tracked test fixture; new tests cannot reproduce on fresh checkout until exact fixture is supplied',blocks_current_native_on_restored_exact_inputs=False)],native_executed=False,tests_executed=False,transport_executed=False,physical_acceptance=False)
(B/'source-only-peer.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(pin(B/'source-only-peer.json')))
