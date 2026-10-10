# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded read-only verification of completed TX05 outputs; no new native run."""
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import resource
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
R = Path.cwd()
B = R / "hw/soc/out/pcie-gen3-transmit-v4-repair-20261005"
O = Path(__file__).resolve().parent
sys.path.insert(0, str(B))  # Exact proof gate imports reviewed owned_lifecycle05.
N = Path('/dev/shm')
D = N / 'nssoc-tx-path-v4-repair05-drt-01'
X = N / 'nssoc-tx-path-v4-repair05-detailed-rc-01'
P = N / 'nssoc-tx-path-v4-postroute-repair-05'
E = N / 'nssoc-tx-path-v4-repair05-equivalence'
T = N / 'nssoc-tx-path-v4-repair05-physical-replay-02'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def j(p):
    return json.loads(Path(p).read_text())


inputs = {}
for directory in (D, X):
    result = j(directory / 'result.json')
    assert result['returncode'] == 0 and result['status'].startswith('COMPLETE_')
    for path, h in result['inputs'].items():
        assert pin(path) == h
        inputs[path] = h
    for name, h in result['outputs'].items():
        assert pin(directory / name) == h
        inputs[str(directory / name)] = h
    inputs[str(directory / 'result.json')] = pin(directory / 'result.json')
assert (D / 'routed.v').read_bytes() == (P / 'repaired.v').read_bytes()
assert (D / 'router-drc.rpt').stat().st_size == 0
assert re.findall(r'Number of violations = (\d+)', (D / 'native.log').read_text())[-1] == '0'
assert 'NATIVE_DETAILED_ROUTING_COMPLETE' in (D / 'native.log').read_text()
log = (X / 'native.log').read_text()
assert 'NATIVE_NOMINAL_RC_SCREEN_COMPLETE' in log
assert not re.search(r'\[ERROR\b|Error:', log)
slacks = {}
paths = []
for corner in ('slow', 'typical', 'fast'):
    values = {}
    for direction in ('max', 'min'):
        part = log.split(f'EXTRACTED_NOMINAL_RC_{corner}_{direction}\n')[1].split('EXTRACTED_NOMINAL_RC_', 1)[0]
        cases = part.split('Startpoint:')[1:]
        assert len(cases) == 6
        for case in cases:
            matches = re.findall(r'(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)', case)
            assert len(matches) == 1
            value = float(matches[0][0])
            assert (value < 0) == (matches[0][1] == 'VIOLATED')
            kind = ('recovery' if 'recovery check' in case else 'setup') if direction == 'max' else ('removal' if 'removal check' in case else 'hold')
            values.setdefault(kind, []).append(value)
            if corner == 'slow' and kind == 'setup':
                paths.append({'startpoint': case.splitlines()[0].strip(), 'endpoint': re.search(r'Endpoint: (\S+)', case)[1], 'slack_ns': value, 'raw_path': case})
    assert all(len(v) == 3 for v in values.values()) and len(values) == 4
    slacks[corner] = {k: min(v) for k, v in values.items()}
# The new measured slacks are not known in advance; record all four classes.
assert all(math.isfinite(value) for corner in slacks.values() for value in corner.values())
old = N / 'nssoc-tx-path-v4-repair03-detailed-rc-01/result.json'
old_result = j(old)
for name,h in old_result['outputs'].items():
    assert pin(old.parent / name) == h
    inputs[str(old.parent / name)] = h
old_log = (old.parent / 'native.log').read_text()
prior_slacks = {}
for corner in ('slow', 'typical', 'fast'):
    values = {}
    for direction in ('max', 'min'):
        part = old_log.split(f'EXTRACTED_NOMINAL_RC_{corner}_{direction}\n')[1].split('EXTRACTED_NOMINAL_RC_', 1)[0]
        for case in part.split('Startpoint:')[1:]:
            value = float(re.findall(r'(-?\d+\.\d+)\s+slack \((?:MET|VIOLATED)\)', case)[0])
            kind = ('recovery' if 'recovery check' in case else 'setup') if direction == 'max' else ('removal' if 'removal check' in case else 'hold')
            values.setdefault(kind, []).append(value)
    prior_slacks[corner] = {k:min(v) for k,v in values.items()}
