// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Raw bit 0 and byte slot 0 are earliest. This is a symbol transport decoder,
// not an LTSSM or link-up detector. Batch delivery is one clock after the
// aligner captures its final raw word. Current flush controls discard pending
// delivery and the current raw word together.
module soc_pcie_gen12_raw32_rx (
 input wire rx_clk_i,rx_rst_ni,enable_i,force_realign_i,polarity_i,raw_valid_i,
 input wire [31:0] raw_i,
 output reg [31:0] data_o,
 output reg [3:0] k_o,code_error_o,disparity_error_o,comma_o,
 output reg [2:0] symbol_count_o,
 output reg boundary_valid_o,acquired_o,rd_o
);
 wire [39:0] aligned_symbols;
 wire [2:0] aligned_count;
 wire [3:0] aligned_comma;
 wire aligned_boundary,aligned_acquired,aligned_rd;
 soc_pcie_gen12_raw32_align aligner(
  .rx_clk_i(rx_clk_i),.rx_rst_ni(rx_rst_ni),.enable_i(enable_i),
  .force_realign_i(force_realign_i),.polarity_i(polarity_i),
  .raw_valid_i(raw_valid_i),.raw_i(raw_i),
  .symbols_o(aligned_symbols),.symbol_count_o(aligned_count),
  .comma_o(aligned_comma),.boundary_valid_o(aligned_boundary),
  .acquired_o(aligned_acquired),.acquired_rd_o(aligned_rd));
 wire [31:0] decoded;
 wire [3:0] decoded_k,bad_code,bad_disparity,next_rd;
 wire [4:0] chain_rd;
 assign chain_rd[0]=aligned_acquired ? aligned_rd : rd_o;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:decoders
  soc_pcie_gen12_8b10b_decode decoder(
   .code_i(aligned_symbols[g*10+:10]),.rd_i(chain_rd[g]),
   .data_o(decoded[g*8+:8]),.k_o(decoded_k[g]),.rd_o(next_rd[g]),
   .code_error_o(bad_code[g]),.disparity_error_o(bad_disparity[g]));
  // Unused slots must not change RD; every received slot must, even if invalid.
  assign chain_rd[g+1]=(aligned_count>g) ? next_rd[g] : chain_rd[g];
 end endgenerate
 reg previous_polarity;
 wire flush=!enable_i || force_realign_i || polarity_i!=previous_polarity;
 integer i;
 always @(posedge rx_clk_i or negedge rx_rst_ni)begin
  if(!rx_rst_ni)begin
   previous_polarity<=0;
   data_o<=0;k_o<=0;code_error_o<=0;disparity_error_o<=0;comma_o<=0;
   symbol_count_o<=0;boundary_valid_o<=0;acquired_o<=0;rd_o<=0;
  end else begin
   previous_polarity<=polarity_i;
   data_o<=0;k_o<=0;code_error_o<=0;disparity_error_o<=0;comma_o<=0;
   symbol_count_o<=0;boundary_valid_o<=0;acquired_o<=0;
   if(flush)begin
    rd_o<=0;
   end else begin
    symbol_count_o<=aligned_count;
    boundary_valid_o<=aligned_boundary;
    acquired_o<=aligned_acquired;
    rd_o<=chain_rd[4];
    for(i=0;i<4;i=i+1)begin
     if(i<aligned_count)begin
      data_o[i*8+:8]<=decoded[i*8+:8];
      k_o[i]<=decoded_k[i];
      code_error_o[i]<=bad_code[i];
      disparity_error_o[i]<=bad_disparity[i];
      comma_o[i]<=aligned_comma[i];
     end
    end
   end
  end
 end
endmodule
`default_nettype wire
