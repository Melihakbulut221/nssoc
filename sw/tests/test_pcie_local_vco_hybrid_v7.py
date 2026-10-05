# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Model interfaces and finite powered-wave failure boundaries."""

import gzip
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import build_pcie_local_vco_hybrid_v7 as h
import diagnose_pcie_local_vco_powered_v8 as p


def test_native_and_foundry_mos_terminal_order_is_explicit():
    assert h.NATIVE_ORDER["sg13_hv_pmos"] == ["S", "G", "D", "B"]
    assert h.MODEL_ORDER["sg13_hv_pmos"] == ["D", "G", "S", "B"]
    assert h.CENSUS["sg13_hv_pmos"] == 4 and sum(h.CENSUS.values()) == 62


@pytest.mark.parametrize("model", ["ptap1", "ntap1"])
def test_native_contact_uses_exact_area_and_perimeter_formula(model):
    parameters = h.model_params(
        dict(model=model, parameters=dict(A=4.0, P=8.0)),
        {model + "_raspec": "0.980n", model + "_rpspec": "0.980m"},
    )
    assert abs(h.number(parameters["R"]) - h.Decimal(245) / 3) < h.Decimal("1e-24")
    assert parameters["w"] == parameters["l"] == "2u"


@pytest.mark.parametrize(
    "parameters", [dict(A=8.0, P=8.0), dict(A=4.0, P=9.0), dict(A=0.0, P=0.0)]
)
def test_changed_finite_contact_geometry_rejects(parameters):
    with pytest.raises(ValueError, match="Contact geometry"):
        h.model_params(dict(model="ptap1", parameters=parameters), {})


def test_separate_w8_native_junction_geometry_is_preserved():
    parameters = dict(L=0.45, W=8.0, AS=2.72, AD=2.72, PS=16.68, PD=16.68, rfmode=0.0)
    result = h.model_params(dict(model="sg13_hv_pmos", parameters=parameters), {})
    assert result["w"] == "8.0u" and result["l"] == "0.45u"
    assert result["as"] == result["ad"] == "2.72p"
    assert result["ps"] == result["pd"] == "16.68u"
    assert result["ng"] == result["m"] == "1"


@pytest.mark.parametrize("bad", ["nan", "inf", "1e4evil", "1;quit", "2mil", ""])
def test_invalid_spice_numbers_reject(bad):
    with pytest.raises(ValueError):
        h.number(bad)


@pytest.mark.parametrize(
    "wrong",
    [
        "X1 b c e body npn13G2 Nx=1",
        "X1 c b e AVSS npn13G2 Nx=1",
        "X1 c b e body npn13G2 Nx=2",
        "",
        "X1 c b e body npn13G2 Nx=1\nRshort c b 0",
    ],
)
def test_device_anchor_body_or_extra_wire_change_rejects(wrong):
    with pytest.raises(ValueError, match="contract changed"):
        h.verify_output(wrong, "X1 c b e body npn13G2 Nx=1")


CONTRACT = dict(
    vectors=["v(c)", "v(e)", "i(q)", "v(p)", "v(n)"],
    hbts=[dict(id=1, Nx=1, C="v(c)", B="v(p)", E="v(e)", current="i(q)")],
    clock_inputs=[],
    clock_drivers=[["v(p)", "v(n)"]],
    sampler_outputs=[],
)


def write_wave(path, fault=None):
    with gzip.open(path, "wt") as f:
        header = ["time", *CONTRACT["vectors"]]
        if fault == "header":
            header[-1] = "v(wrong)"
        f.write(" ".join(header) + "\n")
        for i in range(12001):
            if fault == "gap" and i == 7000:
                continue
            if fault == "early_end" and i > 10000:
                break
            t = i * 1e-12
            vce = 0.8 if fault != "post_window_vce" or i != 7000 else 0.399
            if fault == "startup_upper" and i == 1000:
                vce = 1.61
            signal = 0.4 * math.sin(2 * math.pi * 8e9 * t) if fault != "static" else 0.4
            row = [t, 0.2 + vce, 0.2, 0.001, signal / 2, -signal / 2]
            if fault == "current" and i == 7000:
                row[3] = 0.0031
            if fault == "nonfinite" and i == 7000:
                row[1] = float("nan")
            if fault == "backwards" and i == 7000:
                row[0] = (i - 2) * 1e-12
            if fault == "missing_column" and i == 7000:
                row.pop()
            f.write(" ".join(f"{v:.17g}" for v in row) + "\n")


