# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_clock_trim_stream_v4 as m


def periodic():
    t = np.linspace(0, 12e-9, 24001)
    c = np.sin(2 * np.pi * 8e9 * t)
    d = {
        f"state{i}": 10 + 0.05 * np.sin(2 * np.pi * 8e9 * t + i * 0.2)
        for i in range(53)
    }
    return t, c, d


def test_all53_stable_periodic_envelopes_with_arbitrary_phase_pass():
    t, c, d = periodic()
    r = m.envelopes(t, c, d, 12e-9)
    assert r["pass_envelope_screen"] and len(r["thermal_nodes"]) == 53
    assert (
        r["rate_limit_k_per_ns"] == 0.01 and r["nonincrease_tolerance_k_per_ns"] == 1e-5
    )
    assert r["cycles"] >= 60 and r["declared_window_s"] == [12e-9 - 8e-9, 12e-9]
    assert "not full phase-profile stationarity" in r["scope"]


@pytest.mark.parametrize(
    "fault",
    ["growing", "late_growing", "mean_drift", "late_mean", "amplitude_exponential"],
)
def test_real_growth_cannot_hide_in_zero_cycle_mean(fault):
    t, c, d = periodic()
    ns = t * 1e9
    if fault == "growing":
        d["state52"] = 10 + (0.05 + 0.05 * ns) * c
    elif fault == "late_growing":
        d["state52"] = 10 + (0.05 + 0.05 * np.maximum(ns - 10, 0)) * c
    elif fault == "mean_drift":
        d["state52"] += 0.02 * ns
    elif fault == "late_mean":
        d["state52"] += 0.04 * np.maximum(ns - 10, 0)
    else:
        d["state52"] = 10 + (0.05 + 0.00001 * np.exp(ns)) * c
    if fault == "growing":
        legacy = {"checks": {"final_four_frequency_means_within100ppm": True}}
        assert m.previous.phase_convergence(t, c, d, 12e-9, legacy)["converged"]
    assert not m.envelopes(t, c, d, 12e-9)["pass_envelope_screen"]


def test_below_rate_but_increasing_block_rate_still_rejects():
    t, c, d = periodic()
    ns = t * 1e9
    d["state52"] = 10 + (0.05 + 0.00005 * ns * ns) * c
    r = m.envelopes(t, c, d, 12e-9)
    assert r["checks"]["all_cycle_extrema_rates_within_original_limit"]
    assert not r["checks"][
        "all_fixed_block_extrema_rates_nonincreasing_with_original_tolerance"
    ]
    assert not r["pass_envelope_screen"]


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "extra",
        "nan",
        "infinity",
        "truncated_state",
        "truncated_time",
        "duplicate_time",
        "reversed_time",
        "no_clock",
        "missing_first",
        "clock_nan",
    ],
)
def test_incomplete_or_undefined_capture_rejected(fault):
    t, c, d = periodic()
    if fault == "missing":
        d.pop("state52")
    elif fault == "extra":
        d["state53"] = d["state0"]
    elif fault == "nan":
        d["state52"][-1] = np.nan
    elif fault == "infinity":
        d["state52"][-1] = np.inf
    elif fault == "truncated_state":
        d["state52"] = d["state52"][:-1]
    elif fault == "truncated_time":
        t = t[:-1]
        c = c[:-1]
        d = {k: v[:-1] for k, v in d.items()}
    elif fault == "duplicate_time":
        t[-1] = t[-2]
    elif fault == "reversed_time":
        t[-2] = t[-1] + 1e-12
    elif fault == "no_clock":
        c[:] = 1
    elif fault == "missing_first":
        t = t[10000:]
        c = c[10000:]
        d = {k: v[10000:] for k, v in d.items()}
    else:
        c[-1] = np.nan
    with pytest.raises(ValueError):
        m.envelopes(t, c, d, 12e-9)


def test_fixed8ns_window_excludes_earlier_envelope_without_claiming_cold_equilibrium():
    t, c, d = periodic()
    d["state52"] += np.maximum(3 - t * 1e9, 0) * 0.1
    assert m.envelopes(t, c, d, 12e-9)["pass_envelope_screen"]


