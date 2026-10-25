// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
// Public-port lockstep observer: no assumptions on input validity.
module soc_pcie_gen3_dllp_consumer_compare_v3(
 input wire clk_i,rst_ni,flush_i,input wire [15:0] epoch_i,
 input wire body_valid_i,output wire body_ready_o,
 input wire [127:0] body_data_i,input wire [15:0] body_keep_i,body_sop_i,body_eop_i,body_dllp_i,
 input wire [47:0] body_sequence_i,input wire [23:0] body_owner_i,
 input wire [3:0] descriptor_valid_i,output wire descriptor_ready_o,
 input wire [23:0] descriptor_owner_i,input wire [47:0] descriptor_sequence_i,
 input wire [51:0] descriptor_bytes_i,
 input wire [3:0] descriptor_good_i,descriptor_nullified_i,descriptor_crc_bad_i,descriptor_dllp_i,
 output wire tlp_valid_o,input wire tlp_ready_i,
 output wire [127:0] tlp_data_o,output wire [15:0] tlp_keep_o,tlp_sop_o,tlp_eop_o,
 output wire [47:0] tlp_sequence_o,output wire [23:0] tlp_owner_o,
 output wire [3:0] event_valid_o,input wire event_ready_i,
 output wire [23:0] event_owner_o,output wire [47:0] event_sequence_o,
 output wire [51:0] event_bytes_o,output wire [15:0] event_kind_o,
 output wire [127:0] event_raw_dllp_o,output wire [47:0] event_ack_sequence_o,
 output wire [7:0] event_fc_phase_o,event_fc_class_o,
 output wire [31:0] event_fc_header_o,output wire [47:0] event_fc_data_o,
 output wire [15:0] epoch_o,output wire halted_o
);
wire  old_body_ready_o;
wire  old_descriptor_ready_o;
wire  old_tlp_valid_o;
wire [127:0] old_tlp_data_o;
wire [15:0] old_tlp_keep_o;
wire [15:0] old_tlp_sop_o;
wire [15:0] old_tlp_eop_o;
wire [47:0] old_tlp_sequence_o;
wire [23:0] old_tlp_owner_o;
wire [3:0] old_event_valid_o;
wire [23:0] old_event_owner_o;
wire [47:0] old_event_sequence_o;
wire [51:0] old_event_bytes_o;
wire [15:0] old_event_kind_o;
wire [127:0] old_event_raw_dllp_o;
wire [47:0] old_event_ack_sequence_o;
wire [7:0] old_event_fc_phase_o;
wire [7:0] old_event_fc_class_o;
wire [31:0] old_event_fc_header_o;
wire [47:0] old_event_fc_data_o;
wire [15:0] old_epoch_o;
wire  old_halted_o;
soc_pcie_gen3_dllp_consumer_v1 reference(.clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),.epoch_i(epoch_i),.body_valid_i(body_valid_i),.body_ready_o(old_body_ready_o),.body_data_i(body_data_i),.body_keep_i(body_keep_i),.body_sop_i(body_sop_i),.body_eop_i(body_eop_i),.body_dllp_i(body_dllp_i),.body_sequence_i(body_sequence_i),.body_owner_i(body_owner_i),.descriptor_valid_i(descriptor_valid_i),.descriptor_ready_o(old_descriptor_ready_o),.descriptor_owner_i(descriptor_owner_i),.descriptor_sequence_i(descriptor_sequence_i),.descriptor_bytes_i(descriptor_bytes_i),.descriptor_good_i(descriptor_good_i),.descriptor_nullified_i(descriptor_nullified_i),.descriptor_crc_bad_i(descriptor_crc_bad_i),.descriptor_dllp_i(descriptor_dllp_i),.tlp_valid_o(old_tlp_valid_o),.tlp_ready_i(tlp_ready_i),.tlp_data_o(old_tlp_data_o),.tlp_keep_o(old_tlp_keep_o),.tlp_sop_o(old_tlp_sop_o),.tlp_eop_o(old_tlp_eop_o),.tlp_sequence_o(old_tlp_sequence_o),.tlp_owner_o(old_tlp_owner_o),.event_valid_o(old_event_valid_o),.event_ready_i(event_ready_i),.event_owner_o(old_event_owner_o),.event_sequence_o(old_event_sequence_o),.event_bytes_o(old_event_bytes_o),.event_kind_o(old_event_kind_o),.event_raw_dllp_o(old_event_raw_dllp_o),.event_ack_sequence_o(old_event_ack_sequence_o),.event_fc_phase_o(old_event_fc_phase_o),.event_fc_class_o(old_event_fc_class_o),.event_fc_header_o(old_event_fc_header_o),.event_fc_data_o(old_event_fc_data_o),.epoch_o(old_epoch_o),.halted_o(old_halted_o));
wire  second_body_ready_o;
wire  second_descriptor_ready_o;
wire  second_tlp_valid_o;
wire [127:0] second_tlp_data_o;
wire [15:0] second_tlp_keep_o;
wire [15:0] second_tlp_sop_o;
wire [15:0] second_tlp_eop_o;
wire [47:0] second_tlp_sequence_o;
wire [23:0] second_tlp_owner_o;
wire [3:0] second_event_valid_o;
wire [23:0] second_event_owner_o;
wire [47:0] second_event_sequence_o;
wire [51:0] second_event_bytes_o;
wire [15:0] second_event_kind_o;
wire [127:0] second_event_raw_dllp_o;
wire [47:0] second_event_ack_sequence_o;
wire [7:0] second_event_fc_phase_o;
wire [7:0] second_event_fc_class_o;
wire [31:0] second_event_fc_header_o;
wire [47:0] second_event_fc_data_o;
wire [15:0] second_epoch_o;
wire  second_halted_o;
soc_pcie_gen3_dllp_consumer_v2 second_reference(.clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),.epoch_i(epoch_i),.body_valid_i(body_valid_i),.body_ready_o(second_body_ready_o),.body_data_i(body_data_i),.body_keep_i(body_keep_i),.body_sop_i(body_sop_i),.body_eop_i(body_eop_i),.body_dllp_i(body_dllp_i),.body_sequence_i(body_sequence_i),.body_owner_i(body_owner_i),.descriptor_valid_i(descriptor_valid_i),.descriptor_ready_o(second_descriptor_ready_o),.descriptor_owner_i(descriptor_owner_i),.descriptor_sequence_i(descriptor_sequence_i),.descriptor_bytes_i(descriptor_bytes_i),.descriptor_good_i(descriptor_good_i),.descriptor_nullified_i(descriptor_nullified_i),.descriptor_crc_bad_i(descriptor_crc_bad_i),.descriptor_dllp_i(descriptor_dllp_i),.tlp_valid_o(second_tlp_valid_o),.tlp_ready_i(tlp_ready_i),.tlp_data_o(second_tlp_data_o),.tlp_keep_o(second_tlp_keep_o),.tlp_sop_o(second_tlp_sop_o),.tlp_eop_o(second_tlp_eop_o),.tlp_sequence_o(second_tlp_sequence_o),.tlp_owner_o(second_tlp_owner_o),.event_valid_o(second_event_valid_o),.event_ready_i(event_ready_i),.event_owner_o(second_event_owner_o),.event_sequence_o(second_event_sequence_o),.event_bytes_o(second_event_bytes_o),.event_kind_o(second_event_kind_o),.event_raw_dllp_o(second_event_raw_dllp_o),.event_ack_sequence_o(second_event_ack_sequence_o),.event_fc_phase_o(second_event_fc_phase_o),.event_fc_class_o(second_event_fc_class_o),.event_fc_header_o(second_event_fc_header_o),.event_fc_data_o(second_event_fc_data_o),.epoch_o(second_epoch_o),.halted_o(second_halted_o));
soc_pcie_gen3_dllp_consumer_v3 candidate(.clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),.epoch_i(epoch_i),.body_valid_i(body_valid_i),.body_ready_o(body_ready_o),.body_data_i(body_data_i),.body_keep_i(body_keep_i),.body_sop_i(body_sop_i),.body_eop_i(body_eop_i),.body_dllp_i(body_dllp_i),.body_sequence_i(body_sequence_i),.body_owner_i(body_owner_i),.descriptor_valid_i(descriptor_valid_i),.descriptor_ready_o(descriptor_ready_o),.descriptor_owner_i(descriptor_owner_i),.descriptor_sequence_i(descriptor_sequence_i),.descriptor_bytes_i(descriptor_bytes_i),.descriptor_good_i(descriptor_good_i),.descriptor_nullified_i(descriptor_nullified_i),.descriptor_crc_bad_i(descriptor_crc_bad_i),.descriptor_dllp_i(descriptor_dllp_i),.tlp_valid_o(tlp_valid_o),.tlp_ready_i(tlp_ready_i),.tlp_data_o(tlp_data_o),.tlp_keep_o(tlp_keep_o),.tlp_sop_o(tlp_sop_o),.tlp_eop_o(tlp_eop_o),.tlp_sequence_o(tlp_sequence_o),.tlp_owner_o(tlp_owner_o),.event_valid_o(event_valid_o),.event_ready_i(event_ready_i),.event_owner_o(event_owner_o),.event_sequence_o(event_sequence_o),.event_bytes_o(event_bytes_o),.event_kind_o(event_kind_o),.event_raw_dllp_o(event_raw_dllp_o),.event_ack_sequence_o(event_ack_sequence_o),.event_fc_phase_o(event_fc_phase_o),.event_fc_class_o(event_fc_class_o),.event_fc_header_o(event_fc_header_o),.event_fc_data_o(event_fc_data_o),.epoch_o(epoch_o),.halted_o(halted_o));
always @(posedge clk_i or negedge clk_i) begin
  #0.001;
  if(rst_ni) begin
    if(body_ready_o !== old_body_ready_o) $fatal(1,"Public v1/v2/v3 mismatch: body_ready_o");
    if(descriptor_ready_o !== old_descriptor_ready_o) $fatal(1,"Public v1/v2/v3 mismatch: descriptor_ready_o");
    if(tlp_valid_o !== old_tlp_valid_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_valid_o");
    if(tlp_data_o !== old_tlp_data_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_data_o");
    if(tlp_keep_o !== old_tlp_keep_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_keep_o");
    if(tlp_sop_o !== old_tlp_sop_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_sop_o");
    if(tlp_eop_o !== old_tlp_eop_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_eop_o");
    if(tlp_sequence_o !== old_tlp_sequence_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_sequence_o");
    if(tlp_owner_o !== old_tlp_owner_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_owner_o");
    if(event_valid_o !== old_event_valid_o) $fatal(1,"Public v1/v2/v3 mismatch: event_valid_o");
    if(event_owner_o !== old_event_owner_o) $fatal(1,"Public v1/v2/v3 mismatch: event_owner_o");
    if(event_sequence_o !== old_event_sequence_o) $fatal(1,"Public v1/v2/v3 mismatch: event_sequence_o");
    if(event_bytes_o !== old_event_bytes_o) $fatal(1,"Public v1/v2/v3 mismatch: event_bytes_o");
    if(event_kind_o !== old_event_kind_o) $fatal(1,"Public v1/v2/v3 mismatch: event_kind_o");
    if(event_raw_dllp_o !== old_event_raw_dllp_o) $fatal(1,"Public v1/v2/v3 mismatch: event_raw_dllp_o");
    if(event_ack_sequence_o !== old_event_ack_sequence_o) $fatal(1,"Public v1/v2/v3 mismatch: event_ack_sequence_o");
    if(event_fc_phase_o !== old_event_fc_phase_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_phase_o");
    if(event_fc_class_o !== old_event_fc_class_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_class_o");
    if(event_fc_header_o !== old_event_fc_header_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_header_o");
    if(event_fc_data_o !== old_event_fc_data_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_data_o");
    if(epoch_o !== old_epoch_o) $fatal(1,"Public v1/v2/v3 mismatch: epoch_o");
    if(halted_o !== old_halted_o) $fatal(1,"Public v1/v2/v3 mismatch: halted_o");
    if(body_ready_o !== second_body_ready_o) $fatal(1,"Public v1/v2/v3 mismatch: body_ready_o");
    if(descriptor_ready_o !== second_descriptor_ready_o) $fatal(1,"Public v1/v2/v3 mismatch: descriptor_ready_o");
    if(tlp_valid_o !== second_tlp_valid_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_valid_o");
    if(tlp_data_o !== second_tlp_data_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_data_o");
    if(tlp_keep_o !== second_tlp_keep_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_keep_o");
    if(tlp_sop_o !== second_tlp_sop_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_sop_o");
    if(tlp_eop_o !== second_tlp_eop_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_eop_o");
    if(tlp_sequence_o !== second_tlp_sequence_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_sequence_o");
    if(tlp_owner_o !== second_tlp_owner_o) $fatal(1,"Public v1/v2/v3 mismatch: tlp_owner_o");
    if(event_valid_o !== second_event_valid_o) $fatal(1,"Public v1/v2/v3 mismatch: event_valid_o");
    if(event_owner_o !== second_event_owner_o) $fatal(1,"Public v1/v2/v3 mismatch: event_owner_o");
    if(event_sequence_o !== second_event_sequence_o) $fatal(1,"Public v1/v2/v3 mismatch: event_sequence_o");
    if(event_bytes_o !== second_event_bytes_o) $fatal(1,"Public v1/v2/v3 mismatch: event_bytes_o");
    if(event_kind_o !== second_event_kind_o) $fatal(1,"Public v1/v2/v3 mismatch: event_kind_o");
    if(event_raw_dllp_o !== second_event_raw_dllp_o) $fatal(1,"Public v1/v2/v3 mismatch: event_raw_dllp_o");
    if(event_ack_sequence_o !== second_event_ack_sequence_o) $fatal(1,"Public v1/v2/v3 mismatch: event_ack_sequence_o");
    if(event_fc_phase_o !== second_event_fc_phase_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_phase_o");
    if(event_fc_class_o !== second_event_fc_class_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_class_o");
    if(event_fc_header_o !== second_event_fc_header_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_header_o");
    if(event_fc_data_o !== second_event_fc_data_o) $fatal(1,"Public v1/v2/v3 mismatch: event_fc_data_o");
    if(epoch_o !== second_epoch_o) $fatal(1,"Public v1/v2/v3 mismatch: epoch_o");
    if(halted_o !== second_halted_o) $fatal(1,"Public v1/v2/v3 mismatch: halted_o");
  end
end
endmodule
