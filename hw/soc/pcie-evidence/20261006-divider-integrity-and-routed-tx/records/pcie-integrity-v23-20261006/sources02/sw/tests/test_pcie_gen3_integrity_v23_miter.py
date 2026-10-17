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
TOP = "soc_pcie_gen3_continuous_rx_integrity_v23"
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
OLD_FRAMER = "soc_pcie_gen3_framer_rx_integrity_v22"
NEW_FRAMER = "soc_pcie_gen3_framer_rx_integrity_v23"


HEADER_FAULTS = {'header_wrong_predecessor': ('predecessor=decoded[(index-1)*32+19+:13];', 'predecessor=decoded[index*32+19+:13];'), 'header_current_input_tail': ('if(index==0) predecessor=previous_encoded;', 'if(index==0) predecessor=decoded[15*32+19+:13];'), 'header_shift_wrong': ("current_header_relation<={4'b1111,current_header_relation[15:4]};", "current_header_relation<={4'b1111,current_header_relation[11:0]};"), 'header_promote_stale': ('current_header_relation<=next_header_relation;', 'current_header_relation<=current_header_relation;'), 'header_carried_invert': ('packet_header_mismatch_n=current_header_relation[j];', 'packet_header_mismatch_n=~current_header_relation[j];'), 'header_carried_always_bad': ('current_header_relation[0] : packet_header_mismatch;', "current_header_relation[0] : 1'b1;")}

