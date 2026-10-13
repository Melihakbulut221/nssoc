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
