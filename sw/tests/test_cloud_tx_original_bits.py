# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A delayed input-relative oracle must not hide an end-to-end serial error."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    'cloud_tx_data_driver', Path(__file__).resolve().parents[2] / 'scripts/cloud_tx_data_driver.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def fixture():
    bits = [1, 0, 1, 1, 0, 0, 1, 0]
    t = np.arange(0, 10.001, .01)
    index = np.clip(np.floor(t - 1).astype(int), 0, len(bits) - 1)
    diff = .24 * (2 * np.asarray(bits)[index] - 1)
    return bits, t, diff


def test_exact_original_bits_and_each_unchanged_phase():
    bits, t, diff = fixture()
    r = driver.original_bit_output_screen(t, diff / 2, -diff / 2, bits, 1, 1)
    assert r['passed'] and r['samples'] == 24
    assert r['minimum_margin_v'] == pytest.approx(.24)
    assert all(p['samples'] == 8 and p['wrong_sign_samples'] == 0 for p in r['phases'].values())


@pytest.mark.parametrize('fault', ['polarity', 'one_bit_delay', 'low_amplitude'])
def test_corruption_cannot_pass_as_input_relative_correctness(fault):
    bits, t, diff = fixture()
    if fault == 'polarity':
        diff = -diff
    elif fault == 'one_bit_delay':
        diff = np.interp(t - 1, t, diff)
    else:
        diff *= .25
    r = driver.original_bit_output_screen(t, diff / 2, -diff / 2, bits, 1, 1)
    assert not r['passed'] and r['below_100mv_samples'] > 0
    if fault == 'low_amplitude':
        assert r['wrong_sign_samples'] == 0
    else:
        assert r['wrong_sign_samples'] > 0


@pytest.mark.parametrize('fault', ['truncated', 'nonfinite', 'unordered'])
def test_invalid_capture_never_silently_interpolates_to_pass(fault):
    bits, t, diff = fixture()
    if fault == 'truncated':
        t, diff = t[:700], diff[:700]
    elif fault == 'nonfinite':
        diff[100] = np.nan
    else:
        t[100] = t[99]
    with pytest.raises(AssertionError):
        driver.original_bit_output_screen(t, diff / 2, -diff / 2, bits, 1, 1)


def test_half_cycle_contract_preserves_startup_stop_levels_and_edge_slew():
    source = 'PWL(\n+ 0 0\n+ 1e-9 1.2\n+ 2.25e-9 1.2\n+ 2.26e-9 0\n+ 34e-9 0)'
    actual = driver.half_cycle_launch(source, 2e-9, 34e-9, 125e-12)
    pairs = [tuple(map(float, line.lstrip('+ ').split())) for line in actual[4:-1].splitlines() if line.strip()]
    assert np.asarray(pairs) == pytest.approx(np.asarray([
        (0, 0), (1e-9, 1.2), (2.125e-9, 1.2), (2.135e-9, 0), (34e-9, 0)]), abs=1e-23)
    assert pairs[3][0] - pairs[2][0] == pytest.approx(10e-12, abs=1e-23)
