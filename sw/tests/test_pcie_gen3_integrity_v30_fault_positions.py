# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Malformed public block at every DWORD position, including fourth-word faults."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT/'hw/soc/rtl/pcie'


@pytest.mark.parametrize('drop_fourth',[False,True])
def test_all_sixteen_actual_block_positions(tmp_path, drop_fourth):
    source = (RTL/'soc_pcie_gen3_framer_rx_integrity_v30.v').read_text()
    if drop_fourth:
        old = '(token_failures[2]|token_failures[3]);'
        assert source.count(old) == 1
        source = source.replace(old,'(token_failures[2]|1\'b0);')
    candidate = tmp_path/'candidate.v'
    candidate.write_text(source)
    tb = '''`timescale 1ns/1ps
module tb;
reg clk=0,rst=0,start=0,block_valid=0;
reg [511:0] payload=0;
wire [7:0] control0,control1;
wire [239:0] payload0,payload1;
wire [63:0] events0,events1;
'''
    for version,index in [(28,0),(30,1)]:
        tb += f'''soc_pcie_gen3_framer_rx_integrity_v{version} dut{index}(
.clk_i(clk),.rst_ni(rst),.flush_i(1'b0),.stream_start_i(start),.stream_abort_i(1'b0),
.block_valid_i(block_valid),.block_ready_o(control{index}[0]),.headers_i(8'haa),.payload_i(payload),.block_error_i(1'b0),
.valid_o(control{index}[1]),.ready_i(1'b1),.data_o(payload{index}[127:0]),.keep_o(payload{index}[143:128]),
.sop_o(payload{index}[159:144]),.eop_o(payload{index}[175:160]),.dllp_o(payload{index}[191:176]),.sequence_o(payload{index}[239:192]),
.packet_good_o(events{index}[3:0]),.packet_nullified_o(events{index}[7:4]),.packet_crc_bad_o(events{index}[11:8]),
.packet_dllp_o(events{index}[15:12]),.packet_sequence_o(events{index}[63:16]),
.framing_error_o(control{index}[2]),.overflow_o(control{index}[3]),.stream_end_o(control{index}[4]),
.active_o(control{index}[5]),.halted_o(control{index}[6]),.accepting_o(control{index}[7]));
'''
    tb += r'''
integer position,cycles,witnesses=0;
reg [3:0] seen=0;
task tick;
begin
 clk=0;#1;
 if(rst && dut0.step && dut0.token_failure) begin
   if(dut1.token_failure!==1'b1) $fatal(1,"V30_POSITION_FAULT_LOST");
   if(dut1.token_failures !== (4'b1 << (position%4))) $fatal(1,"V30_POSITION_WRONG_WORD");
   seen=seen|dut1.token_failures;witnesses=witnesses+1;
 end
 clk=1;#1;
 if(rst && {control0,payload0,events0} !== {control1,payload1,events1})
   $fatal(1,"V30_POSITION_PUBLIC_MISMATCH");
 clk=0;#1;
end
endtask
initial begin
 for(position=0;position<16;position=position+1) begin
   rst=0;start=0;block_valid=0;payload=0;tick;
   rst=1;start=1;tick;start=0;
   payload[position*8+:8]=8'h11;payload[128+position*8+:8]=8'h22;
   payload[256+position*8+:8]=8'h33;payload[384+position*8+:8]=8'h44;
   block_valid=1;tick;block_valid=0;
   cycles=0;
   while(!control0[6] && cycles<8) begin tick;cycles=cycles+1;end
   if(!control0[6] || !control0[2] || control0[1] || control0[3] || control0[5])
     $fatal(1,"V30_POSITION_FAULT_REQUIRED");
 end
 if(witnesses!=16 || seen!==4'hf) $fatal(1,"V30_POSITION_MISSING_COVERAGE");
 $display("V30_ALL_SIXTEEN_POSITIONS_PASS witnesses=%0d lanes=%0h",witnesses,seen);
 $finish;
end
endmodule
'''
    bench = tmp_path/'tb.v'
    bench.write_text(tb)
    image = tmp_path/'sim.vvp'
    compile_result = subprocess.run([shutil.which('iverilog'),'-g2012','-s','tb','-o',str(image),
        str(bench),str(RTL/'soc_pcie_gen3_framer_rx_integrity_v28.v'),str(candidate)],capture_output=True,text=True)
    (tmp_path/'compile.log').write_text(compile_result.stdout+compile_result.stderr)
    assert compile_result.returncode == 0, compile_result.stderr
    result = subprocess.run([shutil.which('vvp'),str(image)],capture_output=True,text=True)
    (tmp_path/'simulation.log').write_text(result.stdout+result.stderr)
    if drop_fourth:
        assert result.returncode != 0 and 'V30_POSITION_FAULT_LOST' in result.stdout
    else:
        assert result.returncode == 0 and 'V30_ALL_SIXTEEN_POSITIONS_PASS witnesses=16 lanes=f' in result.stdout
