# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real switch connectivity, source provenance and complete native observations."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_clock_trim_v1 as trim  # noqa: E402


@pytest.mark.parametrize("width", (32, 64, 128))
@pytest.mark.parametrize("bias", (1, 4))
def test_exact_existing_hbts_and_noncap_elements_retained(width, bias):
    text = trim.circuit(dict(trim.old.BASE), width, bias)
    original = trim.CIRCUIT.read_text()
    assert trim.driver.contract(text, 4) == trim.driver.contract(original, 4)
    lines = [
        x for x in original.splitlines() if x.startswith("X") and "cap_cmim" not in x
    ]
    assert all(x in text.splitlines() for x in lines)
    assert text.count("npn13G2 ") == 30
    assert text.count("cap_cmim ") == 18
    assert text.count("sg13_hv_nmos ") == 6
    assert text.count("rppd ") == 23
    assert not any(
        x[0] in "BVSM" for x in text.splitlines() if x and not x.startswith("*")
    )


def test_actual_mos_bridge_two_caps_and_two_bias_resistors_per_bit_stage():
    text = trim.circuit(dict(trim.old.BASE), 64, 4)
    for stage in range(3):
        for bit in range(2):
            assert (
                f"XTSW{stage}{bit} tp{stage}{bit}p trim{bit} tp{stage}{bit}n avss sg13_hv_nmos"
                in text
            )
            for side in "pn":
                assert (
                    f"XTC{stage}{bit}{side} {side}{stage} tp{stage}{bit}{side} cap_cmim"
                    in text
                )
                assert (
                    f"XTR{stage}{bit}{side} tp{stage}{bit}{side} tmid sub rppd" in text
                )
    assert "XTBH avdd tmid sub rppd w=8u" in text
    assert "XTBL tmid avss sub rppd w=8u" in text


@pytest.mark.parametrize("width,bias", ((0, 4), (64, 0), (256, 4), (64, 2)))
def test_unreviewed_geometry_rejected(width, bias):
    with pytest.raises(ValueError):
        trim.circuit(dict(trim.old.BASE), width, bias)


@pytest.mark.parametrize("code", (0, 1, 2))
def test_real_gate_code_voltage_and_full_model_observations(code):
    case = dict(trim.old.BASE, code=code)
    hbts = trim.driver.contract(trim.circuit(case, 64, 4), 4)
    text = trim.deck(
        case, Path("/models"), [Path("/native.osdi")], 0.9e-12, 0.92e-12, hbts
    )
    for bit in range(2):
        assert (
            f"VTRIM{bit} trim{bit} 0 PWL(0 0 5e-10 {2.3 if code > bit else 0:.12g})"
            in text
        )
    assert text.count("alter @q.xosc.") == 30
    assert "tran 1e-12 12n 0 1e-12" in text
    assert "uic" not in text and ".ic " not in text
    assert ".options reltol=1e-4 abstol=1e-12" in text
    observed = trim.vectors(hbts)
    assert set(trim.driver.vectors(hbts)).issubset(observed)
    assert len(observed) == len(set(observed))
    assert len([x for x in observed if ".nsg13_hv_nmos[" in x]) == 18
    assert len([x for x in observed if x.endswith(".dt)")]) == 23


@pytest.mark.parametrize("code", (-1, 3, 4))
def test_invalid_gate_code_rejected(code):
    hbts = trim.driver.contract(trim.circuit(dict(trim.old.BASE), 64, 4), 4)
    with pytest.raises(ValueError, match="thermometer"):
        trim.deck(
            dict(trim.old.BASE, code=code), Path("/models"), [], 0.9e-12, 0.92e-12, hbts
        )


