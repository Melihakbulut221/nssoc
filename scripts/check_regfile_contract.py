#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run real-codec register-file proofs and counterexample negative controls."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "hw/soc/formal"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sby", default="sby")
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    binary = shutil.which(args.sby)
    if binary is None:
        parser.error(f"SymbiYosys not found: {args.sby}")
    binary = Path(binary).absolute()
    env = {**os.environ, "PATH": str(binary.parent) + os.pathsep + os.environ["PATH"]}
    out = ROOT / "hw/soc/out/regfile-contract-checks"
    out.mkdir(parents=True, exist_ok=True)

    def run(name, config, task, expected):
        work = out / name
        with (out / f"{name}.log").open("w") as log:
            result = subprocess.run([str(binary), "-f", "-d", str(work), str(config), task],
                                    cwd=FORMAL, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=240)
        status = (work / "status").read_text().split()[0] if (work / "status").exists() else "MISSING"
        # UNKNOWN, TIMEOUT and tool errors are never successful controls.
        wanted_rc = 0 if expected == "PASS" else 2
        if status != expected or result.returncode != wanted_rc:
            raise RuntimeError(f"{name}: {status}, exit {result.returncode}; expected {expected}; see {out / (name + '.log')}")
        print(f"{name}: {status}" + (" (expected counterexample)" if expected == "FAIL" else ""), flush=True)

    if not args.controls_only:
        for task in ("prove", "prove_noscrub", "cover"):
            run(task, FORMAL / "regfile_contract.sby", task, "PASS")
    original = (ROOT / "hw/soc/rtl/ibex_regfile_secded.v").read_text()
    mutations = {
        "wrong_write": ("rf_reg_q <= wr_data;", "rf_reg_q <= wr_data ^ 32'h1;"),
        "wrong_check": ("rf_chk_q <= wr_chk;", "rf_chk_q <= wr_chk ^ 8'h1;"),
        "wrong_port_b": ("raw_b = rf_data[raddr_b_i];", "raw_b = rf_data[raddr_a_i];"),
    }
    for name, (before, after) in mutations.items():
        if original.count(before) != 1:
            raise RuntimeError(f"{name}: mutation site is no longer unique")
        mutant = out / f"{name}.v"
        mutant.write_text(original.replace(before, after))
        config = out / f"{name}.sby"
        text = (FORMAL / "regfile_contract.sby").read_text()
        text = text.replace("../rtl/ibex_regfile_secded.v",
                            "ibex_regfile_secded.v " + str(mutant))
        # Require a reachable counterexample, not failed induction.
        # Registered assertions need the write and the following sample.
        text = text.replace("prove: mode prove", "prove: mode bmc")
        text = text.replace("prove: depth 3", "prove: depth 6")
        config.write_text(text)
        run(name, config, "prove", "FAIL")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        sys.exit(str(exc))
