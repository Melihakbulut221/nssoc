# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physical collector-load revision preserves all observation and fault contracts."""

import inspect
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_sampler as old  # noqa: E402
import characterize_pcie_sampler_v2 as new  # noqa: E402
import crosscheck_pcie_sampler_v2 as cross  # noqa: E402
import review_pcie_sampler_v2 as review  # noqa: E402


def test_only_native_collector_lengths_change():
    before = old.NETLIST.read_text()
    assert before.count("l=2.04u") == 2  # two instances of the child latch
    assert new.NETLIST.read_text() == before.replace("l=2.04u", "l=2.12u")
    for path, sha in new.FIXED.items():
        assert new.rx.tx.sha(new.ROOT / path) == sha


def test_all_observations_limits_and_stimulus_remain_identical():
    for name in (
        "cases",
        "sequence",
        "pwl",
        "measure",
        "crossings",
        "timestep_sensitivity",
        "disposition",
    ):
        assert inspect.getsource(getattr(new, name)) == inspect.getsource(
            getattr(old, name)
        )
    assert new.LIMITS == old.LIMITS
    assert new.cases() == old.cases()
    assert new.HBT == old.HBT and new.VECTORS == old.VECTORS
    for case in new.cases():
        a = old.deck(case, Path("/models"), Path("/capture/r3_cmc.osdi"))
        b = new.deck(case, Path("/models"), Path("/capture/r3_cmc.osdi"))
        assert b == a.replace(old.NETLIST.name, new.NETLIST.name)


def test_exact_source_inventory_includes_failed_ancestor():
    assert len(new.FIXED) == len(old.FIXED) + 2
    assert "scripts/characterize_pcie_sampler.py" in new.FIXED
    assert "hw/soc/analog/pcie/rx_sampler_hbt.spice" in new.FIXED
    assert review.ASSUMPTIONS["recovered_clock"] is False


def selection_fixture():
    rows = []
    for name, margin, vce, fault in [
        ("hbt_typ_res_typ_27_1.8", 0.15, 0.5, None),
        ("hbt_worst_margin", 0.11, 0.45, None),
        ("hbt_worst_vce", 0.14, 0.41, None),
        ("no_bias", 0.0, 0.1, "no_bias"),
        ("clock_stopped", 0.0, 0.1, "clock_stopped"),
    ]:
        rows.append(
            dict(
                case=dict(name=name, fault=fault),
                measurement=dict(
                    min_signed_margin_v=margin,
                    devices=dict(q=dict(min_vce_v=vce)),
                    screen_pass=fault is None,
                ),
            )
        )
    return dict(cases=rows)


def test_cross_selects_margin_headroom_and_exact_real_negatives():
    x = selection_fixture()
    assert cross.selection(x) == [r["case"]["name"] for r in x["cases"]]
    x["cases"][0]["measurement"]["min_signed_margin_v"] = 0.09
    assert cross.selection(x) == [
        "hbt_typ_res_typ_27_1.8",
        "hbt_worst_vce",
        "no_bias",
        "clock_stopped",
    ]
    assert cross.outcomes(x["cases"])


@pytest.mark.parametrize("which", [0, 3])
def test_cross_rejects_real_positive_failure_or_undetected_fault(which):
    x = selection_fixture()
    x["cases"][which]["measurement"]["screen_pass"] = not x["cases"][which][
        "measurement"
    ]["screen_pass"]
    assert not cross.outcomes(x["cases"])


@pytest.mark.parametrize(
    "status, expected",
    [
        ("PASS_NATIVE_CROSS_VERSION_CAPTURE_REVIEW_ONLY", 0),
        ("PASS_CROSS_VERSION_LIMITED_SAMPLER_SCREEN", 0),
        ("CROSS_VERSION_SCREEN_PASS_NUMERICAL_RESIDUAL", 2),
        ("FAIL_CROSS_VERSION_SAMPLER_SCREEN", 1),
        ("ERROR_PRESERVED", 1),
        ("RUNNING", 1),
    ],
)
def test_cli_outcome_is_fail_closed(status, expected):
    assert cross.exit_code(status) == expected


