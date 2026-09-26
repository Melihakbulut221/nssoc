# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A load conversion must be independent of other loads and cover every pin."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'check_sta_load_slew', Path(__file__).resolve().parents[2] / 'hw/soc/flow/check_sta_load_slew.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def path(bit, slew):
    return (f' 64 0.17 1.5 0.8 2.8 ^ b/X (sg13g2_buf_1)\n'
            f' {slew} 0.0 2.8 ^ m/A_BM[{bit}] (macro)\n')


def test_equal_loads_receive_one_threshold_conversion():
    report = ''.join(path(i, 2.0) for i in range(64))
    result = probe.inspect_report(report, 64, 4/3)
    assert result['status'] == 'PASS'
    assert result['maximum_conversion_error_ns'] == 0


def test_cumulative_conversion_is_rejected():
    report = ''.join(path(i, 1.5 * (4/3)**(i+1)) for i in range(64))
    assert probe.inspect_report(report, 64, 4/3)['status'] == 'FAIL'


@pytest.mark.parametrize('bits', [[0], [0, 0], [0, 2]])
def test_missing_duplicate_and_unexpected_endpoints_are_rejected(bits):
    with pytest.raises(ValueError, match='load paths'):
        probe.inspect_report(''.join(path(i, 2) for i in bits), 2, 4/3)


def test_library_thresholds_are_used_without_model_changes(tmp_path):
    lib = tmp_path / 'lib.lib'
    text = ('slew_lower_threshold_pct_rise : 30;\n'
            'slew_upper_threshold_pct_rise : 70;\n'
            'slew_derate_from_library : 0.5;\n')
    lib.write_text(text)
    assert probe.conversion(lib) == 80
    assert lib.read_text() == text
    lib.write_text(text.replace('0.5', '0'))
    with pytest.raises(ValueError, match='Invalid threshold'):
        probe.conversion(lib)
