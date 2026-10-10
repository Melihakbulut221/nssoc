# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""A real larger-load RX revision must keep model and measurement limits intact."""

import itertools
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_rx as original  # noqa: E402
import characterize_pcie_rx_v2 as revised  # noqa: E402
import review_pcie_rx_v2 as review  # noqa: E402


def test_only_real_collector_geometry_changes_in_v2():
    def statements(path):
        return [
            line for line in path.read_text().splitlines() if not line.startswith("*")
        ]

    old = statements(original.NETLIST)
    new = statements(revised.NETLIST)
    expected = [
        line.replace("nssoc_rx_hbt_rsil", "nssoc_rx_hbt_rsil_v2").replace(
            "l=41.785u", "l=27.5u"
        )
        for line in old
    ]
    assert new == expected
    assert sum("l=27.5u" in line for line in new) == 2
    assert sum("sw_et=1" in line for line in new) == 4
    assert (
        original.tx.sha(original.NETLIST)
        == "4450bac31930cca351a33dcb7b269ef732a342bcafef8d96610ee15340d51e5a"
    )
    assert (
        original.tx.sha(Path(original.__file__))
        == "74d192ab7c95b8113cafbc0202f219c52f2ae9a1e07b410ba72b7512cceb4a99"
    )


def test_every_original_pvt_corner_uses_required_150ff():
    matrix = [c for c in revised.cases() if c["name"].startswith("hbt_")]
    assert len(matrix) == 81
    assert {(c["hbt"], c["resistor"], c["temp"], c["supply"]) for c in matrix} == set(
        itertools.product(
            ("hbt_typ", "hbt_bcs", "hbt_wcs"),
            ("res_typ", "res_bcs", "res_wcs"),
            (-40, 27, 125),
            (1.71, 1.8, 1.89),
        )
    )
    assert all(
        c["cap_f"] == 150e-15
        and c["reference_a"] == 0.00075
        and c["vcm"] == 1.36
        and c["fault"] is None
        for c in matrix
    )
    assert len(revised.cases()) == 97 and len(revised.cases(True)) == 17


def test_faults_change_actual_stimulus_and_remain_negative_controls():
    old = {c["name"]: c for c in original.cases()}
    new = {c["name"]: c for c in revised.cases()}
    faults = [c for c in new.values() if c["fault"]]
    assert len(faults) == 6
    for case in faults:
        reference = old[case["name"]]
        assert case["fault"] == reference["fault"]
    assert new["no_bias"]["reference_a"] == 0
    assert new["clipped_overbias"]["reference_a"] == 0.006
    assert new["reference_3mA_extension"]["reference_a"] == 0.003
    assert new["reference_3mA_extension"]["fault"] is None
    assert new["overload"]["cap_f"] == 100e-12
    assert new["tiny_input"]["amplitude_v"] == 0.005
    assert new["low_common_mode"]["vcm"] == 1.10
    assert new["load_100fF"]["cap_f"] == 100e-15
    assert new["half_timestep"]["cap_f"] == 150e-15
    assert new["half_timestep"]["step_s"] == 0.5e-12


@pytest.mark.parametrize("ac", [False, True])
def test_bench_keeps_native_models_options_bias_and_wave_sampling(tmp_path, ac):
    case = revised.cases(True)[0]
    previous, sequence = original.deck(case, tmp_path, tmp_path / "r.osdi", ac=ac)
    text, bits = revised.deck(case, tmp_path, tmp_path / "r.osdi", ac=ac)
    assert text == previous.replace(
        "rx_hbt_rsil.spice", "rx_hbt_rsil_v2.spice"
    ).replace("nssoc_rx_hbt_rsil", "nssoc_rx_hbt_rsil_v2")
    assert sequence == bits and len(bits) == 254
    assert "CP op 0 1.5e-13" in text
    assert "IREF avdd ref 0.00075" in text
    assert "RSP sp ip 50\nRSN sn inn 50" in text
    assert ".options reltol=1e-4 abstol=1e-12" in text


def test_no_measurement_or_engineering_limit_relaxation():
    assert revised.LIMITS == original.LIMITS
    assert revised.LIMITS["min_margin_v"] == 0.1
    assert revised.LIMITS["min_vce_v"] == 0.4
    assert revised.LIMITS["max_vce_v"] == 1.6
    assert revised.measure is original.measure
    assert revised.measure_ac is original.measure_ac
    assert revised.execute is original.execute


