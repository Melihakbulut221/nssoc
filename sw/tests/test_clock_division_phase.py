# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "clock_phase", Path(__file__).resolve().parents[2] / "scripts/check_clock_division_phase.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run(source, output):
    return MODULE.check_division(source, output, factor=4, start_s=8, stop_s=40, minimum_intervals=7)


def test_crossing_phase_origin_does_not_look_like_missing_clock():
    source = list(range(45))
    output = [4 * i + .99 + (.02 if i % 2 else 0) for i in range(11)]
    exact = [sum(a <= t < b for t in source) for a, b in zip(output[:-1], output[1:])]
    assert set(exact) == {3, 5}
    result = run(source, output)
    assert result["passed"] and result["anchor_s"] < 8
    assert {r["cycle_increment"] for r in result["intervals"]} == {4}
    assert not result["adaptive_phase_fit"]


@pytest.mark.parametrize("fault", ["missing_input", "extra_input", "missing_output", "extra_output", "actual_three_five", "phase_jump", "wrong_factor"])
def test_actual_clock_errors_are_rejected(fault):
    source = list(range(45))
    output = [4 * i + .99 for i in range(11)]
    if fault == "missing_input":
        source.remove(19)
    elif fault == "extra_input":
        source.append(19.5)
        source.sort()
    elif fault == "missing_output":
        output.pop(5)
    elif fault == "extra_output":
        output.append(23)
        output.sort()
    elif fault == "actual_three_five":
        output[5] -= 1
    elif fault == "phase_jump":
        output[5] += .6
    elif fault == "wrong_factor":
        output = [3 * i + .99 for i in range(14)]
    assert not run(source, output)["passed"]


@pytest.mark.parametrize("fault", ["duplicate", "nonfinite", "no_anchor", "unbracketed"])
def test_incomplete_observations_are_not_accepted(fault):
    source = list(range(45))
    output = [4 * i + .99 for i in range(11)]
    if fault == "duplicate":
        source[20] = source[19]
    elif fault == "nonfinite":
        source[20] = float("nan")
    elif fault == "no_anchor":
        output = output[2:]
    elif fault == "unbracketed":
        source = source[:30]
    with pytest.raises(ValueError):
        run(source, output)
