"""Independent saved controls and source-only V20 continuation review."""
from pathlib import Path
import ast
import hashlib
import json
import tarfile
import xml.etree.ElementTree as ET

R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B=Path(__file__).resolve().parent
OLD=B.parent/'pcie-integrity-v19-20261005'

def pin(p):
    p=Path(p)
    with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def funcs(p):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(Path(p).read_text()).body if isinstance(n,ast.FunctionDef)}

def count_xml(p):
    cases=ET.parse(p).findall('.//testcase')
    return dict(passed=sum(all(c.find(t) is None for t in ('error','failure','skipped')) for c in cases),failed=sum(any(c.find(t) is not None for t in ('error','failure')) for c in cases),skipped=sum(c.find('skipped') is not None for c in cases))

policy_path=B/'continuation-policy04.json'
assert pin(policy_path)==dict(bytes=7769,sha256='f1abb77236bbedb3dc1d76395751660101b3200ef49411a34214f407ef83aa4f')
policy=json.loads(policy_path.read_text())
for p,v in policy['method_pins'].items():assert pin(p)==v,p
for p,v in policy['source_pins'].items():assert pin(R/p)==v,p
validation_path=Path(policy['controls']['validation']['path'])
v=json.loads(validation_path.read_text())
assert pin(validation_path)=={k:policy['controls']['validation'][k] for k in ('bytes','sha256')}
assert (v['pytest_executions'],v['pytest_passed_executions'],v['historical_failed_executions'])==(43,40,3)
pytest={n:count_xml(B/f'controls{n}.xml') for n in ('01','03','04')}
assert pytest=={'01':dict(passed=34,failed=1,skipped=0),'03':dict(passed=2,failed=2,skipped=0),'04':dict(passed=4,failed=0,skipped=0)}
for row in v['xml_recount']:
    assert pin(row['path'])=={k:row[k] for k in ('bytes','sha256')}
    assert count_xml(row['path'])==row['helper_counts']
assert [x['helper_counts'] for x in v['xml_recount']]==[dict(passed=14,failed=0,skipped=0),dict(passed=14,failed=1,skipped=0),dict(passed=1,failed=0,skipped=14),dict(passed=1,failed=0,skipped=14)]
assert v['source_freeze']==pin(B/'source-freeze04.json')
assert v['source_peer']==pin(B/'source-only-peer-rx04.json')
for row in v['literal_controls']+v['actual_miter_faults']+v['actual_parser_CRC_faults']:
    assert pin(row['path'])=={k:row[k] for k in ('bytes','sha256')}
for row in v['stalled_zero_keep_witnesses']:
    text=Path(row['path']).read_text()
    assert f"held_cycles={row['held_cycles']} actual_reference_retires={row['actual_reference_retires']} ring=64" in text
assert [r['held_cycles'] for r in v['stalled_zero_keep_witnesses']]==[56,56]
assert v['stalled_zero_keep_witnesses'][1]['actual_reference_retires']==55
negative=Path(v['actual_miter_faults'][-1]['path']).read_text()
assert 'PCIE_RING_CONTROL_MISMATCH' in negative and '48.00ns' in negative and 'FATAL:' in negative
assert 'AssertionError' not in negative
archive=Path(v['archive']['path'])
assert pin(archive)=={k:v['archive'][k] for k in ('bytes','sha256')}
manifest=json.loads((B/'controls-members.json').read_text())
with tarfile.open(archive,'r:xz') as t:
    names=t.getnames()
    assert len(names)==len(set(names))==v['archive']['members']==393
    assert set(names)==set(manifest)|{'members.json'}
    assert json.load(t.extractfile('members.json'))==manifest
    for m in t.getmembers():
        expected=pin(B/'controls-members.json') if m.name=='members.json' else manifest[m.name]
        assert m.isfile() and m.size==expected['bytes']
        with t.extractfile(m) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected['sha256']
for row in manifest.values():
    assert pin(row['original_path'])=={k:row[k] for k in ('bytes','sha256')}
before,after=funcs(OLD/'continue_native02.py'),funcs(B/'continue_native04.py')
same=['pin','explicit_stop','verify_sources','stage']
assert all(before[n]==after[n] for n in same)
suffix='assert shutil.disk_usage(\'/dev/shm\').free>=1024**3\n'
assert (B/'run_balanced_map.py').read_text().split(suffix,1)[1]==(B/'run_balanced_map04.py').read_text().split(suffix,1)[1]
inverse_helpers=['balanced_import.py','balanced_preplacement.py','prove_balanced_import.py','analyze_critical_path.py','measure_native_read_depth.py']
for n in inverse_helpers:
    assert (B/n).read_text().replace('integrity-v20','integrity-v19').replace('integrity_v20','integrity_v19')==(OLD/n).read_text(),n
detach=B/'detach_native04.py'
assert pin(detach)==dict(bytes=1953,sha256='e226cb552dc5a9b6f20cae382b5087f9a261164485c30b8a93a42611d187b610')
assert policy['continuation_source_basis']['sha256']==pin(OLD/'continue_native02.py')['sha256']
assert policy['lifecycle_peer_inherited']['sha256']==pin(policy['lifecycle_peer_inherited']['path'])['sha256']
assert not (B/'continuation-status04.json').exists()
assert not Path('/dev/shm/nssoc-integrity-v20-balanced-map-01').exists()
result=dict(status='PASS_SOURCE_ONLY_V20_MERGED_NATIVE_CONTINUATION',policy=pin(policy_path),findings=[],
    method=pin(Path(__file__)),method_pins=policy['method_pins'],source_pins=policy['source_pins'],detacher=pin(detach),
    control_validation=pin(validation_path),archive=v['archive'],complete_member_readback=393,original_capture_members_rehashed=len(manifest),pytest_recount=pytest,cocotb_xml_recount=v['xml_recount'],
    unchanged_continuation_function_asts=same,unchanged_version_only_helpers=inverse_helpers,map_native_body_byte_exact=True,
    review='Read full corrected sealer/controller/mapper/detacher and timing reducer. All393 archive members independently read/hash-checked and all392 original paths still exact. Initial34PASS/1undetected-mutant and intermediate2PASS/2EDS-positive-fail remain intact; final4PASS includes inverse, same-aligned-stream mutant plus only appended direct/miter. Old14 positive cases remain exact source prefix, with actual14 direct and14 miter results retained; no claim of whole15 rerun. Actual appended held56 cycles and reference55 zero-keep retires confirmed. Aligned mutant really fails at48ns ring-control divergence, not malformedEDS. Exact four ProcessOwner helper ASTs and map native tail retained; five import/proof/depth/STA helpers are full version-only inverses ofV19. Validation/source/peer pins gate every stage. OriginalMAX150/ring64,CPU6/2GiB,4ns/threecorners/port assumptions/floors unchanged. No healthy elapsed deadline, original failures cannot be converted to PASS by transport or count changes.',
    fixed_finding='Stale V19 policy literal in first detached launcher was preserved and replaced by exact current7769-byte policy pin; no native dispatch occurred before correction.',
    native_executed=False,limitations='Approval is for bounded fresh native map/import/proof/preplacement screen. Functional controls are finite and not fullDUTformal or MAX4118 acceptance. Preplacement result still cannot establish placement/route/extractedRC/PHY/mainchip/manufacturing closure.')
p=B/'native-source-only-peer04.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
