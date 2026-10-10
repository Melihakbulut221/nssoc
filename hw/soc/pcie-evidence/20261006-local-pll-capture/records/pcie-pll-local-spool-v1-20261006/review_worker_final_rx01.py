# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent additive worker source/saved-control peer; no producer execution."""
import ast,hashlib,json,difflib
from pathlib import Path
import xml.etree.ElementTree as ET
R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc');B=Path(__file__).resolve().parent
j=lambda p:json.loads(p.read_text())
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=j(B/'source-freeze02.json');assert pin(B/'source-freeze02.json')==dict(bytes=952894,sha256='ae1a0060b605a0b3bbab07e639c80cc19ab1f6db75fa202a4bb179da165ce7d1')
pins={}
for row in f['sources']:
 h={k:row[k]for k in('bytes','sha256')};assert pin(row['path'])==h;pins[row['path']]=h
worker=R/'scripts/publish_pcie_local_spool_v1.py';tests=R/'sw/tests/test_pcie_local_spool_publisher_v1.py';old=B/'worker-peer-candidate01'/worker.name;oldtests=B/'worker-peer-candidate01'/tests.name
before=old.read_text();after=worker.read_text();a={x.name:ast.dump(x,include_attributes=False)for x in ast.parse(before).body if isinstance(x,ast.FunctionDef)};b={x.name:ast.dump(x,include_attributes=False)for x in ast.parse(after).body if isinstance(x,ast.FunctionDef)}
assert a.keys()==b.keys()and {n for n in a if a[n]!=b[n]}=={'command','run'}
changes=[("def command(path, receipt, directory):", "def command(path, receipt, directory, *, stop=None):\n    def check_stop():\n        if stop is not None and stop.is_set():\n            raise life.Cancelled('Explicit stop at publication owner handoff')\n    check_stop()"),
("    with life.ProcessOwner(receipt.with_suffix('.owner.json')) as owner:\n", "    with life.ProcessOwner(receipt.with_suffix('.owner.json')) as owner:\n        check_stop()\n"),
("    owner.check()\n    guard(directory)\n", "    owner.check()\n    check_stop()\n    guard(directory)\n"),
("*, publish=command, poll_seconds=2.0,", "*, publish=None, poll_seconds=2.0,"),
("    stop = threading.Event() if stop is None else stop\n", "    stop = threading.Event() if stop is None else stop\n    if publish is None:\n        def publish(path, receipt, directory):\n            return command(path, receipt, directory, stop=stop)\n"),
("            check()\n            if not (spool / 'parts.json').exists():", "            check()\n            for name in ('native-terminal-invalid.json', 'terminal-retention-failure.json'):\n                failure = spool / name\n                if failure.exists():\n                    state['native_terminal_failure'] = dict(path=str(failure), **pin(failure))\n                    raise ValueError('Native terminal local manifest or retention failed; no complete publication')\n            if not (spool / 'parts.json').exists():")]
rebuilt=before
for source,target in changes:assert rebuilt.count(source)==1;rebuilt=rebuilt.replace(source,target)
assert rebuilt==after
assert tests.read_text().startswith(oldtests.read_text())
for row in f['actual_fixture_files']:
 if 'nssoc-spool-complete-controls03/'in row['path']:
  h={k:row[k]for k in('bytes','sha256')};assert pin(row['path'])==h;pins[row['path']]=h
row=next(x for x in f['controls']if x['name']=='complete-controls03')
for key in('xml','log'):
 r=row[key];h={k:r[k]for k in('bytes','sha256')};assert pin(r['path'])==h;pins[r['path']]=h
cases=list(ET.parse(row['xml']['path']).iter('testcase'));assert len(cases)==67 and not any(any(c.find(t)is not None for t in('failure','error','skipped'))for c in cases)
worker_cases=[c.attrib for c in cases if 'test_pcie_local_spool_publisher_v1'in c.attrib['classname']];assert len(worker_cases)==21
root=Path('/dev/shm/nssoc-spool-complete-controls03');controls=[]
for i in range(2):
 d=root/f'test_actual_signal_at_owner_ha{i}';state=j(d/'publication/publication.json');owner=j(next(d.glob('publication/*.owner.json')));http=j(d/'upload-state.json')
 assert state['status']=='ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'and state['explicit_stop']and 'owner handoff'in state['error']
 assert len(state['attempts'])==1 and not state['assets']and len(owner['processes'])==i and http['uploads']==i
 for p in owner['processes']:
  identity=p['identity'];proc=Path('/proc')/str(identity['pid'])/'stat'
  assert p['returncode']==0 and p['status']=='REAPED_NO_LIVE_MEMBERS'
  if proc.exists():
   fields=proc.read_text().rsplit(')',1)[1].split();assert int(fields[19])!=int(identity['start_ticks'])or fields[0]=='Z'
 controls.append(dict(case=d.name,state=pin(d/'publication/publication.json'),children=len(owner['processes']),uploads=http['uploads']))
for i in range(2):
 d=root/f'test_invalid_native_terminal_s{i}';state=j(d/'publication/publication.json');terminal=j(d/'ssd/native-terminal-invalid.json')
 assert state['status']=='ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'and not state['attempts']and not state['assets']
 assert state['native_terminal_failure']==dict(path=str(d/'ssd/native-terminal-invalid.json'),**pin(d/'ssd/native-terminal-invalid.json'))
 assert terminal['reservation_retained']is True and (d/'ssd/reservation.bin').exists()
 for name,h in terminal['native_capture'].items():assert pin(d/'ssd/native-terminal-capture'/name)==h==pin(d/'native'/name)
 controls.append(dict(case=d.name,state=pin(d/'publication/publication.json'),terminal=pin(d/'ssd/native-terminal-invalid.json'),no_attempts=True))
prior=j(B/'worker-saved-controls-review-rx02.json')
for p,h in prior['fixture_pins'].items():assert pin(p)==h
record=dict(status='PASS_SOURCE_AND_SAVED_LOCAL_SPOOL_WORKER',freeze=pin(B/'source-freeze02.json'),findings=[],source_pins={str(worker):pin(worker),str(tests):pin(tests)},method=pin(Path(__file__)),
 prior_saved_controls=pin(B/'worker-saved-controls-review-rx02.json'),prior_finding=pin(B/'source-saved-worker-findings-rx01.json'),source_candidate01={str(old):pin(old),str(oldtests):pin(oldtests)},
 whole_source_inverse_verified=True,changed_functions=['command','run'],whole_source_diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),
 current_worker_predicates=21,complete_campaign_total=67,worker_cases=worker_cases,actual_additive_controls=controls,verified_pins=pins,
 closed_finding='Shared outer stop checked before ownership, immediately after inner handler entry and after handler restoration; actual before-entry signal gives zerochildren/zerouploads and after-exit signal prevents adopting/starting another transfer. Native invalidterminal check precedes missingledger wait.',
 scope='Worker source + saved local fake-gh/localhost HTTP/file/process controls only. Current21 worker predicates inspected within67PASS aggregate, earlier17 plus resource refinement fixtures rehashed. Core terminal/acquisition changes independently reviewed by root; no fresh simulation/public network/control rerun and no PLL physical acceptance. Frozen V4 limits/transient classifier/dual byte receipt/source preservation unchanged.')
with(B/'source-saved-worker-peer-rx01.json').open('x')as out:json.dump(record,out,indent=2);out.write('\n')
print(json.dumps(dict(peer=pin(B/'source-saved-worker-peer-rx01.json'),worker_predicates=21,verified_pins=len(pins))))
