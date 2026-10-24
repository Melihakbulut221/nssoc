# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fixed-window/time0 and thermal-convergence controls, no threshold waiver."""

from array import array
import copy
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_clock_trim_thermal_v1 as new  # noqa: E402


def synthetic():
    ts = array("d", (i * 0.01e-9 for i in range(4001)))
    vals = array("d", (0.4 * math.sin(2 * math.pi * 8e9 * t) for t in ts))
    return {"time": ts, "v(clkp)": vals, "v(clkn)": array("d", (-x for x in vals))}


def windows():
    return [
        dict(
            declared_window_s=[i * 2e-9, (i + 1) * 2e-9],
            frequency_hz=8e9,
            thermal_nodes={
                "v(xosc.xref.t)": dict(signed_rate_v_per_ns=0.005 / (i + 1))
            },
        )
        for i in range(20)
    ]


def test_exact_unchanged_circuit_and_only_stop_time_changed():
    for c in new.cases():
        assert new.circuit(c) == new.prior.circuit(c, 64, 4)
        hbts = new.driver.contract(new.circuit(c), 4)
        args = c, Path("/models"), [Path("/r.osdi")], 0.9067e-12, 0.9233e-12, hbts
        old = new.prior.deck(*args)
        actual = new.deck(*args)
        assert actual == old.replace(
            f"tran {c['step_s']:.12g} 12n 0", f"tran {c['step_s']:.12g} 40n 0"
        )
        assert actual.count("alter @q.xosc.") == 30
        assert ".options reltol=1e-4 abstol=1e-12" in actual
        assert "uic" not in actual.lower()
        assert new.driver.contract(new.circuit(c), 4) == new.driver.contract(
            new.prior.CIRCUIT.read_text(), 4
        )


def test_only_exact_failed_fast_corner_and_timestep_pair():
    a, b = new.cases()
    assert a["step_s"] == 0.5e-12 and b["step_s"] == 0.25e-12
    assert {k: v for k, v in a.items() if k not in ("name", "step_s")} == {
        k: v for k, v in b.items() if k not in ("name", "step_s")
    }
    assert a["supply"] == 2.415 and a["control"] == 1 and a["code"] == 2
    assert all(
        a[k] == v
        for k, v in dict(new.driver.parent.TUNING)[
            "high_supply_res_bcs_cap_bcs"
        ].items()
    )


def test_fixed_window_clock_equations_and_functional_negative():
    data = synthetic()
    m = new.clock_window(data, *new.FINAL_WINDOW)
    assert m["functional_pass"] and abs(m["frequency_hz"] / 8e9 - 1) < 1e-12
    assert set(m["checks"]) == set(new.driver.FUNCTIONAL_CHECKS)
    data["v(clkn)"] = data["v(clkp)"]
    bad = new.clock_window(data, *new.FINAL_WINDOW)
    assert not bad["functional_pass"] and not bad["checks"]["differential_swing"]


def test_late_pass_does_not_rewrite_early_failure():
    data = synthetic()
    for i, t in enumerate(data["time"]):
        if t < 12e-9:
            data["v(clkp)"][i] *= 0.1
            data["v(clkn)"][i] *= 0.1
    assert not new.clock_window(data, 4e-9, 12e-9)["functional_pass"]
    assert new.clock_window(data, *new.FINAL_WINDOW)["functional_pass"]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_window",
        "wrong_window",
        "missing_node",
        "frequency_drift",
        "thermal_unsettled",
        "thermal_reaccelerating",
    ],
)
def test_convergence_rejects_missing_or_unsettled_trajectory(mutation):
    ws = windows()
    if mutation == "missing_window":
        ws.pop(0)
    elif mutation == "wrong_window":
        ws[-1]["declared_window_s"] = [34e-9, 40e-9]
    elif mutation == "missing_node":
        ws[-1]["thermal_nodes"] = {}
    elif mutation == "frequency_drift":
        ws[-1]["frequency_hz"] *= 1.001
    elif mutation == "thermal_unsettled":
        for w in ws[-4:]:
            w["thermal_nodes"]["v(xosc.xref.t)"]["signed_rate_v_per_ns"] = 0.02
    elif mutation == "thermal_reaccelerating":
        ws[-1]["thermal_nodes"]["v(xosc.xref.t)"]["signed_rate_v_per_ns"] = 0.009
    if mutation in ("missing_window", "wrong_window", "missing_node"):
        with pytest.raises(ValueError):
            new.convergence(ws)
    else:
        assert not new.convergence(ws)["converged"]


def test_convergence_positive_and_every_node_required():
    ws = windows()
    assert new.convergence(ws)["converged"]
    for w in ws:
        w["thermal_nodes"]["other.dt"] = dict(signed_rate_v_per_ns=0.5)
    assert not new.convergence(ws)["converged"]


def test_trajectory_observes_every_thermal_node():
    data = synthetic()
    for i in range(53):
        data[f"v(xosc.r{i}.dt)"] = array("d", (t * 1e7 for t in data["time"]))
    trajectory = new.trajectory(data, dict.fromkeys(range(30)))
    assert len(trajectory) == 20
    assert all(len(w["thermal_nodes"]) == 53 for w in trajectory)
    assert trajectory[-1]["declared_window_s"] == [38e-9, 40e-9]
    del data["v(xosc.r0.dt)"]
    with pytest.raises(ValueError, match="Every"):
        new.trajectory(data, dict.fromkeys(range(30)))


