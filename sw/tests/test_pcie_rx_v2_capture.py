# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""No SPICE execution: exact source inventory and real generated deck rejection."""

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import check_pcie_rx_v2_capture as check  # noqa: E402


def fixture_result():
    models = Path("/native/ihp-sg13g2/libs.tech/ngspice/models")
    ngspice = "/native/ngspice"
    openvaf = "/native/openvaf"
    execution = dict(returncode=0, command=[ngspice, "-n", "-b", "bench.cir"])
    ac = [
        (h, r)
        for h in ("hbt_typ", "hbt_bcs", "hbt_wcs")
        for r in ("res_typ", "res_bcs", "res_wcs")
    ]
    return dict(
        quick=False,
        complete_pvt_cross_product=True,
        source_bytes_unchanged=True,
        limits=check.rx.LIMITS,
        ui_s=check.rx.UI,
        bits=check.rx.BITS,
        pdk_revision=check.rx.tx.PDK_REV,
        assumptions=check.ASSUMPTIONS,
        pcie_compliance=False,
        physical_qualification=False,
        manufacturing_approval=False,
        cases=[
            dict(case=c, execution=copy.deepcopy(execution))
            for c in check.rx.cases(False)
        ],
        ac_cases=[
            dict(
                case=dict(
                    check.rx.cases(False)[0], hbt=h, resistor=r, temp=27, supply=1.8
                ),
                execution=copy.deepcopy(execution),
            )
            for h, r in ac
        ],
        compile=dict(
            returncode=0,
            command=[
                openvaf,
                str(models.parent.parent / "verilog-a/r3_cmc/r3_cmc.va"),
                "-o",
                "/original/capture/r3_cmc.osdi",
            ],
        ),
        source_sha256={
            **{str(check.ROOT / p): h for p, h in check.SOURCE_PINS.items()},
            **{str(models / p): h for p, h in check.rx.tx.MODEL_HASHES.items()},
            **{
                str(models.parent.parent / p): h
                for p, h in check.rx.resistor.RES_HASHES.items()
            },
            openvaf: check.OPENVAF_SHA,
            ngspice: next(iter(check.NGSPICE_PINS)),
        },
    )


def test_frozen_local_methods_and_both_runtime_profiles():
    for path, sha in check.SOURCE_PINS.items():
        check.verify(check.ROOT / path, sha)
    check.verify(Path(check.reviewer.__file__), check.REVIEWER_SHA)
    for sha, version in check.NGSPICE_PINS.items():
        result = fixture_result()
        result["source_sha256"]["/native/ngspice"] = sha
        assert check.source_contract(result)["runtime_version"] == version


@pytest.mark.parametrize("position", range(14))
def test_removing_any_actual_required_source_rejects(position):
    result = fixture_result()
    del result["source_sha256"][list(result["source_sha256"])[position]]
    with pytest.raises(ValueError):
        check.source_contract(result)


@pytest.mark.parametrize("position", range(14))
def test_repinning_any_required_source_rejects(position):
    result = fixture_result()
    result["source_sha256"][list(result["source_sha256"])[position]] = "0" * 64
    with pytest.raises(ValueError):
        check.source_contract(result)


def test_added_source_does_not_make_a_complete_inventory():
    result = fixture_result()
    result["source_sha256"]["/native/extra"] = "0" * 64
    with pytest.raises(ValueError, match="inventory"):
        check.source_contract(result)


@pytest.mark.parametrize(
    "fault",
    [
        "missing_transient",
        "missing_ac",
        "different_runtime",
        "different_compile_input",
        "failed_ac",
        "relaxed_load",
    ],
)
def test_case_and_runtime_contract_rejects(fault):
    result = fixture_result()
    if fault == "missing_transient":
        result["cases"].pop()
    elif fault == "missing_ac":
        result["ac_cases"].pop()
    elif fault == "different_runtime":
        result["cases"][50]["execution"]["command"][0] = "/native/another"
    elif fault == "different_compile_input":
        result["compile"]["command"][1] = "/native/modified.va"
    elif fault == "failed_ac":
        result["ac_cases"][2]["execution"]["returncode"] = 1
    else:
        result["cases"][0]["case"]["cap_f"] = 100e-15
    with pytest.raises(ValueError):
        check.source_contract(result)


@pytest.fixture
def actual_deck(tmp_path):
    result = fixture_result()
    context = check.source_contract(result)
    row = result["cases"][0]
    (tmp_path / "bench.cir").write_text(
        check.rx.deck(row["case"], context["models"], context["osdi"])[0]
    )
    (tmp_path / check.rx.NETLIST.name).write_bytes(check.rx.NETLIST.read_bytes())
    row["output_sha256"] = {p.name: check.digest(p) for p in tmp_path.iterdir()}
    return tmp_path, row, context


def test_actual_bench_and_circuit_bridge(actual_deck):
    check.case_bridge(*actual_deck)


@pytest.mark.parametrize(
    "old,new",
    [
        ("CP op 0 1.5e-13", "CP op 0 1e-13"),
        ("IREF avdd ref 0.00075", "IREF avdd ref 0.0005"),
        ("reltol=1e-4", "reltol=1e-2"),
        ("pre_osdi /original/capture/r3_cmc.osdi", "pre_osdi /other/r3_cmc.osdi"),
    ],
)
def test_changed_bench_rejects_even_after_output_repin(actual_deck, old, new):
    folder, row, context = actual_deck
    path = folder / "bench.cir"
    assert path.read_text().count(old) == 1
    path.write_text(path.read_text().replace(old, new))
    row["output_sha256"][path.name] = check.digest(path)
    with pytest.raises(ValueError, match="Regenerated bench"):
        check.case_bridge(folder, row, context)


def test_changed_circuit_rejects_even_after_output_repin(actual_deck):
    folder, row, context = actual_deck
    path = folder / check.rx.NETLIST.name
    path.write_text(path.read_text().replace("l=27.5u", "l=41.785u"))
    row["output_sha256"][path.name] = check.digest(path)
    with pytest.raises(ValueError, match="byte pin"):
        check.case_bridge(folder, row, context)


def test_symlinked_bench_rejects_even_with_exact_bytes(actual_deck):
    folder, row, context = actual_deck
    path = folder / "bench.cir"
    path.rename(folder / "original.cir")
    path.symlink_to(folder / "original.cir")
    with pytest.raises(ValueError, match="Regenerated bench"):
        check.case_bridge(folder, row, context)


def test_ac_bridge_preserves_original_paths_after_capture_relocation(tmp_path):
    result = fixture_result()
    context = check.source_contract(result)
    for row in result["ac_cases"]:
        folder = tmp_path / (row["case"]["hbt"] + row["case"]["resistor"])
        folder.mkdir()
        (folder / "bench.cir").write_text(
            check.rx.deck(row["case"], context["models"], context["osdi"], ac=True)[0]
        )
        (folder / check.rx.NETLIST.name).write_bytes(check.rx.NETLIST.read_bytes())
        row["output_sha256"] = {p.name: check.digest(p) for p in folder.iterdir()}
        check.case_bridge(folder, row, context, ac=True)
