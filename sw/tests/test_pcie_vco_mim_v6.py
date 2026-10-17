# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact new native-MIM-only source delta and fail-closed pilot classification."""

import copy
import gzip
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_vco_mim_v6 as m


def test_literal_six_native_mim_changes_only():
    assert hashlib.sha256(m.OLD.read_bytes()).hexdigest() == m.OLD_SHA
    assert hashlib.sha256(m.NEW.read_bytes()).hexdigest() == m.NEW_SHA
    changes = m.source_delta(m.OLD.read_text(), m.NEW.read_text())
    assert {r["name"] for r in changes} == set(m.CAPS)
    assert len(changes) == 6


@pytest.mark.parametrize(
    "old,new",
    [
        ("XP0 p0 p2 t0 sub", "XP0 p0 p2 t0 avss"),
        ("Nx=2", "Nx=3"),
        ("w=8u l=0.45u", "w=9u l=0.45u"),
        ("XCP0 p0 avss", "XCP0 p0 sub"),
        ("w=11.2u l=11u", "w=11u l=11u"),
        ("w=11u l=11u", "w=10.9u l=11u"),
        ("cap_cmim", "C"),
        (".ends nssoc_clock_vco_hbt_v6", ".ends wrong"),
    ],
)
def test_real_body_current_geometry_and_terminal_drift_rejected(old, new):
    assert old in m.NEW.read_text()
    with pytest.raises(ValueError):
        m.source_delta(m.OLD.read_text(), m.NEW.read_text().replace(old, new, 1))


def fixture():
    names = list(m.CAPS) + [f"UNCHANGED{i}" for i in range(56)]
    records = []
    binding = {"devices": []}
    for i, name in enumerate(names, 1):
        binding["devices"].append(dict(native_id=i, source_name=name))
        if name in m.CAPS:
            w = "11.7u" if name == "CP0" else "11.5u"
            params = dict(w=w, l="11.5u")
            records.append(
                dict(
                    native_id=i,
                    model="cap_cmim",
                    terminals=[
                        dict(terminal="mim_top", node=f"w_T{i:04}"),
                        dict(terminal="mim_btm", node="w_AVSS"),
                    ],
                    native_parameters=dict(
                        w=11.7 if name == "CP0" else 11.5, l=11.5, m=1.0
                    ),
                    simulator_parameters=params,
                    line=f"XD{i:04} w_T{i:04} w_AVSS cap_cmim w={w} l=11.5u",
                )
            )
        else:
            records.append(
                dict(native_id=i, model="unchanged", line="unchanged " + name)
            )
    return dict(records=records, finite_contacts=13, body_well_terminals=56), binding


def test_candidate_bridge_leaves_all_noncap_records_and_original_unmodified():
    comp, binding = fixture()
    before = copy.deepcopy(comp)
    actual = m.candidate_composition(comp, binding, "candidate")
    assert comp == before and actual["records"][6:] == comp["records"][6:]
    assert actual["candidate_geometry_qualified"] is False
    for n, d in zip(m.CAPS, actual["records"][:6]):
        assert "native_parameters" not in d
        assert "baseline_native_parameters" in d
        assert d["proposed_parameters"] == dict(zip(("w", "l"), m.CAPS[n]))
    old = m.candidate_composition(comp, binding, "original")
    assert old["records"] == comp["records"]


@pytest.mark.parametrize(
    "fault",
    [
        "model",
        "terminal",
        "source_node",
        "params",
        "duplicate_id",
        "duplicate_name",
        "finite_contacts",
    ],
)
def test_named_bridge_mutations_fail(fault):
    c, b = fixture()
    if fault == "model":
        c["records"][0]["model"] = "ideal_C"
    if fault == "terminal":
        c["records"][0]["terminals"].reverse()
    if fault == "source_node":
        c["records"][0]["line"] = c["records"][0]["line"].replace(
            "w_AVSS", "BODY_SUBSTRATE"
        )
    if fault == "params":
        c["records"][0]["simulator_parameters"]["w"] = "12u"
    if fault == "duplicate_id":
        c["records"][-1]["native_id"] = c["records"][0]["native_id"]
    if fault == "duplicate_name":
        b["devices"][-1]["source_name"] = "CP0"
    if fault == "finite_contacts":
        c["finite_contacts"] = 12
    with pytest.raises(ValueError):
        m.candidate_composition(c, b, "candidate")