HEADER_OBSERVER = '// Independent temporal observer: predecessor validity is captured BEFORE the\n// actual acceptance edge and accompanies each bank, never read from newtail.\nreg v23_tail_valid=0,v23_tail_stp=0;\nreg [12:0] v23_tail_encoded=0;\nreg [15:0] v23_current_pred=0,v23_next_pred=0;\nreg [15:0] v23_current_stp=0,v23_next_stp=0;\nreg [15:0] v23_current_relation=16\'hffff,v23_next_relation=16\'hffff;\ninteger v23_accept_base=0,v23_current_base=0,v23_next_base=0;\ninteger v23_last_stp_id=-2;\ninteger v23_i,v23_j,v23_source_id;\nreg [12:0] v23_previous;\nreg [15:0] v23_in_pred,v23_in_stp,v23_in_relation;\nreg v23_original_bad;\ninteger v23_cross_block_headers=0,v23_minimum_same_beat_ends=0;\ninteger v23_missing_predecessor_accepts=0,v23_first_headers=0;\ninteger v23_stp_positions[0:15];\ninitial for(v23_i=0;v23_i<16;v23_i=v23_i+1) v23_stp_positions[v23_i]=0;\nalways @(posedge clk_i) begin\n // Compare OLD valid companions and original late predicate before NBA.\n if(rst_ni===1\'b1 && candidate.framer.current_valid===1\'b1) begin\n  if(candidate.framer.current_header_relation !== v23_current_relation)\n   $fatal(1,"V23_HEADER_BANK_RELATION current");\n end\n if(rst_ni===1\'b1 && candidate.framer.next_valid===1\'b1) begin\n  if(candidate.framer.next_header_relation !== v23_next_relation)\n   $fatal(1,"V23_HEADER_BANK_RELATION next");\n end\n if(rst_ni===1\'b1 && candidate.framer.step===1\'b1) begin\n  if(candidate.framer.state==candidate.framer.TLP && !candidate.framer.header_first &&\n     candidate.framer.packet_header_mismatch !==\n      (reference.framer.header_bad || reference.framer.packet_bytes!=reference.framer.expected_bytes))\n    $fatal(1,"V23_CARRIED_HEADER_RELATION");\n  for(v23_j=0;v23_j<4;v23_j=v23_j+1) begin\n   v23_source_id=v23_current_base+v23_j;\n   if(reference.framer.control_active[v23_j] && reference.framer.control_stp[v23_j] &&\n      (reference.framer.control_modes[v23_j][0] || reference.framer.control_modes[v23_j][2])) begin\n    v23_last_stp_id=v23_source_id;\n    v23_stp_positions[v23_source_id%16]=v23_stp_positions[v23_source_id%16]+1;\n   end\n   if(reference.framer.control_active[v23_j] && reference.framer.control_header_first[v23_j]) begin\n    if(v23_current_pred[v23_j] !== 1\'b1 || v23_current_stp[v23_j] !== 1\'b1 ||\n       v23_source_id != v23_last_stp_id+1)\n      $fatal(1,"V23_FIRST_HEADER_PREDECESSOR_OWNERSHIP");\n    if(v23_j==0) v23_previous=reference.framer.packet_bytes;\n    else v23_previous=reference.framer.control_encoded[v23_j-1];\n    v23_original_bad=reference.framer.current_predecode[v23_j*32+18] ||\n      (v23_previous!=reference.framer.current_predecode[v23_j*32+5+:13]);\n    if(candidate.framer.current_header_relation[v23_j] !== v23_original_bad)\n      $fatal(1,"V23_FIRST_HEADER_RELATION");\n    v23_first_headers=v23_first_headers+1;\n    if(v23_source_id%16==0) v23_cross_block_headers=v23_cross_block_headers+1;\n    if(v23_j==0 && reference.framer.remaining==4 && reference.framer.control_carry_end[3])\n      v23_minimum_same_beat_ends=v23_minimum_same_beat_ends+1;\n   end\n  end\n end\n if(!rst_ni) begin\n  v23_tail_valid<=0;v23_tail_stp<=0;v23_tail_encoded<=0;v23_accept_base<=0;\n  v23_current_pred<=0;v23_next_pred<=0;v23_current_stp<=0;v23_next_stp<=0;\n  v23_current_relation<=16\'hffff;v23_next_relation<=16\'hffff;\n  v23_current_base<=0;v23_next_base<=0;v23_last_stp_id=-2;\n end else begin\n  // Derive each accepted relation independently from reference predecode,\n  // carrying the old predecessor-valid and identity in companion metadata.\n  if(reference.framer.enabled && reference.framer.active_o) begin\n   if(reference.framer.step) begin\n    if(reference.framer.slice==3) begin\n     if(reference.framer.next_valid) begin\n      v23_current_pred<=v23_next_pred;v23_current_stp<=v23_next_stp;\n      v23_current_relation<=v23_next_relation;v23_current_base<=v23_next_base;\n     end\n    end else begin\n     v23_current_pred<={4\'b0,v23_current_pred[15:4]};\n     v23_current_stp<={4\'b0,v23_current_stp[15:4]};\n     v23_current_relation<={4\'b1111,v23_current_relation[15:4]};\n     v23_current_base<=v23_current_base+4;\n    end\n   end\n   if(reference.framer.block_valid_i && reference.framer.block_ready_o) begin\n    v23_in_pred={15\'h7fff,v23_tail_valid};\n    if(v23_in_pred[0] !== v23_tail_valid) $fatal(1,"V23_OBSERVER_OLD_PREDECESSOR");\n    v23_in_stp[0]=v23_tail_stp;\n    for(v23_i=0;v23_i<16;v23_i=v23_i+1) begin\n     if(v23_i==0) v23_previous=v23_tail_encoded;\n     else begin\n      v23_previous=reference.framer.input_predecode[(v23_i-1)*32+19+:13];\n      v23_in_stp[v23_i]=reference.framer.input_predecode[(v23_i-1)*32];\n     end\n     v23_in_relation[v23_i]=reference.framer.input_predecode[v23_i*32+18] ||\n       v23_previous!=reference.framer.input_predecode[v23_i*32+5+:13];\n    end\n    if(!v23_tail_valid) v23_missing_predecessor_accepts=v23_missing_predecessor_accepts+1;\n    if(!reference.framer.current_valid || (reference.framer.last_slice && !reference.framer.next_valid)) begin\n     v23_current_pred<=v23_in_pred;v23_current_stp<=v23_in_stp;\n     v23_current_relation<=v23_in_relation;v23_current_base<=v23_accept_base;\n    end else begin\n     v23_next_pred<=v23_in_pred;v23_next_stp<=v23_in_stp;\n     v23_next_relation<=v23_in_relation;v23_next_base<=v23_accept_base;\n    end\n    v23_tail_encoded<=reference.framer.input_predecode[15*32+19+:13];\n    v23_tail_stp<=reference.framer.input_predecode[15*32];\n    v23_accept_base<=v23_accept_base+16;\n   end\n  end\n  if(flush_i || stream_start_i || (stream_abort_i && reference.framer.active_o) || reference.framer.fault_now) begin\n   v23_tail_valid<=0;v23_accept_base<=0;v23_last_stp_id=-2;\n  end else if(reference.framer.enabled && reference.framer.active_o &&\n              reference.framer.block_valid_i && reference.framer.block_ready_o) v23_tail_valid<=1;\n end\nend\n'

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
     if(ring_offset<reference.framer.occupied && reference.framer.slot_keep[ring_address]!=0 &&
        candidate.framer.slot_verdict[ring_address] !== reference.framer.slot_verdict[ring_address])
       $fatal(1,"V23_OCCUPIED_SLOT_VERDICT_MISMATCH");
   end
 end
