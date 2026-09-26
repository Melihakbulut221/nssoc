#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Require reachable counterexamples for UART, timer and discovery-table faults.

Mutations are made only in new output files. A syntax error, induction failure,
timeout or missing tool is never a successful control. Normal proofs are run by
the uart/pnp/gptimer targets of hw/soc/formal/Makefile.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "hw/soc/formal"
CONTROLS = (
    ("uart_interrupt_enable", "soc_uart", "../rtl/soc_uart.v",
     "ctrl_ti <= pwdata_i[3];", "ctrl_ti <= pwdata_i[2];"),
    ("pnp_response_missing", "soc_pnp", "../rtl/soc_pnp.v",
     "rvalid_o <= req_i;", "rvalid_o <= 1'b0;"),
    ("pnp_signature", "soc_pnp", "../rtl/soc_pnp_rom.vh",
     "32'h4E530001", "32'h4E530003"),
    ("apb_pnp_error", "soc_pnp", "../rtl/soc_apb_pnp.v",
     "assign pslverr_o = 1'b0;", "assign pslverr_o = 1'b1;"),
    ("timer_expiry_clear_collision", "soc_gptimer", "../rtl/soc_gptimer.v",
     "if (t_wrap[n])           t_ip[n] <= 1'b1;",
     "if (t_wrap[n])           t_ip[n] <= 1'b0;"),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sby", default="sby")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    binary = shutil.which(args.sby)
    if not binary:
        parser.error(f"SymbiYosys not found: {args.sby}")
    binary = Path(binary).absolute()
    env = dict(os.environ, PATH=str(binary.parent) + os.pathsep + os.environ.get("PATH", ""))
    if args.output:
        out = args.output.absolute()
        out.mkdir(parents=True, exist_ok=False)
    else:
        base = ROOT / "hw/soc/out/peripheral-contracts"
        base.mkdir(parents=True, exist_ok=True)
        out = Path(tempfile.mkdtemp(prefix="controls-", dir=base))
    inputs = {Path(__file__).resolve(), FORMAL / "Makefile"}
    for job in ("soc_uart", "soc_pnp", "soc_gptimer"):
        config = FORMAL / (job + ".sby")
        inputs.add(config)
        for line in config.read_text().split("[files]\n")[1].splitlines():
            if line.strip() and not line.startswith("#"):
                inputs.add((FORMAL / line.strip()).resolve())
    original = {str(p.relative_to(ROOT)): digest(p) for p in sorted(inputs)}
    report = {"source_sha256": original, "controls": [], "passed": False}
    try:
        for name, job, source_path, before, after in CONTROLS:
            source = (FORMAL / source_path).read_text()
            if source.count(before) != 1:
                raise RuntimeError(f"{name}: mutation site is no longer unique")
            mutant = out / (name + Path(source_path).suffix)
            mutant.write_text(source.replace(before, after))
            config_text = (FORMAL / (job + ".sby")).read_text()
            config_text = config_text.replace(source_path, Path(source_path).name + " " + str(mutant))
            # Use reachability BMC even when the positive proof is PDR.
            config_text = config_text.replace("bmc: abc bmc3", "bmc: smtbmc yices")
            config = out / (name + ".sby")
            config.write_text(config_text)
            work = out / name
            command = [str(binary), "-f", "-d", str(work), str(config), "bmc"]
            start = time.monotonic()
            log = out / (name + ".log")
            with log.open("x") as stream:
                result = subprocess.run(command, cwd=FORMAL, env=env, stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=210)
            status_path = work / "status"
            status = status_path.read_text().split()[0] if status_path.exists() else "MISSING"
            reachable = "Assert failed" in log.read_text() and bool(list(work.glob("engine_*/trace*.vcd")))
            passed = result.returncode == 2 and status == "FAIL" and reachable
            report["controls"].append(dict(name=name, command=command, returncode=result.returncode,
                                            status=status, reachable_counterexample=reachable,
                                            elapsed_s=time.monotonic() - start,
                                            mutant_sha256=digest(mutant), passed=passed))
            if not passed:
                raise RuntimeError(f"{name}: expected reachable FAIL, got {status}, exit {result.returncode}; {log}")
            print(f"EXPECTED FAIL {name}: reachable counterexample", flush=True)
        report["sources_unchanged"] = all(digest(ROOT / p) == h for p, h in original.items())
        if not report["sources_unchanged"]:
            raise RuntimeError("Source changed during controls")
        report["passed"] = True
    finally:
        (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
