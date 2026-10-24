// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Standalone active-Data-Stream bridge. This does not schedule Ordered Sets,
// initialize a trained Link, or imply PMA/main-chip integration.
module soc_pcie_gen3_packet_tx_path #(
 parameter integer MAX_ENCODED_BYTES=150
) (
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire [7:0] data_i, input wire valid_i, output wire ready_o,
 input wire sop_i, input wire eop_i, input wire dllp_i,
 input wire error_i, input wire nullify_i,
 output wire packet_good_o, output wire packet_error_o, output wire busy_o,
 output wire word_valid_o, input wire word_ready_i,
 output wire [127:0] word_o
);
 wire block_valid,block_ready;
 wire [1:0] header;
 wire [511:0] payload;
 soc_pcie_gen3_framer_tx #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) framer(
  .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),.data_i(data_i),
  .valid_i(valid_i),.ready_o(ready_o),.sop_i(sop_i),.eop_i(eop_i),
  .dllp_i(dllp_i),.error_i(error_i),.nullify_i(nullify_i),
  .block_valid_o(block_valid),.block_ready_i(block_ready),
  .header_o(header),.payload_o(payload),.packet_good_o(packet_good_o),
  .packet_error_o(packet_error_o),.busy_o(busy_o));
 soc_pcie_gen3_tx_path_v3 transport(
  .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),
  .block_valid_i(block_valid),.block_ready_o(block_ready),
  .header_i(header),.payload_i(payload),.advance_i(64'hffffffffffffffff),
  .scramble_i(64'hffffffffffffffff),.reseed_after_i(4'b0),
  .word_valid_o(word_valid_o),.word_ready_i(word_ready_i),.word_o(word_o));
endmodule
