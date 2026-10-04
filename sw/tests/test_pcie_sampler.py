# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded sampler contract tests; native SPICE campaigns are separate evidence."""

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_sampler as s  # noqa: E402
import review_pcie_sampler as review  # noqa: E402


def test_native_geometry_and_old_rx_are_frozen():
    for p, sha in s.FIXED.items():
        assert s.rx.tx.sha(s.ROOT / p) == sha
    text = s.NETLIST.read_text()
    assert (
        ".subckt nssoc_rx_sampler_hbt dp dn qp qn clkp clkn avdd avss sub iref" in text
    )
    assert text.count("npn13G2 Nx=2") == 4
    assert text.count("npn13G2 Nx=4") == 3
    assert text.count("npn13G2 Nx=1") == 1
    assert text.count("rppd w=8u l=2.04u b=0 sw_et=1") == 2
    assert text.count("rppd w=1u l=38.4u b=0 sw_et=1") == 2
    assert text.count("rppd w=1u l=3.6u b=0 sw_et=1") == 4
    # The child latch is instantiated twice; only native foundry X devices.
    elements = [line for line in text.splitlines() if line and line[0] not in ".*"]
    assert all(line.startswith("X") for line in elements)
    assert len(s.HBT) == 19 and len(s.THERMAL) == 16


def test_full_matrix_independent_extensions_and_aperture_are_distinct():
    rows = s.cases()
    assert len(rows) == 121 and len({r["name"] for r in rows}) == 121
    pvt = [c for c in rows if c["name"].startswith("hbt_")]
    assert len(pvt) == 81
    assert {c["temp"] for c in pvt} == {-40, 27, 125}
    assert {c["cap_f"] for c in pvt} == {150e-15}
    assert all(c["supply"] == 2.5 * c["rx_supply"] / 1.8 for c in pvt)
    assert len([c for c in rows if c["role"] == "aperture"]) == 25
    assert len([c for c in rows if c["fault"]]) == 6
    assert all(
        c["role"] == "extension" for c in rows if c["name"].startswith("independent_")
    )


def test_prbs_complete_period_and_external_clock_bench():
    c = s.cases(True)[0]
    bits = s.sequence(c)
    assert len(bits) == 127 and set(bits) == {0, 1}
    assert len({tuple((bits + bits)[i : i + 7]) for i in range(127)}) == 127
    text = s.deck(c, Path("/model"), Path("/capture/r3_cmc.osdi"))
    assert ".options reltol=1e-4 abstol=1e-12" in text
    assert "VSAMP savdd 0 2.5" in text
    assert "ISAMP savdd sr 0.0005" in text
    assert "XRX ip inn op on avdd 0 0 ref cm nssoc_rx_hbt_rsil_v2" in text
    assert "RSP sp ip 50" in text and "RCP scp0 scp 10" in text
    assert "CQP qp 0 1.5e-13" in text
    assert "XSAMP op on qp qn scp scn savdd 0 0 sr nssoc_rx_sampler_hbt" in text
    assert "pre_osdi /capture/r3_cmc.osdi" in text


def test_feedback_negative_changes_real_native_connectivity():
    c = next(c for c in s.cases() if c["fault"] == "no_regeneration")
    mutated = s.circuit(c)
    assert mutated != s.NETLIST.read_text()
    assert "XLP qn ref he" in mutated and "XLN qp ref he" in mutated
    assert "XLP qn qp he" not in mutated and "XLN qp qn he" not in mutated
    assert s.circuit(s.cases()[0]) == s.NETLIST.read_text()


def test_clock_negative_has_no_pulse():
    c = next(c for c in s.cases() if c["fault"] == "clock_stopped")
    deck = s.deck(c, Path("/m"), Path("/o"))
    assert "PULSE" not in deck
    common = next(c for c in s.cases() if c["fault"] == "clock_common_only")
    assert common["clock_amplitude_v"] == 0


def fixture_result():
    models = Path("/native/ihp-sg13g2/libs.tech/ngspice/models")
    compiler, ng = "/native/openvaf", "/native/ngspice"
    sources = {str(s.ROOT / p): sha for p, sha in s.FIXED.items()}
    sources.update({str(models / p): sha for p, sha in s.rx.tx.MODEL_HASHES.items()})
    sources.update(
        {
            str(models.parent.parent / p): sha
            for p, sha in s.rx.resistor.RES_HASHES.items()
        }
    )
    sources.update(
        {
            str(s.NETLIST): review.digest(s.NETLIST),
            str(Path(s.__file__)): review.digest(Path(s.__file__)),
            compiler: s.OPENVAF_PIN,
            ng: next(iter(s.RUNTIMES)),
        }
    )
    return dict(
        assumptions=dict(review.ASSUMPTIONS),
        source_bytes_unchanged=True,
        ui_s=s.UI,
        bits=s.BITS,
        quick=False,
        limits=s.LIMITS,
        pdk_revision=s.rx.tx.PDK_REV,
        full_pvt_matrix_cases=81,
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
        source_sha256=sources,
        runtime_version="42",
        compile=dict(
            returncode=0,
            command=[
                compiler,
                str(models.parent.parent / "verilog-a/r3_cmc/r3_cmc.va"),
                "-o",
                "/native/run/r3_cmc.osdi",
            ],
        ),
        cases=[
            dict(
                case=c,
                execution=dict(returncode=0, command=[ng, "-n", "-b", "bench.cir"]),
            )
            for c in s.cases()
        ],
    )


