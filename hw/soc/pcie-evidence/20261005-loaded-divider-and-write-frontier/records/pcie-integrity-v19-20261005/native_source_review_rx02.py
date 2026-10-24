# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent closed-control/source peer; no native or functional execution."""
from pathlib import Path
import ast,hashlib,json,tarfile,xml.etree.ElementTree as ET
B=Path(__file__).resolve().parent;R=B.parents[3];O=B.with_name('pcie-integrity-v18-20261005')
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
policy=read(B/'continuation-policy02.json');verified={}
for p,v in policy['method_pins'].items():assert pin(p)==v;verified[p]=v
for p,v in policy['source_pins'].items():assert pin(R/p)==v;verified[str(R/p)]=v
core=read(policy['controls']['validation']['path']);assert core['source_freeze']==pin(B/'source-freeze04.json');assert core['source_peer']==pin(B/'source-only-peer-rx04.json')
assert core['status']=='PASS_SEVEN_SLOT_QUARANTINE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS'
assert (core['pytest_executions'],core['pytest_passed_executions'],core['historical_failed_executions'])==(29,28,1)
def count(p):
 rows=list(ET.parse(p).getroot().iter('testcase'));return dict(passed=sum(not any(x.find(t) is not None for t in ['failure','error','skipped']) for x in rows),failed=sum(any(x.find(t) is not None for t in ['failure','error']) for x in rows),skipped=sum(x.find('skipped') is not None for x in rows))
assert count(B/'controls01.xml')==dict(passed=26,failed=1,skipped=0)
assert count(B/'controls04.xml')==dict(passed=2,failed=0,skipped=0)
for row in core['xml_recount']:
 assert pin(row['path'])=={k:row[k] for k in ['bytes','sha256']};assert count(row['path'])=={k:row[k] for k in ['passed','failed','skipped']}
assert [(r['epochs'],r['held_faults']) for r in core['epoch_quarantine_witnesses']]==[(16,16)]*3
assert core['epoch_quarantine_witnesses'][1]['extra_fault_steps']==core['epoch_quarantine_witnesses'][1]['invalid_differences']==16
archive=Path(core['archive']['path']);assert pin(archive)=={k:core['archive'][k] for k in ['bytes','sha256']}
manifest=read(B/'controls-members.json');seen=set()
with tarfile.open(archive,'r:xz') as tar:
 for member in tar:
  assert member.isfile() and member.name not in seen;seen.add(member.name)
  expected=pin(B/'controls-members.json') if member.name=='members.json' else {k:manifest[member.name][k] for k in ['bytes','sha256']}
  with tar.extractfile(member) as stream:actual=dict(bytes=member.size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
  assert actual==expected,member.name
assert seen==set(manifest)|{'members.json'} and len(seen)==252
old=(B/'run_balanced_map.py').read_text();new=(B/'run_balanced_map02.py').read_text();marker="assert shutil.disk_usage('/dev/shm').free>=1024**3\n";assert old[old.index(marker):]==new[new.index(marker):]
olddefs={x.name:ast.dump(x) for x in ast.parse((O/'continue_native01.py').read_text()).body if isinstance(x,ast.FunctionDef)}
newdefs={x.name:ast.dump(x) for x in ast.parse((B/'continue_native02.py').read_text()).body if isinstance(x,ast.FunctionDef)}
for name in ['pin','explicit_stop','verify_sources','stage']:assert olddefs[name]==newdefs[name]
method_inverses=[]
for name in ['balanced_import.py','balanced_preplacement.py','prove_balanced_import.py','analyze_critical_path.py','measure_native_read_depth.py','review_timing.py']:
 expected=(O/name).read_text().replace('integrity-v18','integrity-v19').replace('integrity_v18','integrity_v19').replace('V18','V19')
 if name=='measure_native_read_depth.py':expected=expected.replace('candidate=analyze(a.candidate,18)','candidate=analyze(a.candidate,19)')
 assert expected==(B/name).read_text(),name;method_inverses.append(name)
launcher=(B/'detach_native02.py').read_text();assert "start_new_session=True" in launcher and 'stdin=subprocess.DEVNULL' in launcher and "open('x')" in launcher
assert pin(B/'continuation-policy02.json')['sha256'] in launcher
assert not (B/'continuation-status02.json').exists() and not Path('/dev/shm/nssoc-integrity-v19-balanced-map-01').exists()
r=dict(status='PASS_SOURCE_ONLY_V19_MERGED_NATIVE_CONTINUATION',policy=pin(B/'continuation-policy02.json'),findings=[],method=pin(__file__),inputs_rehashed=verified,launcher=pin(B/'detach_native02.py'),closed_control_archive=dict(**pin(archive),full_members=len(seen)),actual_old_pytest=dict(passed=26,failed=1),actual_new_pytest=dict(passed=2,failed=0),new_miter_fault_and_invalid_difference_witnesses=16,unchanged_full_native_map_body=True,unchanged_owned_stage_function_asts=['pin','explicit_stop','verify_sources','stage'],exact_native_method_version_inverses=method_inverses,review=['Read full controller/map/merged sealer and detached launcher. Source freeze and merged receipt are hard gates before native; historical failed miter remains failure, original26successful tests retained, corrected full14miter plus changed directcase separately measured.', 'Actual252-member archive independently streamed and rehashed with old/new XML counts, source snapshots and sixteen real quarantine witnesses. No replay or simulator invocation.', 'Same CPU6, native2GiB, MAX150/ring64, original4ns/SS-TT-FF and all existing pin assumptions. Native mapping body is byte-identical after gate changes; import/proof/preplacement/depth/review differ only by intended V19 identifiers.', 'Exact frozen ProcessOwner tracks native-stage leaders with explicit parent-signal classification and failure cleanup. Stages pin all methods/sources before and after; detached launcher has exclusive once-file and new-session/DEVNULL/logs. It does not adopt or signal concurrent PLL/nativeMAX jobs.', 'Only finite functional/control acceptance authorizes this next native experiment. No mapped, timing, physical, MAX4118 or production result is inferred.'],native_execution_by_peer=False)
p=B/'native-source-only-peer02.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
