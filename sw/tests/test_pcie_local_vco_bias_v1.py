# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bias diagnostic changes only the declared external source, never thresholds."""

from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import diagnose_pcie_local_vco_bias_v1 as m


@pytest.mark.parametrize("value", [0.4, 0.6])
def test_one_exact_voltage_value_changes(value):
    text = "title\nVs_vctrl VCTRL 0 PWL(0 0 500p 0.85)\nR1 a b 22\n"
    changed = m.change_control(text, value)
    assert changed.replace(f"500p {value})", "500p 0.85)") == text


@pytest.mark.parametrize(
    "text,value",
    [
        ("title", 0.4),
        ("Vs_vctrl VCTRL 0 PWL(0 0 500p 0.85)\n" * 2, 0.4),
        ("Vs_vctrl VCTRL 0 PWL(0 0 500p 0.85)", 0.85),
    ],
)
def test_missing_duplicate_or_undeclared_control_rejects(text, value):
    with pytest.raises(ValueError):
        m.change_control(text, value)


@pytest.mark.parametrize(
    "fault",
    ["lower", "upper", "current", "startup_upper", "no_crossing", "small_swing"],
)
def test_each_original_native_safety_or_clock_failure_remains_visible(fault):
    h = {
        str(i): dict(min_vce=0.6, max_vce=1.4, peak_abs_current_per_emitter_a=0.002)
        for i in range(30)
    }
    s = dict(rising_edges=48, minimum_differential_v=-0.4, maximum_differential_v=0.4)
    x = dict(hbt_bounds=h, full_time_max_vce=1.4, signals=[s])
    if fault == "lower":
        h["29"]["min_vce"] = 0.399
    if fault == "upper":
        h["29"]["max_vce"] = 1.601
    if fault == "current":
        h["29"]["peak_abs_current_per_emitter_a"] = 0.003001
    if fault == "startup_upper":
        x["full_time_max_vce"] = 1.601
    if fault == "no_crossing":
        s["rising_edges"] = 0
    if fault == "small_swing":
        s["maximum_differential_v"] = 0.299
    r = m.classify(x)
    assert not all(
        r[k]
        for k in [
            "postsettling_hbt_bounds_pass",
            "all_time_upper_vce_pass",
            "finite_output_clock_screen_pass",
        ]
    )
    if fault in ("lower", "upper", "current"):
        assert r["failed_hbts"] == [29]
