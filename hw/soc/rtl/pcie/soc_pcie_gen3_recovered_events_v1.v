// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Four recovered raw lanes through real OS/CDC/deskew, CRC quarantine and
// owner-ordered TLP/DLLP events. Ready applies to bounded output storage only:
// the serial input cannot pause. Overflow aborts the current epoch. This
// composition preserves bad/null packet events; it is not a scalar bridge.
// Complete records, fixed logical lanes and one coordinated reset/arm epoch.
// Full LTSSM, analog CDR/PMA and physical main-chip qualification are separate.
module soc_pcie_gen3_recovered_events_v1 #(
 parameter FIFO_DEPTH=32,MAX_SKEW_CYCLES=64,MAX_ENCODED_BYTES=150
)(
 input wire por_ni,reset_i,abort_i,input wire [3:0] recovered_clk_i,input wire common_clk_i,
 input wire [3:0] raw_valid_i,input wire [127:0] raw_i,
 input wire [3:0] align_control_i,force_realign_i,input wire arm_i,
 output wire [3:0] lane_running_o,lane_aligned_o,lane_locked_o,lane_fault_o,
 output wire lanes_ready_o,stream_start_o,stream_stop_o,stop_eieos_o,
 output reg stream_end_o,output wire active_o,halted_o,fault_o,overflow_o,framing_error_o,
 output wire [3:0] lane_error_o,lfsr_mismatch_o,
 output wire skp_valid_o,output wire [775:0] skp_block_o,output wire [11:0] skp_length_code_o,
 output wire tlp_valid_o,input wire tlp_ready_i,
 output wire [127:0] tlp_data_o,output wire [15:0] tlp_keep_o,tlp_sop_o,tlp_eop_o,
 output wire [47:0] tlp_sequence_o,output wire [23:0] tlp_owner_o,
 output wire [3:0] event_valid_o,input wire event_ready_i,
 output wire [23:0] event_owner_o,output wire [47:0] event_sequence_o,
 output wire [51:0] event_bytes_o,output wire [15:0] event_kind_o,
 output wire [127:0] event_raw_dllp_o,output wire [47:0] event_ack_sequence_o,
 output wire [7:0] event_fc_phase_o,event_fc_class_o,
 output wire [31:0] event_fc_header_o,output wire [47:0] event_fc_data_o,
 output wire [15:0] epoch_o
);
 wire bv,br,dr,upstream_halted,consumer_halted,upstream_fault,upstream_end,upstream_active;
 wire [127:0] bd;wire [15:0] bk,bs,be,bknd,ep;
 wire [47:0] bseq,dseq;wire [23:0] bo,doid;wire [51:0] dz;
 wire [3:0] dv,dg,dn,db,dk;
 reg consumer_error;
 reg draining;
 reg [6:0] pending_events;
 wire [2:0] accepted_descriptors=dr?({2'b0,dv[0]}+{2'b0,dv[1]}+{2'b0,dv[2]}+{2'b0,dv[3]}):3'd0;
 wire [2:0] accepted_events=event_ready_i?({2'b0,event_valid_o[0]}+{2'b0,event_valid_o[1]}+{2'b0,event_valid_o[2]}+{2'b0,event_valid_o[3]}):3'd0;
 wire [7:0] pending_next={1'b0,pending_events}+accepted_descriptors-accepted_events;
 assign halted_o=upstream_halted || consumer_halted || consumer_error;
 assign fault_o=por_ni && !reset_i && (upstream_fault || consumer_halted || consumer_error);
 assign epoch_o=ep;
 assign active_o=por_ni && !reset_i && (upstream_active || upstream_end || draining);
 soc_pcie_gen3_recovered_owned_rx_v1 #(.FIFO_DEPTH(FIFO_DEPTH),.MAX_SKEW_CYCLES(MAX_SKEW_CYCLES),.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) owned(
 .por_ni(por_ni),.reset_i(reset_i),.abort_i(abort_i || consumer_halted),
 .recovered_clk_i(recovered_clk_i),.common_clk_i(common_clk_i),.raw_valid_i(raw_valid_i),.raw_i(raw_i),
 .align_control_i(align_control_i),.force_realign_i(force_realign_i),.arm_i(arm_i),
 .lane_running_o(lane_running_o),.lane_aligned_o(lane_aligned_o),.lane_locked_o(lane_locked_o),.lane_fault_o(lane_fault_o),
 .lanes_ready_o(lanes_ready_o),.stream_start_o(stream_start_o),.stream_stop_o(stream_stop_o),.stop_eieos_o(stop_eieos_o),
 .stream_end_o(upstream_end),.active_o(upstream_active),.halted_o(upstream_halted),.fault_o(upstream_fault),
 .overflow_o(overflow_o),.framing_error_o(framing_error_o),.lane_error_o(lane_error_o),.lfsr_mismatch_o(lfsr_mismatch_o),
 .skp_valid_o(skp_valid_o),.skp_block_o(skp_block_o),.skp_length_code_o(skp_length_code_o),
 .valid_o(bv),.ready_i(br),.data_o(bd),.keep_o(bk),.sop_o(bs),.eop_o(be),.dllp_o(bknd),.sequence_o(bseq),.owner_o(bo),
 .descriptor_valid_o(dv),.descriptor_ready_i(dr),.descriptor_owner_o(doid),.descriptor_sequence_o(dseq),.descriptor_bytes_o(dz),
 .descriptor_good_o(dg),.descriptor_nullified_o(dn),.descriptor_crc_bad_o(db),.descriptor_dllp_o(dk),.epoch_o(ep),
 .packet_good_o(),.packet_nullified_o(),.packet_crc_bad_o(),.packet_dllp_o(),.packet_sequence_o());
 // An explicit abort or a detected front-end epoch fault suppresses stale
 // output handshakes before the next edge. The subsequent owner epoch change
 // resets rendezvous state. Normal stream_stop alone must not flush it.
 soc_pcie_gen3_dllp_consumer_v5 consumer(
 .clk_i(common_clk_i),.rst_ni(por_ni && !reset_i),
 .flush_i(stream_start_o || abort_i || upstream_fault),.epoch_i(ep),
 .body_valid_i(bv),.body_ready_o(br),.body_data_i(bd),.body_keep_i(bk),.body_sop_i(bs),.body_eop_i(be),.body_dllp_i(bknd),.body_sequence_i(bseq),.body_owner_i(bo),
 .descriptor_valid_i(dv),.descriptor_ready_o(dr),.descriptor_owner_i(doid),.descriptor_sequence_i(dseq),.descriptor_bytes_i(dz),
 .descriptor_good_i(dg),.descriptor_nullified_i(dn),.descriptor_crc_bad_i(db),.descriptor_dllp_i(dk),
 .tlp_valid_o(tlp_valid_o),.tlp_ready_i(tlp_ready_i),.tlp_data_o(tlp_data_o),.tlp_keep_o(tlp_keep_o),.tlp_sop_o(tlp_sop_o),.tlp_eop_o(tlp_eop_o),.tlp_sequence_o(tlp_sequence_o),.tlp_owner_o(tlp_owner_o),
 .event_valid_o(event_valid_o),.event_ready_i(event_ready_i),.event_owner_o(event_owner_o),.event_sequence_o(event_sequence_o),.event_bytes_o(event_bytes_o),.event_kind_o(event_kind_o),
 .event_raw_dllp_o(event_raw_dllp_o),.event_ack_sequence_o(event_ack_sequence_o),.event_fc_phase_o(event_fc_phase_o),.event_fc_class_o(event_fc_class_o),.event_fc_header_o(event_fc_header_o),.event_fc_data_o(event_fc_data_o),
 .epoch_o(),.halted_o(consumer_halted));
 always @(posedge common_clk_i or negedge por_ni) begin
   if(!por_ni) consumer_error<=0;
   else if(reset_i) consumer_error<=0;
   else if(consumer_halted) consumer_error<=1;
 end
 // Upstream end means every body and descriptor reached the consumer, not
 // that its queued events reached the controller. Preserve the whole epoch
 // until the last accepted descriptor has an accepted ordered event.
 always @(posedge common_clk_i or negedge por_ni) begin
   if(!por_ni) begin draining<=0;pending_events<=0;stream_end_o<=0;end
   else begin
     stream_end_o<=0;
     if(reset_i || stream_start_o || abort_i || upstream_fault || consumer_halted) begin
       draining<=0;pending_events<=0;
     end else begin
       pending_events<=pending_next[6:0];
       if(upstream_end) draining<=1;
       if((draining || upstream_end) && pending_next==0) begin
         draining<=0;stream_end_o<=1;
       end
     end
   end
 end
endmodule
`default_nettype wire
