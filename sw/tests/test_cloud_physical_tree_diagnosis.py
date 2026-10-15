# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject biased time statistics and comparisons of different experiments."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

path = Path(__file__).resolve().parents[2] / 'scripts/analyze_cloud_physical_tree.py'
spec = importlib.util.spec_from_file_location('physical_tree_diagnosis', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_nonuniform_sampling_and_exact_window_edges():
    t = np.array([0, 1, 3, 4, 5, 6, 33, 35]) * 1e-9
    y = 2 * t / 1e-9 + 7
    result = m.stats(t, y)
    assert result['minimum'] == pytest.approx(11)
    assert result['maximum'] == pytest.approx(75)
    assert result['time_mean'] == pytest.approx(43)
    assert result['time_mean'] != pytest.approx(y.mean())


@pytest.mark.parametrize('t,y', [
    ([0, 2, 34], [0, np.nan, 1]),
    ([0, 2, 2, 34], [0, 1, 1, 1]),
    ([0, 34, 2], [0, 1, 1]),
    ([3, 34], [0, 1]),
    ([0, 33], [0, 1]),
])
def test_reject_incomplete_or_invalid_captures(t, y):
    with pytest.raises(AssertionError):
        m.stats(np.array(t) * 1e-9, y)


def test_reject_changed_source_bits_or_device_inventory():
    with pytest.raises(AssertionError):
        m.pair({'contract_identity': [0, 1]}, {'contract_identity': [1, 0]})
    with pytest.raises(AssertionError):
        m.pair({'contract_identity': [], 'devices': {'q': {}}},
               {'contract_identity': [], 'devices': {}})


def test_two_evidence_schemas_bind_same_original_bits_and_reject_conflict():
    a={'source_bits_sha256':'actual-source-digest'}
    assert m.source_bits_hash({'signals':a})==m.source_bits_hash({'review':{'signals':a}})
    with pytest.raises(AssertionError):m.source_bits_hash({})
    with pytest.raises(AssertionError):m.source_bits_hash({'signals':a,'review':{'signals':{'source_bits_sha256':'different'}}})


def test_reject_pair_from_different_physical_model_sources():
    with pytest.raises(AssertionError):
        m.pair({'contract_identity':[], 'physical_sources':{'final':'original'}},
               {'contract_identity':[], 'physical_sources':{'final':'unrelated'}})


@pytest.mark.parametrize('study', ['local_tail_hot', 'cascade16_local_tail_hot'])
def test_local_tail_selection_binds_exact_run_corner_model_and_sources(study):
    import copy
    import json
    evidence = json.loads((path.parents[1] / 'docs/evidence/cloud-closure-continuation-20261013.json').read_text())
    records = m.local_tail_records(evidence, study)
    assert len(records) == 2 and {r['model'] for r in records} == {'compact', 'wire'}
    def changed(mutator):
        other = copy.deepcopy(evidence)
        selected = m.local_tail_records(other, study)
        mutator(other, selected)
        with pytest.raises(AssertionError):
            m.local_tail_records(other, study)
    changed(lambda e, r: r[0].update(condition='cold_high'))
    changed(lambda e, r: r[0].update(streams=32))
    changed(lambda e, r: r[0]['physical_prestage_scope'].update(profile='power_trunks'))
    changed(lambda e, r: r[0]['physical_final_scope'].update(mode=r[1]['prestage']))
    changed(lambda e, r: r[0]['review']['signals'].update(source_bits_sha256='changed-bits'))
    changed(lambda e, r: e['completed_local_tail_comparison']['cases'].append(copy.deepcopy(r[0])))


@pytest.mark.parametrize('study', ['supply_feed_hot', 'supply_feed_cold'])
def test_supply_feed_selection_rejects_wrong_corner_clock_run_and_native_models(study):
    import copy
    import json
    evidence = json.loads((path.parents[1] / 'docs/evidence/cloud-closure-continuation-20261013.json').read_text())
    records = m.supply_feed_records(evidence, study)
    assert len(records) == 2
    def changed(mutator):
        other = copy.deepcopy(evidence)
        selected = m.supply_feed_records(other, study)
        mutator(other, selected)
        with pytest.raises(AssertionError):
            m.supply_feed_records(other, study)
    changed(lambda e, r: r[0].update(condition='nominal'))
    changed(lambda e, r: r[0].update(run=38409346107))
    changed(lambda e, r: r[0].update(clock_reference='baseline'))
    changed(lambda e, r: r[0]['physical_prestage_scope'].update(profile='kelvin_dense_wide'))
    changed(lambda e, r: r[0]['physical_final_scope'].update(profile='v8_kelvin_local_return'))
    changed(lambda e, r: r[0]['review']['signals'].update(source_bits_sha256='changed-bits'))
    changed(lambda e, r: e['combined_supply_feed_loaded_study']['cases'].append(copy.deepcopy(r[0])))


@pytest.mark.parametrize('study', ['local_internal_hot', 'low_critical_hot', 'low_critical_cold', 'v9_cascade158_hot', 'v8_low_selects_hot'])
def test_routing_pair_rejects_foreign_wave_and_scope(study):
    import copy
    import json
    evidence = json.loads((path.parents[1] / 'docs/evidence' / m.ROUTING_STUDIES[study][3]).read_text())
    assert len(m.routing_records(evidence, study)) == 2
    corruptions = [
        lambda r: r[0].update(run=38417305677),
        lambda r: r[0].update(condition='nominal'),
        lambda r: r[0].update(streams=32),
        lambda r: r[0].update(clock_reference='baseline'),
        lambda r: r[0]['physical_prestage_scope'].update(profile='kelvin_supply_direct'),
        lambda r: r[0]['physical_final_scope'].update(profile='v8_kelvin_compact_internal'),
        lambda r: r[0]['physical_final_scope'].update(mode=r[1]['prestage']),
        lambda r: r[0]['review']['signals'].update(source_bits_sha256='foreign-bits'),
        lambda r: r.append(copy.deepcopy(r[0])),
    ]
    for corrupt in corruptions:
        other = copy.deepcopy(evidence)
        corrupt(other['cases'])
        with pytest.raises(AssertionError):
            m.routing_records(other, study)


def test_paired_clock_feed_binding_rejects_changed_native_feed():
    common={'clock_reference':'stiff65','clock_reference_sha256':'same-offset',
            'clock_feed_sha256':'original-feed','clock_feed_subckt':'native-feed'}
    changed=dict(common,clock_feed_sha256='different-native-feed')
    with pytest.raises(AssertionError):
        m.pair({'contract_identity':common},{'contract_identity':changed})


@pytest.mark.parametrize('study', ['v8_tc_hot','v8_tc_hot_res_bcs'])
def test_tc_feedback_pair_rejects_wrong_geometry_bias_or_corner(study):
    import copy
    import json
    source=json.loads((path.parents[1]/'docs/evidence/pcie-final-v11-kelvin-low-ports-loads-shunts-series-composition-20261014.json').read_text())
    actual=source['feedback_temperature_compensation_20261014']['actual_geometry_followup']
    corner=m.TC_STUDIES[study]
    # Selector-only positive fixture; no fabricated capture is sent to read_case.
    fixture=copy.deepcopy(source)
    base=fixture['feedback_temperature_compensation_20261014']['actual_geometry_followup']
    pin=copy.deepcopy(actual['cases'][corner])
    pin['result']['prestage']='physical_compact'
    for key in ('physical_prestage_scope','physical_final_scope'):
        pin['result'][key]['mode']='physical_compact'
    base['hot_compact_controls']={'run':38519483522,'cases':{corner:pin}}
    assert len(m.feedback_tc_records(fixture,study))==2
    for key,value in [('condition','nominal'),('pre_bias','native_res'),('streams',32),
                      ('clock_reference','baseline'),('diagnostic_mutation',{})]:
        broken=copy.deepcopy(fixture)
        r=broken['feedback_temperature_compensation_20261014']['actual_geometry_followup']['hot_compact_controls']['cases'][corner]['result']
        r[key]=value
        with pytest.raises(AssertionError):m.feedback_tc_records(broken,study)
    broken=copy.deepcopy(fixture)
    r=broken['feedback_temperature_compensation_20261014']['actual_geometry_followup']['hot_compact_controls']['cases'][corner]['result']
    r['pre_bias_feedback_scope']['sha256']='foreign-bias'
    with pytest.raises(AssertionError):m.feedback_tc_records(broken,study)


@pytest.mark.parametrize('fmt', ['wrdata_text', 'native_binary'])
def test_full_capture_reader_preserves_original_times_and_vector_identity(tmp_path, monkeypatch, fmt):
    import gzip, hashlib
    monkeypatch.syspath_prepend(str(path.parent))
    t = np.array([0.0, 17e-9, 34e-9])
    op = np.array([0.25, -0.125, 0.75])
    on = np.array([-0.5, 0.5, 0.125])
    contract = dict(vectors=['v(op)', 'v(on)'], condition=dict(step_ps=17000))
    if fmt == 'native_binary':
        header = ('Title: fixture\nDate: fixture\nPlotname: Transient Analysis\n'
                  'Flags: real\nNo. Variables: 3\nNo. Points: 3\nVariables:\n'
                  '0 time time\n1 v(on) voltage\n2 v(op) voltage\nBinary:\n')
        raw = header.encode() + np.column_stack((t, on, op)).astype('<f8').tobytes()
    else:
        raw = ('time v(op) v(on)\n' + '\n'.join(
            ' '.join(format(x, '.17g') for x in row) for row in zip(t, op, on)) + '\n').encode()
    (tmp_path/'wave.dat.gz').write_bytes(gzip.compress(raw))
    record = dict(format=fmt, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    values = m.capture_values(tmp_path, contract, record, ['time','v(op)','v(on)'])
    for name, expected in [('time',t),('v(op)',op),('v(on)',on)]:
        assert np.array_equal(values[name], expected)
    if fmt == 'native_binary':
        # A rehashed truncated original still fails native row/column coverage.
        (tmp_path/'wave.raw').unlink()
        raw = raw[:-8]
        (tmp_path/'wave.dat.gz').write_bytes(gzip.compress(raw))
        record.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with pytest.raises(AssertionError):
            m.capture_values(tmp_path, contract, record, ['time','v(op)','v(on)'])
