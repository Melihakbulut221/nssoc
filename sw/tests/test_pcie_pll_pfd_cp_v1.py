# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Parser/metrology rejection tests. Native transistor tests use the runner."""

from collections import Counter
import copy
from pathlib import Path
import struct
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_pll_pfd_cp_v1 as m


def test_actual_source_closure_all_devices_and_models():
    rows = m.device_contract(m.CIRCUIT.read_text())
    assert len(rows) == len({r["path"] for r in rows}) == 112
    assert Counter(r["model"] for r in rows) == {
        "sg13_hv_nmos": 56,
        "sg13_hv_pmos": 55,
        "rppd": 1,
    }
    assert all(
        r["nets"][3] == ("0" if r["model"] == "sg13_hv_nmos" else "avdd")
        for r in rows
        if r["model"] != "rppd"
    )
    source = next(r for r in rows if r["path"] == "xdut.xcp.xpsource")
    reference = next(r for r in rows if r["path"] == "xdut.xcp.xpref")
    assert source["width_um"] == 6.4 and reference["width_um"] == 8
    assert source["length_um"] == reference["length_um"] == 2
    assert m.sha(m.CIRCUIT) == m.CIRCUIT_SHA


@pytest.mark.parametrize(
    "fault",
    [
        "ideal",
        "unknown",
        "width",
        "length",
        "multiplier",
        "missing_device",
        "duplicate",
        "wrong_end",
        "extra_param",
    ],
)
def test_native_parser_rejects_changed_contract(fault):
    text = m.CIRCUIT.read_text()
    if fault == "ideal":
        text = text.replace(
            "XN y a vss sub sg13_hv_nmos w=2u l=0.45u ng=1 m=1", "BFAKE y vss V=1"
        )
    elif fault == "unknown":
        text = text.replace("sg13_hv_nmos", "unknown_mos", 1)
    elif fault == "width":
        text = text.replace("w=2u", "w=11u", 1)
    elif fault == "length":
        text = text.replace("l=0.45u", "l=0.13u", 1)
    elif fault == "multiplier":
        text = text.replace("m=1", "m=2", 1)
    elif fault == "missing_device":
        text = text.replace("XN y a vss sub sg13_hv_nmos w=2u l=0.45u ng=1 m=1", "")
    elif fault == "duplicate":
        text = text.replace(
            ".ends nssoc_pll_inv_hv_v1",
            "XN y a vss sub sg13_hv_nmos w=2u l=0.45u ng=1 m=1\n.ends nssoc_pll_inv_hv_v1",
        )
    elif fault == "wrong_end":
        text = text.replace(".ends nssoc_pll_inv_hv_v1", ".ends unrelated")
    else:
        text = text.replace("m=1", "m=1 ideal=1", 1)
    with pytest.raises(ValueError):
        m.device_contract(text)


def test_case_set_has_real_phase_frequency_missing_clock_reset_and_rc_controls():
    rows = m.cases()
    assert len(rows) == len({r["name"] for r in rows}) == 21
    assert sum(r["role"] == "negative" for r in rows) == 5
    assert {r["missing"] for r in rows} == {"", "ref", "fb"}
    assert {r["reset"] for r in rows} == {"startup", "held", "midstream"}
    assert {r["load"] for r in rows} == {"clamp", "native_rc"}
    for case in rows:
        text = m.deck(case, Path("models"), [Path("real.osdi")])
        assert ".ic " not in text.lower() and " uic" not in text.lower()
        assert "nodeset" not in text.lower() and "BFAKE" not in text
        if case["load"] == "native_rc":
            assert "cap_cmim w=20u l=20u" in text and "VCLAMP" not in text
            assert "XLOADHI" in text and "XLOADLO" in text
        assert m.device_contract(m.circuit(case))


