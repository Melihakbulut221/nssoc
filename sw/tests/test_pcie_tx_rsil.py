# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete native resistor waveforms and preserve independent corners."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import characterize_pcie_tx_rsil as rsil


def test_all_hbt_and_resistor_corners_are_crossed_independently():
    cases = rsil.cases()
    assert len(cases) == len({c['name'] for c in cases}) == 97
    positive = [c for c in cases if c['name'].startswith('hbt_')]
    assert len(positive) == 81
    for corner in ('hbt_typ', 'hbt_bcs', 'hbt_wcs'):
        assert {c['resistor'] for c in positive if c['corner'] == corner} == {'res_typ', 'res_bcs', 'res_wcs'}
    assert {c['fault'] for c in cases if c['fault']} == {'no_bias', 'swapped', 'overload'}


@pytest.mark.parametrize('defect', ['truncated', 'nonfinite', 'missing_column', 'wrong_header', 'duplicate_time', 'gap'])
def test_load_monitor_rejects_corrupt_or_partial_simulation(tmp_path, defect):
    case = rsil.cases()[0]
    header = ['time', *rsil.load_vectors(case)]
    # A complete monitor interval at the permitted 1ps resolution.
    rows = [[i*1e-12, .01, .002, 1.5, .1] for i in range(33751)]
    if defect == 'truncated': rows = rows[:-1]
    elif defect == 'nonfinite': rows[100][2] = float('nan')
    elif defect == 'missing_column': rows[100].pop()
    elif defect == 'wrong_header': header[-1] = 'wrong'
    elif defect == 'duplicate_time': rows[100][0] = rows[99][0]
    else: rows.pop(100)
    path = tmp_path/'loads.dat'
    path.write_text(' '.join(header)+'\n'+'\n'.join(' '.join(map(str, row)) for row in rows)+'\n')
    with pytest.raises(ValueError): rsil.load_measure(path, case)


def test_load_monitor_includes_both_branches_and_uses_absolute_current(tmp_path):
    case = rsil.cases()[0]
    rows = [[i*1e-12, .01, -.014, 1.5, 2.5] for i in range(33751)]
    path = tmp_path/'loads.dat'
    path.write_text(' '.join(['time', *rsil.load_vectors(case)])+'\n'+
                    '\n'.join(' '.join(map(str, row)) for row in rows)+'\n')
    assert rsil.load_measure(path, case) == [dict(peak_absolute_branch_current_a=.014,
                                               maximum_model_temperature_rise_k=2.5)]