def wave_file(tmp_path, monkeypatch, change=None):
    monkeypatch.setattr(new.prior, "vectors", lambda h: ["x"])
    path = tmp_path / "wave.dat"
    rows = [(i * 40e-12, 1) for i in range(1001)]
    if change == "start":
        rows.pop(0)
    if change == "short":
        rows.pop()
    if change == "gap":
        rows.pop(400)
    if change == "nonfinite":
        rows[400] = (rows[400][0], float("nan"))
    if change == "reverse":
        rows[400] = rows[399]
    path.write_text("time x\n" + "".join(f"{t:.15g} {v}\n" for t, v in rows))
    return path


def test_reader_contiguous_double_and_full_time0(tmp_path, monkeypatch):
    d = new.read_wave(wave_file(tmp_path, monkeypatch), {}, dict(step_s=40e-12))
    assert isinstance(d["x"], array) and d["x"].typecode == "d"


@pytest.mark.parametrize("change", ["start", "short", "gap", "nonfinite", "reverse"])
def test_reader_rejects_incomplete_or_corrupt_wave(tmp_path, monkeypatch, change):
    with pytest.raises(ValueError):
        new.read_wave(wave_file(tmp_path, monkeypatch, change), {}, dict(step_s=40e-12))


def test_pair_exact_case_and_timestep_agreement():
    rows = [
        dict(case=c, measurement=dict(final_clock_window=dict(frequency_hz=8e9)))
        for c in new.cases()
    ]
    assert new.pair_agreement(rows)["pass_pair"]
    rows[1]["measurement"]["final_clock_window"]["frequency_hz"] *= 1.001
    assert not new.pair_agreement(rows)["pass_pair"]
    rows[1]["case"]["code"] = 1
    with pytest.raises(ValueError, match="Exact"):
        new.pair_agreement(rows)


def test_source_mutation_rejected(monkeypatch):
    monkeypatch.setattr(new, "PRIOR_SHA", "0" * 64)
    with pytest.raises(ValueError, match="Frozen"):
        new.circuit(new.cases()[0])


def test_safety_and_original_failure_never_replaced_by_final_clock(monkeypatch):
    full = dict(
        settled_window_s=[4e-9, 12e-9], checks=dict(headroom=False, edges=False)
    )
    monkeypatch.setattr(new.prior, "measure", lambda *a: copy.deepcopy(full))
    monkeypatch.setattr(
        new, "clock_window", lambda d, a, b: dict(functional_pass=a == 32e-9)
    )
    monkeypatch.setattr(new, "trajectory", lambda *a: windows())
    m = new.measure({}, {}, {})
    assert not m["limited_thermal_screen_pass"]
    assert m["final_clock_window"]["functional_pass"]
    assert not m["original_4_to12ns_clock_window"]["functional_pass"]
    assert m["full_capture"]["operating_window_s"] == [4e-9, 40e-9]
    assert not m["prior12ns_results_superseded"]


def test_missing_late_oscillation_is_physical_failure_not_missing_capture():
    ws = windows()
    ws[-1]["frequency_hz"] = None
    assert not new.convergence(ws)["converged"]
    rows = [
        dict(case=c, measurement=dict(final_clock_window=dict(frequency_hz=None)))
        for c in new.cases()
    ]
    assert not new.pair_agreement(rows)["pass_pair"]


@pytest.mark.parametrize(
    "status,expected",
    [
        ("PASS_LIMITED40NS_THERMAL_SCREEN", 0),
        ("FAIL_LIMITED40NS_THERMAL_SCREEN", 1),
        ("INCOMPLETE_OR_ERROR", 1),
        ("RUNNING", 1),
    ],
)
def test_cli_never_accepts_actual_fail_or_incomplete(monkeypatch, status, expected):
    monkeypatch.setattr(
        sys,
        "argv",
        ["thermal"]
        + [
            a
            for name in ("baseline", "startup", "capacitance", "out", "prior12")
            for a in ("--" + name, "/unused")
        ],
    )
    monkeypatch.setattr(new, "run", lambda *a: dict(status=status))
    assert new.main() == expected


def test_actual_prior_native_bridge_is_reproducible():
    path = Path("/dev/shm/nssoc-clock-trim-targeted")
    if not path.exists():
        pytest.skip("Optional exact local prior capture")
    row, pins = new.previous_failure(path)
    assert row["measurement"]["checks"]["deterministic_period_spread"] is False
    assert len(pins) == 5
    old_deck = (path / new.PRIOR_CASE / "bench.cir").read_text()
    models = next(
        Path(p).parent
        for p in __import__("json").loads((path / "result.json").read_text())[
            "source_sha256"
        ]
        if Path(p).name == "cornerHBT.lib"
    )
    osdi = [
        Path("/dev/shm/nssoc-clock-vco-full-20261004") / n
        for n in new.driver.parent.init.MODELS
    ]
    for c in new.cases():
        hbts = new.driver.contract(new.circuit(c), 4)
        actual = new.deck(c, models, osdi, 0.9067e-12, 0.9233e-12, hbts)
        # Actual rounded coefficients are read from the pinned capture, not inferred.
        cap = __import__("json").loads((path / "result.json").read_text())
        actual = new.deck(c, models, osdi, cap["load_p_f"], cap["load_n_f"], hbts)
        assert actual == old_deck.replace(
            "tran 5e-13 12n 0 5e-13",
            f"tran {c['step_s']:.12g} 40n 0 {c['step_s']:.12g}",
        )


def test_prior_native_result_mutation_rejected(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    with pytest.raises(ValueError, match="Exact prior12ns"):
        new.previous_failure(tmp_path)