@pytest.mark.parametrize(
    "name",
    ["swap_inputs", "no_common_reset", "no_source", "no_sink", "unbalanced_source"],
)
def test_each_actual_fault_changes_a_real_native_connection_or_geometry(name):
    case = next(r for r in m.cases() if r["fault"] == name)
    original = m.CIRCUIT.read_text()
    changed = m.circuit(case)
    assert changed != original
    before, after = m.device_contract(original), m.device_contract(changed)
    assert len(before) == len(after) == 112 and before != after


def test_changed_case_not_silently_simulated():
    case = copy.deepcopy(m.cases()[0])
    case["step_s"] = 1e-9
    with pytest.raises(ValueError, match="predeclared"):
        m.deck(case, Path("models"), [])


def raw_bytes(names, rows):
    header = "Title: native parser fixture\nFlags: real\n"
    header += f"No. Variables: {len(names)}\nNo. Points: {len(rows)}\nVariables:\n"
    header += "".join(f"\t{i}\t{name}\tvoltage\n" for i, name in enumerate(names))
    return (header + "Binary:\n").encode() + b"".join(
        struct.pack("<" + "d" * len(names), *row) for row in rows
    )


def test_binary_parser_preserves_exact_double_values(tmp_path):
    p = tmp_path / "wave.raw"
    p.write_bytes(raw_bytes(["time", "v(up)"], [[0, 0], [1e-9, 2.5]]))
    data = m.read_raw(p, ["v(up)"], True)
    assert data["time"].tolist() == [0, 1e-9]
    assert data["v(up)"].tolist() == [0, 2.5]


@pytest.mark.parametrize(
    "fault",
    ["truncated", "trailing", "missing", "extra", "duplicate", "nan", "complex"],
)
def test_raw_capture_never_passes_missing_corrupt_or_nonfinite_values(tmp_path, fault):
    names = ["time", "v(up)"]
    if fault == "missing":
        names[1] = "v(down)"
    elif fault == "duplicate":
        names[1] = "time"
    elif fault == "extra":
        names.append("v(down)")
    values = [[0.0] * len(names), [1.0] * len(names)]
    if fault == "nan":
        values[-1][-1] = float("nan")
    raw = raw_bytes(names, values)
    if fault == "truncated":
        raw = raw[:-1]
    elif fault == "trailing":
        raw += b"x"
    elif fault == "complex":
        raw = raw.replace(b"Flags: real", b"Flags: complex")
    p = tmp_path / "bad.raw"
    p.write_bytes(raw)
    with pytest.raises(ValueError):
        m.read_raw(p, ["v(up)"], True)


def test_threshold_active_time_is_interpolated_not_sample_counted():
    t = np.array([0.0, 1.0, 2.0, 4.0])
    y = np.array([0.0, 2.0, 2.0, 0.0])
    assert m.active_time(t, y, 1.0, 0.0, 4.0) == 2.5
    assert m.integrate(t, y, 0.0, 4.0) == 5.0
    assert m.crossings(t, y, 1.0) == [0.5]


def test_truncated_integration_interval_rejected():
    with pytest.raises(ValueError, match="Complete integration"):
        m.integrate(np.array([1.0, 2.0]), np.array([0.0, 1.0]), 0.0, 2.0)


def test_frozen_circuit_mutation_rejected_before_deck(monkeypatch, tmp_path):
    path = tmp_path / "changed.spice"
    path.write_text(m.CIRCUIT.read_text() + "\n")
    monkeypatch.setattr(m, "CIRCUIT", path)
    with pytest.raises(ValueError, match="Frozen original"):
        m.circuit(m.cases()[0])


def test_wrong_runtime_rejected_before_native_launch(tmp_path):
    runtime = tmp_path / "ngspice"
    runtime.write_text("not native")
    output = Path("/dev/shm/nssoc-pfd-never-launched-by-test")
    with pytest.raises(ValueError, match="Exact native"):
        m.run_case(m.cases()[0], output, runtime, tmp_path, [])
    assert not output.exists()
