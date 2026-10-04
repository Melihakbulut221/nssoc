# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite structural/parser controls; actual SPICE cases are a separate CLI."""

from collections import Counter
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_feedback_v1 as m


def test_literal_native_graph_and_ranges():
    rows = m.native.graph(
        {"dut": m.circuit_text()}, m.config_for("nominal", m.CIRCUIT)["roots"]
    )
    assert Counter(r["model"] for r in rows) == {
        "sg13_lv_nmos": 135,
        "sg13_lv_pmos": 133,
        "sg13_hv_nmos": 3,
        "sg13_hv_pmos": 3,
        "rppd": 6,
        "cap_cmim": 1,
    }
    for row in rows:
        if row["model"].startswith("sg13_"):
            assert 0.15 <= float(row["params"]["w"][:-1]) <= 10
            assert row["params"]["ng"] == row["params"]["m"] == "1"


def test_vco_v4_uses_four_separate_calibrated_width_devices():
    base = ROOT / "hw/soc/analog/pcie"
    old = (base / "clock_vco_hbt_v3.spice").read_text()
    new = (base / "clock_vco_hbt_v4.spice").read_text()
    old_lines = [s for s in old.splitlines() if s and not s.startswith("*")]
    new_lines = [s for s in new.splitlines() if s and not s.startswith("*")]
    controls = [s for s in new_lines if s.startswith("XCTRL")]
    assert len(controls) == 4
    assert all(" w=8u " in s and " ng=1 m=1" in s for s in controls)
    one = next(s for s in old_lines if s.startswith("XCTRL "))
    assert " w=32u " in one
    assert [
        s.replace("_v4", "_v3") for s in new_lines if not s.startswith("XCTRL")
    ] == [s for s in old_lines if not s.startswith("XCTRL")]
    for i, line in enumerate(controls):
        assert line == one.replace("XCTRL ", f"XCTRL{i} ").replace("w=32u", "w=8u")


def test_actual_gate_connectivity_all_eight_modulo_states():
    body = m.circuit_text().split(".subckt nssoc_pll_mod5_lv_v1 ")[1].split(".ends")[0]
    gates = [
        line.split()
        for line in body.splitlines()
        if line.startswith("X") and not line.startswith("XFF")
    ]
    for value in range(8):
        nets = {f"q{i}": bool((value >> i) & 1) for i in range(3)}
        nets.update({f"q{i}b": not nets[f"q{i}"] for i in range(3)})
        for gate in gates:
            kind = gate[-1]
            count = 1 if "inv_" in kind else 2 if "nand2_" in kind else 3
            nets[gate[count + 1]] = not all(nets[n] for n in gate[1 : count + 1])
        got = sum(int(nets[f"d{i}"]) << i for i in range(3))
        assert got == (value + 1 if value < 4 else 0)


@pytest.mark.parametrize("fault", m.FAULTS)
def test_fault_changes_one_actual_connection(fault):
    before, after = m.circuit_text(), m.circuit_text(fault)
    old, new = m.FAULTS[fault]
    assert before.count(old) == 1 and after.count(old) == 0 and after.count(new) == 1
    assert after != before


@pytest.mark.parametrize(
    "ulps,accepted",
    [(0, True), (4, True), (5, True), (16, True), (17, False), (64, False)],
)
@pytest.mark.parametrize("direction", [0, np.inf])
def test_raw_endpoint_exact_ulp_boundary(ulps, accepted, direction):
    endpoint = stop = 34e-9
    for _ in range(ulps):
        endpoint = np.nextafter(endpoint, direction)
    t = np.linspace(0, endpoint, 1001)
    if accepted:
        result = m.native.validate_time_grid(t, stop, 1e-9)
        assert result["last_s"] == endpoint and not result["raw_samples_changed"]
    else:
        with pytest.raises(AssertionError):
            m.native.validate_time_grid(t, stop, 1e-9)


@pytest.mark.parametrize("fault", ["duplicate", "nonzero_start", "gap", "nan"])
def test_time_grid_rejects_capture_faults(fault):
    t = np.linspace(0, 34e-9, 1001)
    if fault == "duplicate":
        t[50] = t[49]
    elif fault == "nonzero_start":
        t[0] = 1e-15
    elif fault == "gap":
        t = np.r_[t[:100], t[800:]]
    else:
        t[50] = np.nan
    with pytest.raises(AssertionError):
        m.native.validate_time_grid(t, 34e-9, 1e-9)


def raw(path, values, names=("time", "v(a)")):
    header = "Title: tiny native-format control\nFlags: real\n"
    header += f"No. Variables: {len(names)}\nNo. Points: {len(values)}\nVariables:\n"
    header += "".join(f"\t{i}\t{name}\tvoltage\n" for i, name in enumerate(names))
    path.write_bytes(
        header.encode() + b"Binary:\n" + np.asarray(values, dtype="<f8").tobytes()
    )


@pytest.mark.parametrize(
    "fault", ["truncated", "duplicate_name", "nan", "extra_column"]
)
def test_native_capture_rejects_unproven_bytes(tmp_path, fault):
    p = tmp_path / "wave.raw"
    raw(p, [[0, 0], [1e-12, 1]])
    if fault == "truncated":
        p.write_bytes(p.read_bytes()[:-1])
    elif fault == "duplicate_name":
        raw(p, [[0, 0], [1e-12, 1]], ("time", "time"))
    elif fault == "nan":
        raw(p, [[0, 0], [1e-12, np.nan]])
    else:
        raw(p, [[0, 0, 0], [1e-12, 1, 1]], ("time", "v(a)", "v(b)"))
    with pytest.raises(AssertionError):
        m.native.read_raw(p, ["v(a)"], True)


def test_geometry_outside_native_model_range_cannot_pass():
    r = dict(
        path="x",
        model="sg13_hv_pmos",
        nets=["a", "0", "0", "0"],
        params=dict(w="32u", l="0.45u", ng="1", m="1"),
    )
    d = {
        "time": np.array([0.0, 1.0]),
        "v(a)": np.array([0.0, 0.1]),
        "i(@n.x.nsg13_hv_pmos[ids])": np.array([0.0, 0.0]),
    }
    result = m.native.safety(d, [r], [0, 1])
    assert not result["passed"] and len(result["model_geometry_range_issues"]) == 1


def test_negative_case_does_not_bypass_all_sample_device_bounds():
    r = dict(
        path="x",
        model="sg13_lv_nmos",
        nets=["a", "0", "0", "0"],
        params=dict(w="0.74u", l="0.13u", ng="1", m="1"),
    )
    d = {
        "time": np.array([0.0, 0.5, 1.0]),
        "v(a)": np.array([0.0, 1.6, 0.1]),
        "i(@n.x.nsg13_lv_nmos[ids])": np.array([0.0, 0.0, 0.0]),
    }
    assert not m.native.safety(d, [r], [0.9, 1])["passed"]


def test_case_contracts_remain_explicit_external_clock_and_native_dut():
    for name in m.CASES:
        c = m.config_for(name, m.CIRCUIT)
        assert c["roots"][0][0] == m.TOP
        assert c["step_s"] <= 10e-12 and c["stop_s"] <= 38e-9
        assert any(line.startswith("VP cp 0 PWL(") for line in c["fixture"])
        assert not any(
            token in m.circuit_text().lower()
            for token in (".ic", "uic", "nodeset", "bsource")
        )
