// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Fixed aligned x4 raw stream -> CRC-qualified ownership -> wide events/TLPs.
// Explicit finite stall capacity; no scalar controller or full PCS claim.
module soc_pcie_gen3_rx_events_v2 #(
 parameter integer MAX_ENCODED_BYTES=150
)(input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input wire [127:0] word_i,
 output wire overflow_o,framing_error_o,active_o,
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
 wire bv,br,dr;wire [127:0] bd;wire [15:0] bk,bs,be,bknd,ep;
 wire [47:0] bseq,dseq;wire [23:0] bo,doid;wire [51:0] dz;
 wire [3:0] dv,dg,dn,db,dk;wire upstream_halted,consumer_halted;
 reg consumer_error;
 assign halted_o=upstream_halted || consumer_halted || consumer_error;
 assign epoch_o=ep;
 soc_pcie_gen3_continuous_rx_owned_v2 #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) owned(
 .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),.stream_start_i(stream_start_i),
 .stream_abort_i(stream_abort_i || consumer_halted),.word_i(word_i),
 .valid_o(bv),.ready_i(br),.data_o(bd),.keep_o(bk),.sop_o(bs),.eop_o(be),.dllp_o(bknd),.sequence_o(bseq),.owner_o(bo),
 .descriptor_valid_o(dv),.descriptor_ready_i(dr),.descriptor_owner_o(doid),.descriptor_sequence_o(dseq),.descriptor_bytes_o(dz),
 .descriptor_good_o(dg),.descriptor_nullified_o(dn),.descriptor_crc_bad_o(db),.descriptor_dllp_o(dk),.epoch_o(ep),
 .packet_good_o(),.packet_nullified_o(),.packet_crc_bad_o(),.packet_dllp_o(),.packet_sequence_o(),
 .framing_error_o(framing_error_o),.stream_end_o(),.active_o(active_o),.halted_o(upstream_halted),.overflow_o(overflow_o));
 soc_pcie_gen3_dllp_consumer_v2 consumer(
 .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i || stream_start_i || stream_abort_i),.epoch_i(ep),
 .body_valid_i(bv),.body_ready_o(br),.body_data_i(bd),.body_keep_i(bk),.body_sop_i(bs),.body_eop_i(be),.body_dllp_i(bknd),.body_sequence_i(bseq),.body_owner_i(bo),
 .descriptor_valid_i(dv),.descriptor_ready_o(dr),.descriptor_owner_i(doid),.descriptor_sequence_i(dseq),.descriptor_bytes_i(dz),
 .descriptor_good_i(dg),.descriptor_nullified_i(dn),.descriptor_crc_bad_i(db),.descriptor_dllp_i(dk),
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
 .epoch_o(),.halted_o(consumer_halted));
 always @(posedge clk_i or negedge rst_ni) begin
 if(!rst_ni) consumer_error<=0;
 else if(flush_i || stream_start_i) consumer_error<=0;
 else if(consumer_halted) consumer_error<=1;
 end
endmodule
`default_nettype wire
