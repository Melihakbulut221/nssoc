# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent clock fixtures expose drift hidden by wrapped phase."""
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review_pcie_feedback_response import analyze  # noqa: E402


def waves(feedback_hz=100e6, phase=0.23):
    time = np.linspace(0, 1e-6, 200001)
    ref = 1.25 + np.sin(2 * np.pi * (100e6 * time - 0.1))
    fb = 1.25 + np.sin(2 * np.pi * (feedback_hz * time - phase))
    oscillator = np.sin(2 * np.pi * (8e9 * time - 0.17))
    return np.column_stack([time, ref, fb, oscillator, -oscillator, np.full(len(time), .7)])


def test_constant_offset_is_stationary():
    result = analyze(waves(), [200e-9, 900e-9])
    assert abs(result["feedback_frequency_error_ppm"]) < 1e-6
    assert abs(result["phase"]["change_cycles"]) < 1e-9
    assert abs(result["phase"]["unwrapped_cycles"][0]) > .1
    assert result["vco_to_feedback_ratio"] == pytest.approx(80, rel=1e-8)
    assert result["control_voltage"]["mean_v"] == pytest.approx(.7)


@pytest.mark.parametrize("frequency,sign", [(95e6, -1), (105e6, 1)])
def test_multiple_cycles_of_drift_are_not_wrapped(frequency, sign):
    result = analyze(waves(frequency), [200e-9, 900e-9])
    assert result["feedback_frequency_error_ppm"] == pytest.approx(sign * 50000, abs=.01)
    assert sign * result["phase"]["change_cycles"] > 3
    assert result["phase"]["slope_cycles_per_s"] == pytest.approx(sign * 5e6, rel=1e-5)


def test_missing_feedback_edges_rejected():
    samples = waves()
    samples[:, 2] = 0
    with pytest.raises(ValueError, match="insufficient feedback edges"):
        analyze(samples, [200e-9, 900e-9])


def test_incomplete_window_rejected():
    with pytest.raises(ValueError, match="window coverage"):
        analyze(waves(), [200e-9, 2e-6])


def test_nonmonotonic_time_rejected():
    samples = waves()
    samples[1024, 0] = samples[1023, 0]
    with pytest.raises(ValueError, match="time order"):
        analyze(samples, [200e-9, 900e-9])