delta = {corner:{k:round(slacks[corner][k]-v,6) for k,v in prior_slacks[corner].items()} for corner in prior_slacks}

# Every reported unannotated output belongs to an input-only CTS load.
unannotated = log.split('Found 150 unannotated drivers.\n')[1].split('Found 0 partially unannotated drivers.')[0].split()
assert len(unannotated) == 150 and {p.split('/')[0] for p in unannotated} == {f'clkload{i}' for i in range(150)}
netlist = (D / 'routed.v').read_text()
loads = {}
for output in unannotated:
    inst, pinname = output.split('/')
    match = re.search(r'\b(sg13g2_(?:inv|buf)_\d+)\s+' + inst + r'\s*\((.*?)\);', netlist, re.S)
    assert match
    connections = re.findall(r'\.(\w+)\(([^()]*)\)', match[2])
    assert len(connections) == 1 and connections[0][0] == 'A'
    assert pinname == ('Y' if '_inv_' in match[1] else 'X')
    loads[inst] = {'master': match[1], 'unconnected_output': pinname, 'clock_input_net': connections[0][1]}

# Stream the actual extracted SPEF; bind each dummy input to an annotated net.
names = {}
state = ''
net = None
connected = {}
count = {'nets': 0, 'capacitor_entries': 0, 'resistor_entries': 0, 'zero_resistors': 0}
with (X / 'routed.spef').open() as f:
    for raw in f:
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == '*NAME_MAP':
            state = 'names'
        elif fields[0] == '*PORTS':
            state = 'ports'
        elif fields[0] == '*D_NET':
            net = names.get(fields[1], fields[1])
            count['nets'] += 1
            assert math.isfinite(float(fields[2])) and float(fields[2]) >= 0
            state = 'net'
        elif fields[0] in ('*CONN', '*CAP', '*RES', '*END'):
            state = fields[0]
        elif state == 'names':
            assert len(fields) == 2 and fields[0] not in names
            names[fields[0]] = fields[1]
        elif state == '*CONN' and fields[0] == '*I':
            number, terminal = fields[1].rsplit(':', 1)
            instance = names.get(number, number)
            if instance in loads:
                assert terminal == 'A' and fields[2] == 'I' and net == loads[instance]['clock_input_net']
                assert instance not in connected
                connected[instance] = net
        elif state in ('*CAP', '*RES'):
            value = float(fields[-1])
            assert math.isfinite(value) and value >= 0
            key = 'capacitor_entries' if state == '*CAP' else 'resistor_entries'
            count[key] += 1
            if state == '*RES' and value == 0:
                count['zero_resistors'] += 1
assert set(connected) == set(loads)

# Retained port XML and native-expanded proof payloads are checked again.
ports = j(T / 'result.json')
assert ports['tests'] == {'passed': 3, 'failed': 0, 'skipped': 0}
cases = list(ET.parse(T / 'results.xml').iter('testcase'))
assert len(cases) == 3 and all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases)
for path, h in {**ports['inputs'], **ports.get('runtime', {})}.items():
    assert pin(path) == h
    inputs[path] = h
for name, h in ports['outputs'].items():
    assert pin(T / name) == h
normalization = j(E / 'normalization.json')
for path, h in normalization['inputs'].items():
    assert pin(path) == h
    inputs[path] = h
