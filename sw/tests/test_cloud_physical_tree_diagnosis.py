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
