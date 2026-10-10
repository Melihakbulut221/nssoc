# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent acquisition bridge, source and actual saved-control review."""
import hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_pll_acquisition_v5 as m
import durable_pcie_spool_v1 as local

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def exact(p,h):assert pin(p)=={k:h[k]for k in ('bytes','sha256')},str(p)
F=B/'source-freeze02.json';j=json.loads(F.read_text());assert len(j['sources'])==6 and len(j['dependencies'])==49 and len(j['actual_fixture_files'])==3804
checked={}
for col in ['sources','dependencies','evidence','actual_fixture_files']:
 rows=j[col].values() if isinstance(j[col],dict)else j[col]
 for row in rows:exact(row['path'],row);checked[row['path']]=pin(row['path'])
for name,actual,original in [('capture',m.capture_source,m.previous.capture_source),('native_wait',m.native_wait_source,m.inherited_native_wait),('run',m.run_source,m.previous.run_source),('main',m.main_source,m.previous.main_source)]:
 assert json.loads(json.dumps(m.BRIDGES[name]))==j['bridge_ledger'][name]
 inverse=actual
 for before,after in reversed(m.BRIDGES[name]['exact_replacements']):assert inverse.count(after)==1;inverse=inverse.replace(after,before)
 assert inverse==original and hashlib.sha256(inverse.encode()).hexdigest()==m.BRIDGES[name]['original_sha256']
for name in ['stream_deck','Meter','measurements','acquisition','startup_proof','prerequisites']:assert getattr(m,name)is getattr(m.previous,name)
for name in ['native_limit','CAP','FLOOR','PART_BYTES','life','n']:assert m.namespace[name] is m.previous.namespace[name]
assert (m.TSTEP,m.TMAX,m.STOP)==(2.5e-12,1.25e-12,1e-6)
assert m.previous.base.FREQUENCY_RELATIVE_LIMIT==100e-6 and m.previous.base.PHASE_RANGE_LIMIT_S==50e-12
bench=R/'sw/tests/fixtures/pcie_pll_acquisition_v3/connected-loop-bench.cir';deck=m.stream_deck(bench.read_text(),m.TSTEP,m.STOP);assert deck==m.previous.stream_deck(bench.read_text(),m.TSTEP,m.STOP) and '.tran 2.5e-12 1e-06 0 1.25e-12\n' in deck
counts=[]
for record in j['controls']:
 for k in ['xml','log']:exact(record[k]['path'],record[k])
 cases=ET.parse(record['xml']['path']).findall('.//testcase');fail=sum(any(c.tag in ('error','failure')for c in x)for x in cases);skip=sum(any(c.tag=='skipped'for c in x)for x in cases)
 assert len(cases)==record['cases'] and fail==record['failed'] and len(cases)-fail-skip==record['passed'] and skip==0
 counts.append(dict(name=record['name'],cases=len(cases),failed=fail))
# Current full campaign covers30core+16capture+21worker; final capture adds2
# and reruns all18 against final header source, preserving earlier failures.
full=ET.parse(B/'complete-controls03.xml').findall('.//testcase');last=ET.parse(B/'bridge-controls05.xml').findall('.//testcase');current={(x.attrib['classname'],x.attrib['name'])for x in full+last};assert len(current)==69 and len(last)==18 and all(not list(x)for x in full+last)
# Verify actual preheader and cancelled native fixture evidence, not only XML.
terminals=[];prefixes=[]
for p in checked:
 q=Path(p)
 if q.name=='native-terminal-invalid.json':
  d=json.loads(q.read_text());assert d['status']=='ERROR_LOCAL_MANIFEST_NATIVE_FILES_RETAINED' and d['reservation_retained'] and not d['public_verified'];assert (q.parent/'reservation.bin').exists()
  for rel,h in d['native_capture'].items():exact(q.parent/'native-terminal-capture'/rel,h)
  terminals.append(dict(path=p,pin=pin(q),files=len(d['native_capture'])))
 if q.name=='header-prefix.bin':prefixes.append(dict(path=p,pin=pin(q)))
assert terminals and prefixes
# The full unchanged prior graph remains available; no EDA is dispatched here.
prior=m.verify_parent();assert len(prior['devices'])==539
r=dict(status='PASS_ROOT_SAVED_ACQUISITION_AND_LOCAL_DURABILITY_WORKER_PEER_PENDING',freeze=pin(F),findings=[],method=pin(__file__),unique_pins_checked=len(checked),actual_fixture_files=3804,whole_bridges=4,unchanged_prior_devices=539,generated_deck_sha256=hashlib.sha256(deck.encode()).hexdigest(),campaigns=counts,current_distinct_predicates=69,invalid_terminal_captures=terminals,header_prefix_evidence=prefixes,scope='Exact source/private-scope/deck/numerics and full frozen saved artifacts checked. Actual preheader-invalid terminal files SSD-retained with reservation, original failures remain. This is source/saved controls only; independent final worker peer and launch peer required, no new native result.',native_started=False)
(B/'source-saved-acquisition-peer-root02.json').write_text(json.dumps(r,indent=2)+'\n');print(dict(status=r['status'],pins=len(checked),predicates=69,invalid_terminal_captures=len(terminals),header_prefix_files=len(prefixes)))