def test_startup_strategies_preserve_devices_sources_and_tolerances():
    import diagnose_pcie_sampler_startup as startup

    original = new.deck(new.cases()[0], Path("/models"), Path("/capture/r3_cmc.osdi"))
    hints = {n: 0.8 for n in new.NODES}
    for strategy in startup.STRATEGIES:
        text = startup.transformed_deck(original, strategy, hints)
        assert ".options reltol=1e-4 abstol=1e-12" in text
        assert "\nuic" not in text and " uic" not in text and "\n.ic " not in text
        assert "\nop\nwrdata dc.dat " in text
        # All transistor/model/supply/clock/load lines are literally unchanged.
        wanted = [
            line
            for line in original.splitlines()
            if line.startswith(("X", "V", "I", "R", "C", ".lib", ".include"))
        ]
        assert [
            line
            for line in text.splitlines()
            if line.startswith(("X", "V", "I", "R", "C", ".lib", ".include"))
        ] == wanted
    assert "itl1=1000 noopiter gminsteps=0 srcsteps=1" in startup.transformed_deck(
        original, "source_homotopy", hints
    )
    fine = startup.transformed_deck(original, "half_timestep", hints)
    assert "tran 5e-13 " in fine and " 0 5e-13\n" in fine


def test_startup_rejects_incomplete_guess_or_unknown_strategy():
    import diagnose_pcie_sampler_startup as startup

    original = new.deck(new.cases()[0], Path("/models"), Path("/capture/r3_cmc.osdi"))
    with pytest.raises(ValueError, match="physical node"):
        startup.transformed_deck(original, "physical_nodeset", {})
    with pytest.raises(ValueError, match="Unknown"):
        startup.transformed_deck(original, "clamp", {})
    with pytest.raises(ValueError, match="tolerances"):
        startup.transformed_deck(
            original.replace("reltol=1e-4", "reltol=1e-2"), "more_iterations", {}
        )


def test_projection_preserves_every_native_token_and_timepoint(tmp_path):
    import gzip
    import hashlib
    import project_pcie_sampler_trace as projection

    # Deliberately preserve formatting and negative zero, not float reserialization.
    names = [*projection.COLUMNS, "v(internal)"]
    tokens = [
        [f"{i}.00000e-12", "-0.000", "1.0000", "1.29", "1.30", "2.2", "2.4", "0.7"]
        for i in range(5)
    ]
    raw = (
        "  ".join(names) + "\n" + "\n".join("  ".join(row) for row in tokens) + "\n"
    ).encode()
    source, dest = tmp_path / "full.gz", tmp_path / "selected.gz"
    source.write_bytes(gzip.compress(raw))
    result = projection.project(source, dest, hashlib.sha256(raw).hexdigest())
    assert result["rows"] == 5 and result["time_downsampled"] is False
    assert result["full_waveform_retained"] is False
    assert gzip.decompress(dest.read_bytes()).decode().splitlines()[1:] == [
        "\t".join(row[:7]) for row in tokens
    ]


@pytest.mark.parametrize(
    "fault", ["wrong_hash", "missing_column", "duplicate_column", "short_row"]
)
def test_projection_rejects_unbound_or_malformed_native_table(tmp_path, fault):
    import gzip
    import hashlib
    import project_pcie_sampler_trace as projection

    names = list(projection.COLUMNS)
    values = ["0"] * len(names)
    if fault == "missing_column":
        names[-1] = "v(other)"
    if fault == "duplicate_column":
        names[-1] = names[0]
    if fault == "short_row":
        values.pop()
    raw = (" ".join(names) + "\n" + " ".join(values) + "\n").encode()
    source = tmp_path / "full.gz"
    source.write_bytes(gzip.compress(raw))
    sha = hashlib.sha256(raw).hexdigest() if fault != "wrong_hash" else "0" * 64
    with pytest.raises(ValueError):
        projection.project(source, tmp_path / "out.gz", sha)


def test_native_abort_is_never_accepted_as_a_completed_negative():
    x = selection_fixture()
    row = x["cases"][3]
    del row["measurement"]
    row["native_failure"] = "Transient aborted before required stop time"
    assert not cross.outcomes(x["cases"])
