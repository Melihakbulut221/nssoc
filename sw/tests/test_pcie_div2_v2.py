# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact reuse, source transformation and fail-closed native startup guards."""

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_div2_v2 as v2  # noqa: E402


def case():
    return v2.old.cases()[0]


def test_native_sources_limits_and_only_two_limiter_edits():
    v2.verify_vco()
    assert len(v2.identities(case())) == len(set(v2.identities(case()))) == 33
    assert v2.old.LIMITS["min_vce_v"] == 0.4
    assert v2.old.LIMITS["max_vce_v"] == 1.6
    assert v2.old.LIMITS["max_ic_a_per_nx"] == 0.003


def test_deck_preserves_sources_circuits_and_native_33_flag_order():
    c = case()
    text = v2.deck(c, Path("/models"), [Path("/native.osdi")])
    original = v2.old.deck(c, Path("/models"), [Path("/native.osdi")])
    flags = text[text.index("alter @") : text.index("\ntran ")]
    for name in v2.identities(c):
        assert flags.count(f"alter @{name}[off] = 1\n") == 1
        assert flags.count(f"show {name} : off\n") == 1
    restored = (
        text.replace(flags + "\n", "")
        .replace("nssoc_clock_vco_hbt_v2", "nssoc_clock_vco_hbt")
        .replace("clock_vco_hbt_v2.spice", "clock_vco_hbt.spice")
    )
    assert restored == original
    assert '.include "clock_div2_hbt.spice"' in text
    assert '.include "rx_sampler_hbt_v2.spice"' in text
    assert " uic" not in text.lower() and ".ic " not in text.lower()
    assert ".nodeset" not in text.lower() and "pulse(" not in text.lower()


def flag_log(c):
    return "".join(
        f"NSSOC_DIV2_FLAG_BEGIN {name}\n device {name[:21]}\n off 1\nNSSOC_DIV2_FLAG_END\n"
        for name in v2.identities(c)
    )


def test_exact_native_show_flags():
    c = case()
    assert len(v2.read_flags(flag_log(c), c)) == 33


@pytest.mark.parametrize("mutation", ["zero", "missing", "duplicate", "wrong_name"])
def test_changed_flag_or_native_device_cannot_pass(mutation):
    c = case()
    text = flag_log(c)
    if mutation == "zero":
        text = text.replace(" off 1", " off 0", 1)
    elif mutation == "missing":
        text = text[: text.rfind("NSSOC_DIV2_FLAG_BEGIN")]
    elif mutation == "duplicate":
        text += text
    else:
        text = text.replace(" device ", " device wrong", 1)
    with pytest.raises(ValueError):
        v2.read_flags(text, c)


@pytest.mark.parametrize("mutation", [None, "nonzero", "nan", "vector", "second_row"])
def test_initial_op_requires_complete_exact_finite_zero_vectors(tmp_path, mutation):
    c = case()
    names = v2.old.vectors(c)
    text = "scale " + " ".join(names) + "\n" + " ".join(["0"] * (len(names) + 1)) + "\n"
    if mutation == "nonzero":
        text = text.rstrip() + "\n"
        parts = text.splitlines()
        vals = parts[1].split()
        vals[3] = "0.01"
        text = parts[0] + "\n" + " ".join(vals) + "\n"
    elif mutation == "nan":
        text = text.replace("\n0 ", "\nnan ", 1)
    elif mutation == "vector":
        text = text.replace(names[-1], "v(unobserved)")
    elif mutation == "second_row":
        text += text.splitlines()[1] + "\n"
    path = tmp_path / "initial-op.dat"
    path.write_text(text)
    if mutation is None:
        assert len(v2.initial_op(path, c)) == len(names)
    else:
        with pytest.raises(ValueError):
            v2.initial_op(path, c)


@pytest.mark.parametrize(
    "change",
    [
        {"zero_initial_op": False},
        {"flags_verified": False},
        {"returncode": 1},
        {"execution_failure": "timeout"},
        {"numerical": {"clean": False}},
    ],
)
def test_failed_startup_or_runtime_cannot_qualify_functional_negative(change):
    row = dict(
        case=dict(case(), fault="same_clock"),
        returncode=0,
        zero_initial_op=True,
        flags_verified=True,
        numerical={"clean": True},
        measurement={"functional_divide_pass": False},
    )
    assert v2.accepted(row)
    row.update(change)
    assert not v2.accepted(row)


def test_source_substitution_changes_rejected(tmp_path, monkeypatch):
    path = tmp_path / "clock_vco_hbt_v2.spice"
    path.write_text(v2.VCO.read_text().replace("l=4.0u", "l=3.8u", 1))
    monkeypatch.setattr(v2, "VCO", path)
    with pytest.raises(ValueError, match="exact two limiter"):
        v2.verify_vco()
