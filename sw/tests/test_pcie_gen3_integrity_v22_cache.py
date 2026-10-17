# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual cache update logic; faulted invalid contents are deliberately not equated."""

from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_cache_v22.py"))
SIM = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))["simulate"]


def cache_body():
    text = (RTL / "soc_pcie_gen3_framer_rx_integrity_v22.v").read_text()
    a = text.index(" // BEGIN V6 SHARED OLD VERDICT READS")
    b = text.index(" // END V5 SLOT VERDICT CACHE", a)
    return text[a:b] + " // END V5 SLOT VERDICT CACHE\n"


def test_exact_generated_inverse_and_wrapper_bridge():
    new = (RTL / "soc_pcie_gen3_framer_rx_integrity_v22.v").read_text()
    assert new == GEN["candidate"]()
    assert GEN["inverse"](new) == GEN["SOURCE"].read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v21.v",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v21",
        "scripts/check_pcie_gen3_continuous_rx_integrity_v21.py",
    ]:
        assert (ROOT / name.replace("_v21", "_v22")).read_text().replace("_v22", "_v21") == (ROOT / name).read_text()
    old = (ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v21.py").read_text()
    bench = (ROOT / "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v22.py").read_text()
    normalized = bench.replace("_v22", "_v21").replace("V22_", "V21_")
    assert normalized.startswith(old)
    assert "if(verdict_enable[w]) verdict[verdict_tags[w*PW+:PW]]<=verdict_value[w];" in new


@pytest.mark.parametrize("fault", [None, "skip", "invert", "ignore_step", "stale_owner", "reverse_priority", "restore_fault_gate"])
def test_actual_cache_body_literal_fourstate_and_extra_fault_writes(tmp_path, fault):
    body = cache_body()
    edits = {
        "skip": ("if(step) slot_verdict[cache_slot]<=next_value;", "if(1'b0) slot_verdict[cache_slot]<=next_value;"),
        "invert": ("if(step) slot_verdict[cache_slot]<=next_value;", "if(step) slot_verdict[cache_slot]<=~next_value;"),
        "ignore_step": ("if(step) slot_verdict[cache_slot]<=next_value;", "if(1'b1) slot_verdict[cache_slot]<=next_value;"),
        "stale_owner": ("next_value=cache_write_old_verdict[write_lane];", "next_value=resident_verdict;"),
        "reverse_priority": ("for(verdict_lane=0;verdict_lane<4;verdict_lane=verdict_lane+1)", "for(verdict_lane=3;verdict_lane>=0;verdict_lane=verdict_lane-1)"),
        "restore_fault_gate": ("if(step) slot_verdict[cache_slot]<=next_value;", "if(step && !fault_now) slot_verdict[cache_slot]<=next_value;"),
    }
    if fault:
        before, after = edits[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    bench = """`timescale 1ns/1ps
module tb;
localparam PW=7,RING_DWORDS=64;
reg clk_i=0,step=0,fault_now=0;
reg [PW-1:0] write_ptr;
reg [4*PW-1:0] write_tags,verdict_tags;
reg [3:0] verdict_enable,verdict_value;
reg [PW-1:0] slot_tag[0:RING_DWORDS-1];
reg slot_verdict[0:RING_DWORDS-1];
reg verdict[0:127];
""" + body + """
integer n,i,j,seed=2219371337,updates=0,unknown_holds=0,fault_updates=0,xz_values=0;
reg expected[0:63],before_value[0:63];reg[PW-1:0] tag;reg value;
initial begin
 for(n=0;n<4096;n=n+1) begin
  clk_i=0;step=0;
  for(i=0;i<128;i=i+1) verdict[i]=$random(seed);
  for(i=0;i<64;i=i+1) begin
   slot_tag[i]=$random(seed);slot_verdict[i]=$random(seed);
   before_value[i]=slot_verdict[i];expected[i]=slot_verdict[i];
  end
  write_ptr=n%128;
  for(i=0;i<4;i=i+1) begin
   write_tags[i*PW+:PW]=$random(seed);
   verdict_tags[i*PW+:PW]=$random(seed);
  end
  verdict_enable=$random(seed);verdict_value=$random(seed);
  // Deliberate overlapping updates prove last-writer order independently.
  if(n%3==0) begin
   for(i=0;i<4;i=i+1) verdict_tags[i*PW+:PW]=write_tags[0+:PW];
   verdict_enable=4'b1111;verdict_value=4'b1010;
  end
  // Selected literal X/Z must pass through the procedural cache assignment.
  if(n%13==0) begin verdict_value=4'bzxzx;xz_values=xz_values+1;end
  if(n%17==0) verdict[write_tags[1*PW+:PW]]=1'bz;
  fault_now=(n>>3)&1;
  case((n>>7)&3) 0:step=0;1:step=1;2:step=1'bx;3:step=1'bz;endcase
  #1;
  if(step===1'b1) begin
   updates=updates+1;
   for(i=0;i<64;i=i+1) begin
    tag=slot_tag[i];value=before_value[i];
    for(j=0;j<4;j=j+1) begin
     if(((write_ptr+j)&63)==i) begin
      tag=write_tags[j*PW+:PW];value=verdict[tag];
     end
    end
    for(j=0;j<4;j=j+1) begin
     if(verdict_enable[j] && verdict_tags[j*PW+:PW]==tag) value=verdict_value[j];
    end
    expected[i]=value;
    if(fault_now && value!==before_value[i]) fault_updates=fault_updates+1;
   end
  end else if(step!==1'b0) unknown_holds=unknown_holds+1;
  clk_i=1;#1;
  for(i=0;i<64;i=i+1)
   if(slot_verdict[i]!==expected[i]) $fatal(1,"V22_CACHE_LITERAL trial=%0d slot=%0d",n,i);
 end
 if(updates!=1024 || unknown_holds!=2048 || fault_updates<512 || xz_values<300)
  $fatal(1,"V22_CACHE_LITERAL_COVERAGE");
 $display("PASS_V22_CACHE_LITERAL cases4096 updates%0d unknownholds%0d faultchanges%0d XZcases%0d",updates,unknown_holds,fault_updates,xz_values);
 $finish;
end
endmodule
"""
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "V22_CACHE_LITERAL trial=" in log
    else:
        assert result.returncode == 0 and "PASS_V22_CACHE_LITERAL cases4096" in log
