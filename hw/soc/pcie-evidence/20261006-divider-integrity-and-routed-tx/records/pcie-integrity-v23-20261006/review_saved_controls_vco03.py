"""Independent saved byte/XML/log recount, without producer imports or execution."""
from pathlib import Path
import ast
import hashlib
import json
import re
import tarfile
import xml.etree.ElementTree as ET

R = Path.cwd()
B = Path(__file__).resolve().parent
V = B / 'pcie-integrity-v23-composite-controls-validation-20261006.json'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


def bound(row):
    p = Path(row['path'])
    assert pin(p) == {k: row[k] for k in ('bytes', 'sha256')}, str(p)
    return p


def census(path):
    cases = list(ET.parse(path).getroot().iter('testcase'))
    counts = dict(passed=0, failed=0, skipped=0)
    for case in cases:
        bad = any(case.find(k) is not None for k in ('failure', 'error'))
        skipped = case.find('skipped') is not None
        assert not (bad and skipped)
        counts['failed' if bad else 'skipped' if skipped else 'passed'] += 1
    return cases, counts


j = json.loads(V.read_text())
assert j['status'] == 'PASS_V23_ADJACENT_HEADER_COMPOSITE_CONTROLS'
archive = bound(j['archive'])
with tarfile.open(archive, 'r:xz') as t:
    manifest = json.loads(t.extractfile('members.json').read())
    seen = set()
    for item in t:
        assert item.isfile() and item.name not in seen
        seen.add(item.name)
        data = t.extractfile(item).read()
        if item.name != 'members.json':
            assert dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest()) == {
                k: manifest[item.name][k] for k in ('bytes', 'sha256')}
assert len(seen) == j['members'] == 562 and set(manifest) == seen - {'members.json'}

freezes = {i: json.loads((B / f'source-freeze0{i}.json').read_text()) for i in (1, 2, 3)}
for i, f in freezes.items():
    for name, value in f['sources'].items():
        assert pin(B / f'sources0{i}' / name) == value
for name, value in freezes[3]['sources'].items():
    assert pin(R / name) == value
