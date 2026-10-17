# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import audit_pcie_finite_field_v1 as m

MATRIX = [[1.4e-15, -.28e-15, -.28e-15],
          [-.28e-15, .96e-15, -.65e-15],
          [-.28e-15, -.65e-15, .96e-15]]


def test_exact_pass_is_diagnostic_only():
    r = m.matrix_checks(m.NAMES, MATRIX)
    assert r['finite_matrix_checks_pass'] and r['raw_exactly_symmetric']
    assert r['symmetric_part_positive_definite']
    assert not r['raw_matrix_was_modified']
    assert r['raw_matrix_F'] == MATRIX


def test_actual_baseline_reciprocity_failure_not_symmetrized():
    raw = [[1.39922e-15, -2.87176e-16, -2.8756e-16],
           [-2.89108e-16, 9.65544e-16, -6.5908e-16],
           [-2.89021e-16, -6.58924e-16, 9.65726e-16]]
    snapshot = copy.deepcopy(raw)
    r = m.matrix_checks(m.NAMES, raw)
    assert r['symmetric_part_positive_definite']
    assert not r['finite_matrix_checks_pass']
    assert not r['raw_reciprocity_within_limit']
    assert raw == snapshot == r['raw_matrix_F']


@pytest.mark.parametrize('bad', [0, 1e-16, float('nan'), float('inf'), True])
def test_bad_mutual_rejects(bad):
    x = copy.deepcopy(MATRIX)
    x[0][1] = bad
    with pytest.raises(ValueError):
        m.matrix_checks(m.NAMES, x)


def test_missing_and_reordered_names_reject():
    for names in [m.NAMES[:2], list(reversed(m.NAMES)), ['g1_subs', 'g2_A', 'g2_A']]:
        with pytest.raises(ValueError):
            m.matrix_checks(names, MATRIX)


def test_truncated_matrix_rejects():
    with pytest.raises(ValueError):
        m.matrix_checks(m.NAMES, MATRIX[:2])


def test_wrong_diagonal_and_dominance_reject():
    for v in [0, -1e-15, .1e-15]:
        x = copy.deepcopy(MATRIX)
        x[1][1] = v
        with pytest.raises(ValueError):
            m.matrix_checks(m.NAMES, x)


def test_small_asymmetry_preserved_and_checked():
    x = copy.deepcopy(MATRIX)
    x[0][1] *= 1.003
    r = m.matrix_checks(m.NAMES, x)
    assert r['finite_matrix_checks_pass'] and not r['raw_exactly_symmetric']
    assert r['raw_matrix_F'] == x


def test_threshold_never_adjusted_by_solver_tolerance():
    assert m.RECIPROCITY_LIMIT == .005
    with pytest.raises(ValueError, match='tolerance'):
        m.audit('', 0, .01)


@pytest.mark.parametrize('scale', [1e-100, 1e100])
def test_spd_diagnostic_scale_invariant(scale):
    r = m.matrix_checks(m.NAMES, [[v * scale for v in row] for row in MATRIX])
    assert r['finite_matrix_checks_pass']


def native_log(matrix=MATRIX, tolerance=.005):
    rows = '\n'.join(name + ' ' + ' '.join(str(v * 1e6) for v in row)
                     for name, row in zip(m.NAMES, matrix))
    return (f'Running FasterCap version 6.0.7\nAuto calculation with max error: {tolerance}\n'
            f'Capacitance matrix is:\nDimension 3 x 3\n{rows}\n'
            'Weighted Frobenius norm of the difference between capacitance (auto option): 0.0005\n'
            'Total allocated memory: 300 kilobytes\nTotal time: 0.5s (0s)\n')


@pytest.mark.parametrize('tolerance', [.005, .0025, .001])
def test_native_log_bridge(tolerance):
    result = m.audit(native_log(tolerance=tolerance), 0, tolerance)
    assert result['status'] == 'PASS_FINITE_MATRIX_DIAGNOSTICS_ONLY'
    assert not result['qualified_rc'] and not result['domain_convergence_proved']


@pytest.mark.parametrize('change', ['exit', 'truncated', 'warning', 'wrong_tolerance'])
def test_native_errors_not_excused_by_good_matrix(change):
    text = native_log()
    if change == 'truncated':
        text = text.split('Total allocated memory')[0]
    if change == 'warning':
        text = text.replace('Capacitance matrix is:', 'Warning: unknown error\nCapacitance matrix is:')
    with pytest.raises(ValueError):
        m.audit(text, 1 if change == 'exit' else 0,
                .0025 if change == 'wrong_tolerance' else .005)


def test_cli_real_failed_reciprocity_is_nonzero(tmp_path, monkeypatch):
    x = copy.deepcopy(MATRIX)
    x[0][1] *= 1.02
    log, out = tmp_path / 'native.log', tmp_path / 'audit.json'
    log.write_text(native_log(x))
    monkeypatch.setattr(sys, 'argv', ['audit', '--log', str(log), '--returncode', '0',
                                    '--solver-tolerance', '.005', '--out', str(out)])
    assert m.main() == 2
    assert 'FAIL_RAW_MATRIX' in out.read_text()