def test_actual_stuck_off_mutates_gate_rails_not_model_or_capacitor_geometry():
    case = dict(trim.old.BASE, code=2)
    hbts = trim.driver.contract(trim.circuit(case, 64, 4), 4)
    good = trim.deck(case, Path("/models"), [], 0.9e-12, 0.92e-12, hbts)
    bad = trim.deck(
        dict(case, trim_fault="stuck_off"), Path("/models"), [], 0.9e-12, 0.92e-12, hbts
    )
    assert bad == good.replace(
        "VTRIM0 trim0 0 PWL(0 0 5e-10 2.3)", "VTRIM0 trim0 0 PWL(0 0 5e-10 0)"
    ).replace("VTRIM1 trim1 0 PWL(0 0 5e-10 2.3)", "VTRIM1 trim1 0 PWL(0 0 5e-10 0)")


def test_original_seven_corner_identity_and_no_duplicate_points():
    cases = trim.cases("corners")
    assert len(cases) == len({x["name"] for x in cases}) == 42
    assert len(trim.cases("gaps")) == 18
    assert len(trim.cases("nominal")) == 6
    for label, mods in trim.driver.parent.TUNING:
        rows = [x for x in cases if x["name"].startswith(label + "_")]
        assert len(rows) == 6
        assert all(all(x[k] == v for k, v in mods.items()) for x in rows)


@pytest.mark.parametrize(
    "mutation", ("time0", "reverse", "missing_last", "nan", "missing_vector")
)
def test_raw_time_and_voltage_bridge_rejects_incomplete_or_mutated_capture(
    tmp_path, mutation
):
    case = dict(trim.old.BASE, code=0)
    hbts = trim.driver.contract(trim.circuit(case, 64, 4), 4)
    vs = trim.vectors(hbts)
    times = [i * 1e-12 for i in range(12001)]
    if mutation == "time0":
        times = times[1:]
    if mutation == "reverse":
        times[5000] = times[4999]
    if mutation == "missing_last":
        times = times[:-1]
    if mutation == "missing_vector":
        vs = vs[:-1]
    path = tmp_path / "wave.dat"
    with path.open("w") as f:
        f.write("time " + " ".join(vs) + "\n")
        for i, t in enumerate(times):
            row = ["0"] * len(vs)
            if mutation == "nan" and i == 2000:
                row[-1] = "nan"
            f.write(str(t) + " " + " ".join(row) + "\n")
    with pytest.raises(ValueError):
        trim.read_wave(path, hbts, case)


@pytest.mark.parametrize(
    "mutation", ("none", "gate_bulk", "wrong_gate", "forward_body")
)
def test_native_switch_terminal_safety_and_gate_readback_are_separate(
    monkeypatch, mutation
):
    # Checker-only test: parent clock checks stay true while one observed
    # switch condition changes. This is not an analog simulation.
    monkeypatch.setattr(
        trim.driver, "measure", lambda data, hbts: {"checks": {"parent": True}}
    )
    case = dict(trim.old.BASE, code=2)
    data = {"time": [0.0, 4e-9, 12e-9]}
    gate = 2.3
    if mutation == "gate_bulk":
        case["supply"] = gate = 4.0
    for bit in range(2):
        data[f"v(trim{bit})"] = [0, gate, gate]
    for plate in trim.PLATES:
        data[f"v(xosc.{plate})"] = [0, 1.0, 1.0]
    for name in trim.SWITCHES:
        for field in ("ids", "idb", "isb"):
            data[f"@n.xosc.{name}.nsg13_hv_nmos[{field}]"] = [0, 0, 0]
    if mutation == "wrong_gate":
        data["v(trim1)"] = [0, 0, 0]
    if mutation == "forward_body":
        data["v(xosc.tp00p)"] = [0, -0.2, 0]
    result = trim.measure(data, {}, case)
    assert result["screen_pass"] == (mutation == "none")
    if mutation == "wrong_gate":
        assert result["checks"]["switch_terminal_voltage"]
        assert not result["checks"]["native_trim_gate_rails"]
    if mutation == "gate_bulk":
        # VGS/VGD are only3V; independent gate/body4V check remains essential.
        assert result["checks"]["native_trim_gate_rails"]
        assert not result["checks"]["switch_terminal_voltage"]
