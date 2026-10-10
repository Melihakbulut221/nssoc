# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal old/new decoders and real registered companion transition controls."""

from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "hw/soc/rtl/pcie"
GEN = runpy.run_path(str(ROOT / "scripts/generate_pcie_integrity_predecode_v9.py"))
SIM = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v3_crc.py"))[
    "simulate"
]


def test_exact_generated_inverse_and_wrapper_bridge():
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v9.v").read_text()
    assert source == GEN["candidate"]()
    assert source.count(GEN["predecode"]()) == 1
    source = source.replace(GEN["predecode"](), "")
    for before, after in reversed(GEN["CHANGES"]):
        assert source.count(after) == 1
        source = source.replace(after, before)
    assert source.replace("integrity_v9", "integrity_v7") == GEN["SOURCE"].read_text()
    for name in [
        "hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v7.v",
        "hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v7.py",
        "hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v7",
    ]:
        assert (ROOT / name.replace("_v7", "_v9")).read_text().replace(
            "integrity_v9", "integrity_v7"
        ) == (ROOT / name).read_text()


def functions():
    return (
        GEN["predecode"]()
        .split(" function automatic", 1)[1]
        .split(" reg [511:0] current_predecode", 1)[0]
        .join([" function automatic", ""])
    )


def old_function():
    source = GEN["SOURCE"].read_text()
    decoder = source.split("     length_dw={word[14:8],word[7:4]};", 1)[1].split(
        "     if(control_active[j])", 1
    )[0]
    decoder = "     length_dw={word[14:8],word[7:4]};" + decoder
    expected = source.split("               tlp_payload=", 1)[1].split(
        "               header_bad_n=", 1
    )[0]
    expected = "               tlp_payload=" + expected
    return (
        """function automatic [31:0] original_decode;
input[31:0] word;
reg[10:0] length_dw;reg[12:0] encoded_bytes,tlp_payload,expected_n;
reg[3:0] crc;reg stp_ok,sdp_ok,idl_ok,eds_ok,edb_ok,handled;
integer j;reg[1:0] slice;
begin j=3;slice=3;
"""
        + decoder
        + expected
        + """
original_decode={encoded_bytes,word[7],expected_n,edb_ok,eds_ok,idl_ok,sdp_ok,stp_ok};
end endfunction
"""
    )