assert j['source_freeze'] == pin(B / 'source-freeze03.json')
assert j['source_peer'] == pin(B / 'source-only-peer-vco03.json')
bench = 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py'
miter = 'sw/tests/test_pcie_gen3_integrity_v23_miter.py'
assert {n for n in freezes[1]['sources'] if freezes[1]['sources'][n] != freezes[2]['sources'][n]} == {bench}
assert {n for n in freezes[2]['sources'] if freezes[2]['sources'][n] != freezes[3]['sources'][n]} == {miter}
defs = lambda s: {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(s).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
a = defs((B / 'sources01' / bench).read_text())
c = defs((R / bench).read_text())
assert {n for n in a if a[n] != c[n]} == {'adjacent_header_all_positions_and_bank_boundaries'}
counts = []
for row in j['campaigns']:
    cases, actual = census(bound(row))
    assert actual == {k: row[k] for k in ('passed', 'failed', 'skipped')}
    assert [c.get('name') for c in cases] == [c['name'] for c in row['cases']]
    counts.append(actual)
assert counts == [dict(passed=28, failed=7, skipped=0), dict(passed=6, failed=3, skipped=0), dict(passed=3, failed=0, skipped=0)]
assert sum(sum(c.values()) for c in counts) == j['pytest_executions'] == 47
assert sum(c['failed'] for c in counts) == j['historical_failed_executions'] == 10

helpers = []
for row in j['helper_receipts']:
    p = bound(row)
    h = json.loads(p.read_text())
    assert h['status'] == row['status']
    for name, value in h['inputs'].items():
        source = Path(name)
        if source.is_relative_to(R) and str(source.relative_to(R)) in freezes[row['revision']]['sources']:
            source = B / f"sources0{row['revision']}" / source.relative_to(R)
        assert pin(source) == value, str(source)
    for name, value in h['outputs'].items():
        assert pin(p.parent / name) == value
    assert census(p.parent / 'results.xml')[1] == row['counts']
    assert (p.parent / 'sim/sim.vvp').is_file()
    helpers.append(str(p))

D1 = Path('/dev/shm/nssoc-integrity-v23-public-controls01')
D2 = Path('/dev/shm/nssoc-integrity-v23-public-controls02')
for directory in [D1 / 'test_actual_wide_rx_full_posit0/capture', D1 / 'test_v22_v23_cycle_exact_all_p0/capture']:
    assert census(directory / 'results.xml')[1] == dict(passed=18, failed=0, skipped=0)
saved = json.loads((B / 'saved-targeted-positive02.json').read_text())
assert j['saved_selected_positives'] == pin(B / 'saved-targeted-positive02.json')
for row in saved['records']:
    p = bound(row['result'])
    x = bound(row['xml'])
    bound(row['log'])
    h = json.loads(p.read_text())
    assert h['status'] == 'PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX'
    cases, actual = census(x)
    assert len(cases) == 18 and actual == dict(passed=1, failed=0, skipped=17)
    assert [c.get('name') for c in cases if c.find('skipped') is None] == ['adjacent_header_all_positions_and_bank_boundaries']
log = Path(saved['records'][1]['log']['path']).read_text()
assert 'V23_ADJACENT_WITNESSES positions=' + str([25] * 16) in log
for token in ['cross_block=25', 'minimum_same_beat=28', 'missing_old_predecessor=16']:
    assert token in log
assert j['adjacent_witness'] == saved['records'][1]['witness']
assert j['adjacent_witness']['positions'] == [25] * 16
cache = (D1 / 'test_v22_v23_cycle_exact_all_p0/capture/simulation.log').read_text()
match = re.search(r'V23_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)', cache)
assert match and list(map(int, match.groups())) == [8, 8, 8]

assert len(j['literal_controls']) == 6 and sum(row['positive'] for row in j['literal_controls']) == 1
for row in j['literal_controls']:
    text = bound(row).read_text()
    assert ('PASS_V23_ADJACENT_RELATION binary=557056 literalXZ=1440' in text) if row['positive'] else ('V23_ADJACENT_LITERAL case=' in text)
assert len(j['meaningful_miter_mutants']) == 11
for row in j['meaningful_miter_mutants']:
    p = bound(row)
    text = p.read_text()
    assert row['diagnostics'] and all(diagnostic in text for diagnostic in row['diagnostics'])
    assert 'Cannot convert Logic' not in text
    assert census(p.parent / 'results.xml')[1] == dict(passed=0, failed=1, skipped=17)
assert 'V23_OBSERVER_OLD_PREDECESSOR' in bound(j['observer_negative']).read_text()
for i in range(12):
    p = D1 / f'test_actual_wide_rx_fault_reje{i}/capture'
    assert census(p / 'results.xml')[1] == dict(passed=0, failed=1, skipped=17)
    assert 'AssertionError' in (p / 'simulation.log').read_text()

burst = []
for row in j['promotion_burst']:
    p = bound(row)
    h = json.loads(p.read_text())
    assert h['fault'] == row['fault']
    for name, value in h['inputs'].items():
        assert pin(name) == value
    for name, value in h['outputs'].items():
        assert pin(p.parent / name) == value
    text = bound(row['log']).read_text()
    assert h['blocks'] == 15 and h['bytes'] == 786 and h['packets'] == 25
    if h['fault'] is None:
        assert h['returncode'] == 0
        values = list(map(int, re.search(r'PASS_V23_FRAMER_BURST blocks=(\d+) bytes=(\d+) packets=(\d+) promotions=(\d+) changed=(\d+) concurrent=(\d+) inputstall=(\d+) outputstall=(\d+)', text).groups()))
        assert values == [15, 786, 25, 14, 13, 13, 38, 6]
    else:
        assert h['fault'] == 'header_promote_stale' and h['returncode'] == 1
        assert 'V23_FRAMER_PROMOTION_RELATION' in text and 'Time: 28000' in text
    burst.append(p.parent)
old = 'current_header_relation<=next_header_relation;'
new = 'current_header_relation<=current_header_relation;'
nominal = (burst[0] / 'soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()
fault = (burst[1] / 'soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()
assert nominal.count(old) == 1 and fault.replace(new, old) == nominal
assert pin(burst[0] / 'tb.v') == pin(burst[1] / 'tb.v')
assert pin(burst[0] / 'soc_pcie_gen3_framer_rx_integrity_v22.v') == pin(burst[1] / 'soc_pcie_gen3_framer_rx_integrity_v22.v')
assert j['MAX4118_profile_excluded'] is True and j['physical_acceptance'] is False
receipt = dict(status='PASS_INDEPENDENT_SAVED_V23_COMPOSITE_FUNCTIONAL_CONTROLS',
    validation=pin(V), findings=[], method=pin(__file__), archive=j['archive'],
    all_archive_members_rehashed=562, source_snapshots_rehashed=[1, 2, 3],
    all_helper_inputs_outputs_rehashed=len(helpers), campaign_counts=counts,
    retained_historical_failed_executions=10, original_full_positive_profiles=[18, 18],
    corrected_selected_profiles=[dict(passed=1, failed=0, selected_out_skips=17)] * 2,
    unchanged_public_prefix_cases=17, literal_binary=557056, literal_XZ=1440,
    literal_faults=5, meaningful_wrapper_miter_faults=11, product_faults=12,
    real_promotion_mutant_one_edit_inverse=True, promotion_fault_native_time_ps=28000,
    burst_actual_counts=dict(blocks=15, bytes=786, packets=25, promotions=14,
                             changed=13, concurrent=13, inputstall=38, outputstall=6),
    actual_cache_witness=[8, 8, 8], source_criteria_relaxed=False,
    complete_updated_wrapper_profile_rerun=False, MAX4118_excluded=True,
    no_producer_imports_or_test_native_rerun=True, physical_acceptance=False,
    scope='Independent all-member/source/helper pin and raw XML/log recount. Original ten failures and surviving wrapper-cadence mutant remain historical; exact same promotion mutation is now rejected by actual block-port burst. No exhaustive formal, mapping, timing or full PHY acceptance.')
out = B / 'saved-controls-peer-vco03.json'
assert not out.exists()
out.write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'], pin(out))
