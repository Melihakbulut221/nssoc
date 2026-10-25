# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent measurement faults and exact native divider/source/deck guards."""

import copy
import math
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_div2 as d  # noqa: E402


@pytest.fixture(scope="module")
def case():
    return d.cases()[0]


@pytest.fixture(scope="module")
def waveform(case):
    # Analytical clean 8/4GHz data tests only the independent measurement code;
    # it is never presented as a transistor simulation result.
    t = [i * 1e-12 for i in range(12001)]
    values = {name: [1.45] * len(t) for name in d.vectors(case)}
    values["time"] = t
    for rail, value in [
        ("avdd", 2.3),
        ("dvdd", 2.5),
        ("vctrl", 0.85),
        ("xosc.ref", 0.85),
        ("xosc.bref", 0.85),
        ("xdiv.ref", 0.85),
    ]:
        values[f"v({rail})"] = [value] * len(t)
    for name in ("p0", "p1", "p2", "n0", "n1", "n2", "bo_p", "bo_n"):
        values[f"v(xosc.{name})"] = [1.9] * len(t)
    for name in ("t0", "t1", "t2", "bt"):
        values[f"v(xosc.{name})"] = [0.9] * len(t)
    for stage in ("xm", "xs"):
        values[f"v(xdiv.{stage}.te)"] = [0.65] * len(t)
    clock = [0.24 * math.sin(2 * math.pi * 8e9 * x) for x in t]
    output = [0.12 * math.sin(2 * math.pi * 4e9 * (x - 20e-12)) for x in t]
    for p, n, cm, diff in [
        ("clkp", "clkn", 1.25, clock),
        ("qp", "qn", 2.25, output),
        ("xdiv.mp", "xdiv.mn", 2.25, output),
    ]:
        values[f"v({p})"] = [cm + x for x in diff]
        values[f"v({n})"] = [cm - x for x in diff]
    hbts, resistors = d.device_contract(case)
    for name, (_, nx) in hbts.items():
        values["@q." + name + ".qnpn13g2[ic]"] = [nx * 0.001] * len(t)
    for name in resistors:
        values["v(" + name + ".dt)"] = [0.5] * len(t)
    for source in ("vdd", "vddiv", "vctrl"):
        values["i(" + source + ")"] = [-0.004] * len(t)
    assert set(values) == {"time", *d.vectors(case)}
    return values


def test_exact_native_hierarchy_and_feedback(case):
    for path, digest in d.FROZEN.items():
        assert d.sha(path) == digest
    hbts, resistors = d.device_contract(case)
    assert len(hbts) == 33 and len(resistors) == 18
    assert hbts["xdiv.xm.xdp"] == (("xdiv.mn", "qn", "xdiv.xm.se"), 2)
    assert hbts["xdiv.xm.xdn"] == (("xdiv.mp", "qp", "xdiv.xm.se"), 2)
    assert hbts["xdiv.xs.xdp"] == (("qn", "xdiv.mp", "xdiv.xs.se"), 2)
    assert hbts["xdiv.xm.xcs"][0][1] == "clkn"
    assert hbts["xdiv.xs.xcs"][0][1] == "clkp"


def test_deck_contains_native_zero_ramp_not_a_behavioral_divider(case):
    text = d.deck(case, Path("/models"), [Path("/models/native.osdi")])
    body = "\n".join(
        line for line in text.splitlines() if not line.startswith("*")
    ).lower()
    assert "pulse(" not in body and " sin(" not in body
    assert (
        ".ic " not in body
        and " uic" not in body
        and ".nodeset" not in body
        and "\nalter " not in body
    )
    assert body.count("pwl(0 0 5e-10 ") == 3
    assert "xosc clkp clkn vctrl avdd 0 0 nssoc_clock_vco_hbt" in body
    assert "xdiv clkp clkn qp qn dvdd 0 0 nssoc_clock_div2_hbt" in body
    assert '.include "rx_sampler_hbt_v2.spice"' in body
    assert ".options reltol=1e-4 abstol=1e-12" in body


def test_analytical_measurement_oracle_is_exact_two(case, waveform):
    m = d.measure(waveform, case)
    assert m["screen_pass"] and m["functional_divide_pass"]
    assert abs(m["input_frequency_hz"] / 8e9 - 1) < 1e-10
    assert abs(m["output_frequency_hz"] / 4e9 - 1) < 1e-10
    assert set(m["input_edges_per_output_period"]) == {2}
    assert set(m["output_toggle_input_edge_steps"]) == {1}
    assert max(abs(x - 0.5) for x in m["duty_range"]) < 1e-10


