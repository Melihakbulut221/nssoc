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
