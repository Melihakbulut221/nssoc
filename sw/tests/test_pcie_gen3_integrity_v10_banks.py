# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal bank writers: reachable valid-bank equality, including real fault edges."""

from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_banks_v10.py"))
OLD = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v9_predecode.py"))
SIM = OLD["SIM"]


def test_exact_generated_inverse_and_wrapper_bridge():
    text = (RTL / "soc_pcie_gen3_framer_rx_integrity_v10.v").read_text()
    assert text == GEN["candidate"]()
    assert text.count(GEN["bank_writer"]()) == 1
    text = text.replace(GEN["bank_writer"](), "")
    for before, after in reversed(GEN["CHANGES"]):
        assert text.count(after) == 1
        text = text.replace(after, before)
    assert text.replace("integrity_v10", "integrity_v9") == GEN["SOURCE"].read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v9.v",
        "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v9.py",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v9",
    ]:
        assert (ROOT / name.replace("_v9", "_v10")).read_text().replace(
            "integrity_v10", "integrity_v9"
        ) == (ROOT / name).read_text()


def mini(source, name, writer):
    transition = OLD["buffer_transition"](source)
    reset = "current_valid<=0;next_valid<=0;slice<=0;"
    if not writer:
        reset += "current_block<=0;next_block<=0;current_predecode<=predecode_block(512'b0);next_predecode<=predecode_block(512'b0);"
    return (
        """module NAME(input clk_i,rst_ni,active_o,flush_i,stream_start_i,stream_abort_i,fault_now,
input drive_step,block_valid_i,drive_ready,ending,ending_n,input[511:0] payload_i);
localparam MAX_ENCODED_BYTES=150;
reg[511:0] current_block,next_block,current_predecode,next_predecode;
reg current_valid,next_valid;reg[1:0] slice;
wire enabled=rst_ni&&!flush_i&&!stream_start_i&&!stream_abort_i;
wire step=enabled&&active_o&&!ending&&current_valid&&drive_step;
wire block_ready_o=enabled&&active_o&&!ending&&drive_ready&&(!next_valid||last_slice);
wire last_slice=step&&slice==3;
wire[511:0] input_predecode=predecode_block(payload_i);
""".replace("NAME", name)
        + OLD["functions"]()
        + writer
        + """
always @(posedge clk_i or negedge rst_ni) begin
if(!rst_ni) begin
"""
        + reset
        + """
end else if(flush_i||stream_start_i) begin current_valid<=0;next_valid<=0;slice<=0;end
else if((stream_abort_i&&active_o)||fault_now) begin current_valid<=0;next_valid<=0;end
else if(active_o) begin
"""
        + transition
        + "\nend end\nendmodule\n"
    )


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "wrong_shift",
        "wrong_handoff",
        "lost_current_load",
        "lost_next_load",
        "lost_payload_shift",
    ],
)
def test_literal_valid_banks_and_fault_quarantine(tmp_path, fault):
    old = GEN["SOURCE"].read_text()
    new = (RTL / "soc_pcie_gen3_framer_rx_integrity_v10.v").read_text()
    writer = GEN["bank_writer"]()
    changes = {
        "wrong_shift": ("current_predecode[511:128]", "current_predecode[510:127]"),
        "wrong_handoff": (
            "current_predecode<=next_predecode",
            "current_predecode<=input_predecode",
        ),
        "lost_current_load": (
            "current_predecode<=input_predecode;",
            "current_predecode<=current_predecode;",
        ),
        "lost_next_load": (
            "next_predecode<=input_predecode;",
            "next_predecode<=next_predecode;",
        ),
        "lost_payload_shift": (
            "32'b0,current_block[127:32]",
            "32'b0,current_block[126:31]",
        ),
    }
    if fault:
        before, after = changes[fault]
        assert writer.count(before) == 1
        writer = writer.replace(before, after)
    ports = "(clk,rst,active,flush,start,abort,fault,consume,valid,ready,ending,ending_n,payload)"
    bench = (
        mini(old, "old_banks", "")
        + mini(new, "new_banks", writer)
        + """
module tb;
reg clk=0,rst=0,active=0,flush=0,start=0,abort=0,fault=0;
reg consume=0,valid=0,ready=0,ending=0,ending_n=0;reg[511:0]payload=0;
always #1 clk=~clk;
old_banks gold PORTS;new_banks gate PORTS;
integer trial,k,seed=100051,replace_count=0,fault_updates=0,hidden_difference=0,reset_count=0,abort_count=0,valid_checks=0;
initial begin
for(trial=0;trial<8192;trial=trial+1) begin
 @(negedge clk);
 if({gold.current_valid,gold.next_valid,gold.slice} !== {gate.current_valid,gate.next_valid,gate.slice})$fatal(1,"VISIBLE_CONTROL_MISMATCH");
 if(gate.current_valid) begin
   valid_checks=valid_checks+1;
   if(gold.current_block!==gate.current_block || gold.current_predecode!==gate.current_predecode ||
      gate.current_predecode!==gate.predecode_block(gate.current_block))$fatal(1,"VALID_BANK_MISMATCH current");
 end
 if(gate.next_valid) begin
   valid_checks=valid_checks+1;
   if(gold.next_block!==gate.next_block || gold.next_predecode!==gate.next_predecode ||
      gate.next_predecode!==gate.predecode_block(gate.next_block))$fatal(1,"VALID_BANK_MISMATCH next");
 end
 if(!gate.current_valid && (gold.current_block!==gate.current_block)) hidden_difference=hidden_difference+1;
 rst=(trial%103!=27);active=1;flush=(trial%97==20);start=(trial%53==18);abort=(trial%131==44);
 for(k=0;k<16;k=k+1)payload[k*32+:32]=$random(seed);
 consume=($random(seed)&3)!=0;valid=($random(seed)&3)!=0;ready=($random(seed)&7)!=0;
 ending=trial%71==33;ending_n=trial%61==32;fault=trial%37==12;
 #0.01;
 if(gate.last_slice&&gate.next_valid&&valid&&gate.block_ready_o&&!fault&&!abort&&!flush&&!start)replace_count=replace_count+1;
 if(fault&&gate.step)fault_updates=fault_updates+1;
 if(!rst)reset_count=reset_count+1;
 if(abort)abort_count=abort_count+1;
end
if(replace_count<10||fault_updates<20||hidden_difference<20||reset_count<20||abort_count<20||valid_checks<1000)$fatal(1,"BANK_COVERAGE");
$display("PASS_VALID_BANK_QUARANTINE cases=8192 replace=%0d fault=%0d hidden_difference=%0d reset=%0d abort=%0d valid=%0d",replace_count,fault_updates,hidden_difference,reset_count,abort_count,valid_checks);$finish;
end endmodule
""".replace("PORTS", ports)
    )
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "VALID_BANK_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS_VALID_BANK_QUARANTINE cases=8192" in log
