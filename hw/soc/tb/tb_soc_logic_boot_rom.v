// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Exhaustive address/read-only protocol check against independent raw words
// and the frozen hardware encoder. ROM_EXPECTED_HEX belongs only to the bench.
`ifndef ROM_EXPECTED_HEX
 `define ROM_EXPECTED_HEX "expected.hex"
`endif
`timescale 1ns/1ps
module tb_logic_rom #(parameter RDREG=1);
 reg clk=0,rst=0,req=0,we=0,scrub=0;
 reg[31:0] addr=0;
 wire gnt,valid,err,sec,rd,ded;
 wire[31:0] data,evt;
 reg[31:0] expected[0:2047];
 reg[31:0] enc_data;
 wire[7:0] enc_check;
 wire[71:0] enc_code;
 integer i,reads=0,writes=0;
 always #10 clk=!clk;
`ifdef SOC_ROM_GATE_LEVEL
 soc_logic_boot_rom
`else
 soc_logic_boot_rom #(.RDREG(RDREG))
`endif
 dut(.clk_i(clk),.rst_ni(rst),.req_i(req),.addr_i(addr),.we_i(we),.be_i(4'hf),.wdata_i(32'hbadc0ffe),.gnt_o(gnt),.rvalid_o(valid),.rdata_o(data),.err_o(err),.scrub_en_i(scrub),.scrub_ivl_i(16'h0),.sec_o(sec),.rd_o(rd),.ded_o(ded),.evt_addr_o(evt));
 secded_enc oracle(.data_in({32'h0,enc_data}),.check_out(enc_check),.code_out(enc_code));
 task access;
 input integer a;
 input w;
 begin
  @(negedge clk);addr=a*4;req=1;we=w;enc_data=expected[a];
  #1;if(gnt!==1)$fatal(1,"grant missing");
  @(negedge clk);req=0;we=0;
  if(!w && dut.row_dout!=={enc_check[6:0],enc_data})$fatal(1,"ROM codeword mismatch %0d",a);
  if(RDREG) @(negedge clk);
  if(valid!==1 || err!==w)$fatal(1,"response status mismatch %0d write=%0d",a,w);
  if(!w && data!==expected[a])$fatal(1,"read mismatch %0d",a);
  if(sec!==0 || rd!==0 || ded!==0)$fatal(1,"unexpected ECC event %0d",a);
  if(w)writes=writes+1;else reads=reads+1;
  @(negedge clk);if(valid!==0)$fatal(1,"duplicate response");
 end endtask
 initial begin
  $readmemh(`ROM_EXPECTED_HEX,expected);
  repeat(3)@(negedge clk);rst=1;
  for(i=0;i<2048;i=i+1)begin
   access(i,0);
   if(i%127==0)begin access(i,1);access(i,0);end
  end
  scrub=1;
  for(i=0;i<2048;i=i+1)access(i,0);
  $display("LOGIC_ROM PASS reads=%0d rejected_writes=%0d words=2048 oracle=frozen_secded_encoder scrub=on_off",reads,writes);
  $finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
