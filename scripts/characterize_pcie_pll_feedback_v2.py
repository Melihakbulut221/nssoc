# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native /20 revision adding physical NAND-stack charge stabilization only.

The frozen v1 controls and limits are reused without changing their globals.
This is a component fixture with an external CML clock, not a closed PLL.
"""

import argparse
from pathlib import Path
import shutil
import tempfile

import characterize_pcie_pll_feedback_v1 as base

native = base.native
ROOT = base.ROOT
CIRCUIT = ROOT / "hw/soc/analog/pcie/pll_feedback_div20_lv_v2.spice"
TOP = "nssoc_pll_feedback_div20_v2"
CASES = base.CASES
FAULTS = base.FAULTS
measure = base.measure
REUSE_PINS = {
    Path(
        base.__file__
    ): "cd71ab14fb96350c582babc28b2faed100ac3553b3c1e27f677287a3cbe568b3",
    Path(
        native.__file__
    ): "ba483cc0a740db3c774225ef2c42cb0a41cf56311050512217ec588ab2172223",
}


def circuit_text(fault=""):
    assert all(native.common.sha(p) == value for p, value in REUSE_PINS.items())
    original = base.circuit_text()
    anchor = "XNC n2 c vss sub sg13_lv_nmos w=1.68u l=0.13u ng=1 m=1\n"
    added = "* Native MIM restrains actual reset-induced n1 charge feedthrough.\n"
    added += "XSTAB n1 vss cap_cmim w=2u l=2u\n"
    assert original.count(anchor) == 1
    expected = original.replace(anchor, anchor + added).replace("_v1", "_v2")
    assert CIRCUIT.read_text() == expected
    if fault:
        old, new = FAULTS[fault]
        assert expected.count(old) == 1
        expected = expected.replace(old, new)
    return expected


def config_for(case, source):
    assert all(native.common.sha(p) == value for p, value in REUSE_PINS.items())
    config = base.config_for(case, source)
    model, path, nodes = config["roots"][0]
    assert model == base.TOP
    config["roots"] = [(TOP, path, nodes)]
    config["method_inputs"] += [str(CIRCUIT), str(Path(base.__file__))]
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    args = parser.parse_args()
    scratch = Path(
        tempfile.mkdtemp(prefix="nssoc-pll-feedback-v2-source-", dir="/dev/shm")
    )
    source = scratch / CIRCUIT.name
    source.write_text(circuit_text(args.case if args.case in FAULTS else ""))
    try:
        result = native.run(config_for(args.case, source), args.out, __file__, measure)
        healthy = result["safety"]["passed"]
        functional = result["measurement"]["passed"]
        accepted = healthy and (not functional if args.case in FAULTS else functional)
        result["accepted"] = accepted
        result["case_role"] = (
            "actual_native_fault" if args.case in FAULTS else "positive"
        )
        result["acceptance_status"] = (
            "PASS_FINITE_FEEDBACK_PREREQUISITE"
            if accepted
            else "FAIL_FINITE_FEEDBACK_PREREQUISITE"
        )
        result["scope"] = (
            "Physical CMOS /20 with external differential clock. Only the 21 native "
            "2x2um MIMs and subcircuit names differ from v1. No complete connected "
            "/80, closed PLL, PVT, physical layout or foundry SOA qualification."
        )
        native.common.atomic(args.out / "result.json", result)
        print(result["acceptance_status"])
        return 0 if accepted else 1
    finally:
        if (args.out / CIRCUIT.name).is_file() and (
            args.out / CIRCUIT.name
        ).read_bytes() == source.read_bytes():
            shutil.rmtree(scratch)


if __name__ == "__main__":
    raise SystemExit(main())
