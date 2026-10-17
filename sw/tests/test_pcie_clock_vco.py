# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent metrology counterexamples, not transistor behavior models."""
import copy
import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("pcie_clock_vco", ROOT / "scripts/characterize_pcie_clock_vco.py")
vco = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vco)


def synthetic():
    t = [i * 1e-12 for i in range(12001)]
    data = {name: [0.] * len(t) for name in vco.vectors()}
    data["time"] = t
    for name in data:
        if name.startswith("v("):
            value = 2.1
            if name in ("v(avdd)",):
                value = 2.3
            if name in ("v(vctrl)", "v(xosc.ref)", "v(xosc.bref)"):
                value = 0.85
            if name in ("v(xosc.t0)", "v(xosc.t1)", "v(xosc.t2)", "v(xosc.bt)"):
                value = 1.2
            data[name] = [value] * len(t)
        if name.startswith("@q."):
            data[name] = [0.001] * len(t)
    data["v(clkp)"] = [1.25 + 0.23 * math.sin(2 * math.pi * 8e9 * x + 0.23) for x in t]
    data["v(clkn)"] = [2.5 - p for p in data["v(clkp)"]]
    data["i(vdd)"] = [-0.03] * len(t)
    return data


def test_native_inventory_and_no_synthetic_clock():
    source = vco.CIRCUIT.read_text()
    hbts, res = vco.device_contract(source)
    assert len(hbts) == 18 and len(res) == 9
    lines = [line for line in source.splitlines() if line and not line.startswith(("*", "."))]
    assert all(line.startswith("X") for line in lines)
    assert sum("cap_cmim" in line for line in lines) == 6
    assert sum("sg13_hv_pmos" in line for line in lines) == 1
    assert "XCP0 p0 avss cap_cmim w=12.2u l=12u" in source
    for n in range(3):
        assert f"XP{n} p{n} p{(n+2)%3} t{n}" in source


def test_actual_deck_uses_zero_source_ramp_without_forced_periodic_clock():
    d = vco.deck(dict(vco.BASE), Path("/models"), [Path("/native.osdi")])
    for forbidden in ("PULSE", ".ic", ".nodeset", " UIC", " SIN("):
        assert forbidden.lower() not in d.lower()
    assert "PWL(0 0 5e-10 2.3)" in d
    assert "CLOADP clkp 0 5e-14" in d
    assert "reltol=1e-4 abstol=1e-12" in d


def test_case_matrix_preserves_exploratory_boundaries():
    c = vco.cases()
    assert len(c) == 72
    assert len({x["name"] for x in c}) == len(c)
    assert {x["name"] for x in c if x["role"] == "required"} == {"nominal", "half_step"}
    assert len([x for x in c if x["fault"]]) == 4
    assert len([x for x in c if x["name"].startswith("hbt_")]) == 27
    assert len([x for x in c if x["name"].startswith("res_")]) == 27


def test_independent_sinusoidal_metrology_fixture():
    result = vco.measure(synthetic())
    assert result["screen_pass"]
    assert abs(result["frequency_hz"] / 8e9 - 1) < 0.0001
    assert result["duty_range"][0] == pytest.approx(0.5, abs=0.0001)
    assert len(result["devices"]) == 18


@pytest.mark.parametrize("fault", ["stopped", "same_clock", "weak", "bad_duty", "low_vce", "overcurrent"])
def test_metrology_rejects_actual_waveform_faults(fault):
    d = synthetic()
    if fault == "stopped":
        d["v(clkp)"] = [1.4] * len(d["time"])
        d["v(clkn)"] = [1.1] * len(d["time"])
    elif fault == "same_clock":
        d["v(clkn)"] = list(d["v(clkp)"])
    elif fault == "weak":
        d["v(clkp)"] = [1.25 + (x-1.25)/100 for x in d["v(clkp)"]]
        d["v(clkn)"] = [2.5-x for x in d["v(clkp)"]]
    elif fault == "bad_duty":
        d["v(clkp)"] = [1.25 + (0.23 if (t*8e9) % 1 < 0.2 else -0.23) for t in d["time"]]
        d["v(clkn)"] = [2.5-x for x in d["v(clkp)"]]
    elif fault == "low_vce":
        d["v(xosc.t0)"] = [2.] * len(d["time"])
    else:
        d["@q.xosc.xref.qnpn13g2[ic]"] = [0.1] * len(d["time"])
    assert not vco.measure(d)["screen_pass"]


@pytest.mark.parametrize("line", ["Warning: ignored model", "Error: native abort", "temperature limiting NaN", "starting gmin stepping", "singular matrix", "timestep too small"])
def test_numerical_failures_never_hidden_by_good_waveform(line):
    assert not vco.diagnostics(line)["clean"]
    assert vco.diagnostics(line)["lines"] == [line]


def test_native_negative_mutations_change_real_devices():
    for fault, new in (("no_feedback", "XP0 p0 p0 t0"), ("same_clock", "XFN avdd bo_p clkn")):
        changed = vco.circuit(dict(vco.BASE, fault=fault))
        assert changed != vco.CIRCUIT.read_text()
        assert new in changed
    assert "2.3)" in vco.deck(dict(vco.BASE, fault="no_bias"), Path("/models"), [])
    assert "CLOADP clkp 0 1e-10" in vco.deck(dict(vco.BASE, fault="overload"), Path("/models"), [])


def test_native_table_rejects_bad_vectors_and_time(tmp_path):
    file = tmp_path / "wave.dat"
    file.write_text("time broken\n0 0\n")
    with pytest.raises(ValueError, match="vector"):
        vco.read_wave(file)
    d = synthetic()
    header = ["time", *vco.vectors()]
    d["time"][10] = d["time"][9]
    file.write_text(" ".join(header) + "\n" + "\n".join(" ".join(str(d[k][i]) for k in header) for i in range(len(d["time"]))))
    with pytest.raises(ValueError, match="time"):
        vco.read_wave(file)


def test_measurement_has_no_mutation_of_input():
    d = synthetic()
    before = copy.deepcopy(d)
    vco.measure(d)
    assert d == before
