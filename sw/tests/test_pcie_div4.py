# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physical cascade binding and fail-closed capture controls; no ideal divider."""

import json
import copy
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_div4 as d  # noqa: E402


@pytest.mark.parametrize("case", d.cases("finite"), ids=lambda x: x["name"])
def test_all_real_devices_are_bound_and_initialized(case):
    h, r = d.device_contract(case)
    assert len(h) == 60 and len(r) == 35
    assert sum(n.startswith("xosc.") for n in h) == 30
    assert sum(n.startswith("xdiv.xfirst.") for n in h) == 15
    assert sum(n.startswith("xdiv.xsecond.") for n in h) == 15
    assert all(1 <= nx <= 10 for _, nx in h.values())
    vectors = d.vectors(case)
    assert len(vectors) == len(set(vectors)) == 215
    for n in h:
        assert "@q." + n + ".qnpn13g2[ic]" in vectors
        assert "v(" + n + ".t)" in vectors
    text = d.deck(case, Path("/models"), [Path("/real.osdi")])
    assert text.count("alter @q.") == 60
    assert "PULSE" not in text and ".ic " not in text and "uic" not in text
    assert "tran " + format(case["step_s"], ".12g") + " 2e-08 0 " in text
    assert text.count("PWL(0 0 ") == 3
    assert ".options reltol=1e-4 abstol=1e-12" in text


@pytest.mark.parametrize(
    "name",
    ["second_no_toggle", "second_same_phase", "second_no_bias", "second_same_clock"],
)
def test_real_fault_only_changes_second_core(name):
    baseline = dict(d.old.BASE)
    clean, _ = d.device_contract(baseline)
    bad, _ = d.device_contract(dict(baseline, fault=name))
    changed = {n for n in clean if clean[n] != bad[n]}
    if name == "second_no_bias":
        # Bias resistor terminals change; all HBT terminal names remain real.
        assert not changed
        assert (
            "XBIAS avss ref sub"
            in d.source_texts(dict(baseline, fault=name))[d.old.CIRCUIT.name]
        )
    else:
        assert changed and all(n.startswith("xdiv.xsecond.") for n in changed)
    for p in (d.VCO, d.CONDITIONER, d.old.LATCH):
        assert d.source_texts(dict(baseline, fault=name))[p.name] == p.read_text()


@pytest.mark.parametrize(
    "before,after",
    [
        ("XDP ckp avss", "XDP ckp avdd"),
        ("XSP s1p ckp", "XSP s1n ckp"),
        ("w=2u l=4u", "w=2u l=8u"),
        ("XSECOND ckp ckn", "XSECOND ckn ckp"),
    ],
)
def test_wrong_interstage_physical_topology_rejected(
    tmp_path, monkeypatch, before, after
):
    p = tmp_path / "changed.spice"
    p.write_text(d.CIRCUIT.read_text().replace(before, after, 1))
    monkeypatch.setattr(d, "CIRCUIT", p)
    with pytest.raises(ValueError, match="topology"):
        d.verify_sources()


def test_off_flags_are_native_complete_unique_and_true():
    case = dict(d.old.BASE)
    body = "".join(
        f"NSSOC_DIV4_FLAG_BEGIN {n}\n device {n[:21]}\n off 1\nNSSOC_DIV4_FLAG_END\n"
        for n in d.identities(case)
    )
    assert len(d.read_flags(body, case)) == 60
    for changed in (
        body.replace("off 1", "off 0", 1),
        body + body,
        body.replace("q.xdiv.xsecond.xref.qnpn13g2", "q.xdiv.fake.qnpn13g2"),
    ):
        with pytest.raises(ValueError):
            d.read_flags(changed, case)


def test_initial_op_covers_thermal_and_electrical_without_forced_state(tmp_path):
    case = dict(d.old.BASE)
    names = d.electrical_vectors(case)
    p = tmp_path / "initial-op.dat"
    prefix = "time " + " ".join(names) + "\n"
    zeros = ["0"] * (len(names) + 1)
    p.write_text(prefix + " ".join(zeros) + "\n")
    assert len(d.initial_op(p, case)) == 203
    for value in ("nan", "inf", "1e-8"):
        bad = zeros.copy()
        bad[-1] = value
        p.write_text(prefix + " ".join(bad) + "\n")
        with pytest.raises(ValueError):
            d.initial_op(p, case)
    p.write_text(prefix.replace(names[-1], "v(unobserved)") + " ".join(zeros) + "\n")
    with pytest.raises(ValueError):
        d.initial_op(p, case)


def test_twenty_ns_required_in_addition_to_frozen_reader(monkeypatch):
    monkeypatch.setattr(d, "_read", lambda *_: {"time": [0.0, 12e-9]})
    with pytest.raises(ValueError, match="20ns"):
        d.read_wave("unused", d.old.BASE)


