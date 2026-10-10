# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "phase_slacks", Path(__file__).resolve().parents[2] / "scripts/read_opensta_phase_slacks.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def path(group, slack, kind="max"):
    return f"""Startpoint: launch/Q
Endpoint: capture/D
Path Group: {group}
Path Type: {kind}
Corner: slow
  {slack} slack (VIOLATED)
"""


def test_worst_group_is_not_first_group():
    result = MODULE.parse_phases("PHASE_before_slow_max\n" + path("cpu", -.1) + path("pcie", -2.4))
    assert result["before_slow_max"]["worst_slack_ns"] == -2.4
    assert result["before_slow_max"]["path_count"] == 2


def test_hold_and_phase_boundaries():
    text = "PHASE_before_slow_min\n" + path("cpu", .2, "min") + path("ethernet", -.21, "min")
    text += "PHASE_after_slow_min\n" + path("cpu", .1, "min") + path("ethernet", .01, "min")
    result = MODULE.parse_phases(text)
    assert result["before_slow_min"]["worst_slack_ns"] == -.21
    assert result["after_slow_min"]["worst_slack_ns"] == .01


def test_corner_markers():
    result = MODULE.parse_phases("CORNER_slow_max\n" + path("pcie", -2.4), "CORNER")
    assert result["slow_max"]["worst_slack_ns"] == -2.4


@pytest.mark.parametrize("text", [
    "no phases", "PHASE_empty\n",
    "PHASE_a\n" + path("cpu", .2).replace("  0.2 slack (VIOLATED)\n", "") + "PHASE_b\n" + path("pcie", -.1),
    "PHASE_a\n" + path("cpu", .2) + "PHASE_a\n" + path("pcie", -.1),
    "PHASE_a\n" + path("cpu", "nan"),
    "PHASE_a\n" + path("cpu", "inf"),
    "PHASE_a\n" + path("cpu", .1) + path("pcie", -.1, "min"),
    "PHASE_a\n" + path("cpu", .1).replace("Path Group: cpu\n", ""),
    "PHASE_a\n" + path("cpu", .1) + "  -.2 slack (VIOLATED)\n",
])
def test_rejects_incomplete_ambiguous_or_nonfinite_report(text):
    with pytest.raises(ValueError):
        MODULE.parse_phases(text)
