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
TOP = "soc_pcie_gen3_continuous_rx_integrity_v15"
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
OLD_FRAMER = "soc_pcie_gen3_framer_rx_integrity_v11"
NEW_FRAMER = "soc_pcie_gen3_framer_rx_integrity_v15"


def pin(p):
    return {
        "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }


def miter(directory, fault=None):
    directory.mkdir()
    for name in (
        "soc_pcie_gen3_ingress_integrity_v11",
        "soc_pcie_gen3_data_descrambler",
        NEW_FRAMER,
    ):
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
    compare += """always @(negedge clk_i) begin
 #0.001;
 if(rst_ni===1'b1 && ((candidate.framer.current_valid &&
     (candidate.framer.current_predecode !== candidate.framer.predecode_block(candidate.framer.current_block) ||
      candidate.framer.current_block !== reference.framer.current_block ||
      candidate.framer.current_predecode !== reference.framer.current_predecode)) ||
     (candidate.framer.next_valid &&
     (candidate.framer.next_predecode !== candidate.framer.predecode_block(candidate.framer.next_block) ||
      candidate.framer.next_block !== reference.framer.next_block ||
      candidate.framer.next_predecode !== reference.framer.next_predecode))))
   $fatal(1,"PCIE_PREDECODE_COMPANION_MISMATCH");
end
""".replace("\n+", "\n")
    compare += """integer ingress_slot,ingress_address;
always @(negedge clk_i) begin
 #0.001;
 if(rst_ni===1'b1) begin
   if({candidate.ingress.running,candidate.ingress.queued,candidate.ingress.rd_ptr,candidate.ingress.wr_ptr} !==
      {reference.ingress.running,reference.ingress.queued,reference.ingress.rd_ptr,reference.ingress.wr_ptr})
     $fatal(1,"PCIE_INGRESS_CONTROL_MISMATCH");
   for(ingress_slot=0;ingress_slot<4;ingress_slot=ingress_slot+1) begin
     ingress_address=(reference.ingress.rd_ptr+ingress_slot)&3;
     if(ingress_slot<reference.ingress.queued &&
        candidate.ingress.blocks[ingress_address] !== reference.ingress.blocks[ingress_address])
       $fatal(1,"PCIE_VALID_INGRESS_SLOT_MISMATCH");
   end
 end
end
"""
    compare += """integer ring_offset,ring_address;
always @(negedge clk_i) begin
 #0.001;
 if(rst_ni===1'b1) begin
   if({candidate.framer.write_ptr,candidate.framer.read_ptr,candidate.framer.commit_ptr} !==
      {reference.framer.write_ptr,reference.framer.read_ptr,reference.framer.commit_ptr})
     $fatal(1,"PCIE_RING_CONTROL_MISMATCH");
   for(ring_offset=0;ring_offset<RING_DWORDS;ring_offset=ring_offset+1) begin
     ring_address=(reference.framer.read_ptr+ring_offset)&(RING_DWORDS-1);
     if(ring_offset<reference.framer.occupied &&
        {candidate.framer.slot_data[ring_address],candidate.framer.slot_keep[ring_address],
         candidate.framer.slot_sop[ring_address],candidate.framer.slot_eop[ring_address],
         candidate.framer.slot_dllp[ring_address],candidate.framer.slot_sequence[ring_address],
         candidate.framer.slot_tag[ring_address]} !==
        {reference.framer.slot_data[ring_address],reference.framer.slot_keep[ring_address],
         reference.framer.slot_sop[ring_address],reference.framer.slot_eop[ring_address],
         reference.framer.slot_dllp[ring_address],reference.framer.slot_sequence[ring_address],
         reference.framer.slot_tag[ring_address]})
       $fatal(1,"PCIE_OCCUPIED_SLOT_MISMATCH");
     if(ring_offset<reference.framer.committed && reference.framer.slot_keep[ring_address]!=0 &&
        candidate.framer.slot_verdict[ring_address] !== reference.framer.slot_verdict[ring_address])
       $fatal(1,"PCIE_COMMITTED_SLOT_VERDICT_MISMATCH");
   end
 end
end
"""
    wrapper = "\n".join(
        [
            header,
            *declarations,
            instance(TOP + "_core", "candidate", False),
            instance(TOP.replace("_v15", "_v11"), "reference", True),
            compare,
            "endmodule",
            core,
            (RTL / (TOP.replace("_v15", "_v11") + ".v")).read_text(),
            (RTL / (OLD_FRAMER + ".v")).read_text(),
            (RTL / "soc_pcie_gen3_ingress.v").read_text(),
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
def test_v11_v15_cycle_exact_all_public_outputs(tmp_path, maximum):
    helper = runpy.run_path(
        str(ROOT / "sw/tests/test_pcie_gen3_continuous_rx_integrity_v15.py")
    )
    rtl = miter(tmp_path / "miter-rtl")
    result, record, cases, out = helper["run"](tmp_path, maximum=maximum, rtl=rtl)
    assert result.returncode == 0 and record["tests"] == {
        "passed": 13,
        "failed": 0,
        "skipped": 0,
    }
    assert all(c.find("failure") is None for c in cases)
    (out / "miter-scope.json").write_text(
        json.dumps(
            {
                "status": "PASS_THIRTEEN_CYCLE_EXACT_PUBLIC_PORT_CASES",
                "maximum": maximum,
                "inputs": INPUTS,
                "outputs": OUTPUTS,
                "source_pins": {
                    str(p.relative_to(ROOT)): pin(p)
                    for p in [
                        RTL / (OLD_FRAMER + ".v"),
                        RTL / (NEW_FRAMER + ".v"),
                        RTL / (TOP + ".v"),
                        RTL / (TOP.replace("_v15", "_v11") + ".v"),
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
        str(ROOT / "scripts/check_pcie_gen3_continuous_rx_integrity_v15.py"),
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


def test_only_quarantined_slot_edits_to_frozen_sources():
    checker = runpy.run_path(
        str(ROOT / "sw/tests/test_pcie_gen3_integrity_v15_read.py")
    )
    checker["test_exact_generated_inverse_and_wrapper_bridge"]()