@pytest.mark.parametrize(
    "measurement,clean,status",
    [
        (False, False, "FAIL_RX_V2_MEASUREMENT_SCREEN"),
        (False, True, "FAIL_RX_V2_MEASUREMENT_SCREEN"),
        (True, False, "RX_V2_MEASUREMENT_PASS_NUMERICAL_RESIDUAL"),
        (True, True, "PASS_RX_V2_LIMITED_SCREEN"),
    ],
)
def test_measurement_pass_never_erases_initialization_failures(
    measurement, clean, status
):
    assert revised.disposition(measurement, clean) == status


@pytest.mark.parametrize(
    "message",
    [
        "The temperature limiting function received NaN.",
        "Warning: singular matrix",
        "Note: Starting dynamic gmin stepping",
        "WARNING: Irb current density is greater than specified by jmax",
    ],
)
def test_original_recovery_failures_remain_visible_in_v2(message):
    assert not review.diagnostics(
        message + "\nNo. of Data Rows : 34520\nngspice-42 done"
    )["numerical_clean"]


def test_ac_review_rejects_missing_corner_and_old_bias():
    entries = [
        dict(
            case=dict(revised.cases()[0], hbt=h, resistor=r, temp=27, supply=1.8),
            execution={"returncode": 0},
        )
        for h, r in itertools.product(
            ("hbt_typ", "hbt_bcs", "hbt_wcs"), ("res_typ", "res_bcs", "res_wcs")
        )
    ]
    result = dict(quick=False, ac_cases=entries)
    review.ac_contract(result)
    with pytest.raises(ValueError, match="coverage"):
        review.ac_contract(dict(result, ac_cases=entries[:-1]))
    entries[0]["case"]["reference_a"] = 0.0005
    with pytest.raises(ValueError, match="bias"):
        review.ac_contract(result)


def test_reviewer_binds_actual_v2_netlist_inventory(tmp_path):
    entry = dict(case={"name": "hbt_typ_res_typ_27_1.8"}, output_sha256={})
    for name in ("bench.cir", "run.log", "rx_hbt_rsil_v2.spice", "wave.dat.gz"):
        path = tmp_path / name
        path.write_text(name)
        entry["output_sha256"][name] = revised.tx.sha(path)
    assert review.transient_files(tmp_path, entry, False) == tmp_path / "wave.dat.gz"
    (tmp_path / "rx_hbt_rsil_v2.spice").rename(tmp_path / "rx_hbt_rsil.spice")
    with pytest.raises(ValueError, match="inventory"):
        review.transient_files(tmp_path, entry, False)


def test_publication_retains_exactly_actual_worst_pvt_and_never_assumes_four():
    rows = [
        dict(case=case, measurement={"min_signed_margin_v": 0.15})
        for case in revised.cases()
        if case["name"].startswith("hbt_")
    ]
    rows[-1]["measurement"]["min_signed_margin_v"] = 0.112
    result = dict(cases=rows)
    assert review.retained_wave_names(result) == {rows[-1]["case"]["name"]}
    with pytest.raises(ValueError, match="81"):
        review.retained_wave_names(dict(cases=rows[:-1]))


def test_limited_replay_rejects_missing_selected_wave_and_extra_unselected_wave(
    tmp_path,
):
    import lzma

    entry = dict(case={"name": "hbt_wcs_res_wcs_125_1.89"}, output_sha256={})
    for name in ("bench.cir", "run.log", "rx_hbt_rsil_v2.spice"):
        path = tmp_path / name
        path.write_text(name)
        entry["output_sha256"][name] = revised.tx.sha(path)
    entry["output_sha256"]["wave.dat.gz"] = "0" * 64
    selected = {entry["case"]["name"]}
    with pytest.raises(ValueError, match="inventory"):
        review.transient_files(tmp_path, entry, True, selected)
    wave = tmp_path / "wave.dat.xz"
    wave.write_bytes(lzma.compress(b"original native bytes"))
    assert review.transient_files(tmp_path, entry, True, selected) == wave
    with pytest.raises(ValueError, match="inventory"):
        review.transient_files(tmp_path, entry, True, frozenset())
    wave.unlink()
    assert review.transient_files(tmp_path, entry, True, frozenset()) is None
