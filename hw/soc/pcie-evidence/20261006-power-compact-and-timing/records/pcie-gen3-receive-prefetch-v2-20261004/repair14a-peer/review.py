# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded read-only verification of completed RX14A outputs; no new native run."""
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import resource
import xml.etree.ElementTree as ET
from pathlib import Path

resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
R = Path.cwd()
B = R / "hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004"
O = Path(__file__).resolve().parent
N = Path('/dev/shm')
D = N / 'nssoc-rx-prefetch-v2-repair14a-drt-01'
X = N / 'nssoc-rx-prefetch-v2-repair14a-detailed-rc-01'
P = N / 'nssoc-rx-prefetch-v2-postroute-repair-14a'
E = N / 'nssoc-rx-prefetch-v2-repair14a-equivalence'
T = N / 'nssoc-rx-prefetch-v2-repair14a-physical-replay-01'


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
electrical_report = log.split('tns max ', 1)[1].split('\n', 1)[1].split('EXTRACTED_NOMINAL_RC_slow_max', 1)[0]
electrical_violations = electrical_report.count('(VIOLATED)')
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
old = B / 'repair13-peer/review.json'
delta = round(slacks['slow']['setup'] - j(old)['nominal_rc_cell_corner_slack_ns']['slow']['setup'], 6)
all_timing_positive = all(value >= 0 for corner in slacks.values() for value in corner.values())

# Every reported unannotated output belongs to an input-only CTS load.
unannotated = log.split('Found 78 unannotated drivers.\n')[1].split('Found 0 partially unannotated drivers.')[0].split()
assert len(unannotated) == 78 and {p.split('/')[0] for p in unannotated} == {f'clkload{i}' for i in range(78)}
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
assert ports['tests'] == {'passed': 6, 'failed': 0, 'skipped': 0}
cases = list(ET.parse(T / 'results.xml').iter('testcase'))
assert len(cases) == 6 and all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases)
for path, h in {**ports['inputs'], **ports['runtime']}.items():
    assert pin(path) == h
    inputs[path] = h
for name, h in ports['outputs'].items():
    assert pin(T / name) == h
normalization = j(E / 'normalization.json')
for path, h in normalization['inputs'].items():
    assert pin(path) == h
    inputs[path] = h
for run in normalization['runs']:
    compressed = E / (run['name'] + '.json.gz')
    assert pin(compressed)['sha256'] == run['expanded_json']['lossless_gzip_sha256']
    with gzip.open(compressed, 'rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == run['expanded_json']['sha256']

# Preserve and revalidate actual completed proof execution. No repeated proof run.
spec = importlib.util.spec_from_file_location('rx14a_saved_execution_gate', B / 'proof_gate_repair14a.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
binding = gate.verify_binding()
recomputed = j(E / 'equivalence.json')
mutations = j(E / 'mutation-controls.json')
assert recomputed['states'] == 1804 and recomputed['matched'] == recomputed['targets'] == 5443 and not recomputed['mismatches']
assert len(mutations['controls']) == 10 and all(c['status'].startswith('REJECTED_') for c in mutations['controls'])
for path in gate.input_paths():
    inputs[str(path)] = pin(path)
inputs[str(E / 'proof-execution-binding.json')] = pin(E / 'proof-execution-binding.json')
owned = j(T / 'owned-driver.json')
assert owned['status'] == 'PASS_EXACT_PROVED_RX14A_SIX_NATIVE_PORT_CASES'
assert owned['inputs'] == {path: pin(path) for path in owned['inputs']}
inputs.update(owned['inputs'])
compiled = T / 'sim/sim.vvp.gz'
assert pin(compiled) == owned['lossless_closed_program']['gzip']
with gzip.open(compiled, 'rb') as stream:
    h = hashlib.sha256()
    size = 0
    while data := stream.read(1024**2):
        h.update(data)
        size += len(data)
assert {'bytes': size, 'sha256': h.hexdigest()} == owned['lossless_closed_program']['raw']
inputs[str(compiled)] = pin(compiled)
inputs[str(T / 'owned-driver.json')] = pin(T / 'owned-driver.json')

sdc = (D / 'routed.sdc').read_text()
assert 'create_clock -name development_clock -period 4.0000' in sdc
assert not re.search(r'^set_(?:false_path|multicycle_path)', sdc, re.M)
before = (P / 'repaired.sdc').read_text()
def constraint_lines(s):
    return [l for l in s.splitlines() if l and not l.startswith('#')]
assert constraint_lines(sdc) == constraint_lines(before)
for p in [Path(__file__), B / 'eco-proof/compare.py', E / 'equivalence.json', E / 'mutation-controls.json', E / 'normalization.json', T / 'result.json', old]:
    inputs[str(p)] = pin(p)
record = {
    'status': 'REVIEWED_RX14A_ZERO_ROUTER_DRC_AND_FUNCTION__NOMINAL_TIMING_' + ('PASS' if all_timing_positive else 'FAIL'),
    'all_nominal_cell_corner_timing_nonnegative': all_timing_positive,
    'electrical_check_report': electrical_report, 'max_slew_cap_violations_reported': electrical_violations,
    'nominal_rc_cell_corner_slack_ns': slacks, 'SS_setup_improvement_vs13_ns': delta,
    'unannotated_output_analysis': {'reported': 78, 'partially_unannotated': 0, 'all_output_pins_unconnected_CTS_loads': True, 'all78_input_pins_present_on_correct_extracted_clock_nets': True, 'instances': loads},
    'spef_numeric_census': count, 'SS_three_worst_setup_paths': paths,
    'saved_canonical_binary_kernel_receipt_revalidated': recomputed,
    'preserved_original_fault_controls': 10, 'port_XML_cases_recounted': 6,
    'inputs_rehashed': inputs,
    'scope': 'Independent saved-output review, complete SPEF numeric/clock-load binding census, all declared DRT/RC inputs/outputs rehashed, six saved portXML cases, actual previous binary proof execution rebound to unchanged compressed/expanded native graphs and methods, compiled native program fully decompressed and checked. No repeated OpenROAD/Icarus/SAT/kernel execution by this review; saved mutation controls inspected, not rerun. Unchanged4ns/IO constraints. Nominal sameRC at all cell corners is unqualified; see actual timing flags. No fullchip/PDN/foundryDRC/PHY acceptance.',
}
(O / 'review.json').write_text(json.dumps(record, indent=2) + '\n')
print({'slacks': slacks, 'spef': count, 'review': pin(O / 'review.json')})