def test_meter_requires_both_inherited_safety_phase_and_envelope(monkeypatch):
    t, c, d = periodic()
    obj = object.__new__(m.Meter)
    obj.stop = 12e-9
    obj.phase_names = ["time", "v(clkp)", "v(clkn)"] + sorted(d)
    obj.phase_data = dict(time=t, **{"v(clkp)": c, "v(clkn)": np.zeros_like(c)}, **d)
    monkeypatch.setattr(
        m.previous.Meter, "finish", lambda self: dict(phase_invariant_screen_pass=False)
    )
    r = obj.finish()
    assert (
        r["thermal_envelope"]["pass_envelope_screen"]
        and not r["bounded_mean_envelope_screen_pass"]
    )
    monkeypatch.setattr(
        m.previous.Meter, "finish", lambda self: dict(phase_invariant_screen_pass=True)
    )
    d["state52"][:] = 10 + (0.05 + 0.05 * t * 1e9) * c
    assert not obj.finish()["bounded_mean_envelope_screen_pass"]


@pytest.mark.parametrize(
    "fault", ["status", "safety", "envelope", "raw_pin", "method_pin", "rows"]
)
def test_first_receipt_cannot_be_mutated_without_recomputation(
    tmp_path, monkeypatch, fault
):
    exact = dict(
        status="PASS_V4_FIRST_MEAN_ENVELOPE_REVIEW",
        full_replay_path="fixed",
        tail_part_path="fixedpart",
        first_case=dict(
            measurement=dict(
                safety_checks=dict(vce=True),
                thermal_envelope=dict(pass_envelope_screen=True),
            )
        ),
        source_sha256=dict(raw="abc", method="def"),
        fulltime_raw_replay_rows=2000011,
    )
    got = copy.deepcopy(exact)
    if fault == "status":
        got["status"] = "FAIL_V4_FIRST_MEAN_ENVELOPE_SCREEN"
    elif fault == "safety":
        got["first_case"]["measurement"]["safety_checks"]["vce"] = False
    elif fault == "envelope":
        got["first_case"]["measurement"]["thermal_envelope"]["pass_envelope_screen"] = (
            False
        )
    elif fault == "raw_pin":
        got["source_sha256"]["raw"] = "bad"
    elif fault == "method_pin":
        got["source_sha256"]["method"] = "bad"
    else:
        got["fulltime_raw_replay_rows"] -= 1
    (tmp_path / "result.json").write_text(json.dumps(got))
    monkeypatch.setattr(m, "first_evidence", lambda *a: exact)
    with pytest.raises(ValueError):
        m.bind_first(tmp_path)


def test_first_full_replay_digest_checked_before_parsing(tmp_path, monkeypatch):
    (tmp_path / "result.json").write_text("{}")
    monkeypatch.setattr(m.previous, "__file__", m.previous.__file__)
    with pytest.raises(ValueError, match="Exact completed full31part replay"):
        m.first_evidence(tmp_path, tmp_path / "absent")


def test_second_native_never_starts_from_failed_first(tmp_path, monkeypatch):
    (tmp_path / "result.json").write_text(
        json.dumps(dict(status="FAIL_V4_FIRST_MEAN_ENVELOPE_SCREEN"))
    )
    monkeypatch.setattr(
        m.lifecycle, "native_wait", lambda *a, **k: pytest.fail("No native permitted")
    )
    with pytest.raises(ValueError):
        m.run_second(tmp_path, tmp_path / "parent", tmp_path / "output", "no-launch")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "status", ["FAIL_V4_FIRST_MEAN_ENVELOPE_SCREEN", "ERROR_V4_INCOMPLETE"]
)
def test_cli_failures_never_exit_success(monkeypatch, status):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "test",
            "review-first",
            "--replay",
            "unused",
            "--part",
            "unused",
            "--out",
            "unused",
        ],
    )
    monkeypatch.setattr(m, "review_first", lambda *a: dict(status=status))
    with pytest.raises(SystemExit) as exc:
        m.main()
    assert exc.value.code == 1


def test_previous_producers_and_native_lifecycle_unchanged():
    assert m.sha(m.previous.__file__) == m.PREVIOUS_SHA
    assert m.sha(m.lifecycle.__file__) == m.previous.LIFECYCLE_SHA
    assert m.lifecycle.native_wait is m.previous.lifecycle.native_wait
