# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound startup protocol and independent terminal-current guards."""

from pathlib import Path
import copy
import math
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import diagnose_pcie_zero_start_v3 as d  # noqa: E402
import check_pcie_startup_kcl_v3 as k  # noqa: E402


def bench(kind="sampler", fault=None):
    cases = d.s.cases(False) if kind == "sampler" else d.s.rx.cases(False)
    case = next(c for c in cases if c["name"] == (fault or d.PILOT[0]))
    text = (
        d.s.deck(case, Path("/models"), Path("/r3.osdi"))
        if kind == "sampler"
        else d.s.rx.deck(case, Path("/models"), Path("/r3.osdi"))[0]
    )
    return case, text


@pytest.mark.parametrize("kind", ["rx", "sampler"])
def test_transform_changes_only_explicit_initialization_and_source_prefix(kind):
    _, original = bench(kind)
    changed = d.transform(original, kind)
    assert ".options reltol=1e-4 abstol=1e-12" in changed
    assert (
        ".nodeset" not in changed
        and "uic" not in changed.lower()
        and ".ic " not in changed
    )
    assert "PWL(0 0 1e-09 " in changed
    assert len(re.findall(r"^alter @q\.", changed, re.M)) == (
        19 if kind == "sampler" else 4
    )
    assert [
        line
        for line in changed.splitlines()
        if line.startswith(
            ("X", "R", "C", ".include", ".lib", ".temp", "tran ", "wrdata wave")
        )
    ] == [
        line
        for line in original.splitlines()
        if line.startswith(
            ("X", "R", "C", ".include", ".lib", ".temp", "tran ", "wrdata wave")
        )
    ]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.replace("reltol=1e-4", "reltol=.1"),
        lambda x: x.replace("VDD avdd", "VZZ avdd"),
        lambda x: x + ".ic v(ref)=.8\n",
        lambda x: x.replace("tran 1e-12", "tran 1e-12 uic"),
        lambda x: x + "alter @foo = 1\n",
    ],
)
def test_reject_changed_source_or_forced_state(mutation):
    with pytest.raises(ValueError):
        d.transform(mutation(bench()[1]), "sampler")


def flag_log(value="1"):
    return "".join(
        f"NSSOC_FLAG_BEGIN q.{n}.qnpn13g2\n VBIC: Vertical Bipolar Inter-Company Model\n     device {'q.' + n + '.qnpn13g2':.21}\n      model native\n        off {value}\nNSSOC_FLAG_END\n"
        for n in d.hbts("sampler")
    )


def test_native_integer_show_and_exact_device_census():
    assert len(d.flags_observed(flag_log(), "sampler", "zero_off")) == 19


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.replace("off 1", "off 0", 1),
        lambda s: s.replace("off 1", "off nan", 1),
        lambda s: s + s,
        lambda s: s.replace(
            "device q.xsamp.xm.xdp.qnpn13", "device q.xsamp.xm.xdn.qnpn13"
        ),
        lambda s: s.replace(
            "NSSOC_FLAG_BEGIN q.xrx.xp", "NSSOC_FLAG_BEGIN q.xrx.xn", 1
        ),
    ],
)
def test_off_misread_missing_or_wrong_identity_rejected(mutate):
    with pytest.raises(ValueError):
        d.flags_observed(mutate(flag_log()), "sampler", "zero_off")


def test_default_and_powered_negative_protocols_remain_distinct():
    original = bench()[1]
    assert "alter @q." not in d.transform(original, "sampler", "zero_default")
    powered = d.transform(original, "sampler", "powered_off")
    assert "VDD avdd 0 1.8" in powered and "VSCP scp0 0 PULSE(" in powered
    assert "alter @q." in powered


@pytest.mark.parametrize("fault", ["no_bias", "swapped_output", "clock_stopped"])
def test_functional_negative_still_has_actual_broken_source_or_wiring(fault):
    _, original = bench(fault=fault)
    changed = d.transform(original, "sampler")
    if fault == "no_bias":
        assert "ISAMP savdd sr PWL(0 0 1e-09 0)" in changed
    elif fault == "swapped_output":
        assert "XSAMP op on qn qp" in changed
    else:
        assert "VSCP scp0 0 PWL(0 0 1e-09 1.14)" in changed


