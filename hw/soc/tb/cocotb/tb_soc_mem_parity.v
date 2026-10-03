// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_soc_mem_parity #(
    parameter WORDS=8192, HARDEN=1, RDREG=1
);
  reg clk_i=0, rst_ni=0, req_i=0, we_i=0, scrub_en_i=0;
  reg [31:0] addr_i=0, wdata_i=0;
  reg [3:0] be_i=0;
  reg [15:0] scrub_ivl_i=7;
  wire a_gnt, a_valid, a_err, a_sec, a_ded, a_rd;
  wire b_gnt, b_valid, b_err, b_sec, b_ded, b_rd;
  wire [31:0] a_data, b_data, a_evt, b_evt;
  soc_mem_array #(.WORDS(WORDS), .HARDEN(HARDEN), .RDREG(RDREG)) array (
    .clk_i(clk_i), .rst_ni(rst_ni), .req_i(req_i), .we_i(we_i),
    .addr_i(addr_i), .wdata_i(wdata_i), .be_i(be_i),
    .scrub_en_i(scrub_en_i), .scrub_ivl_i(scrub_ivl_i),
    .gnt_o(a_gnt), .rvalid_o(a_valid), .rdata_o(a_data), .err_o(a_err),
    .sec_o(a_sec), .ded_o(a_ded), .rd_o(a_rd), .evt_addr_o(a_evt));
  soc_mem_macro #(.WORDS(WORDS), .HARDEN(HARDEN), .RDREG(RDREG)) macro (
    .clk_i(clk_i), .rst_ni(rst_ni), .req_i(req_i), .we_i(we_i),
    .addr_i(addr_i), .wdata_i(wdata_i), .be_i(be_i),
    .scrub_en_i(scrub_en_i), .scrub_ivl_i(scrub_ivl_i),
    .gnt_o(b_gnt), .rvalid_o(b_valid), .rdata_o(b_data), .err_o(b_err),
    .sec_o(b_sec), .ded_o(b_ded), .rd_o(b_rd), .evt_addr_o(b_evt));
endmodule
