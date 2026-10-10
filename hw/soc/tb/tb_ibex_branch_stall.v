// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps

// Taken branch immediately following a store whose response is delayed.
// The unsupported WB=1/BTA=0 control jumps to 254-2008 = 0xfffff926.
module tb_ibex_branch_stall;
  parameter integer WRITEBACK = 1;
  parameter integer BRANCH_ALU = WRITEBACK;
  parameter integer RESPONSE_CYCLES = 5;
  reg clk = 0;
  always #5 clk = ~clk;
  reg rst_n = 0;
  wire halted;
  wire [31:0] exit_code;
  wire minor, major_internal, major_bus, double_fault;
  ibex_min_system #(.DATA_RESPONSE_CYCLES(RESPONSE_CYCLES)) dut (
      .clk_i(clk), .rst_ni(rst_n), .halted_o(halted), .exit_code_o(exit_code),
      .alert_minor_o(minor), .alert_major_internal_o(major_internal),
      .alert_major_bus_o(major_bus), .double_fault_seen_o(double_fault),
      .core_sleep_o());
  defparam dut.u_ibex.WritebackStage = WRITEBACK;
  defparam dut.u_ibex.BranchTargetALU = BRANCH_ALU;

  integer i;
  integer stores = 0;
  integer loads = 0;
  always @(posedge clk) if (rst_n) begin
    if (dut.data_req && dut.data_we && dut.data_addr == 32'h200) begin
      if (dut.data_wdata !== 0 || dut.data_be !== 4'hf)
        $fatal(1, "Incorrect accepted store");
      stores = stores + 1;
    end
    if (dut.data_req && !dut.data_we && dut.data_addr == 32'h200)
      loads = loads + 1;
    if (minor || major_internal || major_bus || double_fault)
      $fatal(1, "Unexpected core alert");
    if (dut.u_ibex.u_ibex_core.csr_save_cause)
      $fatal(1, "Unexpected trap cause=%h pc=%h",
             dut.u_ibex.u_ibex_core.exc_cause,
             dut.u_ibex.u_ibex_core.pc_id);
  end

  initial begin
    for (i=0; i<dut.MEM_WORDS; i=i+1) dut.mem[i] = 0;
    dut.mem[128] = 32'hbadf00d;
    dut.mem[32] = 32'h20000293; // li t0,0x200
    dut.mem[33] = 32'h0fe00793; // li a5,254
    dut.mem[34] = 32'h7d800c93; // li s9,2008
    dut.mem[35] = 32'h0002a023; // sw zero,0(t0)
    dut.mem[36] = 32'h01979663; // bne a5,s9,good (+12)
    dut.mem[37] = 32'h00100513; // li a0,1 (wrong fallthrough)
    dut.mem[38] = 32'h0100006f; // j finish
    dut.mem[39] = 32'h0002a303; // good: lw t1,0(t0)
    dut.mem[40] = 32'hfe031ae3; // bnez t1,wrong fallthrough (-12)
    dut.mem[41] = 32'h00000513; // li a0,0
    dut.mem[42] = 32'h001002b7; // finish: lui t0,0x100
    dut.mem[43] = 32'h00428293; // addi t0,t0,4 (halt address)
    dut.mem[44] = 32'h00a2a023; // sw a0,0(t0)
    dut.mem[45] = 32'h0000006f; // j .
    repeat (10) @(negedge clk);
    rst_n = 1;
    for (i=0; i<1000 && !halted; i=i+1) @(negedge clk);
    if (!halted || exit_code !== 0 || stores != 1 || loads != 1 || dut.mem[128] !== 0)
      $fatal(1, "Incorrect completion halted=%b code=%h stores=%0d",
             halted, exit_code, stores);
    $display("PASS branch after delayed store: wb=%0d bta=%0d delay=%0d cycles=%0d",
             WRITEBACK, BRANCH_ALU, RESPONSE_CYCLES, i);
    $finish;
  end
endmodule