def test_atomic_write_does_not_destroy_previous_receipt_on_partial_failure(
    tmp_path, monkeypatch
):
    p = tmp_path / "result.json"
    d.atomic(p, {"status": "PRESERVED"})
    original = p.read_bytes()
    original_write = Path.write_text

    def fail(path, data, *args, **kwargs):
        original_write(path, data[:8], *args, **kwargs)
        raise OSError("simulated ENOSPC")

    monkeypatch.setattr(Path, "write_text", fail)
    with pytest.raises(OSError, match="ENOSPC"):
        d.atomic(p, {"status": "INCOMPLETE"})
    assert p.read_bytes() == original
    assert json.loads(p.read_text())["status"] == "PRESERVED"


def valid_record(fault=""):
    case = dict(d.old.BASE, name="nominal", fault=fault)
    return dict(
        case=case,
        returncode=0,
        numerical={"clean": True},
        flags_observed=dict.fromkeys(d.identities(case), 1),
        zero_initial_op=dict.fromkeys(d.electrical_vectors(case), 0.0),
        measurement=dict(
            screen_pass=not fault,
            functional_divide_pass=not fault,
            stages={
                "first": {"functional_divide_pass": True},
                "second": {"functional_divide_pass": not fault},
            },
        ),
    )


@pytest.mark.parametrize("fault", ["", "second_no_toggle"])
def test_native_failure_or_incomplete_observations_cannot_be_an_expected_outcome(fault):
    clean = valid_record(fault)
    assert d.accepted(clean)
    changes = [
        ("returncode", None),
        ("returncode", 1),
        ("execution_failure", "timeout"),
        ("numerical", {"clean": False}),
        ("flags_observed", {}),
        ("zero_initial_op", {}),
    ]
    for key, value in changes:
        changed = copy.deepcopy(clean)
        changed[key] = value
        assert not d.accepted(changed)
    for key in ("flags_observed", "zero_initial_op"):
        changed = copy.deepcopy(clean)
        changed[key][next(iter(changed[key]))] = float("nan")
        assert not d.accepted(changed)


def test_electrical_failure_or_broken_first_stage_does_not_validate_second_stage_fault():
    row = valid_record("second_no_toggle")
    row["measurement"].update(screen_pass=False, functional_divide_pass=True)
    row["measurement"]["stages"]["second"]["functional_divide_pass"] = True
    assert not d.accepted(row)
    row = valid_record("second_no_toggle")
    row["measurement"]["stages"]["first"]["functional_divide_pass"] = False
    assert not d.accepted(row)


def kinematic_trace(second_hz=2e9):
    """Independent periodic port oracle, explicitly not an electrical model."""
    case = dict(d.old.BASE, name="nominal")
    time = [i * 2e-12 for i in range(10001)]
    data = {n: [0.0] * len(time) for n in d.vectors(case)}
    data["time"] = time
    for p, n, frequency, phase, cm, amplitude in (
        ("clkp", "clkn", 8e9, 13e-12, 1.4, 0.2),
        ("xdiv.xfirst.ckp", "xdiv.xfirst.ckn", 8e9, 13e-12, 1.4, 0.2),
        ("xdiv.s1p", "xdiv.s1n", 4e9, 33e-12, 2.3, 0.15),
        ("xdiv.ckp", "xdiv.ckn", 4e9, 33e-12, 1.4, 0.15),
        ("qp", "qn", second_hz, 53e-12, 2.3, 0.15),
    ):
        wave = [
            amplitude * math.sin(2 * math.pi * frequency * (t - phase)) for t in time
        ]
        data["v(" + p + ")"] = [cm + x for x in wave]
        data["v(" + n + ")"] = [cm - x for x in wave]
    for n in d.CONDITIONERS:
        data["@n." + n + ".nr1[r_dc]"] = [500.0] * len(time)
    return case, data


def test_exact_four_edge_relation_and_wrong_second_frequency():
    case, data = kinematic_trace()
    m = d.measure(data, case)
    assert m["functional_divide_pass"]
    assert set(m["input_edges_per_output_period"]) == {4}
    assert m["output_frequency_hz"] == pytest.approx(2e9, rel=1e-4)
    assert m["stages"]["first"]["functional_divide_pass"]
    assert m["stages"]["second"]["functional_divide_pass"]
    # No electrical model is present: this cannot pass the complete screen.
    assert not m["screen_pass"]
    bad_case, bad_data = kinematic_trace(3e9)
    broken = d.measure(bad_data, bad_case)
    assert broken["stages"]["first"]["functional_divide_pass"]
    assert not broken["stages"]["second"]["functional_divide_pass"]
    assert not broken["checks"]["exactly_four_input_periods"]
    assert not broken["functional_divide_pass"]


def test_added_real_driver_branch_current_is_a_full_capture_gate():
    case, data = kinematic_trace()
    data["@q.xosc.xfpd3.qnpn13g2[ic]"][1] = 0.0121
    m = d.measure(data, case)
    assert m["functional_divide_pass"]
    assert not m["checks"]["full_capture_current_density"]
    assert m["devices"]["xosc.xfpd3"]["max_capture_ic_a_per_nx"] > 0.003