def test_initial_op_exact_finite_and_nonforced(tmp_path):
    p = tmp_path / "op.dat"
    p.write_text("index v(a) i(vb)\n0 0 0\n\n")
    assert d.initial_op(p, ["v(a)", "i(vb)"]) == {"v(a)": 0, "i(vb)": 0}
    for text in (
        "index v(a) i(vb)\n0 nan 0\n",
        "index v(a) i(vb)\n0 0 0\n1 0 0\n",
        "index v(b) i(vb)\n0 0 0\n",
    ):
        p.write_text(text)
        with pytest.raises(ValueError):
            d.initial_op(p, ["v(a)", "i(vb)"])


@pytest.mark.parametrize(
    "message",
    [
        "The temperature limiting function received NaN.",
        "Starting dynamic gmin stepping",
        "Error: vector missing",
        "tran simulation(s) aborted",
        "specified by jmax",
        "source stepping failed",
    ],
)
def test_native_zero_exit_does_not_erase_actual_failure(message):
    assert not d.diagnostics(message)["numerical_clean"]


@pytest.mark.parametrize("kind", ["rx", "sampler"])
def test_complete_corner_set_and_separate_controls(kind):
    assert len(d.cases(kind, "full")) == 81
    assert {c["name"] for c in d.cases(kind, "pilot")} == set(d.PILOT)
    assert [c["name"] for c in d.cases(kind, "controls")] == [
        d.PILOT[-1],
        "no_bias",
        "swapped_output",
    ]


def test_native_probe_instrumentation_has_exact_contraction():
    texts, leaves = k.instrumentation()
    assert len(leaves) == 35
    assert sum(len(x["probes"]) for x in leaves) == 124
    assert len({p for x in leaves for p in x["probes"]}) == 124
    assert all(
        re.search(r"^Vzp_\S+ \S+ \S+ 0$", line)
        for text in texts.values()
        for line in text.splitlines()
        if line.startswith("Vzp_")
    )
    case, _ = bench()
    text, observed = k.constant_deck(case, Path("/models"), Path("/r3.osdi"), leaves)
    assert "tran 1e-10 1e-06 0 1e-10" in text
    assert text.count("PWL(0 0 1e-07 ") == 9
    assert len(observed) == len(set(observed))


def table_fixture():
    case, _ = bench()
    _, leaves = k.instrumentation()
    _, columns = k.constant_deck(case, Path("/models"), Path("/r3.osdi"), leaves)
    table = {name: [0.0] * 10001 for name in columns}
    table["time"] = [k.SETTLE_S * i / 10000 for i in range(10001)]
    # Zero source currents are a useful KCL failure because both actual bias
    # currents remain nonzero; no all-zero 'passing circuit' is manufactured.
    return case, leaves, table


def test_missing_bias_currents_are_not_a_kcl_pass():
    case, leaves, table = table_fixture()
    result = k.analyze(table, leaves, case)
    assert not result["pass_kcl"] and not result["pass_active"]


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_terminal",
        "missing_leaf",
        "duplicate_leaf",
        "nan",
        "short_wave",
        "time_gap",
    ],
)
def test_kcl_guard_rejects_wrong_topology_or_native_data(mutation):
    case, leaves, table = table_fixture()
    leaves = copy.deepcopy(leaves)
    if mutation == "wrong_terminal":
        leaves[0]["terminals"][0] = "0"
    elif mutation == "missing_leaf":
        leaves.pop()
    elif mutation == "duplicate_leaf":
        leaves.append(leaves[0])
    elif mutation == "nan":
        table["v(qp)"][-1] = math.nan
    elif mutation == "time_gap":
        table["time"][-2] -= 2 * k.STEP_S
    else:
        table["time"][-1] *= 0.5
    with pytest.raises(ValueError):
        k.analyze(table, leaves, case)
