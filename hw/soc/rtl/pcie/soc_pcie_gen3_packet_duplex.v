// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Independent packet TX/RX with an explicit elastic aligned-word seam.
// The testbench may connect the word ports; this module does not short them.
// Slow packet staging/receive parsing can backpressure these test/development
// ports. A real continuously-clocked PMA needs its own rated buffering/overrun
// contract, alignment/deskew and OS/LTSSM owner before any SoC/PHY connection.
module soc_pcie_gen3_packet_duplex #(
 parameter integer MAX_ENCODED_BYTES=150
)(
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire [7:0] tx_data_i, input wire tx_valid_i, output wire tx_ready_o,
 input wire tx_sop_i, input wire tx_eop_i, input wire tx_dllp_i,
 input wire tx_error_i, input wire tx_nullify_i,
 output wire tx_packet_good_o, output wire tx_packet_error_o, output wire tx_busy_o,
 output wire tx_word_valid_o, input wire tx_word_ready_i, output wire [127:0] tx_word_o,
 input wire rx_word_valid_i, output wire rx_word_ready_o, input wire [127:0] rx_word_i,
 input wire rx_stream_start_i, input wire rx_stream_abort_i,
 output wire rx_valid_o, input wire rx_ready_i, output wire [7:0] rx_data_o,
 output wire rx_sop_o, output wire rx_eop_o, output wire rx_dllp_o,
 output wire rx_packet_good_o, output wire rx_packet_nullified_o,
 output wire [11:0] rx_sequence_o, output wire rx_framing_error_o,
 output wire rx_stream_end_o, output wire rx_active_o, output wire rx_halted_o
);
 soc_pcie_gen3_packet_tx_path #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) tx(
  .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),
  .data_i(tx_data_i),.valid_i(tx_valid_i),.ready_o(tx_ready_o),
  .sop_i(tx_sop_i),.eop_i(tx_eop_i),.dllp_i(tx_dllp_i),
  .error_i(tx_error_i),.nullify_i(tx_nullify_i),
  .packet_good_o(tx_packet_good_o),.packet_error_o(tx_packet_error_o),.busy_o(tx_busy_o),
  .word_valid_o(tx_word_valid_o),.word_ready_i(tx_word_ready_i),.word_o(tx_word_o));
 soc_pcie_gen3_packet_rx_path #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) rx(
  .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),
  .stream_start_i(rx_stream_start_i),.stream_abort_i(rx_stream_abort_i),
  .word_valid_i(rx_word_valid_i),.word_ready_o(rx_word_ready_o),.word_i(rx_word_i),
  .valid_o(rx_valid_o),.ready_i(rx_ready_i),.data_o(rx_data_o),
  .sop_o(rx_sop_o),.eop_o(rx_eop_o),.dllp_o(rx_dllp_o),
  .packet_good_o(rx_packet_good_o),.packet_nullified_o(rx_packet_nullified_o),
  .sequence_o(rx_sequence_o),.framing_error_o(rx_framing_error_o),
  .stream_end_o(rx_stream_end_o),.active_o(rx_active_o),.halted_o(rx_halted_o));
endmodule
