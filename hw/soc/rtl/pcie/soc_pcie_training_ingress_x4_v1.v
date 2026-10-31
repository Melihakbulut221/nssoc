// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Candidate typed training ingress, not a semantic TS/EQ owner or LTSSM.
// One full Gen1/2 collector+CDC per lane, one frozen Gen3 shared front. At most
// one encoding is live. Every command aborts the previous epoch and flushes
// both record transports before a new all-lane applied-command barrier.
// Reset/loss inputs are clean assertions supplied by the PMA/reset integrator;
// this module does not detect an unreported mid-epoch stopped recovered clock.
// Downstream consumers must discard retained state when epoch_active_o falls.
module soc_pcie_training_ingress_x4_v1 #(parameter EPOCH_W=16,FIFO_DEPTH=32) (
 input wire por_ni,common_clk_i,input wire [3:0] recovered_clk_i,
 input wire reset_i,input wire [3:0] lane_reset_i,lane_loss_i,
 input wire command_valid_i,output wire command_ready_o,
 input wire [1:0] command_encoding_i,input wire [3:0] command_polarity_i,command_align_i,
 output wire command_done_o,command_success_o,
 output wire pma_request_o,input wire pma_ack_i,
 input wire [EPOCH_W-1:0] pma_ack_epoch_i,input wire [1:0] pma_ack_encoding_i,
 output wire [EPOCH_W-1:0] epoch_o,output wire [1:0] encoding_o,
 output wire epoch_active_o,epoch_fault_o,front_reset_o,
 output wire [3:0] lane_request_o,lane_ack_o,lane_running_o,common_running_o,
 output wire [4*EPOCH_W-1:0] lane_epoch_o,output wire [7:0] lane_encoding_o,
 output wire [3:0] lane_polarity_o,lane_align_o,
 input wire [3:0] raw_valid_i,input wire [127:0] raw_i,
 output wire [3:0] gen12_valid_o,input wire [3:0] gen12_ready_i,
 output wire [511:0] gen12_data_o,
 output wire [63:0] gen12_k_o,gen12_code_error_o,gen12_disparity_error_o,gen12_comma_o,
 output wire [3:0] gen12_boundary_o,gen12_rd_o,
 output wire [3:0] gen3_valid_o,input wire [3:0] gen3_ready_i,
 output wire [775:0] gen3_block_o,output wire [11:0] gen3_length_code_o,
 output wire [3:0] gen3_skp_o,gen3_eieos_o,gen3_realign_o,
 output wire [3:0] gen3_aligned_o,gen3_locked_o
);
 wire selected_gen3=(encoding_o==2'b10);
 wire [3:0] g12_running,g12_common,g12_fault,g12_common_fault,g12_valid;
 wire [3:0] g3_running,g3_common,g3_fault,g3_common_fault,g3_valid;
 wire fronts_ready=&common_running_o;
 wire front_fault=selected_gen3 ? (|(g3_fault|g3_common_fault)) :
                                               (|(g12_fault|g12_common_fault));
 wire epoch_abort=(|lane_reset_i) || (|lane_loss_i) || front_fault;
 soc_pcie_training_epoch_control_v1 #(.EPOCH_W(EPOCH_W)) command_owner (
  .por_ni(por_ni),.common_clk_i(common_clk_i),.recovered_clk_i(recovered_clk_i),
  .reset_i(reset_i),.epoch_abort_i(epoch_abort),
  .command_valid_i(command_valid_i),.command_ready_o(command_ready_o),
  .command_encoding_i(command_encoding_i),.command_polarity_i(command_polarity_i),
  .command_align_i(command_align_i),.command_done_o(command_done_o),.command_success_o(command_success_o),
  .epoch_o(epoch_o),.encoding_o(encoding_o),.polarity_o(),.align_o(),
  .pma_request_o(pma_request_o),.pma_ack_i(pma_ack_i),
  .pma_ack_epoch_i(pma_ack_epoch_i),.pma_ack_encoding_i(pma_ack_encoding_i),
  .fronts_ready_i(fronts_ready),.front_reset_o(front_reset_o),
  .epoch_active_o(epoch_active_o),.epoch_fault_o(epoch_fault_o),
  .lane_request_o(lane_request_o),.lane_ack_o(lane_ack_o),
  .lane_epoch_o(lane_epoch_o),.lane_encoding_o(lane_encoding_o),
  .lane_polarity_o(lane_polarity_o),.lane_align_o(lane_align_o)
 );
 wire reset_gen12=front_reset_o || selected_gen3;
 wire reset_gen3=front_reset_o || !selected_gen3;
 assign lane_running_o=selected_gen3 ? g3_running : g12_running;
 assign common_running_o=selected_gen3 ? g3_common : g12_common;
 // Ready and valid have the SAME all-lane epoch owner. No hidden FIFO retirement.
 assign gen12_valid_o=g12_valid & {4{epoch_active_o && !selected_gen3}};
 assign gen3_valid_o=g3_valid & {4{epoch_active_o && selected_gen3}};
 wire [127:0] gen3_raw;
 genvar lane;
 generate for(lane=0;lane<4;lane=lane+1)begin:lanes
  assign gen3_raw[lane*32+:32]=raw_i[lane*32+:32] ^ {32{lane_polarity_o[lane]}};
  soc_pcie_gen12_recovered_records_v1 #(.FIFO_DEPTH(FIFO_DEPTH)) gen12_front (
   .por_ni(por_ni),.recovered_clk_i(recovered_clk_i[lane]),.common_clk_i(common_clk_i),
   .recovered_reset_i(reset_gen12),.common_reset_i(reset_gen12),
   .raw_valid_i(raw_valid_i[lane]),.polarity_i(lane_polarity_o[lane]),.loss_i(1'b0),
   .raw_i(raw_i[lane*32+:32]),.recovered_running_o(g12_running[lane]),
   .boundary_valid_o(gen12_boundary_o[lane]),.rd_o(gen12_rd_o[lane]),
   .recovered_accept_o(),.recovered_fault_o(g12_fault[lane]),.recovered_overflow_o(),
   .common_running_o(g12_common[lane]),.common_fault_o(g12_common_fault[lane]),
   .record_valid_o(g12_valid[lane]),
   .record_ready_i(gen12_ready_i[lane] && epoch_active_o && !selected_gen3),
   .record_data_o(gen12_data_o[lane*128+:128]),.record_k_o(gen12_k_o[lane*16+:16]),
   .record_code_error_o(gen12_code_error_o[lane*16+:16]),
   .record_disparity_error_o(gen12_disparity_error_o[lane*16+:16]),
   .record_comma_o(gen12_comma_o[lane*16+:16])
  );
 end endgenerate
 soc_pcie_gen3_recovered_front_x4_v1 #(.FIFO_DEPTH(FIFO_DEPTH)) gen3_front (
  .por_ni(por_ni),.reset_i(reset_gen3),.recovered_clk_i(recovered_clk_i),
  .common_clk_i(common_clk_i),.raw_valid_i(raw_valid_i),.raw_i(gen3_raw),
  .align_control_i(lane_align_o),.force_realign_i(4'b0),
  .lane_running_o(g3_running),.lane_aligned_o(gen3_aligned_o),.lane_locked_o(gen3_locked_o),
  .lane_fault_o(g3_fault),.common_running_o(g3_common),.common_fault_o(g3_common_fault),
  .record_valid_o(g3_valid),.record_ready_i(gen3_ready_i & {4{epoch_active_o && selected_gen3}}),
  .record_block_o(gen3_block_o),.record_length_code_o(gen3_length_code_o),
  .record_skp_o(gen3_skp_o),.record_eieos_o(gen3_eieos_o),.record_realign_o(gen3_realign_o)
 );
endmodule
`default_nettype wire
