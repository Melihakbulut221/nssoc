# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Only measured limiter geometry may differ; failures remain outside brackets."""

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_clock_headroom_v2 as new  # noqa: E402


@pytest.mark.parametrize("length", new.LENGTHS)
def test_only_two_loads_and_unique_top_differ(length):
    before = new.old.CIRCUIT.read_text()
    after = new.revised(before, length)
    changed = [
        (a, b) for a, b in zip(before.splitlines(), after.splitlines()) if a != b
    ]
    assert len(changed) == 4
    assert {a.split()[0] for a, _ in changed} == {".subckt", ".ends", "XBRP", "XBRN"}
    assert new.old.device_contract(after) == new.old.device_contract(before)
    assert after.count("rppd w=8u l=4.4u") == 6
    assert after.count(f"rppd w=8u l={length}u") == 2


@pytest.mark.parametrize(
    "mutation",
    [
        lambda x: x.replace("XBRN ", "XBRQ "),
        lambda x: x + "\n.ends nssoc_clock_vco_hbt\n",
        lambda x: x.replace("XBRP avdd", "XBRP avss"),
        lambda x: x.replace("l=4.4u", "l=4.5u"),
    ],
)
def test_wrong_limiter_or_top_rejected(mutation):
    with pytest.raises(ValueError):
        new.revised(mutation(new.old.CIRCUIT.read_text()), "4.0")


def test_unknown_geometry_rejected():
    with pytest.raises(ValueError):
        new.revised(new.old.CIRCUIT.read_text(), "3.0")


@pytest.mark.parametrize("case", new.old.cases(False)[-4:])
def test_real_functional_faults_preserved(case):
    before = new.old.circuit(case)
    after = new.revised(before, "4.0")
    assert (
        len([1 for a, b in zip(before.splitlines(), after.splitlines()) if a != b]) == 4
    )


def test_deck_only_rebinds_selected_circuit_and_preserves_stimulus_limits():
    case = new.old.cases(False)[0]
    args = (case, Path("/models"), [Path("/a.osdi")])
    before = new.init.transform(new.old.deck(*args))
    after = new.deck(*args)
    changed = [
        (a, b) for a, b in zip(before.splitlines(), after.splitlines()) if a != b
    ]
    assert len(changed) == 2
    assert {a.split()[0] for a, _ in changed} == {".include", "XOSC"}
    assert new.old.LIMITS["min_vce_v"] == 0.4
    assert new.old.LIMITS["min_diff_peak_v"] == 0.3


def test_suite_preserves_all_old_failures_and_explicit_tuning_coverage():
    assert new.cases("full") == new.old.cases(False)
    assert len(new.cases("pilot")) == 13
    rows = new.cases("tuning")
    assert len(rows) == len({r["name"] for r in rows}) == 63
    assert sum(r["control"] == 1.3 for r in rows) == 7
    with pytest.raises(ValueError):
        new.cases("unknown")


def tuning_rows():
    return [
        dict(
            case=c,
            clean_initialization=True,
            measurement=dict(
                screen_pass=True, frequency_hz=(12e9 - c["control"] * 5e9)
            ),
        )
        for c in new.cases("tuning")
    ]


def test_only_passing_actual_adjacent_samples_bracket_target():
    rows = tuning_rows()
    before = copy.deepcopy(rows)
    report = new.classify_tuning(rows)
    assert rows == before
    assert len(report) == 7
    assert all(r["measured_8ghz_bracket_found"] for r in report)
    for row in rows:
        if row["case"]["control"] in (0.8, 0.85):
            row["measurement"]["screen_pass"] = False
    assert all(not r["measured_8ghz_bracket_found"] for r in new.classify_tuning(rows))


def test_dirty_or_incomplete_tuning_not_accepted():
    rows = tuning_rows()
    for row in rows:
        row["clean_initialization"] = False
    assert all(not r["measured_8ghz_bracket_found"] for r in new.classify_tuning(rows))
    with pytest.raises(ValueError, match="Incomplete"):
        new.classify_tuning(rows[:-1])


def test_frozen_ancestor_source_pins():
    assert new.old.sha(Path(new.init.__file__)) == new.INIT_SHA
    assert new.old.sha(new.old.CIRCUIT) == new.init.CIRCUIT_SHA
