// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Opaque complete 16-symbol candidate transport. Fields are evidence, not TS acceptance.
// The frozen Gen3 container transports 194 payload bits with fixed legal code 4;
// two padding bits and its three protocol metadata bits are unused constants.
// Neither wrapper implements Gen3 block semantics, clock-loss detection or LTSSM.
module soc_pcie_gen12_record_cdc_v1 #(parameter DEPTH=32) (
 input wire por_ni,wr_clk_i,rd_clk_i,wr_reset_i,rd_reset_i,
 input wire wr_valid_i,wr_loss_i,
 input wire [127:0] wr_data_i,
 input wire [15:0] wr_k_i,wr_code_error_i,wr_disparity_error_i,wr_comma_i,
 output wire wr_running_o,wr_accept_o,wr_fault_o,wr_overflow_o,
 output wire rd_running_o,rd_fault_o,rd_valid_o,
 input wire rd_ready_i,
 output wire [127:0] rd_data_o,
 output wire [15:0] rd_k_o,rd_code_error_o,rd_disparity_error_o,rd_comma_o
);
 wire [193:0] container_out;
 wire [191:0] record_out=rd_valid_o ? container_out[191:0] : 192'b0;
 assign {rd_comma_o,rd_disparity_error_o,rd_code_error_o,rd_k_o,rd_data_o}=record_out;
 soc_pcie_gen3_block_cdc_v1 #(.DEPTH(DEPTH)) u_transport (
  .por_ni(por_ni),.wr_clk_i(wr_clk_i),.rd_clk_i(rd_clk_i),
  .wr_reset_i(wr_reset_i),.rd_reset_i(rd_reset_i),
  .wr_valid_i(wr_valid_i),.wr_loss_i(wr_loss_i),
  .wr_block_i({2'b0,wr_comma_i,wr_disparity_error_i,wr_code_error_i,wr_k_i,wr_data_i}),
  .wr_length_code_i(3'd4),.wr_skp_i(1'b0),.wr_eieos_i(1'b0),.wr_realign_i(1'b0),
  .wr_running_o(wr_running_o),.wr_accept_o(wr_accept_o),
  .wr_fault_o(wr_fault_o),.wr_overflow_o(wr_overflow_o),
  .rd_running_o(rd_running_o),.rd_fault_o(rd_fault_o),
  .rd_valid_o(rd_valid_o),.rd_ready_i(rd_ready_i),
  .rd_block_o(container_out),.rd_length_code_o(),
  .rd_skp_o(),.rd_eieos_o(),.rd_realign_o()
 );
endmodule
`default_nettype wire
