# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "hbt_domain", ROOT / "scripts/check_pcie_hbt_model_domain.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_valid_boundaries_and_parallel_devices():
    result = MODULE.inspect_source(
        "XREF r r 0 sub npn13G2 Nx=1\n"
        "XA c b e sub npn13G2 Nx=6\n"
        "XB c b e sub npn13G2\n+ Nx = 10 $ supported boundary\n")
    assert result["passed"] and len(result["devices"]) == 3


def test_reject_historical_out_of_domain_circuit():
    source = ROOT / "hw/soc/analog/pcie/tx_mux2_hbt_n12_v1.spice"
    result = MODULE.inspect_source(source.read_text())
    assert not result["passed"]
    assert [d["instance"] for d in result["devices"] if not d["passed"]] == [
        "xap", "xan", "xbp", "xbn"]


def test_reject_unresolved_or_invalid_multiplicity():
    for value in ["0", "-1", "11", "16", "48", "1.5", "{size}", "nan", "inf"]:
        assert not MODULE.inspect_source(
            f"XQ c b e sub npn13G2 Nx={value}\n")["passed"]
    assert not MODULE.inspect_source("XQ c b e sub npn13G2 Nx=2 Nx=12")["passed"]
    assert not MODULE.inspect_source("XQ c b e sub npn13G2 Nx=")["passed"]


def test_empty_or_wrong_terminal_census_is_not_a_pass():
    assert not MODULE.inspect_source("* npn13G2 Nx=12\n")["passed"]
    assert not MODULE.inspect_source("XQ c b e npn13G2 Nx=2")["passed"]