end
"""
    compare += """integer v22_fault_step_events=0,v22_invalid_difference_events=0;
integer v22_scan,v22_diff;reg v22_fault_edge=0;reg v23_before_cache[0:RING_DWORDS-1];
always @(posedge clk_i) begin
 v22_fault_edge = candidate.framer.step && candidate.framer.fault_now;
 if(v22_fault_edge===1'b1) begin
  v22_fault_step_events=v22_fault_step_events+1;
  for(v22_scan=0;v22_scan<RING_DWORDS;v22_scan=v22_scan+1)
    v23_before_cache[v22_scan]=candidate.framer.slot_verdict[v22_scan];
 end
 // Observe completed NBAs on this actual fault edge, before Ports.cycle returns.
 #0.002;
 if(rst_ni===1'b1 && v22_fault_edge===1'b1) begin
  if({candidate.framer.write_ptr,candidate.framer.read_ptr,candidate.framer.commit_ptr}!==0 ||
     candidate.framer.output_valid!==0 || candidate.framer.retire_valid!==0 ||
     candidate.framer.active_o!==0 || candidate.framer.halted_o!==1)
   $fatal(1,"V23_FAULT_QUARANTINE_NOT_ATOMIC");
  v22_diff=0;
  for(v22_scan=0;v22_scan<RING_DWORDS;v22_scan=v22_scan+1) begin
   if(candidate.framer.slot_verdict[v22_scan] !== v23_before_cache[v22_scan]) v22_diff=1;
  end
  if(v22_diff) v22_invalid_difference_events=v22_invalid_difference_events+1;
 end
end
// Aliases expose the unchanged public oracle's descriptor observers.
generate if(1) begin:framer
 wire retire_valid=candidate.framer.retire_valid;
 wire retire_has_data=candidate.framer.retire_has_data;
 wire output_valid=candidate.framer.output_valid;
 wire retire_pop=candidate.framer.retire_pop;
 wire retire=candidate.framer.retire;
 wire fault_now=candidate.framer.fault_now;
 wire [$clog2(RING_DWORDS):0] read_ptr=candidate.framer.read_ptr;
 wire [$clog2(RING_DWORDS):0] write_ptr=candidate.framer.write_ptr;
 wire [$clog2(RING_DWORDS):0] commit_ptr=candidate.framer.commit_ptr;
end endgenerate
always @(negedge clk_i) begin
 #0.003;
 if(rst_ni===1'b1) begin
  if({candidate.framer.retire_valid,candidate.framer.retire_has_data} !==
     {reference.framer.retire_valid,reference.framer.retire_has_data})
   $fatal(1,"V23_DESCRIPTOR_OWNERSHIP_MISMATCH");
  if(candidate.framer.retire_valid &&
     {candidate.framer.retire_data,candidate.framer.retire_keep,candidate.framer.retire_sop,
      candidate.framer.retire_eop,candidate.framer.retire_dllp,candidate.framer.retire_sequence} !==
     {reference.framer.retire_data,reference.framer.retire_keep,reference.framer.retire_sop,
      reference.framer.retire_eop,reference.framer.retire_dllp,reference.framer.retire_sequence})
   $fatal(1,"V23_OWNED_DESCRIPTOR_PAYLOAD_MISMATCH");
 end
end
"""
    compare += HEADER_OBSERVER
    wrapper = "\n".join(
        [
            header,
            *declarations,
            instance(TOP + "_core", "candidate", False),
            instance(TOP.replace("_v23", "_v22"), "reference", True),
            compare,
            "endmodule",
            core,
            (RTL / (TOP.replace("_v23", "_v22") + ".v")).read_text(),
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
            "wire [127:0] miter_gate_data;\nassign data_o=miter_gate_data ^ ({128{valid_o}} & 128'b1);\nwire gold_valid_o;",
            1,
        )
    elif fault == "unqualified_speculative_fault":
        p = directory / (NEW_FRAMER + ".v")
        s = p.read_text()
        before = "|| (step && token_failure);"
        assert s.count(before) == 1
        p.write_text(s.replace(before, "|| token_failure;"))
    elif fault in ("cache_skips_step", "cache_inverts_value", "fault_keeps_ring_owner", "cache_stale_new_owner"):
        p = directory / (NEW_FRAMER + ".v")
        text = p.read_text()
        edits = {
            "cache_skips_step": ("if(step) slot_verdict[cache_slot]<=next_value;", "if(1'b0) slot_verdict[cache_slot]<=next_value;"),
            "cache_inverts_value": ("if(step) slot_verdict[cache_slot]<=next_value;", "if(step) slot_verdict[cache_slot]<=~next_value;"),
            "cache_stale_new_owner": ("next_value=cache_write_old_verdict[write_lane];", "next_value=resident_verdict;"),
            "fault_keeps_ring_owner": ("write_ptr<=0;read_ptr<=0;commit_ptr<=0;error_pulse<=1;", "write_ptr<=write_ptr;read_ptr<=read_ptr;commit_ptr<=commit_ptr;error_pulse<=1;"),
        }
        before, after = edits[fault]
        assert text.count(before) == 1
        p.write_text(text.replace(before, after))
    elif fault in HEADER_FAULTS:
        p = directory / (NEW_FRAMER + ".v")
        text = p.read_text()
        before, after = HEADER_FAULTS[fault]
        assert text.count(before) == 1
        p.write_text(text.replace(before, after))
    elif fault == "observer_forgets_old_predecessor":
        before = "v23_in_pred={15'h7fff,v23_tail_valid};"
        assert wrapper.count(before)==1
        wrapper=wrapper.replace(before,"v23_in_pred=16'hffff;")
    elif fault is not None:
        raise ValueError(fault)
    (directory / (TOP + ".v")).write_text(wrapper)
    return directory


@pytest.mark.parametrize("maximum", [150, 4118])
def test_v22_v23_cycle_exact_all_public_outputs(tmp_path, maximum):
    helper = runpy.run_path(
        str(ROOT / "sw/tests/test_pcie_gen3_continuous_rx_integrity_v23.py")
    )
    rtl = miter(tmp_path / "miter-rtl")
    result, record, cases, out = helper["run"](tmp_path, maximum=maximum, rtl=rtl)
    assert result.returncode == 0 and record["tests"] == {
        "passed": 18,
        "failed": 0,
        "skipped": 0,
    }
    assert all(c.find("failure") is None for c in cases)
    (out / "miter-scope.json").write_text(
        json.dumps(
            {
                "status": "PASS_EIGHTEEN_CYCLE_EXACT_PUBLIC_PORT_CASES",
                "maximum": maximum,
                "inputs": INPUTS,
                "outputs": OUTPUTS,
                "source_pins": {
                    str(p.relative_to(ROOT)): pin(p)
                    for p in [
                        RTL / (OLD_FRAMER + ".v"),
                        RTL / (NEW_FRAMER + ".v"),
                        RTL / (TOP + ".v"),
                        RTL / (TOP.replace("_v23", "_v22") + ".v"),
                    ]
                },
                "scope": "Actual two complete RTL implementations, unchanged external serial oracle; all public outputs compared every falling edge after reset. Not exhaustive formal or timing proof.",
            },
            indent=2,
        )
        + "\n"
    )


@pytest.mark.parametrize(
    "fault",
    [
        "public_data_inversion",
        "unqualified_speculative_fault",
        "cache_skips_step",
        "cache_inverts_value",
        "cache_stale_new_owner",
        "fault_keeps_ring_owner",
        *HEADER_FAULTS,
    ],
)
def test_actual_miter_fault_is_observed(tmp_path, fault):
    rtl = miter(tmp_path / "fault-rtl", fault)
    out = tmp_path / "capture"
    tool = Path(shutil.which("iverilog") or "/usr/bin/iverilog")
    command = [
        sys.executable,
        str(ROOT / "scripts/check_pcie_gen3_continuous_rx_integrity_v23.py"),
        "--out",
        str(out),
        "--rtl-dir",
        str(rtl),
        "--iverilog-dir",
        str(tool.parent),
        "--test",
        "cache_fault_write_and_new_epoch_reuse"
        if fault.startswith(("cache_", "fault_"))
        else "adjacent_header_all_positions_and_bank_boundaries"
        if fault in HEADER_FAULTS else "sustained_minimum_packets_exceed_every_buffer",
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
    assert result.returncode != 0 and any(
        message in log
        for message in (
            "PCIE_CYCLE_MITER_OUTPUT_MISMATCH",
            "PCIE_RING_CONTROL_MISMATCH",
            "PCIE_OCCUPIED_SLOT_MISMATCH",
            "V23_OCCUPIED_SLOT_VERDICT_MISMATCH",
            "V23_DESCRIPTOR_OWNERSHIP_MISMATCH",
            "V23_OWNED_DESCRIPTOR_PAYLOAD_MISMATCH",
            "V23_FAULT_QUARANTINE_NOT_ATOMIC",
            "V23_HEADER_BANK_RELATION",
            "V23_FIRST_HEADER_RELATION",
            "V23_CARRIED_HEADER_RELATION",
        )
    )
    assert (out / "sim/sim.vvp").is_file()


def test_only_registered_header_edits_to_frozen_sources():
    checker = runpy.run_path(
        str(ROOT / "sw/tests/test_pcie_gen3_integrity_v23_header.py")
    )
    checker["test_exact_generated_inverse_and_wrapper_bridge"]()


def test_actual_old_predecessor_observer_negative(tmp_path):
    # A deliberately broken observer must not count newtail as old ownership.
    # This is observer validation, not a DUT protocol failure or timing result.
    rtl=miter(tmp_path/'observer-fault', 'observer_forgets_old_predecessor')
    out=tmp_path/'observer-capture'
    tool=Path(shutil.which('iverilog') or '/usr/bin/iverilog')
    command=[sys.executable,str(ROOT/'scripts/check_pcie_gen3_continuous_rx_integrity_v23.py'),
             '--out',str(out),'--rtl-dir',str(rtl),'--iverilog-dir',str(tool.parent),
             '--test','adjacent_header_all_positions_and_bank_boundaries']
    with (tmp_path/'observer-launch.log').open('w') as log:
        result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                              env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode!=0
    assert 'V23_OBSERVER_OLD_PREDECESSOR' in (out/'simulation.log').read_text()
    assert (out/'sim/sim.vvp').is_file()
