// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_scrub_native_clear;
  reg clk=0, por=0, rst=0, sel=0;
  reg [11:0] addr=0;
  reg [31:0] data=0;
  reg [5:0] events=0;
  wire [31:0] rd;
  wire irq;
  integer source, n;
  always #5 clk=~clk;
  soc_scrub dut(.clk_i(clk),.rst_ni(rst),.rst_por_ni(por),
    .psel_i(sel),.penable_i(sel),.pwrite_i(sel),.paddr_i(addr),
    .pwdata_i(data),.prdata_o(rd),.irq_o(irq),
    .ram_sec_i(events[0]),.ram_rd_i(events[1]),.ram_ded_i(events[2]),
    .rom_sec_i(events[3]),.rom_rd_i(events[4]),.rom_ded_i(events[5]),
    .ram_addr_i(32'h100),.rom_addr_i(32'hc0000100));
  task write_clear;
    input [5:0] mask;
    begin
      addr=12'h020; data={26'b0,mask}; sel=1;
      @(negedge clk); sel=0;
    end
  endtask
  task expect_count;
    input integer channel;
    input [31:0] expected;
    begin
      addr=12'h008+channel*4; #1;
      if(rd!==expected) $fatal(1,"source=%0d expected=%h actual=%h",channel,expected,rd);
    end
  endtask
  initial begin
    repeat(3) @(negedge clk); por=1; rst=1;
    @(negedge clk);
    for(source=0;source<6;source=source+1) begin
      // Model undefined SRAM reports through the real input port. No force,
      // deposit, initialized state or modified PDK simulation model.
      events=0; events[source]=1'bx;
      repeat(3) @(negedge clk); events=0;
      addr=12'h008+source*4; #1;
      if((^rd)!==1'bx) $fatal(1,"Negative precondition: event did not poison count");
      @(negedge clk); write_clear(6'b1<<source);
      expect_count(source,0);
      @(negedge clk); events=6'b1<<source; write_clear(6'b1<<source);
      events=0; expect_count(source,1);
      @(negedge clk); rst=0;
      repeat(3) @(negedge clk); rst=1; expect_count(source,1);
      @(negedge clk); write_clear(6'b1<<source); expect_count(source,0);
      @(negedge clk);
    end
    // Every source saturates, then a simultaneous clear/event produces one.
    events=6'h3f;
    repeat(65540) @(negedge clk);
    events=0;
    for(n=0;n<6;n=n+1) expect_count(n,65535);
    @(negedge clk);events=6'h3f;write_clear(6'h3f);events=0;
    for(n=0;n<6;n=n+1) expect_count(n,1);
    @(negedge clk);por=0;
    repeat(3) @(negedge clk);por=1;
    for(n=0;n<6;n=n+1) expect_count(n,0);
    $display("SCRUB_NATIVE_CLEAR PASS sources=6 saturation=65535 clear_event=1");
    $finish;
  end
  initial begin #1000000; $fatal(1,"Scrub native clear test timed out"); end
endmodule
