# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-byte RX16one audit. No producer imports or subprocesses."""
import collections
import datetime
import gzip
import hashlib
import json
import math
import re
import resource
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
R = Path.cwd()
B = R / 'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
O = B / 'repair16one-peer'
C = B / 'repair16one-continuation01'
N = Path('/dev/shm')
P = N / 'nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04'
D = N / 'nssoc-rx-prefetch-v2-repair16one-drt-01'
X = N / 'nssoc-rx-prefetch-v2-repair16one-detailed-rc-01'
E = N / 'nssoc-rx-prefetch-v2-repair16one-equivalence'
T = N / 'nssoc-rx-prefetch-v2-repair16one-physical-replay-01'
checked = {}


def stream_pin(f):
    h, n = hashlib.sha256(), 0
    while block := f.read(1024 * 1024):
        h.update(block)
        n += len(block)
    return {'bytes': n, 'sha256': h.hexdigest()}


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        v = stream_pin(f)
    checked[str(p)] = v
    return v


def verify(p, expected):
    actual = checked.get(str(p)) or pin(p)
    assert actual == {k: expected[k] for k in ('bytes', 'sha256')}, str(p)


def read(p):
    pin(p)
    return json.loads(Path(p).read_text())


def pin_map(m, base=None):
    for name, h in m.items():
        verify(Path(name) if base is None else base / name, h)


def absent_birth(row):
    f = Path('/proc') / str(row['pid']) / 'stat'
    if not f.exists():
        return True
    fields = f.read_text().rsplit(')', 1)[1].split()
    return fields[19] != str(row['start_ticks']) or fields[0] == 'Z'


review = read(O / 'review.json')
manifest = read(C / 'manifest.json')
continuation = read(C / 'result.json')
assert continuation['status'] == 'COMPLETE_RX16ONE_FINITE_ROUTE_RC_REVIEW_PUBLICATION'
verify(C / 'manifest.json', continuation['manifest'])
for m in (manifest['inputs'], manifest['route_inputs'], continuation['inputs'], review['inputs_rehashed']):
    pin_map(m)
assert len(continuation['stages']) == 4
for stage in continuation['stages']:
    assert stage['returncode'] == 0
    assert stage['source_pins_before'] == stage['source_pins_after']
    pin_map(stage['source_pins_after'])
    verify(stage['log'], stage['log_pin'])
    assert absent_birth(stage['identity'])
assert all(absent_birth(row) for row in [manifest['route_owner'], manifest['route_native'], continuation['controller_identity']])
for root in (D, X):
    record = read(root / 'result.json')
    assert record['status'].startswith('COMPLETE_') and record['returncode'] == 0
    pin_map(record['inputs'])
    pin_map(record['outputs'], root)
assert pin(D / 'routed.v') == pin(P / 'repaired.v')
assert (D / 'router-drc.rpt').stat().st_size == 0
route_log = (D / 'native.log').read_text()
assert re.findall(r'Number of violations = (\d+)', route_log)[-1] == '0'
assert 'NATIVE_DETAILED_ROUTING_COMPLETE' in route_log

# Independent extraction of individual report blocks, including all four classes.
raw = (X / 'native.log').read_text()
assert 'NATIVE_NOMINAL_RC_SCREEN_COMPLETE' in raw
assert not re.search(r'\[ERROR\b|Error:', raw)
blocks = re.split(r'^EXTRACTED_NOMINAL_RC_(slow|typical|fast)_(max|min)\s*$', raw, flags=re.M)
timing, reports = {}, []
assert len(blocks) == 19
for i in range(1, len(blocks), 3):
    corner, direction, body = blocks[i:i+3]
    for path in body.split('Startpoint:')[1:]:
        end = re.search(r'^Endpoint:\s+(\S+)', path, re.M)[1]
        match = re.search(r'^\s*(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)', path, re.M)
        assert match
        slack = float(match[1])
        assert (slack < 0) == (match[2] == 'VIOLATED')
        if direction == 'max':
            kind = 'recovery' if 'recovery check' in path else 'setup'
        else:
            kind = 'removal' if 'removal check' in path else 'hold'
        timing.setdefault(corner, {}).setdefault(kind, []).append(slack)
        reports.append({'corner': corner, 'class': kind, 'startpoint': path.splitlines()[0].strip(), 'endpoint': end, 'slack_ns': slack})
assert len(reports) == 36
assert all(set(v) == {'setup', 'hold', 'recovery', 'removal'} and all(len(a) == 3 for a in v.values()) for v in timing.values())
minima = {corner: {k: min(values) for k, values in kinds.items()} for corner, kinds in timing.items()}
assert minima == review['nominal_rc_cell_corner_slack_ns'] == continuation['native_timing']
assert minima['slow']['setup'] == -0.301453
assert all(v > 0 for c in minima.values() for k, v in c.items() if k != 'setup')
previous = read(B / 'repair14a-peer/review.json')
gain = round(minima['slow']['setup'] - previous['nominal_rc_cell_corner_slack_ns']['slow']['setup'], 6)
assert gain == 0.101025 == review['SS_setup_improvement_vs14a_ns']
electrical = raw.split('tns max ', 1)[1].split('\n', 1)[1].split('EXTRACTED_NOMINAL_RC_slow_max', 1)[0]
assert electrical.strip() == '' and review['max_slew_cap_violations_reported'] == 0
def sdc_commands(p):
    return [line for line in p.read_text().splitlines() if line and not line.startswith('#')]
