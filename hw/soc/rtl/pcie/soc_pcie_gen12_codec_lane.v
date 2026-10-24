// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Independent single-symbol TX/RX state. No clock crossing is implemented.
// Active-low resets assert asynchronously; their release is a caller-owned
// per-domain reset contract. RD resets negative. Disabled cycles hold payload
// and RD, clearing valid/error strobes. Invalid TX K is reported, not sent.
// RX valid reports every received symbol, including an explicitly flagged error.
module soc_pcie_gen12_codec_lane (
 input wire tx_clk_i,tx_rst_ni,tx_enable_i,
 input wire [7:0] tx_data_i,input wire tx_k_i,
 output reg [9:0] tx_code_o,output reg tx_valid_o,tx_k_error_o,
 output reg tx_rd_o,
 input wire rx_clk_i,rx_rst_ni,rx_enable_i,
 input wire [9:0] rx_code_i,
 output reg [7:0] rx_data_o,output reg rx_k_o,rx_valid_o,
 output reg rx_code_error_o,rx_disparity_error_o,rx_rd_o
);
 wire [9:0] tx_code;
 wire tx_next_rd,tx_bad;
 wire [7:0] rx_data;
 wire rx_k,rx_next_rd,rx_bad,rx_disparity;
 soc_pcie_gen12_8b10b_encode tx(
  .data_i(tx_data_i),.k_i(tx_k_i),.rd_i(tx_rd_o),
  .code_o(tx_code),.rd_o(tx_next_rd),.k_error_o(tx_bad));
 soc_pcie_gen12_8b10b_decode rx(
  .code_i(rx_code_i),.rd_i(rx_rd_o),.data_o(rx_data),.k_o(rx_k),
  .rd_o(rx_next_rd),.code_error_o(rx_bad),.disparity_error_o(rx_disparity));
 always @(posedge tx_clk_i or negedge tx_rst_ni) begin
  if(!tx_rst_ni) begin
   tx_code_o<=0;tx_rd_o<=0;tx_valid_o<=0;tx_k_error_o<=0;
  end else begin
   tx_valid_o<=tx_enable_i && !tx_bad;
   tx_k_error_o<=tx_enable_i && tx_bad;
   if(tx_enable_i && !tx_bad) begin tx_code_o<=tx_code;tx_rd_o<=tx_next_rd;end
  end
 end
 always @(posedge rx_clk_i or negedge rx_rst_ni) begin
  if(!rx_rst_ni) begin
   rx_data_o<=0;rx_k_o<=0;rx_rd_o<=0;rx_valid_o<=0;
   rx_code_error_o<=0;rx_disparity_error_o<=0;
  end else begin
   rx_valid_o<=rx_enable_i;
   rx_code_error_o<=rx_enable_i && rx_bad;
   rx_disparity_error_o<=rx_enable_i && rx_disparity;
   if(rx_enable_i) begin rx_data_o<=rx_data;rx_k_o<=rx_k;rx_rd_o<=rx_next_rd;end
  end
 end
endmodule
`default_nettype wire
