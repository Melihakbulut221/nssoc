# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Detect omitted pin-node wire capacitance without confusing it with Liberty C."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'audit_estimated_spef', ROOT / 'hw/soc/flow/audit_estimated_spef.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample(tmp_path, body, unit='1 PF', pin_cap='NONE'):
    path = tmp_path / 'estimate.spef'
    path.write_text(f'*DESIGN_FLOW "PIN_CAP {pin_cap}"\n*C_UNIT {unit}\n' + body)
    return path


def test_detects_actual_exporter_pin_node_omission(tmp_path):
    # The six-decimal D_NET total includes a pin stub omitted from *CAP.
    path = sample(tmp_path, '*D_NET n 0.0162618\n*CAP\n'
                  '1 n:1 0.000166584\n2 n:2 0.00526556\n3 n:3 0.00526556\n'
                  '4 n:4 0.00243534\n5 n:5 0.00269875\n*END\n')
    result = module.audit(path)
    assert result['status'] == 'FAIL'
    assert result['inconsistent_nets'] == 1
    assert result['difference_pf'] == pytest.approx(0.000430006)
    path.write_text(path.read_text().replace('*END', '6 cell:A 0.000430006\n*END'))
    assert module.audit(path)['status'] == 'PASS within scope'


@pytest.mark.parametrize('unit,declared,cap', [('1 PF', '.003', '.003'),
                                             ('1 FF', '3', '3'),
                                             ('0.1 PF', '.03', '.03')])
def test_units_and_zero_capacitance_nets(tmp_path, unit, declared, cap):
    path = sample(tmp_path, f'*D_NET n {declared}\n*CAP\n1 cell:A {cap}\n*END\n'
                  '*D_NET zero 0\n*CAP\n1 zero:1 0\n*END\n', unit=unit)
    result = module.audit(path)
    assert result['nets'] == 2
    assert result['serialized_total_pf'] == pytest.approx(.003)
    assert result['status'] == 'PASS within scope'


@pytest.mark.parametrize('body', ['', '*D_NET n 1\n*CAP\n1 n:1 1\n',
                                '*D_NET n 1\n*CAP\n1 n:1 other:2 1\n*END\n',
                                '*D_NET n 1\n*CAP\n1 n:1 NaN\n*END\n',
                                '*D_NET n 1\n*CAP\n1 n:1 -1\n*END\n',
                                '*D_NET n 1\n*D_NET m 1\n*END\n'])
def test_unsupported_or_incomplete_data_is_rejected(tmp_path, body):
    with pytest.raises(ValueError):
        module.audit(sample(tmp_path, body))


def test_pin_cap_included_is_outside_this_check(tmp_path):
    with pytest.raises(ValueError, match='PIN_CAP NONE'):
        module.audit(sample(tmp_path, '*D_NET n 0\n*END\n', pin_cap='INPUT_OUTPUT'))


def test_six_digit_rounding_is_not_an_omission(tmp_path):
    result = module.audit(sample(tmp_path, '*D_NET n 0.123457\n*CAP\n'
                                '1 n:1 0.1\n2 cell:A 0.0234568\n*END\n'))
    assert result['status'] == 'PASS within scope'
