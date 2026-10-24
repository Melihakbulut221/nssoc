# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
import math
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import diagnose_pcie_clock_trim_thermal_poles_v1 as m  # noqa: E402


def synthetic():
    times = [i * 1e-10 for i in range(10001)]
    data = {}
    dc = {}
    for i, (w, l) in enumerate(m.geometries()[1]):
        p = m.pole(w, l)
        g = p["conductance_w_per_k"]
        data[f"v(xr{i}.dt)"] = [1 - math.exp(-t / p["tau_s"]) for t in times]
        for field, value in [
            ("rth", 1 / g),
            ("cth", p["capacitance_j_per_k"]),
            ("power", g),
        ]:
            data[f"@n.xr{i}.nr1[{field}]"] = [value] * len(times)
        data[f"@n.xr{i}.nr1[power]"][0] = 0
        dc[f"v(xr{i}.dt)"] = [1.0]
        dc[f"@n.xr{i}.nr1[power]"] = [g]
    return data, times, dc


def test_all23_devices_and_exact5_geometries():
    rows, unique = m.geometries()
    assert len(rows) == 23 and len(unique) == 5
    assert unique == [(2, 7.4), (4, 29), (8, 4), (8, 4.4), (8, 7.4)]
    assert all(0 < m.pole(w, l)["tau_s"] < 99e-9 for w, l in unique)
    assert abs(m.pole(2, 7.4)["tau_s"] - 69.59938078340473e-9) < 1e-21


def test_exact_native_source_wrapper_models_no_forced_thermal_state():
    cold = m.deck("/models", "/r.osdi", "cold")
    assert (
        sum(" rppd " in line for line in cold.splitlines() if line.startswith("XR"))
        == 5
        and cold.count("sw_et=1") == 5
    )
    assert '.lib "/models/cornerRES.lib" res_bcs' in cold
    assert "PWL(0 0 0.5n 1.2)" in cold
    assert "tran .1n 1u 0 .1n" in cold
    assert (
        "uic" not in cold.lower()
        and ".ic " not in cold.lower()
        and ".nodeset" not in cold.lower()
    )
    assert m.deck("/models", "/r.osdi", "selfheat_off") == cold.replace(
        "sw_et=1", "sw_et=0"
    )
    assert m.deck("/models", "/r.osdi", "wrong_geometry") == cold.replace(
        "XR0 a 0 0 rppd w=2u", "XR0 a 0 0 rppd w=4u"
    )
    with pytest.raises(ValueError):
        m.deck("/models", "/r.osdi", "bad")


def test_thermal_energy_and_dc_positive():
    data, t, dc = synthetic()
    assert m.audit(data, t, dc)["pass_native"]


@pytest.mark.parametrize(
    "fault",
    [
        "flat_thermal",
        "wrong_cth",
        "wrong_rth",
        "nonzero_initial",
        "wrong_dc",
        "wrong_power",
    ],
)
def test_thermal_energy_and_coefficient_mutations_rejected(fault):
    data, t, dc = synthetic()
    if fault == "flat_thermal":
        data["v(xr0.dt)"] = [0] * len(t)
    elif fault == "wrong_cth":
        data["@n.xr0.nr1[cth]"][10] *= 2
    elif fault == "wrong_rth":
        data["@n.xr0.nr1[rth]"][10] *= 2
    elif fault == "nonzero_initial":
        data["v(xr0.dt)"][0] = 0.1
    elif fault == "wrong_dc":
        dc["v(xr0.dt)"][0] *= 2
    elif fault == "wrong_power":
        data["@n.xr0.nr1[power]"] = [x * 2 for x in data["@n.xr0.nr1[power]"]]
    if fault in ("flat_thermal", "wrong_power"):
        assert not m.audit(data, t, dc)["pass_native"]
    else:
        with pytest.raises(ValueError):
            m.audit(data, t, dc)


def test_actual_dc_header_and_no_unknown_columns(tmp_path):
    p = tmp_path / "op.dat"
    header = ["a", *m.observations(5)]
    p.write_text(" ".join(header) + "\n" + " ".join(["0"] * len(header)) + "\n")
    d, t = m.read(p, dc=True)
    assert t == [0] and d["v(a)"] == [0]
    p.write_text(p.read_text().replace("a v(a)", "v(a) v(a)", 1))
    with pytest.raises(ValueError, match="observations"):
        m.read(p, dc=True)


@pytest.mark.parametrize("mutation", ["duplicate_row", "nan", "missing_column"])
def test_native_reader_fail_closed(tmp_path, mutation):
    p = tmp_path / "op.dat"
    header = ["a", *m.observations(5)]
    vals = ["0"] * len(header)
    if mutation == "nan":
        vals[3] = "nan"
    if mutation == "missing_column":
        vals.pop()
    row = " ".join(vals) + "\n"
    p.write_text(
        " ".join(header) + "\n" + row * (2 if mutation == "duplicate_row" else 1)
    )
    with pytest.raises(ValueError):
        m.read(p, dc=True)


def test_reference_data_not_mutated_by_auditor():
    data, t, dc = synthetic()
    before = copy.deepcopy((data, t, dc))
    m.audit(data, t, dc)
    assert (data, t, dc) == before