@pytest.mark.parametrize("maximum", [18, 150, 4118])
@pytest.mark.parametrize(
    "fault", [None, "encoded_off_by_one", "crc_flip", "lost_digest"]
)
def test_literal_decoder_length_crc_parity_header_space(tmp_path, maximum, fault):
    body = functions()
    changes = {
        "encoded_off_by_one": (
            "encoded={length,2'b00}-13'd2;",
            "encoded={length,2'b00}-13'd1;",
        ),
        "crc_flip": ("check_crc==value[23:20]", "(check_crc^4'b1)==value[23:20]"),
        "lost_digest": ("+(value[23]?13'd4:13'd0)", "+13'd0"),
    }
    if fault:
        before, after = changes[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    bench = (
        f"module tb;localparam MAX_ENCODED_BYTES={maximum};\n"
        + body
        + old_function()
        + """
reg[31:0] value;integer length,check,p,fmt,digest,seed=9405,cases=0,i;
task compare;
begin
if(original_decode(value)!==predecode_word(value))
 $fatal(1,"PREDECODE_MISMATCH word=%h old=%h new=%h",value,original_decode(value),predecode_word(value));
cases=cases+1;
end endtask
initial begin
for(length=0;length<2048;length=length+1)
 for(check=0;check<16;check=check+1)
  for(p=0;p<2;p=p+1) begin
   value={$random(seed)};value[3:0]=15;value[7:4]=length[3:0];value[14:8]=length[10:4];
   value[15]=p;value[23:20]=check;compare;
  end
for(length=0;length<1024;length=length+1)
 for(fmt=0;fmt<8;fmt=fmt+1)
  for(digest=0;digest<2;digest=digest+1) begin
   value={$random(seed)};value[7:5]=fmt;value[23]=digest;
   value[17:16]=length[9:8];value[31:24]=length[7:0];compare;
  end
for(i=0;i<16384;i=i+1) begin value=$random(seed);compare;end
value=0;compare;value=32'h0090801f;compare;value=32'hc0c0c0c0;compare;value=32'h1200acf0;compare;
if(cases!=98308)$fatal(1,"COUNT");
$display("PASS_LITERAL_PREDECODE cases=%0d",cases);$finish;
end endmodule
"""
    )
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "PREDECODE_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS_LITERAL_PREDECODE cases=98308" in log


def buffer_transition(source):
    body = source.split("         if(slice==3) begin\n", 1)[1].split(
        "       if(ending && read_ptr==write_ptr", 1
    )[0]
    return "if(step) begin\n         if(slice==3) begin\n" + body


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "shift_width",
        "wrong_replacement",
        "lost_current_load",
        "lost_next_load",
        "bad_reset",
    ],
)
def test_actual_companion_bank_transition_and_priority(tmp_path, fault):
    source = (RTL / "soc_pcie_gen3_framer_rx_integrity_v9.v").read_text()
    transition = buffer_transition(source)
    reset = source.split("     state<=TOKEN;current_block<=0;next_block<=0;", 1)[
        1
    ].split("     write_ptr<=", 1)[0]
    reset = "current_block<=0;next_block<=0;" + reset
    body = transition + reset
    changes = {
        "shift_width": ("current_predecode[511:128]", "current_predecode[510:127]"),
        "wrong_replacement": (
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
        "bad_reset": (
            "current_predecode<=predecode_block(512'b0);",
            "current_predecode<=0;",
        ),
    }
    if fault:
        before, after = changes[fault]
        assert body.count(before) == 1
        transition = transition.replace(before, after)
        reset = reset.replace(before, after)
    bench = (
        "module tb;localparam MAX_ENCODED_BYTES=150;\n"
        + functions()
        + """
reg clk=0,rst=0,active=0,flush=0,abort=0;
reg[511:0] current_block,next_block,payload_i,current_predecode,next_predecode;
reg current_valid,next_valid;reg[1:0] slice;reg step,block_valid_i,block_ready_o,ending,ending_n;
wire last_slice=step&&slice==3;wire[511:0] input_predecode=predecode_block(payload_i);
always #1 clk=~clk;
always @(posedge clk) begin
if(!rst) begin
"""
        + reset
        + """
end else if(flush || abort) begin current_valid<=0;next_valid<=0;slice<=0;end
else if(active) begin
"""
        + transition
        + """
end end
integer trial,k,seed=9411,full_replace=0,bypass=0,shifts=0,next_load=0,flushes=0;
initial begin
step=0;block_valid_i=0;block_ready_o=0;ending=0;ending_n=0;payload_i=0;
for(trial=0;trial<4096;trial=trial+1) begin
 @(negedge clk);
 if(current_predecode!==predecode_block(current_block) || next_predecode!==predecode_block(next_block))
  $fatal(1,"COMPANION_BANK_MISMATCH trial=%0d",trial);
 rst=1;active=1;
 for(k=0;k<16;k=k+1)payload_i[k*32+:32]=$random(seed);
 flush=(trial%97==20);abort=(trial%131==44);
 block_valid_i=($random(seed)&3)!=0;block_ready_o=($random(seed)&7)!=0;
 step=current_valid && (($random(seed)&3)!=0);ending=trial%71==33;ending_n=trial%61==32;
 if(flush||abort)flushes=flushes+1;
 else begin
  if(last_slice&&next_valid&&block_valid_i&&block_ready_o)full_replace=full_replace+1;
  if(block_valid_i&&block_ready_o&&(!current_valid||(last_slice&&!next_valid)))bypass=bypass+1;
  if(block_valid_i&&block_ready_o&&current_valid&&!(last_slice&&!next_valid))next_load=next_load+1;
  if(step&&slice!=3)shifts=shifts+1;
 end
end
if(full_replace<10 || bypass<10 || shifts<100 || next_load<100 || flushes<10)$fatal(1,"TRANSITION_COVERAGE");
$display("PASS_COMPANION_TRANSITIONS cases=4096 fullreplace=%0d bypass=%0d shifts=%0d next=%0d flushabort=%0d",full_replace,bypass,shifts,next_load,flushes);$finish;
end endmodule
"""
    )
    result, log = SIM(tmp_path, bench)
    if fault:
        assert result.returncode != 0 and "COMPANION_BANK_MISMATCH" in log
    else:
        assert result.returncode == 0 and "PASS_COMPANION_TRANSITIONS cases=4096" in log
