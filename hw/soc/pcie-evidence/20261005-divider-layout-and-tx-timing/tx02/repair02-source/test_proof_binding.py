# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual file mutation controls for the proof-binding gate, no fake DUT verdict."""
import gzip
import importlib.util
import json
from pathlib import Path
import sys
import pytest

METHOD = Path(__file__).resolve().parents[1] / 'proof_gate_repair02.py'


@pytest.fixture
def fixture(tmp_path):
    spec = importlib.util.spec_from_file_location('tested_proof_gate', METHOD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.B = tmp_path / 'methods'
    m.E = tmp_path / 'capture'
    m.NET = tmp_path / 'netlist.v'
    m.B.mkdir()
    m.E.mkdir()
    (m.B / 'proof02').mkdir()
    m.NET.write_text('tiny explicitly synthetic fixture netlist\n')
    m.EXPECTED_NET = m.pin(m.NET)
    for name in ['proof02/compare.py', 'proof02/mutations.py', 'postroute_repair02.py']:
        (m.B / name).write_text('synthetic fixture byte pin only\n')
    normalization = {'inputs': {str(m.NET): m.pin(m.NET)}, 'runs': []}
    for name in ('gold', 'gate'):
        raw = ('synthetic graph ' + name).encode()
        (m.E / (name + '.json.gz')).write_bytes(gzip.compress(raw))
        (m.E / (name + '.ys')).write_text('synthetic script\n')
        (m.E / (name + '.log')).write_text('synthetic log\n')
        import hashlib
        normalization['runs'].append({'name': name, 'returncode': 0, 'script_sha256': m.pin(m.E / (name + '.ys'))['sha256'], 'log_sha256': m.pin(m.E / (name + '.log'))['sha256'], 'expanded_json': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'lossless_gzip_sha256': m.pin(m.E / (name + '.json.gz'))['sha256']}})
    (m.E / 'normalization.json').write_text(json.dumps(normalization))
    eq = {'status': 'PASS_COMPLETE_STATE_TRANSITION_AND_OUTPUT_FUNCTION_EQUALITY', 'states': 3850, 'matched': 11680, 'targets': 11680, 'mismatches': []}
    (m.E / 'equivalence.json').write_text(json.dumps(eq))
    mutations = {'status': 'PASS_TEN_MEANINGFUL_EQUIVALENCE_KERNEL_CONTROLS', 'positive': eq, 'controls': [{'kind': k, 'status': 'REJECTED_SYNTHETIC_FIXTURE'} for k in m.KINDS]}
    (m.E / 'mutation-controls.json').write_text(json.dumps(mutations))
    for name in ('bound-compare.log', 'bound-mutations.log'):
        (m.E / name).write_text('synthetic fixture\n')
    inputs = {str(p): m.pin(p) for p in m.input_paths(m.E)}
    graphs = m.graph_pins(m.E)
    runtime = {'path': sys.executable, 'pin': m.pin(sys.executable)}
    record = {'status': 'PASS_ACTUAL_TX02_PROOF_AND_MUTATION_EXECUTION_BOUND', 'before_inputs': inputs, 'after_inputs': inputs, 'expanded_graphs_before': graphs, 'expanded_graphs_after': graphs, 'runtime_before': runtime, 'runtime_after': runtime, 'outputs': {n: m.pin(m.E / n) for n in ('equivalence.json', 'mutation-controls.json', 'bound-compare.log', 'bound-mutations.log')}, 'runs': [{'method': n, 'returncode': 0, 'command': [sys.executable, str(m.B / 'proof02' / n)]} for n in ('compare.py', 'mutations.py')]}
    (m.E / 'proof-execution-binding.json').write_text(json.dumps(record))
    return m


def test_consistent_synthetic_binding(fixture):
    assert fixture.verify_binding(fixture.E)['status'].startswith('PASS_')


@pytest.mark.parametrize('name', ['gate.json.gz', 'gold.json.gz', 'equivalence.json', 'mutation-controls.json', 'normalization.json', 'bound-compare.log'])
def test_real_file_mutation_is_rejected(fixture, name):
    path = fixture.E / name
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(AssertionError):
        fixture.verify_binding(fixture.E)


def test_same_size_success_from_other_proof_rejected(fixture):
    path = fixture.E / 'equivalence.json'
    data = json.loads(path.read_text())
    data['other_proof_with_same_counts'] = True
    path.write_text(json.dumps(data))
    with pytest.raises(AssertionError):
        fixture.verify_binding(fixture.E)


def test_changed_kernel_is_rejected(fixture):
    (fixture.B / 'proof02/compare.py').write_text('changed proof method\n')
    with pytest.raises(AssertionError):
        fixture.verify_binding(fixture.E)


def test_expanded_graph_mismatch_rejected_even_after_outer_pin_update(fixture):
    p = fixture.E / 'proof-execution-binding.json'
    data = json.loads(p.read_text())
    norm = fixture.E / 'normalization.json'
    n = json.loads(norm.read_text())
    n['runs'][1]['expanded_json']['sha256'] = '0' * 64
    norm.write_text(json.dumps(n))
    data['before_inputs'][str(norm)] = fixture.pin(norm)
    data['after_inputs'][str(norm)] = fixture.pin(norm)
    p.write_text(json.dumps(data))
    with pytest.raises(AssertionError):
        fixture.verify_binding(fixture.E)
