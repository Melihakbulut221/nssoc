# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cycle-exact old/new public-port comparison using the unchanged serial oracle."""

from pathlib import Path
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
TOP = "soc_pcie_gen3_continuous_rx_integrity_v2"
INPUTS = {
    "clk_i": 1,
    "rst_ni": 1,
    "flush_i": 1,
    "stream_start_i": 1,
    "stream_abort_i": 1,
    "word_i": 128,
    "ready_i": 1,
}
OUTPUTS = {
    "valid_o": 1,
    "data_o": 128,
    "keep_o": 16,
    "sop_o": 16,
    "eop_o": 16,
    "dllp_o": 16,
    "sequence_o": 48,
    "packet_good_o": 4,
    "packet_nullified_o": 4,
    "packet_crc_bad_o": 4,
    "packet_dllp_o": 4,
    "packet_sequence_o": 48,
    "framing_error_o": 1,
    "stream_end_o": 1,
    "active_o": 1,
    "halted_o": 1,
    "overflow_o": 1,
}
OLD_FRAMER = "soc_pcie_gen3_framer_rx_integrity_v1"
NEW_FRAMER = "soc_pcie_gen3_framer_rx_integrity_v2"


def pin(p):
    return {
        "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }


def miter(directory, fault=None):
    directory.mkdir()
    for name in ("soc_pcie_gen3_ingress", "soc_pcie_gen3_data_descrambler", NEW_FRAMER):
        shutil.copyfile(RTL / (name + ".v"), directory / (name + ".v"))
    candidate = (RTL / (TOP + ".v")).read_text()
    header = candidate.split(");", 1)[0] + ");\n"
    ports = header.split(")(", 1)[1].rsplit(");", 1)[0]
    ports = re.sub(r"\b(input|output|wire|reg)\b|\[[^\]]*\]", "", ports)
    assert {p.strip() for p in ports.split(",")} == INPUTS.keys() | OUTPUTS.keys()
    core = candidate.replace("module " + TOP + " #(", "module " + TOP + "_core #(", 1)
    declarations = []
    for name, width in OUTPUTS.items():
        declarations.append(
            "wire " + (f"[{width - 1}:0] " if width > 1 else "") + "gold_" + name + ";"
        )

    def instance(module, name, gold):
        connections = [f".{p}({p})" for p in INPUTS]
        connections += [f".{p}({'gold_' if gold else ''}{p})" for p in OUTPUTS]
        return (
            module
            + " #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) "
            + name
            + "("
            + ",".join(connections)
            + ");"
        )

    gate = "{" + ",".join(OUTPUTS) + "}"
    gold = "{" + ",".join("gold_" + p for p in OUTPUTS) + "}"
    compare = f'always @(negedge clk_i) begin\n #0.001;\n if(rst_ni===1\'b1 && {gate} !== {gold}) $fatal(1,"PCIE_CYCLE_MITER_OUTPUT_MISMATCH");\nend\n'
    wrapper = "\n".join(
        [
            header,
            *declarations,
            instance(TOP + "_core", "candidate", False),
            instance(TOP.replace("_v2", "_v1"), "reference", True),
            compare,
            "endmodule",
            core,
            (RTL / (TOP.replace("_v2", "_v1") + ".v")).read_text(),
            (RTL / (OLD_FRAMER + ".v")).read_text(),
        ]
    )
    wrapper = "`timescale 1ns/1ps\n" + wrapper
    if fault == "public_data_inversion":
        assert ".data_o(data_o)" in wrapper
        wrapper = wrapper.replace(".data_o(data_o)", ".data_o(miter_gate_data)", 1)
        wrapper = wrapper.replace(
            "wire gold_valid_o;",
            "wire [127:0] miter_gate_data;\nassign data_o=miter_gate_data ^ 128'b1;\nwire gold_valid_o;",
            1,
        )
    elif fault == "unqualified_speculative_fault":
        p = directory / (NEW_FRAMER + ".v")
        s = p.read_text()
        before = "|| (step && token_failure);"
        assert s.count(before) == 1
        p.write_text(s.replace(before, "|| token_failure;"))
    elif fault is not None:
        raise ValueError(fault)
    (directory / (TOP + ".v")).write_text(wrapper)
    return directory


@pytest.mark.parametrize("maximum", [150, 4118])
def test_v1_v2_cycle_exact_all_public_outputs(tmp_path, maximum):
    helper = runpy.run_path(
        str(ROOT / "sw/tests/test_pcie_gen3_continuous_rx_integrity_v2.py")
    )
    rtl = miter(tmp_path / "miter-rtl")
    result, record, cases, out = helper["run"](tmp_path, maximum=maximum, rtl=rtl)
    assert result.returncode == 0 and record["tests"] == {
        "passed": 12,
        "failed": 0,
        "skipped": 0,
    }
    assert all(c.find("failure") is None for c in cases)
    (out / "miter-scope.json").write_text(
        json.dumps(
            {
                "status": "PASS_TWELVE_CYCLE_EXACT_PUBLIC_PORT_CASES",
                "maximum": maximum,
                "inputs": INPUTS,
                "outputs": OUTPUTS,
                "source_pins": {
                    str(p.relative_to(ROOT)): pin(p)
                    for p in [
                        RTL / (OLD_FRAMER + ".v"),
                        RTL / (NEW_FRAMER + ".v"),
                        RTL / (TOP + ".v"),
                        RTL / (TOP.replace("_v2", "_v1") + ".v"),
                    ]
                },
                "scope": "Actual two complete RTL implementations, unchanged external serial oracle; all public outputs compared every falling edge after reset. Not exhaustive formal or timing proof.",
            },
            indent=2,
        )
        + "\n"
    )


@pytest.mark.parametrize(
    "fault", ["public_data_inversion", "unqualified_speculative_fault"]
)
def test_actual_miter_fault_is_observed(tmp_path, fault):
    rtl = miter(tmp_path / "fault-rtl", fault)
    out = tmp_path / "capture"
    tool = Path(shutil.which("iverilog") or "/usr/bin/iverilog")
    command = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_gen3_continuous_rx_integrity_v2.py"),
        "--out",
        str(out),
        "--rtl-dir",
        str(rtl),
        "--iverilog-dir",
        str(tool.parent),
        "--test",
        "sustained_minimum_packets_exceed_every_buffer",
    ]
    with (tmp_path / "launch.log").open("w") as f:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=f,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    log = (out / "simulation.log").read_text()
    assert result.returncode != 0 and "PCIE_CYCLE_MITER_OUTPUT_MISMATCH" in log
    assert (out / "sim/sim.vvp").is_file()


def test_only_three_functional_changes_to_frozen_framer():
    old = (RTL / (OLD_FRAMER + ".v")).read_text()
    new = (RTL / (NEW_FRAMER + ".v")).read_text().replace(NEW_FRAMER, OLD_FRAMER)
    changes = [
        (
            "wire fault_now=ring_overflow_now || bad_block_now || token_failure;",
            "wire fault_now=ring_overflow_now || bad_block_now || (step && token_failure);",
        ),
        (
            "if(step && !token_failure && !ending_n) begin",
            "if(!token_failure && !ending_n) begin",
        ),
        (
            "if(ending_n) begin current_valid<=0;next_valid<=0;end",
            "if(ending || (step && ending_n)) begin current_valid<=0;next_valid<=0;end",
        ),
    ]
    for before, after in changes:
        assert old.count(before) == 1 and new.count(after) == 1
        old = old.replace(before, after)

    def code(s):
        return "\n".join(
            line for line in s.splitlines() if not line.lstrip().startswith("//")
        )

    assert code(old) == code(new)