commands = sdc_commands(D / 'routed.sdc')
assert commands == sdc_commands(P / 'repaired.sdc')
assert any('create_clock -name development_clock -period 4.0000' in line for line in commands)
assert not any(line.startswith(('set_false_path', 'set_multicycle_path')) for line in commands)

# Unannotated outputs must be genuinely unconnected; all their inputs must be on
# the corresponding extracted clock nets. Independently stream every R/C value.
unannotated = raw.split('Found 78 unannotated drivers.\n')[1].split('Found 0 partially unannotated drivers.')[0].split()
assert len(unannotated) == 78
text = (D / 'routed.v').read_text()
instances = {m[2]: (m[1], dict(re.findall(r'\.(\w+)\s*\(\s*([^()]*)\s*\)', m[3]))) for m in re.finditer(r'\b(sg13g2_\w+)\s+(\w+)\s*\((.*?)\);', text, re.S)}
loads = {}
for p in unannotated:
    name, terminal = p.split('/')
    master, ports = instances[name]
    assert set(ports) == {'A'} and terminal == ('Y' if master.startswith('sg13g2_inv_') else 'X')
    loads[name] = ports['A'].strip()
assert set(loads) == {f'clkload{i}' for i in range(78)}
names, mode, net, seen = {}, None, None, set()
census = dict(nets=0, capacitor_entries=0, resistor_entries=0, zero_resistors=0)
with (X / 'routed.spef').open() as f:
    for line in f:
        fields = line.split()
        if not fields:
            continue
        tag = fields[0]
        if tag in ('*NAME_MAP', '*PORTS', '*CONN', '*CAP', '*RES', '*END'):
            mode = tag
        elif tag == '*D_NET':
            net, mode = names.get(fields[1], fields[1]), tag
            census['nets'] += 1
            assert math.isfinite(float(fields[2])) and float(fields[2]) >= 0
        elif mode == '*NAME_MAP':
            assert len(fields) == 2 and tag not in names
            names[tag] = fields[1]
        elif mode == '*CONN' and tag == '*I':
            ref, terminal = fields[1].rsplit(':', 1)
            name = names.get(ref, ref)
            if name in loads:
                assert terminal == 'A' and fields[2] == 'I' and net == loads[name] and name not in seen
                seen.add(name)
        elif mode in ('*CAP', '*RES'):
            value = float(fields[-1])
            assert math.isfinite(value) and value >= 0
            census['capacitor_entries' if mode == '*CAP' else 'resistor_entries'] += 1
            census['zero_resistors'] += int(mode == '*RES' and value == 0)
assert seen == set(loads) and census == review['spef_numeric_census']

# Rebind original execution receipts without executing their methods.
binding = read(E / 'proof-execution-binding.json')
assert binding['status'] == 'PASS_ACTUAL_RX16ONE_PROOF_AND_MUTATION_EXECUTION_BOUND'
assert binding['before_inputs'] == binding['after_inputs']
assert binding['expanded_graphs_before'] == binding['expanded_graphs_after']
assert binding['runtime_before'] == binding['runtime_after']
pin_map(binding['after_inputs'])
pin_map(binding['outputs'], E)
verify(binding['runtime_after']['path'], binding['runtime_after']['pin'])
assert [x['method'] for x in binding['runs']] == ['compare.py', 'mutations.py']
assert all(x['returncode'] == 0 for x in binding['runs'])
normalization = read(E / 'normalization.json')
pin_map(normalization['inputs'])
for name, record in binding['expanded_graphs_after'].items():
    verify(E / f'{name}.json.gz', record['compressed'])
    with gzip.open(E / f'{name}.json.gz', 'rb') as stream:
        assert stream_pin(stream) == record['expanded']
    run = next(r for r in normalization['runs'] if r['name'] == name)
    assert run['returncode'] == 0 and run['expanded_json']['sha256'] == record['expanded']['sha256']
eq = read(E / 'equivalence.json')
assert (eq['states'], eq['input_bits'], eq['output_bits'], eq['targets'], eq['matched']) == (1804, 528, 31, 5443, 5443)
assert eq['mismatches'] == []
mutants = read(E / 'mutation-controls.json')['controls']
assert len(mutants) == 10 and all(m['status'].startswith('REJECTED_') for m in mutants)
ports = read(T / 'result.json')
assert ports['tests'] == dict(passed=6, failed=0, skipped=0)
for m in (ports['inputs'], ports['runtime']):
    pin_map(m)
