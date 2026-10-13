# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import pytest

p = Path(__file__).resolve().parents[2] / 'scripts/analyze_cloud_metal_resistance.py'
s = importlib.util.spec_from_file_location('metal_resistance', p)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)


def test_shared_series_and_parallel_paths_obey_kcl_and_energy():
    edges = [('shared', 'g', 'a', 2), ('left', 'a', 'b', 6), ('right', 'a', 'b', 3)]
    result = m.resistance(edges, 'g', ['a', 'b'])
    assert result['terminals']['a']['effective_ohms'] == pytest.approx(2)
    assert result['terminals']['b']['effective_ohms'] == pytest.approx(4)
    assert result['terminals']['b']['dissipated_w_at_1a'] == pytest.approx(4)
    assert result['terminals']['b']['largest_power_edges'][0]['name'] == 'shared'
    pair = next(p for p in result['terminal_pairs'] if p['nodes'] == ['a', 'b'])
    assert pair['effective_ohms'] == pytest.approx(2)
    # Moving the arbitrary calculation reference cannot change pair resistance.
    reversed_reference = m.resistance(edges, 'a', ['g', 'b'])
    pair = next(p for p in reversed_reference['terminal_pairs'] if p['nodes'] == ['g', 'b'])
    assert pair['effective_ohms'] == pytest.approx(4)


def test_open_and_parallel_faults_change_measured_resistance():
    base = [('a', 'g', 't', 8), ('b', 'g', 't', 8)]
    assert m.resistance(base, 'g', ['t'])['terminals']['t']['effective_ohms'] == pytest.approx(4)
    assert m.resistance(base[:1], 'g', ['t'])['terminals']['t']['effective_ohms'] == pytest.approx(8)
    with pytest.raises(AssertionError):
        m.resistance([('a', 'g', 'x', 8)], 'g', ['t'])


@pytest.mark.parametrize('value', [0, -1, float('nan'), float('inf')])
def test_reject_nonphysical_resistance(value):
    with pytest.raises(AssertionError):
        m.resistance([('a', 'g', 't', value)], 'g', ['t'])


def test_reject_duplicate_devices_and_unknown_native_model():
    for text in ('.subckt cell a b\nR1 a b 1\nR1 a b 2\n.ends cell',
                 '.subckt cell a b\nX1 a b unknown\n.ends cell'):
        with pytest.raises(AssertionError):
            m.parse(text)


COMPACT = '.subckt cell avdd avss\nX1 avdd internal sub rppd w=1u l=2u\nX2 internal avss sub rppd w=1u l=3u\n.ends cell\n'
WIRE = '.subckt cell avdd avss\nR1 avdd a 10\nR2 b c 20\nR3 d avss 30\nC1 a b 1e-15\nC2 c avss 2e-15\nX1 a b sub rppd w=1u l=2u\nX2 c d sub rppd w=1u l=3u\n.ends cell\n'


def test_class_reduction_preserves_devices_caps_and_unselected_resistance():
    changed, report = m.reduce_conductor_class(COMPACT, WIRE, 'internal')
    assert changed == WIRE.replace('R2 b c 20', 'R2 b c 0.20000000000000001')
    assert set(report['selected_resistors']) == {'R2'}
    assert report['selected_resistors']['R2']['conductor'] == 'internal'
    assert report['conductors'] == 3 and report['resistors'] == 3
    assert report['original_sha256'] != report['mutated_sha256']
    all_changed, all_report = m.reduce_conductor_class(COMPACT, WIRE, 'all')
    assert set(all_report['selected_resistors']) == {'R1','R2','R3'}
    assert m.parse(all_changed)[2][0][3] == pytest.approx(.1)


