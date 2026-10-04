# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source and metrology rejection controls; actual native capture is separate."""

from collections import Counter
from pathlib import Path
import sys
import copy
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_loop_v1 as m


def test_real_closed_graph_no_ideal_internal_primitives():
    c = m.config()
    rows = m.n.graph(
        {Path(p).name: Path(p).read_text() for p in c["sources"]}, c["roots"]
    )
    models = Counter(x["model"] for x in rows)
    assert len(rows) == 539 and models["npn13g2"] == 64
    assert set(models) == {
        "npn13g2",
        "rppd",
        "cap_cmim",
        "sg13_lv_nmos",
        "sg13_lv_pmos",
        "sg13_hv_nmos",
        "sg13_hv_pmos",
    }
    assert not any(x.startswith("VCTRL") for x in c["fixture"])
    source = (ROOT / "hw/soc/analog/pcie/pll_loop_hbt_v1.spice").read_text()
    assert "XDET fb ref reset up down vctrl div_avdd avss sub" in source
    assert [
        x["nets"] for x in rows if x["path"] in ["xloop.xrhi", "xloop.xrlo", "xloop.xc"]
    ] == [["avdd", "vctrl", "0"], ["vctrl", "0", "0"], ["vctrl", "0"]]
    assert c["step_s"] == 5e-12 and c["stop_s"] == 34e-9
    assert len(m.n.vectors(rows, c["extra_vectors"])) == 825


@pytest.mark.parametrize("name", m.SOURCE_PINS)
def test_source_drift_rejected_before_native(monkeypatch, name):
    original = m.n.common.sha
    monkeypatch.setattr(
        m.n.common, "sha", lambda p: "0" * 64 if Path(p).name == name else original(p)
    )
    with pytest.raises(AssertionError):
        m.config()


def count_fixture(monkeypatch):
    t = np.linspace(0, 34e-9, 34001)
    d = {
        "time": t,
        "v(clkp)": np.sin(2 * np.pi * 8e9 * t),
        "v(clkn)": np.zeros_like(t),
        "v(qp)": np.zeros_like(t),
        "v(qn)": np.zeros_like(t),
    }
    cml = list(np.arange(4.03125e-9, 34e-9, 0.5e-9))
    fb = [11.03125e-9, 21.03125e-9, 31.03125e-9]
    monkeypatch.setattr(
        m.counter.base,
        "count_measure",
        lambda d, c: dict(
            checks={"inherited_counter": True}, edge_times={"cml": cml, "feedback": fb}
        ),
    )
    return d, dict(window_s=[4e-9, 34e-9])


def test_exact_div80_cycle_census(monkeypatch):
    d, c = count_fixture(monkeypatch)
    r = m.measure_chain(d, c)
    assert r["passed"] and r["actual_vco_period_counts"]["whole_native_div80"] == [
        80,
        80,
    ]
    assert not r["closed_pll"]


@pytest.mark.parametrize(
    "fault", ["one_missing_vco_edge", "stopped_vco", "wrong_ratio"]
)
def test_actual_waveform_period_fault_cannot_pass(monkeypatch, fault):
    d, c = count_fixture(monkeypatch)
    t = d["time"]
    if fault == "stopped_vco":
        d["v(clkp)"][:] = 0
    elif fault == "wrong_ratio":
        d["v(clkp)"] = np.sin(2 * np.pi * 7.9e9 * t)
    else:
        d["v(clkp)"][(t > 15e-9) & (t < 15.125e-9)] = -1
    assert not m.measure_chain(d, c)["passed"]


def loop_fixture(monkeypatch):
    t = np.linspace(0, 34e-9, 34001)
    pulse = lambda period, phase, width: (((t - phase) % period) < width) & (t >= phase)
    d = {
        "time": t,
        "v(reference)": 2.5 * pulse(10e-9, 14e-9, 5e-9),
        "v(vctrl)": np.full_like(t, 0.85),
        "v(up)": 2.5 * pulse(10e-9, 21e-9, 2e-9),
        "v(down)": np.zeros_like(t),
        "i(@n.xloop.xdet.xcp.xpenable.nsg13_hv_pmos[ids])": np.full_like(t, -5e-6),
        "i(@n.xloop.xdet.xcp.xnenable.nsg13_hv_nmos[ids])": np.zeros_like(t),
    }
    base = dict(
        vctrl_external_v=0.85,
        closed_pll=False,
        checks={"prior_chain": True},
        edge_times={"feedback": [11e-9, 21e-9, 31e-9]},
    )
    monkeypatch.setattr(m, "measure_chain", lambda d, c: copy.deepcopy(base))
    return d, dict(window_s=[4e-9, 34e-9])


def test_startup_pass_never_claims_lock(monkeypatch):
    d, c = loop_fixture(monkeypatch)
    r = m.measure(d, c)
    assert r["passed"] and r["connected_loop"] and not r["lock_demonstrated"]
    assert "closed_pll" not in r and "vctrl_external_v" not in r


def test_future_reference_is_never_invented_for_last_feedback(monkeypatch):
    d, c = loop_fixture(monkeypatch)
    d["v(reference)"][d["time"] >= 33e-9] = 0
    r = m.measure(d, c)
    assert r["passed"] and len(r["phase_observation"]) == 2
    assert r["unpaired_feedback_edges_s"] == [31e-9]


@pytest.mark.parametrize(
    "fault",
    ["negative_pump", "no_pump", "no_detector", "no_reference", "escaped_control"],
)
def test_loaded_loop_observation_rejects_real_signal_fault(monkeypatch, fault):
    d, c = loop_fixture(monkeypatch)
    if fault == "negative_pump":
        d["i(@n.xloop.xdet.xcp.xpenable.nsg13_hv_pmos[ids])"] *= -1
    elif fault == "no_pump":
        d["i(@n.xloop.xdet.xcp.xpenable.nsg13_hv_pmos[ids])"][:] = 0
    elif fault == "no_detector":
        d["v(up)"][:] = 0
    elif fault == "no_reference":
        d["v(reference)"][:] = 0
    else:
        d["v(vctrl)"][5000] = 1.6
    assert not m.measure(d, c)["passed"]
