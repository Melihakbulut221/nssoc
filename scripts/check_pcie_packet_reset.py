# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove the exact top-level packet reset cone after power-on reset.

The initial formal event asserts rst_sys_n. Clocks, reset transitions and
stopped-clock intervals thereafter are unconstrained. Both release-state bits
are observed alongside the reset output; no valid-cycle masking is used.
This is a digital reset proof, not analog reset-recovery or metastability signoff.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SHA = "92b87d6aed56c07b803149f9b547b5ec899107c63d15f94bbcea0351f0dbc453"


def extract(top):
    marker = '  (* ASYNC_REG="TRUE" *) reg [1:0] packet_reset_release;'
    if top.count(marker) != 1 or top.count("  wire packet_rst_n=") != 2:
        raise ValueError("Unexpected async/synchronous packet reset source")
    start = top.index(marker)
    end = top.index(";", top.index("  wire packet_rst_n=", start)) + 1
    return (
        "module soc_pcie_packet_reset(pcie_clk_i, rst_sys_n, packet_rst_n, release_state);\n"
        "input wire pcie_clk_i, rst_sys_n;\noutput packet_rst_n;\n"
        "output wire [1:0] release_state;\n"
        + top[start:end]
        + "\nassign release_state=packet_reset_release;\nendmodule\n"
    )


def run(top, out, yosys, fault=None):
    reference = ROOT / "sw/tests/fixtures/pcie_chip_timing/raw-packet-reset.v"
    if hashlib.sha256(reference.read_bytes()).hexdigest() != REFERENCE_SHA:
        raise ValueError("Frozen packet reset reference changed")
    gate = extract(top.read_text())
    if fault:
        before, after = {
            "synchronous_assertion": (" or negedge rst_sys_n", ""),
            "early_release": (
                "wire packet_rst_n=packet_reset_release[1]",
                "wire packet_rst_n=packet_reset_release[0]",
            ),
            "wrong_reset_state": (
                "packet_reset_release<=0",
                "packet_reset_release<=2'b10",
            ),
            "clock_gated_output": (
                "wire packet_rst_n=packet_reset_release[1]",
                "wire packet_rst_n=packet_reset_release[1] && pcie_clk_i",
            ),
        }[fault]
        if gate.count(before) != 1:
            raise ValueError("Fault anchor drift")
        gate = gate.replace(before, after)
    out.mkdir(parents=True, exist_ok=False)
    for name, text in (("gold", reference.read_text()), ("gate", gate)):
        (out / (name + ".v")).write_text(
            text.replace("module soc_pcie_packet_reset", "module " + name)
        )
    script = "\n".join(
        [
            "read_verilog -sv gold.v gate.v",
            "proc",
            "opt",
            "clk2fflogic",
            "opt",
            "miter -equiv -flatten gold gate miter",
            "hierarchy -top miter",
            "opt",
            "sat -seq 4 -tempinduct -maxsteps 20 -set-at 1 in_rst_sys_n 0 -prove trigger 0 "
            "-show-inputs -show-outputs -show-regs -dump_vcd trace.vcd",
            "",
        ]
    )
    (out / "proof.ys").write_text(script)
    files = [top, reference, Path(__file__), yosys]
    pins = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with (out / "proof.log").open("w") as log:
        p = subprocess.run(
            [str(yosys.resolve()), "-s", "proof.ys"],
            cwd=out,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    text = (out / "proof.log").read_text()
    unchanged = all(
        hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in pins.items()
    )
    passed = (
        p.returncode == 0 and unchanged and "Induction step proven: SUCCESS!" in text
    )
    result = dict(
        status="PASS_AFTER_POR" if passed else "FAIL",
        fault=fault,
        returncode=p.returncode,
        inputs=pins,
        inputs_unchanged=unchanged,
        initial_condition="rst_sys_n asserted at first event; no subsequent input/clock constraints",
        observables=["packet_rst_n", "release_state[1:0]"],
        scope="Extracted reset cone only; no four-state startup or analog recovery/PHY signoff",
    )
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--top", type=Path, default=ROOT / "hw/soc/rtl/soc_top.v")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--yosys", type=Path, required=True)
    a = p.parse_args()
    r = run(a.top, a.out, a.yosys)
    print(r["status"])
    return int(r["status"] != "PASS_AFTER_POR")


if __name__ == "__main__":
    raise SystemExit(main())