def test_actual_all_sample_window_and_clock_census(tmp_path):
    path = tmp_path / "wave.gz"
    write_wave(path)
    r = p.wave_measure(path, CONTRACT)
    assert r["samples"] == 12001 and r["active_samples"] == 6001
    assert r["operating_window_start_s"] == 6e-9
    assert r["min_vce"] == 0.8 and r["signals"][0]["rising_edges"] >= 47
    assert abs(r["signals"][0]["mean_frequency_hz"] - 8e9) < 1


@pytest.mark.parametrize(
    "fault", ["header", "gap", "early_end", "nonfinite", "backwards", "missing_column"]
)
def test_incomplete_or_forged_wave_rejects(tmp_path, fault):
    path = tmp_path / "wave.gz"
    write_wave(path, fault)
    with pytest.raises(ValueError):
        p.wave_measure(path, CONTRACT)


@pytest.mark.parametrize(
    "fault", ["startup_upper", "post_window_vce", "current", "static"]
)
def test_real_finite_physics_failures_remain_visible(tmp_path, fault):
    path = tmp_path / "wave.gz"
    write_wave(path, fault)
    r = p.wave_measure(path, CONTRACT)
    if fault == "startup_upper":
        assert r["full_time_max_vce"] == 1.61 and r["max_vce"] == 0.8
    elif fault == "post_window_vce":
        assert r["min_vce"] < 0.4
    elif fault == "current":
        assert r["peak_abs_current_per_emitter_a"] > 0.003
    else:
        assert (
            r["signals"][0]["rising_edges"] == 0
            and r["signals"][0]["mean_frequency_hz"] is None
        )


def test_only_explicit_external_bias_changes_the_native_recipe():
    import diagnose_pcie_local_vco_powered_v1 as previous

    comp = dict(
        ports=[
            "CLKP",
            "CLKN",
            "VCTRL",
            "AVDD",
            "AVSS",
            "SUB",
            "BODY_SUBSTRATE",
            "WIRE_CREF",
        ]
    )
    contract = dict(hbts=[dict(id=1)], vectors=["v(CLKP)", "v(CLKN)"])
    models, osdis = Path("/models"), [Path("/native/model.osdi")]
    nominal = p.deck(comp, contract, models, osdis, 0.85)
    prior = previous.deck(comp, contract, models, osdis)
    assert nominal == prior.replace(
        "nssoc_vco_local_hybrid_open_v1", "nssoc_vco_local_hybrid_open_v2"
    )
    for bias in (0.4, 0.6):
        assert p.deck(comp, contract, models, osdis, bias) == nominal.replace(
            "Vs_vctrl VCTRL 0 PWL(0 0 500p 0.85)",
            f"Vs_vctrl VCTRL 0 PWL(0 0 500p {bias})",
        )
    # Diagnostic bias selection never changes source ramp, periodic stimulus,
    # operating window, capacitance, numerical tolerance or transistor limits.
    assert p.STOP == previous.STOP == 12e-9
    assert p.STEP == previous.STEP == 1e-12
    assert p.BEGIN == previous.BEGIN == 6e-9


@pytest.mark.parametrize("bias", [0.2, 1.0, float("nan")])
def test_unreviewed_bias_point_rejects_before_deck_generation(bias):
    with pytest.raises(ValueError, match="Predeclared VCTRL"):
        p.deck({}, {}, Path("/models"), [], bias)
