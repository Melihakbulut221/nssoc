// SPDX-License-Identifier: Apache-2.0
// Verification only: original and shared-front chains receive identical public inputs.
// The functional oracle reads public candidate outputs. Comparisons below cover ALL
// public v4/v5 and events_v2/v3 outputs; no private state is a functional oracle.
`timescale 1ns/1ps
`default_nettype none
module pcie_shared_front_events_compare #(parameter FIFO_DEPTH=32, MAX_SKEW_CYCLES=64, MAX_ENCODED_BYTES=150) (
  input wire  por_ni,
  input wire  reset_i,
  input wire  abort_i,
  input wire [3:0] recovered_clk_i,
  input wire  common_clk_i,
  input wire [3:0] raw_valid_i,
  input wire [127:0] raw_i,
  input wire [3:0] align_control_i,
  input wire [3:0] force_realign_i,
  input wire  arm_i,
  output wire [3:0] lane_running_o,
  output wire [3:0] lane_aligned_o,
  output wire [3:0] lane_locked_o,
  output wire [3:0] lane_fault_o,
  output wire  lanes_ready_o,
  output wire  stream_start_o,
  output wire  stream_stop_o,
  output wire  stop_eieos_o,
  output wire  stream_end_o,
  output wire  active_o,
  output wire  halted_o,
  output wire  fault_o,
  output wire  overflow_o,
  output wire  framing_error_o,
  output wire [3:0] lane_error_o,
  output wire [3:0] lfsr_mismatch_o,
  output wire  skp_valid_o,
  output wire [775:0] skp_block_o,
  output wire [11:0] skp_length_code_o,
  output wire  tlp_valid_o,
  input wire  tlp_ready_i,
  output wire [127:0] tlp_data_o,
  output wire [15:0] tlp_keep_o,
  output wire [15:0] tlp_sop_o,
  output wire [15:0] tlp_eop_o,
  output wire [47:0] tlp_sequence_o,
  output wire [23:0] tlp_owner_o,
  output wire [3:0] event_valid_o,
  input wire  event_ready_i,
  output wire [3:0] event_packet_dllp_o,
  output wire [23:0] event_owner_o,
  output wire [47:0] event_sequence_o,
  output wire [51:0] event_bytes_o,
  output wire [15:0] event_kind_o,
  output wire [127:0] event_raw_dllp_o,
  output wire [47:0] event_ack_sequence_o,
  output wire [7:0] event_fc_phase_o,
  output wire [7:0] event_fc_class_o,
  output wire [31:0] event_fc_header_o,
  output wire [47:0] event_fc_data_o,
  output wire [15:0] epoch_o,
  output wire equivalent_o, normal_equivalent_o
);
  wire [3:0] reference_lane_running_o;
  wire [3:0] reference_lane_aligned_o;
  wire [3:0] reference_lane_locked_o;
  wire [3:0] reference_lane_fault_o;
  wire  reference_lanes_ready_o;
  wire  reference_stream_start_o;
  wire  reference_stream_stop_o;
  wire  reference_stop_eieos_o;
  wire  reference_stream_end_o;
  wire  reference_active_o;
  wire  reference_halted_o;
  wire  reference_fault_o;
  wire  reference_overflow_o;
  wire  reference_framing_error_o;
  wire [3:0] reference_lane_error_o;
  wire [3:0] reference_lfsr_mismatch_o;
  wire  reference_skp_valid_o;
  wire [775:0] reference_skp_block_o;
  wire [11:0] reference_skp_length_code_o;
  wire  reference_tlp_valid_o;
  wire [127:0] reference_tlp_data_o;
  wire [15:0] reference_tlp_keep_o;
  wire [15:0] reference_tlp_sop_o;
  wire [15:0] reference_tlp_eop_o;
  wire [47:0] reference_tlp_sequence_o;
  wire [23:0] reference_tlp_owner_o;
  wire [3:0] reference_event_valid_o;
  wire [3:0] reference_event_packet_dllp_o;
  wire [23:0] reference_event_owner_o;
  wire [47:0] reference_event_sequence_o;
  wire [51:0] reference_event_bytes_o;
  wire [15:0] reference_event_kind_o;
  wire [127:0] reference_event_raw_dllp_o;
  wire [47:0] reference_event_ack_sequence_o;
  wire [7:0] reference_event_fc_phase_o;
  wire [7:0] reference_event_fc_class_o;
  wire [31:0] reference_event_fc_header_o;
  wire [47:0] reference_event_fc_data_o;
  wire [15:0] reference_epoch_o;
  soc_pcie_gen3_recovered_events_v2 #(.FIFO_DEPTH(FIFO_DEPTH),.MAX_SKEW_CYCLES(MAX_SKEW_CYCLES),.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) reference (
    .por_ni(por_ni),
    .reset_i(reset_i),
    .abort_i(abort_i),
    .recovered_clk_i(recovered_clk_i),
    .common_clk_i(common_clk_i),
    .raw_valid_i(raw_valid_i),
    .raw_i(raw_i),
    .align_control_i(align_control_i),
    .force_realign_i(force_realign_i),
    .arm_i(arm_i),
    .lane_running_o(reference_lane_running_o),
    .lane_aligned_o(reference_lane_aligned_o),
    .lane_locked_o(reference_lane_locked_o),
    .lane_fault_o(reference_lane_fault_o),
    .lanes_ready_o(reference_lanes_ready_o),
    .stream_start_o(reference_stream_start_o),
    .stream_stop_o(reference_stream_stop_o),
    .stop_eieos_o(reference_stop_eieos_o),
    .stream_end_o(reference_stream_end_o),
    .active_o(reference_active_o),
    .halted_o(reference_halted_o),
    .fault_o(reference_fault_o),
    .overflow_o(reference_overflow_o),
    .framing_error_o(reference_framing_error_o),
    .lane_error_o(reference_lane_error_o),
    .lfsr_mismatch_o(reference_lfsr_mismatch_o),
    .skp_valid_o(reference_skp_valid_o),
    .skp_block_o(reference_skp_block_o),
    .skp_length_code_o(reference_skp_length_code_o),
    .tlp_valid_o(reference_tlp_valid_o),
    .tlp_ready_i(tlp_ready_i),
    .tlp_data_o(reference_tlp_data_o),
    .tlp_keep_o(reference_tlp_keep_o),
    .tlp_sop_o(reference_tlp_sop_o),
    .tlp_eop_o(reference_tlp_eop_o),
    .tlp_sequence_o(reference_tlp_sequence_o),
    .tlp_owner_o(reference_tlp_owner_o),
    .event_valid_o(reference_event_valid_o),
    .event_ready_i(event_ready_i),
    .event_packet_dllp_o(reference_event_packet_dllp_o),
    .event_owner_o(reference_event_owner_o),
    .event_sequence_o(reference_event_sequence_o),
    .event_bytes_o(reference_event_bytes_o),
    .event_kind_o(reference_event_kind_o),
    .event_raw_dllp_o(reference_event_raw_dllp_o),
    .event_ack_sequence_o(reference_event_ack_sequence_o),
    .event_fc_phase_o(reference_event_fc_phase_o),
    .event_fc_class_o(reference_event_fc_class_o),
    .event_fc_header_o(reference_event_fc_header_o),
    .event_fc_data_o(reference_event_fc_data_o),
    .epoch_o(reference_epoch_o)
  );
  soc_pcie_gen3_recovered_events_v3 #(.FIFO_DEPTH(FIFO_DEPTH),.MAX_SKEW_CYCLES(MAX_SKEW_CYCLES),.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) candidate (
    .por_ni(por_ni),
    .reset_i(reset_i),
    .abort_i(abort_i),
    .recovered_clk_i(recovered_clk_i),
    .common_clk_i(common_clk_i),
    .raw_valid_i(raw_valid_i),
    .raw_i(raw_i),
    .align_control_i(align_control_i),
    .force_realign_i(force_realign_i),
    .arm_i(arm_i),
    .lane_running_o(lane_running_o),
    .lane_aligned_o(lane_aligned_o),
    .lane_locked_o(lane_locked_o),
    .lane_fault_o(lane_fault_o),
    .lanes_ready_o(lanes_ready_o),
    .stream_start_o(stream_start_o),
    .stream_stop_o(stream_stop_o),
    .stop_eieos_o(stop_eieos_o),
    .stream_end_o(stream_end_o),
    .active_o(active_o),
    .halted_o(halted_o),
    .fault_o(fault_o),
    .overflow_o(overflow_o),
    .framing_error_o(framing_error_o),
    .lane_error_o(lane_error_o),
    .lfsr_mismatch_o(lfsr_mismatch_o),
    .skp_valid_o(skp_valid_o),
    .skp_block_o(skp_block_o),
    .skp_length_code_o(skp_length_code_o),
    .tlp_valid_o(tlp_valid_o),
    .tlp_ready_i(tlp_ready_i),
    .tlp_data_o(tlp_data_o),
    .tlp_keep_o(tlp_keep_o),
    .tlp_sop_o(tlp_sop_o),
    .tlp_eop_o(tlp_eop_o),
    .tlp_sequence_o(tlp_sequence_o),
    .tlp_owner_o(tlp_owner_o),
    .event_valid_o(event_valid_o),
    .event_ready_i(event_ready_i),
    .event_packet_dllp_o(event_packet_dllp_o),
    .event_owner_o(event_owner_o),
    .event_sequence_o(event_sequence_o),
    .event_bytes_o(event_bytes_o),
    .event_kind_o(event_kind_o),
    .event_raw_dllp_o(event_raw_dllp_o),
    .event_ack_sequence_o(event_ack_sequence_o),
    .event_fc_phase_o(event_fc_phase_o),
    .event_fc_class_o(event_fc_class_o),
    .event_fc_header_o(event_fc_header_o),
    .event_fc_data_o(event_fc_data_o),
    .epoch_o(epoch_o)
  );
  assign equivalent_o = (reference_lane_running_o === lane_running_o) &&
    (reference_lane_aligned_o === lane_aligned_o) &&
    (reference_lane_locked_o === lane_locked_o) &&
    (reference_lane_fault_o === lane_fault_o) &&
    (reference_lanes_ready_o === lanes_ready_o) &&
    (reference_stream_start_o === stream_start_o) &&
    (reference_stream_stop_o === stream_stop_o) &&
    (reference_stop_eieos_o === stop_eieos_o) &&
    (reference_stream_end_o === stream_end_o) &&
    (reference_active_o === active_o) &&
    (reference_halted_o === halted_o) &&
    (reference_fault_o === fault_o) &&
    (reference_overflow_o === overflow_o) &&
    (reference_framing_error_o === framing_error_o) &&
    (reference_lane_error_o === lane_error_o) &&
    (reference_lfsr_mismatch_o === lfsr_mismatch_o) &&
    (reference_skp_valid_o === skp_valid_o) &&
    (reference_skp_block_o === skp_block_o) &&
    (reference_skp_length_code_o === skp_length_code_o) &&
    (reference_tlp_valid_o === tlp_valid_o) &&
    (reference_tlp_data_o === tlp_data_o) &&
    (reference_tlp_keep_o === tlp_keep_o) &&
    (reference_tlp_sop_o === tlp_sop_o) &&
    (reference_tlp_eop_o === tlp_eop_o) &&
    (reference_tlp_sequence_o === tlp_sequence_o) &&
    (reference_tlp_owner_o === tlp_owner_o) &&
    (reference_event_valid_o === event_valid_o) &&
    (reference_event_packet_dllp_o === event_packet_dllp_o) &&
    (reference_event_owner_o === event_owner_o) &&
    (reference_event_sequence_o === event_sequence_o) &&
    (reference_event_bytes_o === event_bytes_o) &&
    (reference_event_kind_o === event_kind_o) &&
    (reference_event_raw_dllp_o === event_raw_dllp_o) &&
    (reference_event_ack_sequence_o === event_ack_sequence_o) &&
    (reference_event_fc_phase_o === event_fc_phase_o) &&
    (reference_event_fc_class_o === event_fc_class_o) &&
    (reference_event_fc_header_o === event_fc_header_o) &&
    (reference_event_fc_data_o === event_fc_data_o) &&
    (reference_epoch_o === epoch_o);
  assign normal_equivalent_o = (reference.owned.front.stream_stop_o === candidate.owned.front.stream_stop_o) &&
    (reference.owned.front.stop_eieos_o === candidate.owned.front.stop_eieos_o) &&
    (reference.owned.front.lane_running_o === candidate.owned.front.lane_running_o) &&
    (reference.owned.front.lane_aligned_o === candidate.owned.front.lane_aligned_o) &&
    (reference.owned.front.lane_locked_o === candidate.owned.front.lane_locked_o) &&
    (reference.owned.front.lane_fault_o === candidate.owned.front.lane_fault_o) &&
    (reference.owned.front.lanes_ready_o === candidate.owned.front.lanes_ready_o) &&
    (reference.owned.front.stream_start_o === candidate.owned.front.stream_start_o) &&
    (reference.owned.front.active_o === candidate.owned.front.active_o) &&
    (reference.owned.front.fault_o === candidate.owned.front.fault_o) &&
    (reference.owned.front.data_valid_o === candidate.owned.front.data_valid_o) &&
    (reference.owned.front.data_o === candidate.owned.front.data_o) &&
    (reference.owned.front.lane_error_o === candidate.owned.front.lane_error_o) &&
    (reference.owned.front.lfsr_mismatch_o === candidate.owned.front.lfsr_mismatch_o) &&
    (reference.owned.front.skp_valid_o === candidate.owned.front.skp_valid_o) &&
    (reference.owned.front.skp_block_o === candidate.owned.front.skp_block_o) &&
    (reference.owned.front.skp_length_code_o === candidate.owned.front.skp_length_code_o);
  always @(negedge common_clk_i) begin
    #0.001;
    if(por_ni && !reset_i && (!equivalent_o || !normal_equivalent_o))
      $fatal(1,"SHARED_FRONT_PUBLIC_PIN_EQUIVALENCE common-domain outputs differ");
  end
  always @(recovered_clk_i) begin
    #0.001;
    if(por_ni && !reset_i && (!equivalent_o || !normal_equivalent_o))
      $fatal(1,"SHARED_FRONT_PUBLIC_PIN_EQUIVALENCE recovered-domain outputs differ");
  end
endmodule
`default_nettype wire