def measurement():
    return dict(
        numerical_clean=True,
        metrics=dict(
            hbt_bounds={
                str(i): dict(
                    min_vce=0.5, max_vce=1.3, peak_abs_current_per_emitter_a=0.002
                )
                for i in range(30)
            },
            full_time_max_vce=1.4,
            signals=[dict(rising_edges=11, mean_frequency_hz=8e9)],
        ),
    ), dict(cycles=[{}] * 10, all_complete_cycles_pass=True)


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "current",
        "lower_vce",
        "upper_vce",
        "startup_upper_vce",
        "warnings",
        "missing_hbt",
        "no_cycles",
        "bad_amplitude",
        "cycle_count",
    ],
)
def test_finite_screen_never_promotes_real_failure(fault):
    a, c = measurement()
    if fault == "current":
        a["metrics"]["hbt_bounds"]["0"]["peak_abs_current_per_emitter_a"] = 0.003001
    if fault == "lower_vce":
        a["metrics"]["hbt_bounds"]["0"]["min_vce"] = 0.3999
    if fault == "upper_vce":
        a["metrics"]["hbt_bounds"]["0"]["max_vce"] = 1.6001
    if fault == "startup_upper_vce":
        a["metrics"]["full_time_max_vce"] = 1.6001
    if fault == "warnings":
        a["numerical_clean"] = False
    if fault == "missing_hbt":
        del a["metrics"]["hbt_bounds"]["0"]
    if fault == "no_cycles":
        a["metrics"]["signals"][0]["rising_edges"] = 0
        c = dict(cycles=[], all_complete_cycles_pass=False)
    if fault == "bad_amplitude":
        c["all_complete_cycles_pass"] = False
    if fault == "cycle_count":
        c["cycles"].pop()
    if fault in ("missing_hbt", "cycle_count"):
        with pytest.raises(ValueError):
            m.classify(a, c)
    else:
        assert m.classify(a, c)["passed"] == (fault is None)


@pytest.mark.parametrize("amplitude", [0.4, 0.2, 0])
def test_complete_cycles_use_each_actual_positive_and_negative_peak(
    tmp_path, amplitude
):
    p = tmp_path / "wave.dat.gz"
    rows = ["time v(CLKP) v(CLKN)"]
    for i in range(21):
        v = (-1 if i % 2 == 0 else 1) * amplitude
        rows.append(f"{6e-9 + i * 1e-11:.16g} {v} 0")
    with gzip.open(p, "wt") as f:
        f.write("\n".join(rows) + "\n")
    out = m.cycle_screen(p, dict(vectors=["v(CLKP)", "v(CLKN)"]))
    assert out["all_complete_cycles_pass"] == (amplitude == 0.4)
    assert len(out["cycles"]) == (9 if amplitude else 0)


def test_exact_frozen_solver_controller_has_no_changed_limits():
    assert m.pin(Path(m.base.__file__))["sha256"] == m.BASE_SHA
    assert m.base.BEGIN == 6e-9 and m.base.STOP == 12e-9 and m.base.STEP == 1e-12
    assert m.base.OWN_LIMIT == 80 * 1024**2 and m.base.SHARED_RESERVE == 512 * 1024**2
    assert (
        m.base.LAUNCH_HEADROOM == 24 * 1024**2 and m.base.RECEIPT_RESERVE == 2 * 1024**2
    )


def test_complete_cycle_and_electrical_screens_unchanged():
    import inspect
    import characterize_pcie_vco_mim_v5 as prior

    for name in ("cycle_screen", "classify"):
        assert inspect.getsource(getattr(m, name)) == inspect.getsource(
            getattr(prior, name)
        )
    for name in ("wave_measure", "audit_native", "run_native", "stream_wave", "limits"):
        assert inspect.getsource(getattr(m.base, name)) == inspect.getsource(
            getattr(prior.base, name)
        )