@pytest.mark.parametrize('fault', [
    WIRE.replace('R2 b c 20', 'R2 b c 20\nRshort a b 1'),
    WIRE.replace('R2 b c 20', 'R2 b z 20\nRopen c y 1'),
    WIRE.replace('R2 b c 20', 'R2 b c 20\nRextra z y 1'),
    WIRE.replace('w=1u l=2u', 'w=1u l=9u'),
    WIRE.replace('a b sub rppd', 'a b wrongbody rppd'),
])
def test_class_reduction_rejects_short_open_unanchored_parameter_and_body_faults(fault):
    with pytest.raises(AssertionError):
        m.reduce_conductor_class(COMPACT, fault, 'internal')


@pytest.mark.parametrize('factor', [0, -1, 1, 2, float('nan'), float('inf')])
def test_class_reduction_rejects_invalid_scale(factor):
    with pytest.raises(AssertionError):
        m.reduce_conductor_class(COMPACT, WIRE, 'internal', factor)


def test_class_reduction_rejects_missing_class():
    with pytest.raises(AssertionError, match='No metal resistors selected'):
        m.reduce_conductor_class(COMPACT, WIRE, 'outputs')


def test_native_capacitance_reference_is_preserved_and_never_a_metal_anchor():
    wire = WIRE.replace('.subckt cell avdd avss', '.subckt cell avdd avss wire_cref')
    wire = wire.replace('C2 c avss 2e-15', 'C2 c wire_cref 2e-15')
    changed, report = m.reduce_conductor_class(COMPACT, wire, 'internal')
    assert 'C2 c wire_cref 2e-15' in changed
    assert report['conductors'] == 3
    for corrupted in [wire.replace('R3 d avss 30', 'R3 d wire_cref 30'),
                      wire.replace('c d sub rppd', 'c d wire_cref rppd'),
                      wire.replace('wire_cref', 'unrecognized_extra_port'),
                      wire.replace('C2 c wire_cref 2e-15', 'C2 c avss 2e-15')]:
        with pytest.raises(AssertionError):
            m.reduce_conductor_class(COMPACT, corrupted, 'internal')


def mux_graph():
    devices = {}
    def add(base, collector, emitter, count):
        for i in range(count):
            devices[f'{base}-{i}'] = dict(model='npn13g2', nodes=[collector, base, emitter, 'body'])
    add('ap', 'n_qn', 'n_ea', 3)
    add('an', 'n_qp', 'n_ea', 3)
    add('bp', 'n_qn', 'n_eb', 3)
    add('bn', 'n_qp', 'n_eb', 3)
    add('sp', 'n_ea', 'n_tail', 2)
    add('sn', 'n_eb', 'n_tail', 2)
    add('iref', 'n_tail', 'avss', 2)
    devices['reference'] = dict(model='npn13g2', nodes=['iref','iref','avss','body'])
    return devices


def test_internal_roles_survive_extractor_node_and_device_renumbering():
    devices = mux_graph()
    original = m.canonical_internal_roles(devices)
    rename = {node: f'n_{i+39}' for i, node in enumerate(reversed(sorted(original)))}
    remapped = {f'X{i:04d}': dict(model=d['model'], nodes=[rename.get(n,n) for n in d['nodes']])
                for i, d in enumerate(reversed(list(devices.values())))}
    assert m.canonical_internal_roles(remapped) == {rename[n]: role for n, role in original.items()}
    assert set(original.values()) == {'qn','qp','ea','eb','tail'}


def test_internal_roles_reject_selector_crosswire_merged_net_and_missing_device():
    import copy
    graph = mux_graph()
    crossed = copy.deepcopy(graph); crossed['sp-0']['nodes'][0] = 'n_eb'
    merged = copy.deepcopy(graph)
    for d in merged.values(): d['nodes'] = ['n_ea' if n=='n_eb' else n for n in d['nodes']]
    missing = copy.deepcopy(graph); del missing['reference']
    unknown = copy.deepcopy(graph); unknown['ap-0']['nodes'][1] = 'unbound_base'
    for bad in [crossed, merged, missing, unknown]:
        with pytest.raises(AssertionError): m.canonical_internal_roles(bad)
