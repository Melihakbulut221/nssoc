# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source/topology controls; native DRC/LVS remain separate measured evidence."""

from collections import Counter
import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "hw/soc/flow"), str(ROOT / "scripts")]
import make_pcie_clock_div4_v6 as m  # noqa: E402
import check_pcie_clock_div4_v6 as c  # noqa: E402


def test_tiled_placement_has_exact_once_topology_groups_and_local_row_clearance():
    rows = m.devices(ROOT)
    plan, starts, nets = m.placement_plan(rows)
    assert set(plan) == {r["name"] for r in rows}
    assert Counter(p[0] for p in plan.values()) == {0: 23, 1: 23, 2: 30, 3: 17, 4: 26}
    assert len({(p[1], p[2]) for p in plan.values()}) == 119
    for rid in range(4):
        assert starts[rid + 1] - (starts[rid] + 90 + 10 * (len(nets[rid]) - 1)) == 50
    assert max(p[1] for p in plan.values()) <= 1320
    assert plan["OSC__XFPD1"][0] == plan["OSC__XFND1"][0] == 1
    assert abs(plan["OSC__XFPD1"][1] - plan["OSC__XFND1"][1]) == 40
    assert plan["DIV__XFIRST__XSP"][0] == 2
    assert plan["DIV__XSECOND__XM__XDP"][0] == 4


@pytest.mark.parametrize("fault", ["omit", "duplicate", "unknown"])
def test_tiled_plan_rejects_changed_primitive_census(fault):
    rows = copy.deepcopy(m.devices(ROOT))
    if fault == "omit":
        rows.pop()
    elif fault == "duplicate":
        rows[-1] = rows[0]
    else:
        rows[-1]["name"] = "UNSUPPORTED_NEW_CELL"
    with pytest.raises(ValueError):
        m.placement_plan(rows)


def test_exact_five_source_closure_and_reached_devices():
    rows = m.devices(ROOT)
    assert Counter(r["kind"] for r in rows) == dict(
        hbt=64, resistor=42, capacitor=12, pmos=1
    )
    assert Counter(r["nx"] for r in rows if r["kind"] == "hbt") == {1: 5, 2: 35, 4: 24}
    assert Counter(r["kind"] for r in rows if r["name"].startswith("DIV__")) == dict(
        hbt=34, resistor=33, capacitor=6
    )
    assert not any("NSSOC_RX_SAMPLER_HBT" == r["source_subcircuit"] for r in rows)


def test_hbt_topology_independently_matches_frozen_analog_producer():
    import characterize_pcie_div4_v5 as analog

    analog.verify_sources()
    expected, resistors = analog.device_contract(analog.cases("finite")[0])

    def path(n):
        return (
            n.replace("OSC__", "xosc.", 1)
            .replace("DIV__", "xdiv.", 1)
            .replace("__", ".")
            .lower()
        )

    def node(n):
        return {"VCO_AVDD": "avdd", "DIV_AVDD": "dvdd", "AVSS": "0", "SUB": "0"}.get(
            n, path(n)
        )

    rows = m.devices(ROOT)
    actual = {
        path(r["name"]): (tuple(node(n) for n in r["nets"][:3]), r["nx"])
        for r in rows
        if r["kind"] == "hbt"
    }
    assert actual == expected
    assert {path(r["name"]) for r in rows if r["kind"] == "resistor"} == set(resistors)