@pytest.mark.parametrize("index", range(17))
def test_any_omitted_required_source_rejects(index, monkeypatch):
    result = fixture_result()
    monkeypatch.setattr(review, "verify", lambda *_: None)
    del result["source_sha256"][list(result["source_sha256"])[index]]
    with pytest.raises(ValueError):
        review.source_contract(result)


@pytest.mark.parametrize(
    "fault",
    ["missing_case", "lower_load", "changed_runtime", "new_threshold", "phy_claim"],
)
def test_source_contract_rejects_substituted_experiment(fault, monkeypatch):
    result = copy.deepcopy(fixture_result())
    monkeypatch.setattr(review, "verify", lambda *_: None)
    if fault == "missing_case":
        result["cases"].pop()
    elif fault == "lower_load":
        result["cases"][0]["case"]["cap_f"] = 1e-15
    elif fault == "changed_runtime":
        result["cases"][1]["execution"]["command"][0] = "/other/runtime"
    elif fault == "new_threshold":
        result["limits"]["min_margin_v"] = 0.05
    else:
        result["pcie_compliance"] = True
    with pytest.raises(ValueError):
        review.source_contract(result)


def synthetic_wave(case, dip=False, missing_clock=False):
    step = case["step_s"]
    ts = [i * step for i in range(round(s.STOP / step) + 1)]
    data = {n: [0.0] * len(ts) for n in s.VECTORS}
    data["time"] = ts
    bits = s.sequence(case)
    for k, t in enumerate(ts):
        rel = (t - s.START) / s.UI
        clk = 1 if (rel - 0.5) % 1 < 0.5 else -1
        data["v(scp)"][k] = 0 if missing_clock else clk * 0.15
        data["v(scn)"][k] = 0 if missing_clock else -clk * 0.15
        captured = max(0, min(s.BITS - 1, int((t - s.START - 0.6 * s.UI) // s.UI)))
        sign = 1 if bits[captured] else -1
        mag = 0.05 if dip and 32.94 <= rel <= 32.96 else 0.2
        data["v(qp)"][k] = sign * mag / 2
        data["v(qn)"][k] = -sign * mag / 2
        current = max(0, min(s.BITS - 1, int((t - s.START - 0.1 * s.UI) // s.UI)))
        sg = 1 if bits[current] else -1
        data["v(xsamp.lp)"][k] = sg * 0.1
        data["v(xsamp.ln)"][k] = -sg * 0.1
    return data


def test_continuous_hold_dip_rejects_between_three_good_samples(monkeypatch):
    c = s.cases(True)[0]
    data = synthetic_wave(c)
    monkeypatch.setattr(s.rx.rx, "read_table", lambda *_: data)
    baseline = s.measure(Path("unused"), c)
    assert baseline["checks"]["clock_census"] is True
    assert baseline["checks"]["margin"] is True
    assert baseline["continuous_hold_points"] > baseline["signed_samples"]
    data = synthetic_wave(c, dip=True)
    changed = s.measure(Path("unused"), c)
    assert changed["checks"]["clock_census"] is True
    assert changed["min_signed_margin_v"] == pytest.approx(0.05)
    assert changed["checks"]["margin"] is False


def test_missing_actual_clock_cannot_pass_from_ideal_schedule(monkeypatch):
    c = s.cases(True)[0]
    data = synthetic_wave(c, missing_clock=True)
    monkeypatch.setattr(s.rx.rx, "read_table", lambda *_: data)
    row = s.measure(Path("unused"), c)
    assert row["captured_bits"] == 0
    assert row["checks"]["clock_census"] is False
    assert row["checks"]["margin"] is False


def test_timestep_guard_rejects_missing_or_changed_actual_observation():
    base = dict(
        case=dict(name="hbt_typ_res_typ_27_1.8"),
        measurement=dict(min_signed_margin_v=0.15, sampler_supply_power_w=0.014),
    )
    half = dict(
        case=dict(name="half_timestep"),
        measurement=dict(min_signed_margin_v=0.15001, sampler_supply_power_w=0.014001),
    )
    assert s.timestep_sensitivity([base, half])["screen_pass"]
    with pytest.raises(ValueError):
        s.timestep_sensitivity([base])
    bad = copy.deepcopy(half)
    bad["measurement"]["min_signed_margin_v"] = 0.153
    assert not s.timestep_sensitivity([base, bad])["screen_pass"]


def test_initialization_nan_is_not_erased_by_finite_transient_text():
    text = "The temperature limiting function received NaN.\nInitial Transient Solution\nNo. of Data Rows: 1000\n"
    d = s.diagnostics.diagnostics(text)
    assert d["thermal_nan_reported"]
    assert not d["numerical_clean"]


@pytest.mark.parametrize("field", sorted(review.ASSUMPTIONS))
def test_external_clock_and_physical_assumptions_cannot_be_relabelled(
    field, monkeypatch
):
    result = fixture_result()
    monkeypatch.setattr(review, "verify", lambda *_: None)
    value = result["assumptions"][field]
    result["assumptions"][field] = not value if type(value) is bool else value + 1
    with pytest.raises(ValueError, match="assumptions"):
        review.source_contract(result)


def test_complete_source_contract_accepts_both_pinned_runtime_profiles(monkeypatch):
    monkeypatch.setattr(review, "verify", lambda *_: None)
    for sha, version in s.RUNTIMES.items():
        result = fixture_result()
        result["source_sha256"]["/native/ngspice"] = sha
        result["runtime_version"] = version
        models, osdi = review.source_contract(result)
        assert models == Path("/native/ihp-sg13g2/libs.tech/ngspice/models")
        assert osdi == Path("/native/run/r3_cmc.osdi")