for run in normalization['runs']:
    assert run['returncode'] == 0
    for suffix, key in [('.ys','script_sha256'),('.log','log_sha256')]:
        file = E / (run['name'] + suffix)
        assert pin(file)['sha256'] == run[key]
        inputs[str(file)] = pin(file)
    compressed = E / (run['name'] + '.json.gz')
    assert pin(compressed)['sha256'] == run['expanded_json']['lossless_gzip_sha256']
    inputs[str(compressed)] = pin(compressed)
    with gzip.open(compressed, 'rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == run['expanded_json']['sha256']

spec = importlib.util.spec_from_file_location('tx05_review_kernel', B / 'proof05/compare.py')
kernel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)
kernel.ROOT = E
recomputed = kernel.compare(kernel.read('gold'), kernel.read('gate'))
original = j(E / 'equivalence.json')
assert all(original[k] == v for k, v in recomputed.items())
assert recomputed['states'] == 3850 and recomputed['matched'] == recomputed['targets'] == 11680 and not recomputed['mismatches']
binding_spec = importlib.util.spec_from_file_location('tx05_saved_binding', B / 'proof_gate_repair05.py')
binding_module = importlib.util.module_from_spec(binding_spec)
binding_spec.loader.exec_module(binding_module)
binding_record = binding_module.verify_binding(E)
assert binding_record['before_inputs'] == binding_record['after_inputs']
for path, expected in binding_record['before_inputs'].items():
    assert pin(path) == expected
    inputs[path] = expected
inputs[str(E / 'proof-execution-binding.json')] = pin(E / 'proof-execution-binding.json')
mutations = j(E / 'mutation-controls.json')
assert len(mutations['controls']) == 10 and all(c['status'].startswith('REJECTED_') for c in mutations['controls'])

sdc = (D / 'routed.sdc').read_text()
assert 'create_clock -name development_clock -period 4.0000' in sdc
assert not re.search(r'^set_(?:false_path|multicycle_path)', sdc, re.M)
before = (P / 'repaired.sdc').read_text()
def constraint_lines(s):
    return [l for l in s.splitlines() if l and not l.startswith('#')]
assert constraint_lines(sdc) == constraint_lines(before)
for p in [Path(__file__), B / 'proof05/compare.py', B / 'proof05/mutations.py', B / 'proof_gate_repair05.py', P / 'repaired.v', E / 'equivalence.json', E / 'mutation-controls.json', E / 'normalization.json', T / 'result.json', old]:
    inputs[str(p)] = pin(p)
record = {
    'status': 'REVIEWED_TX05_ZERO_ROUTER_DRC_AND_FUNCTION__MEASURED_NOMINAL_TIMING',
    'nominal_all_cell_corners_pass': {kind: all(v[kind] >= 0 for v in slacks.values()) for kind in ('setup', 'hold', 'recovery', 'removal')},
    'physical_acceptance': False, 'qualified_rc': False,
    'nominal_rc_cell_corner_slack_ns': slacks, 'nominal_prior_and_improvement': {'prior':prior_slacks,'delta_ns':delta},
    'unannotated_output_analysis': {'reported': 150, 'partially_unannotated': 0, 'all_output_pins_unconnected_CTS_loads': True, 'all150_input_pins_present_on_correct_extracted_clock_nets': True, 'instances': loads},
    'spef_numeric_census': count, 'SS_three_worst_setup_paths': paths,
    'canonical_binary_kernel_replay': recomputed,
    'preserved_original_fault_controls': 10, 'port_XML_cases_recounted': 3,
    'inputs_rehashed': inputs,
    'runtime_warnings_retained': [l for l in (T / 'simulation.log').read_text().splitlines() if 'Unexpected sys.executable' in l],
    'scope': 'Independent saved-output review, complete SPEF numeric/clock-load binding census, all declared DRT/RC inputs/outputs rehashed, three saved portXML cases, fresh replay of existing canonical binary kernel on unchanged native-expanded JSONs. No new OpenROAD/Icarus/SAT run or independent proof algorithm; mutation controls inspected, not rerun. Unchanged4ns/IO constraints. Nominal sameRC at all cell corners is unqualified; All measured setup, hold, recovery and removal values are retained without a predetermined pass result. No fullchip/PDN/foundryDRC/PHY acceptance.',
}
assert all(pin(path) == h for path,h in inputs.items())
(O / 'review.json').write_text(json.dumps(record, indent=2) + '\n')
print({'slacks': slacks, 'spef': count, 'review': pin(O / 'review.json')})