@pytest.mark.parametrize("filename", list(m.SOURCES))
def test_any_frozen_circuit_byte_mutation_is_rejected(tmp_path, filename):
    for path in m.SOURCES:
        p = tmp_path / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / path).read_bytes())
    p = tmp_path / filename
    p.write_text(p.read_text() + "\n")
    with pytest.raises(ValueError, match="Frozen source differs"):
        m.devices(tmp_path)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "unclosed",
        "outside",
        "ideal",
        "nx",
        "selfheat",
        "pmos_multiplier",
        "recursion",
        "arity",
    ],
)
def test_flatten_parser_rejects_unsupported_topology_or_geometry(fault):
    texts = m.source_texts(ROOT)
    key = "hw/soc/analog/pcie/clock_div4_hbt_v5.spice"
    s = texts[key]
    if fault == "duplicate":
        s += s
    elif fault == "unclosed":
        s = s.replace(".ends nssoc_clock_div4_hbt_v5", "")
    elif fault == "outside":
        s += "\nVFAKE qp qn 1\n"
    elif fault == "ideal":
        s = s.replace("XLREF lref lref avss sub npn13G2 Nx=1", "VFAKE qp qn 1")
    elif fault == "nx":
        s = s.replace("Nx=1", "Nx=20")
    elif fault == "selfheat":
        s = s.replace("sw_et=1", "sw_et=0", 1)
    elif fault == "pmos_multiplier":
        other = "hw/soc/analog/pcie/clock_vco_hbt_v3.spice"
        texts[other] = texts[other].replace("ng=1 m=1", "ng=1 m=2")
    elif fault == "recursion":
        s = s.replace("nssoc_clock_div2_conditioned_hbt", "nssoc_clock_div4_hbt_v5")
    else:
        s = s.replace("XFIRST clkp clkn", "XFIRST clkp")
    texts[key] = s
    with pytest.raises(ValueError):
        m.flatten(texts)


def test_exact_real_supplies_substrate_and_physical_reference():
    rows = m.devices(ROOT)
    text = m.physical_reference(ROOT)
    assert text.count("ptap1 A=4p P=8u") == 30
    assert text.count("RNTAP VCO_AVDD NWELL ntap1 A=4p P=8u") == 1
    assert ".subckt " + m.TOP + " " + " ".join(m.PORTS) in text
    assert m.PORTS == (
        "CLKP",
        "CLKN",
        "QP",
        "QN",
        "VCTRL",
        "VCO_AVDD",
        "DIV_AVDD",
        "AVSS",
        "SUB",
    )
    assert {n for r in rows for n in r["nets"] if n.endswith("AVDD")} == {
        "VCO_AVDD",
        "DIV_AVDD",
    }
    assert all(r["nets"][-1] == "SUB" for r in rows if r["kind"] in ("hbt", "resistor"))
    assert not any(
        line.startswith(("V", "I", "B", "E", "G")) for line in text.splitlines()
    )
    assert "RDIV__XLRP DIV_AVDD DIV__LP BULK rppd w=8u l=4.4u" in text
    assert "CDIV__XCP DIV__LP DIV__CKP cap_cmim w=20u l=20u" in text


@pytest.mark.parametrize("fault", c.REFERENCE_FAULTS)
def test_exact_reference_fault_binds_once_and_cannot_be_silent(fault):
    text = m.physical_reference(ROOT)
    changed = c.fault_reference(text, fault)
    assert changed != text
    with pytest.raises(ValueError, match="exactly once"):
        c.fault_reference(changed, fault)


def test_port_use_and_direction_match_independent_rails():
    assert m.use_direction("VCO_AVDD") == ("POWER", "INOUT")
    assert m.use_direction("DIV_AVDD") == ("POWER", "INOUT")
    assert m.use_direction("SUB") == ("GROUND", "INOUT")
    assert all(
        m.use_direction(n) == ("SIGNAL", "OUTPUT") for n in ("CLKP", "CLKN", "QP", "QN")
    )
    assert m.use_direction("VCTRL") == ("SIGNAL", "INPUT")


def test_audit_rejects_unrelated_negative_failure():
    step = dict(
        name="feedback",
        audit_execution=dict(returncode=1),
        audit=dict(status="FAIL", circuit_status_counts={"Match": 1}),
    )
    with pytest.raises(ValueError, match="Unrelated"):
        c.validate_lvs(step, "", False)
    step["audit"]["status"] = "PASS within comparison scope"
    with pytest.raises(ValueError, match="negative accepted"):
        c.validate_lvs(step, "", False)


def test_positive_native_census_never_accepted_from_status_only():
    step = dict(
        audit_execution=dict(returncode=0),
        audit=dict(status="PASS within comparison scope", circuits=[]),
    )
    with pytest.raises(ValueError):
        c.validate_lvs(step, "", True)


def test_input_source_dictionary_not_mutated_by_flatten():
    texts = m.source_texts(ROOT)
    before = copy.deepcopy(texts)
    m.flatten(texts)
    assert texts == before