@pytest.mark.parametrize(
    "frequency,delay,amplitude",
    [
        (8e9, 20e-12, 0.12),
        (2e9, 20e-12, 0.12),
        (4e9, 80e-12, 0.12),
        (4e9, 20e-12, 0.01),
    ],
)
def test_wrong_frequency_phase_or_swing_cannot_pass(
    case, waveform, frequency, delay, amplitude
):
    data = dict(waveform)
    diff = [
        amplitude * math.sin(2 * math.pi * frequency * (x - delay))
        for x in data["time"]
    ]
    data["v(qp)"] = [2.25 + x for x in diff]
    data["v(qn)"] = [2.25 - x for x in diff]
    m = d.measure(data, case)
    assert not m["screen_pass"] and not m["functional_divide_pass"]


@pytest.mark.parametrize(
    "vector,index,value,check",
    [
        ("v(xdiv.xm.te)", 5000, 0.2, "operating_headroom"),
        ("v(xdiv.ref)", 1000, 1.7, "full_capture_maximum_vce"),
        ("@q.xdiv.xref.qnpn13g2[ic]", 1000, 0.01, "current_density"),
    ],
)
def test_unsafe_operating_or_startup_point_is_not_hidden(
    case, waveform, vector, index, value, check
):
    data = dict(waveform)
    data[vector] = list(data[vector])
    data[vector][index] = value
    measured = d.measure(data, case)
    assert not measured["screen_pass"] and not measured["checks"][check]
    # Functional behavior still passes; an unrelated unsafe-current screen must
    # not falsely qualify a deliberately broken divide-by-two negative control.
    assert measured["functional_divide_pass"]
    assert not d.expected_result(
        dict(
            case=dict(case, fault="no_toggle"),
            returncode=0,
            numerical=dict(clean=True),
            measurement=measured,
        )
    )


@pytest.mark.parametrize(
    "change",
    [
        {"returncode": 1},
        {"returncode": None},
        {"execution_failure": "timeout"},
        {"numerical": {"clean": False}},
        {"measurement": {}},
    ],
)
def test_runtime_or_missing_measurements_never_become_negative_pass(case, change):
    row = dict(
        case=dict(case, fault="no_toggle"),
        returncode=0,
        numerical=dict(clean=True),
        measurement=dict(screen_pass=False, functional_divide_pass=False),
    )
    row.update(change)
    assert not d.expected_result(row)


@pytest.mark.parametrize("fault", ["no_toggle", "same_phase", "no_bias", "same_clock"])
def test_native_fault_is_explicit_and_uses_its_actual_pin_mapping(case, fault):
    c = dict(case, fault=fault)
    assert d.device_contract(c)[0].keys() == d.device_contract(case)[0].keys()
    if fault == "same_clock":
        assert d.circuit(c) == d.circuit(case)
        assert d.device_contract(c)[0]["xdiv.xm.xcs"][0][1] == "clkp"
    else:
        assert d.circuit(c) != d.circuit(case)


@pytest.mark.parametrize(
    "field,value", [("step_s", 0), ("step_s", 2e-12), ("ramp_s", 0), ("ramp_s", 3e-9)]
)
def test_unsupported_native_step_or_ramp_rejected(case, field, value):
    with pytest.raises(ValueError):
        d.deck(dict(case, **{field: value}), Path("/models"), [])


def test_wave_reader_rejects_time_gap_column_change_and_nonfinite(tmp_path, case):
    path = tmp_path / "wave.dat"
    header = " ".join(["time", *d.vectors(case)]) + "\n"
    row = " ".join(["0"] * (len(d.vectors(case)) + 1)) + "\n"
    path.write_text(header.replace("v(avdd)", "v(not_avdd)") + row)
    with pytest.raises(ValueError, match="vector"):
        d.read_wave(path, case)
    path.write_text(header + row.replace("0", "nan", 1))
    with pytest.raises(ValueError, match="nonfinite"):
        d.read_wave(path, case)
    path.write_text(
        header
        + "".join(
            " ".join([str(i * 12e-12), *["0"] * len(d.vectors(case))]) + "\n"
            for i in range(1001)
        )
    )
    with pytest.raises(ValueError, match="step"):
        d.read_wave(path, case)
