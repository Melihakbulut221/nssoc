# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal slot/tag/verdict transitions, including same-tag writes on fault edges."""

from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_slots_v13.py"))
SIM = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))["simulate"]
FIELDS = {"data": 32, "keep": 4, "sop": 4, "eop": 4, "dllp": 4, "sequence": 12}


def test_exact_generated_inverse_and_wrapper_bridge():
    new = (RTL / "soc_pcie_gen3_framer_rx_integrity_v13.v").read_text()
    assert new == GEN["candidate"]()
    old = new.replace("integrity_v13", "integrity_v12")
    for before, after in reversed(GEN["CHANGES"]):
        assert old.count(after) == 1
        old = old.replace(after, before)
    assert old == GEN["SOURCE"].read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v12.v",
        "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v12.py",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v12",
    ]:
        candidate = (ROOT / name.replace("_v12", "_v13")).read_text()
        candidate = candidate.replace("integrity_v13", "integrity_v12")
        assert candidate == (ROOT / name).read_text()


@pytest.mark.parametrize("fault", [None, "ignore_current_valid", "write_during_ending", "overflow_not_fault"])
def test_actual_capacity_predicates_only_add_aborted_writes(tmp_path, fault):
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v13.v").read_text()
    lines = []
    for name in ["ring_overflow_now", "step", "slot_content_step", "fault_now"]:
        matches = [x for x in source.splitlines() if x.startswith(" wire " + name + "=")]
        assert len(matches) == 1
        lines += matches
    body = "\n".join(lines)
    edits = {
        "ignore_current_valid": ("slot_content_step=enabled && active_o && !ending && current_valid;", "slot_content_step=enabled && active_o && !ending;"),
        "write_during_ending": ("slot_content_step=enabled && active_o && !ending && current_valid;", "slot_content_step=enabled && active_o && current_valid;"),
        "overflow_not_fault": ("fault_now=ring_overflow_now || bad_block_now", "fault_now=bad_block_now"),
    }
    if fault:
        before, after = edits[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    tb = """module tb;
reg enabled,active_o,ending,current_valid,capacity_overflow,bad_block_now,token_failure;
""" + body + """
integer n,extra=0;
initial begin
for(n=0;n<128;n=n+1) begin
 {enabled,active_o,ending,current_valid,capacity_overflow,bad_block_now,token_failure}=n;
 #1;
 if(slot_content_step !== (step || ring_overflow_now))$fatal(1,"CONTENT_CAPACITY_DOMAIN");
 if(slot_content_step && !step) begin
   extra=extra+1;
   if(!ring_overflow_now || !fault_now)$fatal(1,"CONTENT_CAPACITY_ABORT");
 end
end
if(extra!=4)$fatal(1,"CONTENT_CAPACITY_COVERAGE");
$display("PASS_EXHAUSTIVE_CONTENT_CAPACITY_PREDICATES128 extra4");$finish;
end endmodule
"""
    result, log = SIM(tmp_path, tb)
    if fault:
        assert result.returncode != 0 and "CONTENT_CAPACITY_" in log
    else:
        assert result.returncode == 0 and "PASS_EXHAUSTIVE_CONTENT_CAPACITY" in log


@pytest.mark.parametrize("fault", [None, "cache_capacity_gated", "writer_capacity_gated", "lost_tag_write", "wrong_data_lane",
                                  "lost_verdict_broadcast", "first_verdict_wins", "cache_old_tag"])
def test_literal_slot_writer_and_full_cache_relation(tmp_path, fault):
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v13.v").read_text()
    start = source.index(" // BEGIN V6 SHARED OLD VERDICT READS\n")
    stop = source.index(" // END V5 SLOT VERDICT CACHE\n", start)
    body = source[start:stop] + GEN["writer"]()
    edits = {
        "cache_capacity_gated": ("if(slot_content_step) slot_verdict[cache_slot]", "if(step) slot_verdict[cache_slot]"),
        "writer_capacity_gated": ("   if(slot_content_step) begin", "   if(step) begin"),
        "lost_tag_write": ("<=write_tags[slot_write_lane*PW+:PW]", "<=slot_tag[(write_ptr+slot_write_lane)&(RING_DWORDS-1)]"),
        "wrong_data_lane": ("write_data[slot_write_lane*32+:32]", "write_data[((slot_write_lane+1)%4)*32+:32]"),
        "lost_verdict_broadcast": ("verdict_enable[verdict_lane] &&", "verdict_enable[verdict_lane] && cache_slot==0 &&"),
        "first_verdict_wins": ("verdict_lane=0;verdict_lane<4;verdict_lane=verdict_lane+1", "verdict_lane=3;verdict_lane>=0;verdict_lane=verdict_lane-1"),
        "cache_old_tag": ("effective_tag=write_tags[write_lane*PW+:PW];", "effective_tag=resident_tag;"),
    }
    if fault:
        before, after = edits[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    declarations = []
    initial = []
    expected = []
    checks = []
    for name, width in FIELDS.items():
        declarations += [f"reg[{width-1}:0] slot_{name}[0:63],expected_{name}[0:63];",
                         f"reg[{4*width-1}:0] write_{name};"]
        initial += [f"for(i=0;i<64;i=i+1) begin slot_{name}[i]=$random(seed);expected_{name}[i]=slot_{name}[i];end",
                    f"for(i=0;i<4;i=i+1) write_{name}[i*{width}+:{width}]=$random(seed);"]
        expected += [f"expected_{name}[(write_ptr+j)&63]=write_{name}[j*{width}+:{width}];"]
        checks += [f'if(slot_{name}[i]!==expected_{name}[i]) $fatal(1,"SLOT_TRANSITION {name} %0d %0d",n,i);']
    tb = """`timescale 1ns/1ps
module tb;
localparam RING_DWORDS=64,PW=7;
reg clk_i=0,slot_content_step=0,fault_now=0;
wire step=slot_content_step && !fault_now;
reg[PW-1:0]write_ptr=0;
reg[4*PW-1:0]write_tags=0,verdict_tags=0;
reg[3:0]verdict_enable=0,verdict_value=0;
reg[PW-1:0]slot_tag[0:63],expected_tag[0:63];
reg verdict[0:127],expected_verdict[0:127];
reg slot_verdict[0:63];
""" + "\n".join(declarations) + body + """
integer n,i,j,seed=1281337,fault_steps=0,good_steps=0,wraps=0;
initial begin
 for(n=0;n<8192;n=n+1) begin
   clk_i=0;slot_content_step=0;fault_now=0;
   for(i=0;i<128;i=i+1) begin verdict[i]=$random(seed);expected_verdict[i]=verdict[i];end
   for(i=0;i<64;i=i+1) begin
     slot_tag[i]=$random(seed);expected_tag[i]=slot_tag[i];
     slot_verdict[i]=verdict[slot_tag[i]];
   end
""" + "\n".join(initial) + """
   write_ptr=$random(seed);write_tags={$random(seed),$random(seed)};
   verdict_tags={$random(seed),$random(seed)};
   verdict_enable=n[3:0];verdict_value=n[7:4];
   if(n[8]) for(j=0;j<4;j=j+1) begin
     if(n[j+9]) verdict_tags[j*PW+:PW]=write_tags[(j%2)*PW+:PW];
     else verdict_tags[j*PW+:PW]=slot_tag[(write_ptr+j)&63];
   end
   slot_content_step=n[12:11]!=0;fault_now=n[11:10]==3;
   #1;
   // Binary next-state shadow applies the four writes in source order. The
   // cached relation must still follow the complete new tag/verdict arrays.
   if(slot_content_step) begin
     if(fault_now)fault_steps=fault_steps+1;else good_steps=good_steps+1;
     if((write_ptr&63)>60)wraps=wraps+1;
     for(j=0;j<4;j=j+1) begin
       expected_tag[(write_ptr+j)&63]=write_tags[j*PW+:PW];
       if(verdict_enable[j]) expected_verdict[verdict_tags[j*PW+:PW]]=verdict_value[j];
""" + "\n".join(expected) + """
     end
   end
   clk_i=1;#1;
   for(i=0;i<128;i=i+1) if(verdict[i]!==expected_verdict[i])$fatal(1,"SLOT_TRANSITION verdict");
   for(i=0;i<64;i=i+1) begin
     if(slot_tag[i]!==expected_tag[i])$fatal(1,"SLOT_TRANSITION tag");
     if(slot_verdict[i]!==expected_verdict[expected_tag[i]])$fatal(1,"CACHE_NEXT_RELATION %0d %0d",n,i);
""" + "\n".join(checks) + """
   end
 end
 if(fault_steps<1000||good_steps<3000||wraps<100)$fatal(1,"SLOT_COVERAGE");
 $display("PASS_LITERAL_QUARANTINED_SLOTS cases=8192 relations=524288 fault=%0d good=%0d wrap=%0d",fault_steps,good_steps,wraps);
 $finish;
end endmodule
"""
    result, log = SIM(tmp_path, tb)
    if fault:
        assert result.returncode != 0 and ("SLOT_TRANSITION" in log or "CACHE_NEXT_RELATION" in log)
    else:
        assert result.returncode == 0 and "PASS_LITERAL_QUARANTINED_SLOTS" in log
