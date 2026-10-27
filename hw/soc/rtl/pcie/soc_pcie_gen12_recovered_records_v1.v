// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Raw32 recovered lane -> qualified record collector -> opaque record CDC.
// Either clean reset request resets BOTH clock domains and all collector state.
// No independent local flush: a running polarity change or known loss faults the
// epoch. The owner resets both domains before reacquisition. Peer-up bits enforce
// startup only; they do not detect a clock stopping during an established epoch.
module soc_pcie_gen12_recovered_records_v1 #(parameter FIFO_DEPTH=32) (
 input wire por_ni,recovered_clk_i,common_clk_i,recovered_reset_i,common_reset_i,
 input wire raw_valid_i,polarity_i,loss_i,
 input wire [31:0] raw_i,
 output wire recovered_running_o,boundary_valid_o,rd_o,
 output wire recovered_accept_o,recovered_fault_o,recovered_overflow_o,
 output wire common_running_o,common_fault_o,record_valid_o,
 input wire record_ready_i,
 output wire [127:0] record_data_o,
 output wire [15:0] record_k_o,record_code_error_o,record_disparity_error_o,record_comma_o
);
 wire cdc_running;
 reg source_armed;
 // The frozen collector/decoder remember polarity=0 on reset. Give them one
 // internal running edge to settle explicit polarity before admitting raw data.
 always @(posedge recovered_clk_i or negedge cdc_running)
  if(!cdc_running) source_armed<=1'b0;
  else source_armed<=1'b1;
 assign recovered_running_o=cdc_running && source_armed;
 wire reset_request=!por_ni || recovered_reset_i || common_reset_i;
 reg previous_polarity;
 always @(posedge recovered_clk_i or posedge reset_request)
  if(reset_request) previous_polarity<=1'b0;
  else previous_polarity<=polarity_i;
 wire polarity_loss=recovered_running_o && (polarity_i!=previous_polarity);
 wire collected_valid,collector_overflow;
 wire [127:0] collected_data;
 wire [15:0] collected_k,collected_code_error,collected_disparity_error,collected_comma;
 wire epoch_loss=loss_i || collector_overflow || polarity_loss;
 // The collector's qualified RX contains the full decoder RD state. No second
 // RD owner is added here. Its inactive TX half is constant-tied and pruned.
 soc_pcie_gen12_training_records u_collector (
  .rx_clk_i(recovered_clk_i),.rx_rst_ni(cdc_running),
  .rx_enable_i(1'b1),.rx_force_realign_i(1'b0),.rx_polarity_i(polarity_i),
  .rx_raw_valid_i(raw_valid_i && recovered_running_o),.rx_raw_i(raw_i),
  .rx_record_valid_o(collected_valid),.rx_record_ready_i(recovered_accept_o),
  .rx_record_data_o(collected_data),.rx_record_k_o(collected_k),
  .rx_record_code_error_o(collected_code_error),
  .rx_record_disparity_error_o(collected_disparity_error),.rx_record_comma_o(collected_comma),
  .rx_overflow_o(collector_overflow),.rx_boundary_valid_o(boundary_valid_o),.rx_rd_o(rd_o),
  .tx_clk_i(recovered_clk_i),.tx_rst_ni(por_ni),.tx_enable_i(1'b0),.tx_flush_i(1'b1),
  .tx_record_valid_i(1'b0),.tx_record_ready_o(),
  .tx_record_data_i(128'b0),.tx_record_k_i(16'b0),.tx_record_force_negative_rd_i(1'b0),
  .tx_record_error_o(),.tx_record_queued_o(),.tx_raw_o(),.tx_raw_valid_o(),
  .tx_raw_ready_i(1'b0),.tx_stream_active_i(1'b0),
  .tx_underflow_o(),.tx_rd_o(),.tx_transport_error_o()
 );
 soc_pcie_gen12_record_cdc_v1 #(.DEPTH(FIFO_DEPTH)) u_records (
  .por_ni(por_ni),.wr_clk_i(recovered_clk_i),.rd_clk_i(common_clk_i),
  .wr_reset_i(recovered_reset_i),.rd_reset_i(common_reset_i),
  .wr_valid_i(collected_valid),.wr_loss_i(epoch_loss),
  .wr_data_i(collected_data),.wr_k_i(collected_k),.wr_code_error_i(collected_code_error),
  .wr_disparity_error_i(collected_disparity_error),.wr_comma_i(collected_comma),
  .wr_running_o(cdc_running),.wr_accept_o(recovered_accept_o),
  .wr_fault_o(recovered_fault_o),.wr_overflow_o(recovered_overflow_o),
  .rd_running_o(common_running_o),.rd_fault_o(common_fault_o),
  .rd_valid_o(record_valid_o),.rd_ready_i(record_ready_i),
  .rd_data_o(record_data_o),.rd_k_o(record_k_o),.rd_code_error_o(record_code_error_o),
  .rd_disparity_error_o(record_disparity_error_o),.rd_comma_o(record_comma_o)
 );
endmodule
`default_nettype wire
