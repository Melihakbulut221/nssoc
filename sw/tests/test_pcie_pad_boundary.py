# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed native pad comparisons and actual model result interpretation."""

import copy
import math
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_pad_boundary as make
import check_pcie_pad_boundary as check
import check_pcie_esd_loading as loading


def test_fixed_native_model_order():
    text = make.reference()
    lines = text.splitlines()
    assert lines[2] == ".subckt nssoc_pcie_pad_boundary PADP PADN AVDD AVSS"
    assert lines[3:7] == [
        "DPdd AVDD PADP AVSS diodevdd_2kv m=1",
        "DPss AVDD PADP AVSS diodevss_2kv m=1",
        "DNdd AVDD PADN AVSS diodevdd_2kv m=1",
        "DNss AVDD PADN AVSS diodevss_2kv m=1",
    ]
    model = loading.model_reference()
    assert model.count("\nX") == 4 and "\nD" not in model
    assert "XPdd AVDD PADP AVSS diodevdd_2kv m=1" in model


@pytest.mark.parametrize("fault", ["multiplicity", "wrong_polarity", "wrong_rail"])
def test_negative_is_one_literal_device_change(fault):
    original = make.reference()
    wrong = check.fault_reference(original, fault)
    assert len(wrong.splitlines()) == len(original.splitlines())
    assert sum(a != b for a, b in zip(original.splitlines(), wrong.splitlines())) == 1
    with pytest.raises(ValueError):
        check.fault_reference(wrong, fault)


def test_unknown_fault_rejected():
    with pytest.raises(ValueError):
        check.fault_reference(make.reference(), "skip")
    with pytest.raises(ValueError):
        check.mutation_script("a", "b", "skip")


def open_audit():
    return dict(
        status="FAIL",
        circuits=[
            dict(
                layout=make.TOP,
                schematic=make.TOP.upper(),
                status="Match",
                layout_devices_recursive=4,
                schematic_devices_recursive=4,
            )
        ],
        extraction_diagnostics=[],
        reasons=[
            "Missing explicit successful deck verdict",
            "Deck explicitly reported a mismatch",
        ],
    )


def test_exact_native_missing_pad_open_is_expected_strict_rejection():
    check.validate_open(open_audit(), 1, ".SUBCKT " + make.TOP + " AVSS AVDD PADN\n")


@pytest.mark.parametrize(
    "mutation",
    [
        "status",
        "count",
        "error",
        "reason",
        "pass_exit",
        "wrong_missing",
        "all_ports",
        "extra_port",
        "empty",
    ],
)
def test_open_cannot_accept_unrelated_failure(mutation):
    a = copy.deepcopy(open_audit())
    code = 1
    header = ".SUBCKT " + make.TOP + " AVSS AVDD PADN\n"
    if mutation == "status":
        a["status"] = "PASS within comparison scope"
    elif mutation == "count":
        a["circuits"][0]["layout_devices_recursive"] = 3
    elif mutation == "error":
        a["extraction_diagnostics"] = [dict(severity="Error")]
    elif mutation == "reason":
        a["reasons"].append("Unresolved extraction warning")
    elif mutation == "pass_exit":
        code = 0
    elif mutation == "wrong_missing":
        header = header.replace("PADN", "PADP")
    elif mutation == "all_ports":
        header = header.rstrip() + " PADP\n"
    elif mutation == "extra_port":
        header = header.rstrip() + " UNRELATED\n"
    elif mutation == "empty":
        header = ""
    with pytest.raises(ValueError):
        check.validate_open(a, code, header)


def write_native_fixture(out):
    (out / "native.log").write_text("i(vp) = -1e-12\n")
    for i, f in enumerate(loading.FREQUENCIES):
        (out / f"y{i}.dat").write_text(
            f" frequency yr yi\n{f:.0f} 0 {2 * math.pi * f * 50e-15:.15g}\n"
        )


def test_known_cap_native_parser_has_real_units(tmp_path):
    write_native_fixture(tmp_path)
    r = loading.parse_case(tmp_path, 0)
    assert loading.normal_gate(r)
    assert all(
        x["capacitance_f"] == pytest.approx(50e-15, rel=1e-12) for x in r["frequencies"]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "exit",
        "warning",
        "missing_op",
        "duplicate_op",
        "missing_row",
        "extra_row",
        "wrong_frequency",
        "nan",
    ],
)
def test_model_parser_rejects_incomplete_native_outputs(tmp_path, fault):
    write_native_fixture(tmp_path)
    code = 0
    if fault == "exit":
        code = 1
    elif fault == "warning":
        (tmp_path / "native.log").write_text("Warning: bad initialization\ni(vp) = 0\n")
    elif fault == "missing_op":
        (tmp_path / "native.log").write_text("done\n")
    elif fault == "duplicate_op":
        (tmp_path / "native.log").write_text("i(vp) = 0\ni(vp) = 0\n")
    else:
        p = tmp_path / "y1.dat"
        lines = p.read_text().splitlines()
        if fault == "missing_row":
            lines = lines[:1]
        elif fault == "extra_row":
            lines.append(lines[-1])
        elif fault == "wrong_frequency":
            lines[-1] = lines[-1].replace("4000000000", "8000000000")
        elif fault == "nan":
            lines[-1] = "4000000000 0 nan"
        p.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError):
        loading.parse_case(tmp_path, code)


def test_forward_conduction_fails_same_sanity_gate(tmp_path):
    write_native_fixture(tmp_path)
    r = loading.parse_case(tmp_path, 0)
    r["leakage_a"] = 0.01
    assert not loading.normal_gate(r)


def test_native_bench_keeps_actual_source_and_explicit_three_frequencies():
    s = loading.bench(Path("/models"), Path("/source"), 1.8, 1.36, 27, Path("/out"))
    assert "XBOUND padp padn avdd 0 nssoc_pcie_pad_boundary" in s
    assert s.count("ac lin 1 ") == 3
    assert "ideal" not in s and "raw_lvs" not in s
    assert "XBOUND padp padn 0 avdd nssoc_pcie_pad_boundary" in loading.bench(
        "/models", "/source", 1.8, 1.36, 27, "/out", "wrong_rail"
    )
    with pytest.raises(ValueError):
        loading.bench("/m", "/s", 1.8, 1.36, 27, "/o", "skip")