pin_map(ports['outputs'], T)
xml = ET.parse(T / 'results.xml')
cases = list(xml.iter('testcase'))
assert len(cases) == 6 and not any(list(case) for case in cases)
owned = read(T / 'owned-driver.json')
assert owned['status'] == 'PASS_EXACT_PROVED_RX16ONE_SIX_NATIVE_PORT_CASES'
pin_map(owned['inputs'])
compiled = owned['lossless_closed_program']
verify(T / 'sim/sim.vvp.gz', compiled['gzip'])
with gzip.open(T / 'sim/sim.vvp.gz', 'rb') as stream:
    assert stream_pin(stream) == compiled['raw'] == compiled['full_decompressed_readback']

# Every archived regular member is re-read, compared to the frozen manifest,
# and all five complete native roots are independently matched to that manifest.
package = read(O / 'package.json')
verify(package['archive']['path'], package['archive'])
members = {}
with tarfile.open(package['archive']['path'], 'r|xz') as archive:
    for member in archive:
        assert member.isfile() and member.name not in members
        with archive.extractfile(member) as stream:
            members[member.name] = stream_pin(stream)
        assert members[member.name]['bytes'] == member.size
assert members == package['members'] and len(members) == package['member_count'] == 110
native_files = 0
for root in (P, E, T, D, X):
    files = {f'native/{root.name}/{p.relative_to(root)}': p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert set(files) == {n for n in members if n.startswith(f'native/{root.name}/')}
    for n, p in files.items():
        assert not p.is_symlink()
        verify(p, members[n])
    native_files += len(files)

# Saved V3 transport transcripts contain full download hashes and byte-prefix
# comparisons. No network request is repeated by this independent peer.
release = read(O / 'release.json')
assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and not release['physical_acceptance']
verify(O / 'release.json', continuation['release'])
verify(release['transport_journal']['path'], release['transport_journal'])
journal = read(release['transport_journal']['path'])
assert len(release['files']) == len(release['assets']) == 3
for file, asset in zip(release['files'], release['assets']):
    verify(file['path'], file)
    assert all(file[k] == asset[k] for k in ('name', 'bytes', 'sha256'))
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
    for kind in ('authenticated', 'anonymous'):
        rows = [r for r in journal if r['kind'] == kind and r['asset']['id'] == asset['asset_id'] and r['status'] == 'PASS']
        assert len(rows) == 1
        row = rows[0]
        observation = row['observed_download']
        assert all(observation[k] == file[k] for k in ('bytes', 'sha256'))
        assert observation['matched_local_prefix_bytes'] == file['bytes'] and observation['mismatching_chunk'] is None
for row in journal:
    assert row['status'] == 'PASS' and row['returncode'] == 0
    for side in ('stdout', 'stderr'):
        payload = row[side]
        verify(payload['path'], payload)
        with gzip.open(payload['path'], 'rb') as stream:
            assert stream_pin(stream) == payload['uncompressed']
    if 'response' in row:
        verify(row['response']['path'], row['response'])
    pin(row['owned_processes'])
validation_path = O / 'pcie-rx-repair16one-finite-physical-validation-20261006.json'
validation = read(validation_path)
verify(validation_path, package['validation'])
assert validation['nominal_rc_cell_corner_slack_ns'] == minima
assert not validation['physical_acceptance'] and not validation['qualified_rc']
peer = {
    'status': 'PASS_INDEPENDENT_SAVED_RX16ONE_FINITE_CAPTURE__4NS_TIMING_REMAINS_FAIL',
    'findings': [], 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'nominal_cell_corner_slack_ns': minima, 'individual_report_count': len(reports),
    'individual_reports': reports, 'SS_setup_gain_vs14a_ns': gain,
    'route_drc': 0, 'reported_slew_cap_violations': 0, 'spef_census': census,
    'input_only_CTS_loads_fully_bound': len(seen), 'partial_unannotated_drivers': 0,
    'binary_proof': {'states': 1804, 'functions': 5443, 'actual_negative_controls': 10, 'original_gold_reused': True},
    'native_port_XML_cases': [case.attrib for case in cases],
    'archive': package['archive'], 'archive_members': len(members), 'complete_native_files': native_files,
    'public_assets': release['assets'], 'actual_transport_operations': len(journal),
    'actual_transport_failures': 0, 'prior_failed_experiments_preserved': True,
    'terminal_note': 'Controller utc is its initialization time; terminal status and four closed zero-return stages are the completion authority. Exact recorded route/controller/stage births no longer live.',
    'adoption_boundary': 'RX16one is a proved, six-port-checked and zero-router-DRC standalone default150 receiver candidate with improved measured nominal RC. SS setup remains negative. It is not accepted as 4ns timing closure, qualified process-RC, full-chip, foundry DRC, PDN or full PCIe PHY.',
    'method': {'path': str(Path(__file__)), **pin(__file__)}, 'files_rehashed': checked,
    'scope': 'Only independent stdlib saved-byte reading and arithmetic. No EDA, proof/kernel, simulation, reviewed producer execution, process signal or fresh network transfer.',
}
out = O / 'saved-result-peer-rx01.json'
assert not out.exists()
out.write_text(json.dumps(peer, indent=2) + '\n')
print(json.dumps({'peer': str(out), **pin(out), 'unique_rehashed_files': len(checked), 'slacks': minima, 'archive_members': len(members)}))
