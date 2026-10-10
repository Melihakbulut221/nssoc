// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Four actual recovered lanes through record CDC, OS-aware LFSR, strict SDS/OS
// cohorts and token-context CRC-qualified packet ownership. EDS+SKP resumes the same stream;
// EDS+EIOS/EIEOS drains it. This receives complete records; truncated EIOS,
// lane assignment/equalization/LTSSM, analog clocks and main-chip timing remain
// separate. One coordinated reset/arm epoch, fixed logical lane order0..3.
module soc_pcie_gen3_recovered_owned_rx_v1 #(
 parameter FIFO_DEPTH=32, MAX_SKEW_CYCLES=64,
 parameter MAX_ENCODED_BYTES=150,
 parameter RING_DWORDS=(1 << $clog2((MAX_ENCODED_BYTES+2)/4+16))
)(
 input wire por_ni,reset_i,abort_i,input wire [3:0] recovered_clk_i,input wire common_clk_i,
 input wire [3:0] raw_valid_i,input wire [127:0] raw_i,
 input wire [3:0] align_control_i,force_realign_i,input wire arm_i,
 output wire [3:0] lane_running_o,lane_aligned_o,lane_locked_o,lane_fault_o,
 output wire lanes_ready_o,stream_start_o,stream_stop_o,stop_eieos_o,
 output wire stream_end_o,active_o,halted_o,fault_o,
 output wire [3:0] lane_error_o,lfsr_mismatch_o,
 output wire skp_valid_o,output wire [775:0] skp_block_o,output wire [11:0] skp_length_code_o,
 output wire valid_o,input wire ready_i,output wire [127:0] data_o,
 output wire [15:0] keep_o,sop_o,eop_o,dllp_o,output wire [47:0] sequence_o,
 output wire [3:0] packet_good_o,packet_nullified_o,packet_crc_bad_o,packet_dllp_o,
 output wire [47:0] packet_sequence_o,
 output wire [23:0] owner_o,
 output wire [3:0] descriptor_valid_o,input wire descriptor_ready_i,
 output wire [23:0] descriptor_owner_o,output wire [47:0] descriptor_sequence_o,
 output wire [51:0] descriptor_bytes_o,
 output wire [3:0] descriptor_good_o,descriptor_nullified_o,descriptor_crc_bad_o,descriptor_dllp_o,
 output wire [15:0] epoch_o,
 output wire framing_error_o,overflow_o
);
 wire block_valid,block_ready,decision,eds,front_fault;
 wire [511:0] block_data;
 // A complete normal EIOS/EIEOS ends this packet epoch. Later idle/training
 // transport faults remain visible in lane_fault_o but cannot discard already
 // accepted complete packets during their downstream drain. A new epoch still
 // requires the coordinated reset/arm contract; this latch is not an LTSSM.
 reg stopped_q;
 wire epoch_fault=(front_fault && !stopped_q) || abort_i;
 always @(posedge common_clk_i or negedge por_ni) begin
   if(!por_ni) stopped_q<=0;
   else if(reset_i) stopped_q<=0;
   else if(stream_stop_o) stopped_q<=1;
 end
 assign fault_o=por_ni && !reset_i && (epoch_fault || halted_o);
 soc_pcie_gen3_recovered_x4_v4 #(.FIFO_DEPTH(FIFO_DEPTH),.MAX_SKEW_CYCLES(MAX_SKEW_CYCLES)) front(
 .por_ni(por_ni),.reset_i(reset_i),.recovered_clk_i(recovered_clk_i),.common_clk_i(common_clk_i),
 .raw_valid_i(raw_valid_i),.raw_i(raw_i),.align_control_i(align_control_i),.force_realign_i(force_realign_i),
 .arm_i(arm_i),.parser_fault_i(halted_o),.decision_valid_i(decision),.decision_eds_i(eds),
 .lane_running_o(lane_running_o),.lane_aligned_o(lane_aligned_o),.lane_locked_o(lane_locked_o),.lane_fault_o(lane_fault_o),
 .lanes_ready_o(lanes_ready_o),.stream_start_o(stream_start_o),.stream_stop_o(stream_stop_o),.stop_eieos_o(stop_eieos_o),
 .active_o(),.fault_o(front_fault),.data_valid_o(block_valid),.data_ready_i(block_ready),.data_o(block_data),
 .lane_error_o(lane_error_o),.lfsr_mismatch_o(lfsr_mismatch_o),
 .skp_valid_o(skp_valid_o),.skp_ready_i(1'b1),.skp_block_o(skp_block_o),.skp_length_code_o(skp_length_code_o));
 soc_pcie_gen3_framer_rx_owned_v3 #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) framer(
 .clk_i(common_clk_i),.rst_ni(por_ni && !reset_i),.flush_i(1'b0),
 .stream_start_i(stream_start_o),.stream_abort_i(epoch_fault),.stream_stop_i(stream_stop_o),
 .block_valid_i(block_valid),.block_ready_o(block_ready),.headers_i(8'haa),.payload_i(block_data),.block_error_i(1'b0),
 .block_decision_o(decision),.block_eds_o(eds),.valid_o(valid_o),.ready_i(ready_i),.data_o(data_o),
 .keep_o(keep_o),.sop_o(sop_o),.eop_o(eop_o),.dllp_o(dllp_o),.sequence_o(sequence_o),
 .owner_o(owner_o),.descriptor_valid_o(descriptor_valid_o),.descriptor_ready_i(descriptor_ready_i),
 .descriptor_owner_o(descriptor_owner_o),.descriptor_sequence_o(descriptor_sequence_o),.descriptor_bytes_o(descriptor_bytes_o),
 .descriptor_good_o(descriptor_good_o),.descriptor_nullified_o(descriptor_nullified_o),.descriptor_crc_bad_o(descriptor_crc_bad_o),.descriptor_dllp_o(descriptor_dllp_o),.epoch_o(epoch_o),
 .packet_good_o(packet_good_o),.packet_nullified_o(packet_nullified_o),.packet_crc_bad_o(packet_crc_bad_o),
 .packet_dllp_o(packet_dllp_o),.packet_sequence_o(packet_sequence_o),
 .framing_error_o(framing_error_o),.overflow_o(overflow_o),.stream_end_o(stream_end_o),.active_o(active_o),.halted_o(halted_o),.accepting_o());
endmodule
`default_nettype wire
