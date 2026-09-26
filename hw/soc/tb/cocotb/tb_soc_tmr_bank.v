// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_soc_tmr_bank;
  reg clk_i=0, rst_ni=0;
  reg [63:0] data=0;
  wire [3:0] a4, b4, c4, voted4;
  wire mismatch4;
  soc_tmr_bank #(.W(4), .RST_VAL(64'h0123456789abcdef), .POL(64'h0), .MIX(0)) bank_a4
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[3:0]), .q_o(a4));
  soc_tmr_bank #(.W(4), .RST_VAL(64'h0123456789abcdef), .POL(64'haaaaaaaaaaaaaaaa), .MIX(0)) bank_b4
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[3:0]), .q_o(b4));
  soc_tmr_bank #(.W(4), .RST_VAL(64'h0123456789abcdef), .POL(64'h5555555555555555), .MIX(1)) bank_c4
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[3:0]), .q_o(c4));
  tmr_voter #(.WIDTH(4)) vote_4 (.in_a(a4), .in_b(b4), .in_c(c4), .out(voted4), .mismatch(mismatch4));
  wire [4:0] a5, b5, c5, voted5;
  wire mismatch5;
  soc_tmr_bank #(.W(5), .RST_VAL(64'h0123456789abcdef), .POL(64'h0), .MIX(0)) bank_a5
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[4:0]), .q_o(a5));
  soc_tmr_bank #(.W(5), .RST_VAL(64'h0123456789abcdef), .POL(64'haaaaaaaaaaaaaaaa), .MIX(0)) bank_b5
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[4:0]), .q_o(b5));
  soc_tmr_bank #(.W(5), .RST_VAL(64'h0123456789abcdef), .POL(64'h5555555555555555), .MIX(1)) bank_c5
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[4:0]), .q_o(c5));
  tmr_voter #(.WIDTH(5)) vote_5 (.in_a(a5), .in_b(b5), .in_c(c5), .out(voted5), .mismatch(mismatch5));
  wire [7:0] a8, b8, c8, voted8;
  wire mismatch8;
  soc_tmr_bank #(.W(8), .RST_VAL(64'h0123456789abcdef), .POL(64'h0), .MIX(0)) bank_a8
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[7:0]), .q_o(a8));
  soc_tmr_bank #(.W(8), .RST_VAL(64'h0123456789abcdef), .POL(64'haaaaaaaaaaaaaaaa), .MIX(0)) bank_b8
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[7:0]), .q_o(b8));
  soc_tmr_bank #(.W(8), .RST_VAL(64'h0123456789abcdef), .POL(64'h5555555555555555), .MIX(1)) bank_c8
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[7:0]), .q_o(c8));
  tmr_voter #(.WIDTH(8)) vote_8 (.in_a(a8), .in_b(b8), .in_c(c8), .out(voted8), .mismatch(mismatch8));
  wire [31:0] a32, b32, c32, voted32;
  wire mismatch32;
  soc_tmr_bank #(.W(32), .RST_VAL(64'h0123456789abcdef), .POL(64'h0), .MIX(0)) bank_a32
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[31:0]), .q_o(a32));
  soc_tmr_bank #(.W(32), .RST_VAL(64'h0123456789abcdef), .POL(64'haaaaaaaaaaaaaaaa), .MIX(0)) bank_b32
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[31:0]), .q_o(b32));
  soc_tmr_bank #(.W(32), .RST_VAL(64'h0123456789abcdef), .POL(64'h5555555555555555), .MIX(1)) bank_c32
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[31:0]), .q_o(c32));
  tmr_voter #(.WIDTH(32)) vote_32 (.in_a(a32), .in_b(b32), .in_c(c32), .out(voted32), .mismatch(mismatch32));
  wire [63:0] a64, b64, c64, voted64;
  wire mismatch64;
  soc_tmr_bank #(.W(64), .RST_VAL(64'h0123456789abcdef), .POL(64'h0), .MIX(0)) bank_a64
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[63:0]), .q_o(a64));
  soc_tmr_bank #(.W(64), .RST_VAL(64'h0123456789abcdef), .POL(64'haaaaaaaaaaaaaaaa), .MIX(0)) bank_b64
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[63:0]), .q_o(b64));
  soc_tmr_bank #(.W(64), .RST_VAL(64'h0123456789abcdef), .POL(64'h5555555555555555), .MIX(1)) bank_c64
    (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(data[63:0]), .q_o(c64));
  tmr_voter #(.WIDTH(64)) vote_64 (.in_a(a64), .in_b(b64), .in_c(c64), .out(voted64), .mismatch(mismatch64));
endmodule
