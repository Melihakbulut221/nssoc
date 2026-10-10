`timescale 1ns/1ps
// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Separate sustained fixed-Data-Block x4 development path. Raw input cannot
// pause; packet retirement is128 bits plus per-byte keep/boundary/type masks.
// No byte adapter, SKP search, CDC, serial receiver or complete PCS is implied.
`default_nettype none
module soc_pcie_gen3_continuous_rx_integrity_v25 #(
 parameter integer MAX_ENCODED_BYTES=150,
 parameter integer RING_DWORDS=(1 << $clog2((MAX_ENCODED_BYTES+2)/4+16))
)(
 input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input wire [127:0] word_i,
 output wire valid_o,input wire ready_i,output wire [127:0] data_o,
 output wire [15:0] keep_o,sop_o,eop_o,dllp_o,
 output wire [47:0] sequence_o,
 output wire [3:0] packet_good_o,packet_nullified_o,packet_crc_bad_o,packet_dllp_o,
 output wire [47:0] packet_sequence_o,
 output wire framing_error_o,stream_end_o,active_o,halted_o,overflow_o
);

soc_pcie_gen3_continuous_rx_integrity_v25_core #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) candidate(.clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),.stream_start_i(stream_start_i),.stream_abort_i(stream_abort_i),.word_i(word_i),.ready_i(ready_i),.valid_o(valid_o),.data_o(data_o),.keep_o(keep_o),.sop_o(sop_o),.eop_o(eop_o),.dllp_o(dllp_o),.sequence_o(sequence_o),.packet_good_o(packet_good_o),.packet_nullified_o(packet_nullified_o),.packet_crc_bad_o(packet_crc_bad_o),.packet_dllp_o(packet_dllp_o),.packet_sequence_o(packet_sequence_o),.framing_error_o(framing_error_o),.stream_end_o(stream_end_o),.active_o(active_o),.halted_o(halted_o),.overflow_o(overflow_o));

localparam CPW=$clog2(RING_DWORDS)+1;
localparam COMMAND_BITS=10*CPW+248;
reg v25_model_valid=0;reg [COMMAND_BITS-1:0] v25_model_payload;
reg [CPW-1:0] v25_model_commit=0;
reg v25_pre_pending,v25_pre_apply,v25_pre_ending,v25_pre_step;
integer v25_commands=0,v25_applies=0,v25_bubble_applies=0,v25_ending_applies=0;
integer v25_replacements=0,v25_wraps=0,v25_zero_keep_applies=0,v25_epoch_pending[0:5];
integer v25_o;reg [CPW-1:0] v25_last_address=0;
initial for(v25_o=0;v25_o<6;v25_o=v25_o+1) v25_epoch_pending[v25_o]=0;
always @(posedge clk_i) begin
 v25_pre_pending=(candidate.framer.command_valid===1'b1);
 v25_pre_apply=0;v25_pre_ending=candidate.framer.ending;v25_pre_step=candidate.framer.step;
 if(rst_ni===1'b1 && candidate.framer.command_valid !== v25_model_valid)
  $fatal(1,"V25_COMMAND_VALID_OWNERSHIP");
 if(rst_ni===1'b1 && v25_model_valid && {candidate.framer.command_address,candidate.framer.command_commit,candidate.framer.command_data,candidate.framer.command_keep,candidate.framer.command_sop,candidate.framer.command_eop,candidate.framer.command_dllp,candidate.framer.command_sequence,candidate.framer.command_tags,candidate.framer.command_verdict_enable,candidate.framer.command_verdict_tags,candidate.framer.command_verdict_value} !== v25_model_payload)
  $fatal(1,"V25_COMMAND_ATOMIC_FIELDS");
 if(!rst_ni) begin
  if(v25_model_valid) v25_epoch_pending[0]=v25_epoch_pending[0]+1;
  v25_model_valid=0;v25_model_commit=0;v25_last_address=0;
 end else if(flush_i || stream_start_i) begin
  if(v25_pre_pending) begin
   if(flush_i) v25_epoch_pending[1]=v25_epoch_pending[1]+1;
   if(stream_start_i) v25_epoch_pending[2]=v25_epoch_pending[2]+1;
  end
  v25_model_valid=0;v25_model_commit=0;v25_last_address=0;
 end else if((stream_abort_i && candidate.framer.active_o) || candidate.framer.fault_now) begin
  if(v25_pre_pending) begin
   if(stream_abort_i) v25_epoch_pending[3]=v25_epoch_pending[3]+1;
   if(candidate.framer.fault_now) v25_epoch_pending[4]=v25_epoch_pending[4]+1;
   if(candidate.framer.ring_overflow_now) v25_epoch_pending[5]=v25_epoch_pending[5]+1;
  end
  v25_model_valid=0;v25_model_commit=0;v25_last_address=0;
 end else if(candidate.framer.active_o) begin
  if(candidate.framer.enabled) begin
   if(v25_model_valid) begin
    v25_pre_apply=1;
    v25_model_commit=v25_model_payload[COMMAND_BITS-CPW-1-:CPW];
    v25_applies=v25_applies+1;
    if(!candidate.framer.step) v25_bubble_applies=v25_bubble_applies+1;
    if(candidate.framer.ending) v25_ending_applies=v25_ending_applies+1;
    if(candidate.framer.command_keep==0) v25_zero_keep_applies=v25_zero_keep_applies+1;
   end
   v25_model_valid=0;
   if(candidate.framer.step) begin
    v25_model_valid=1;v25_model_payload={candidate.framer.write_ptr,candidate.framer.commit_n,candidate.framer.write_data,candidate.framer.write_keep,candidate.framer.write_sop,candidate.framer.write_eop,candidate.framer.write_dllp,candidate.framer.write_sequence,candidate.framer.write_tags,candidate.framer.verdict_enable,candidate.framer.verdict_tags,candidate.framer.verdict_value};
    v25_commands=v25_commands+1;
    if(v25_pre_pending) v25_replacements=v25_replacements+1;
    if(candidate.framer.write_ptr<v25_last_address) v25_wraps=v25_wraps+1;
    v25_last_address=candidate.framer.write_ptr;
   end
  end
 end
 #0.002;
 if(candidate.framer.command_valid !== v25_model_valid)
  $fatal(1,"V25_COMMAND_VALID_TRANSITION");
 if(candidate.framer.visible_commit_ptr !== v25_model_commit)
  $fatal(1,"V25_COMMAND_VISIBLE_COMMIT_EDGE");
 if(v25_model_valid && {candidate.framer.command_address,candidate.framer.command_commit,candidate.framer.command_data,candidate.framer.command_keep,candidate.framer.command_sop,candidate.framer.command_eop,candidate.framer.command_dllp,candidate.framer.command_sequence,candidate.framer.command_tags,candidate.framer.command_verdict_enable,candidate.framer.command_verdict_tags,candidate.framer.command_verdict_value} !== v25_model_payload)
  $fatal(1,"V25_COMMAND_ATOMIC_CAPTURE");
 if(candidate.framer.committed !== ((v25_model_commit-candidate.framer.read_ptr)&((2*RING_DWORDS)-1)))
  $fatal(1,"V25_COMMAND_VISIBLE_RETIRE_FRONTIER");
 if(candidate.framer.active_o && v25_model_valid &&
    candidate.framer.write_ptr !== ((candidate.framer.command_address+4)&((2*RING_DWORDS)-1)))
  $fatal(1,"V25_COMMAND_RESERVED_ADDRESS");
 if(stream_end_o && (candidate.framer.command_valid ||
    candidate.framer.visible_commit_ptr!==candidate.framer.commit_ptr))
  $fatal(1,"V25_COMMAND_PREMATURE_EDS");
end
final $display("V25_COMMAND_DUT_WITNESSES commands=%0d applies=%0d bubble=%0d ending=%0d replacements=%0d wraps=%0d zero=%0d epochs=%0d,%0d,%0d,%0d,%0d,%0d",
 v25_commands,v25_applies,v25_bubble_applies,v25_ending_applies,v25_replacements,v25_wraps,
 v25_zero_keep_applies,v25_epoch_pending[0],v25_epoch_pending[1],v25_epoch_pending[2],v25_epoch_pending[3],v25_epoch_pending[4],v25_epoch_pending[5]);

// Independent temporal observer: predecessor validity is captured BEFORE the
// actual acceptance edge and accompanies each bank, never read from newtail.
reg v25_tail_valid=0,v25_tail_stp=0;
reg [12:0] v25_tail_encoded=0;
reg [15:0] v25_current_pred=0,v25_next_pred=0;
reg [15:0] v25_current_stp=0,v25_next_stp=0;
reg [15:0] v25_current_relation=16'hffff,v25_next_relation=16'hffff;
integer v25_accept_base=0,v25_current_base=0,v25_next_base=0;
integer v25_last_stp_id=-2;
integer v25_i,v25_j,v25_source_id;
reg [12:0] v25_previous;
reg [15:0] v25_in_pred,v25_in_stp,v25_in_relation;
reg v25_original_bad;
integer v25_cross_block_headers=0,v25_minimum_same_beat_ends=0;
integer v25_missing_predecessor_accepts=0,v25_first_headers=0;
integer v25_stp_positions[0:15];
initial for(v25_i=0;v25_i<16;v25_i=v25_i+1) v25_stp_positions[v25_i]=0;
always @(posedge clk_i) begin
 // Compare OLD valid companions and original late predicate before NBA.
 if(rst_ni===1'b1 && candidate.framer.current_valid===1'b1) begin
  if(candidate.framer.current_header_relation !== v25_current_relation)
   $fatal(1,"V25_HEADER_BANK_RELATION current");
 end
 if(rst_ni===1'b1 && candidate.framer.next_valid===1'b1) begin
  if(candidate.framer.next_header_relation !== v25_next_relation)
   $fatal(1,"V25_HEADER_BANK_RELATION next");
 end
 if(rst_ni===1'b1 && candidate.framer.step===1'b1) begin
  if(candidate.framer.state==candidate.framer.TLP && !candidate.framer.header_first &&
     candidate.framer.packet_header_mismatch !==
      (candidate.framer.header_bad || candidate.framer.packet_bytes!=candidate.framer.expected_bytes))
    $fatal(1,"V25_CARRIED_HEADER_RELATION");
  for(v25_j=0;v25_j<4;v25_j=v25_j+1) begin
   v25_source_id=v25_current_base+v25_j;
   if(candidate.framer.control_active[v25_j] && candidate.framer.control_stp[v25_j] &&
      (candidate.framer.control_modes[v25_j][0] || candidate.framer.control_modes[v25_j][2])) begin
    v25_last_stp_id=v25_source_id;
    v25_stp_positions[v25_source_id%16]=v25_stp_positions[v25_source_id%16]+1;
   end
   if(candidate.framer.control_active[v25_j] && candidate.framer.control_header_first[v25_j]) begin
    if(v25_current_pred[v25_j] !== 1'b1 || v25_current_stp[v25_j] !== 1'b1 ||
       v25_source_id != v25_last_stp_id+1)
      $fatal(1,"V25_FIRST_HEADER_PREDECESSOR_OWNERSHIP");
    if(v25_j==0) v25_previous=candidate.framer.packet_bytes;
    else v25_previous=candidate.framer.control_encoded[v25_j-1];
    v25_original_bad=candidate.framer.current_predecode[v25_j*32+18] ||
      (v25_previous!=candidate.framer.current_predecode[v25_j*32+5+:13]);
    if(candidate.framer.current_header_relation[v25_j] !== v25_original_bad)
      $fatal(1,"V25_FIRST_HEADER_RELATION");
    v25_first_headers=v25_first_headers+1;
    if(v25_source_id%16==0) v25_cross_block_headers=v25_cross_block_headers+1;
    if(v25_j==0 && candidate.framer.remaining==4 && candidate.framer.control_carry_end[3])
      v25_minimum_same_beat_ends=v25_minimum_same_beat_ends+1;
   end
  end
 end
 if(!rst_ni) begin
  v25_tail_valid<=0;v25_tail_stp<=0;v25_tail_encoded<=0;v25_accept_base<=0;
  v25_current_pred<=0;v25_next_pred<=0;v25_current_stp<=0;v25_next_stp<=0;
  v25_current_relation<=16'hffff;v25_next_relation<=16'hffff;
  v25_current_base<=0;v25_next_base<=0;v25_last_stp_id=-2;
 end else begin
  // Derive each accepted relation independently from reference predecode,
  // carrying the old predecessor-valid and identity in companion metadata.
  if(candidate.framer.enabled && candidate.framer.active_o) begin
   if(candidate.framer.step) begin
    if(candidate.framer.slice==3) begin
     if(candidate.framer.next_valid) begin
      v25_current_pred<=v25_next_pred;v25_current_stp<=v25_next_stp;
      v25_current_relation<=v25_next_relation;v25_current_base<=v25_next_base;
     end
    end else begin
     v25_current_pred<={4'b0,v25_current_pred[15:4]};
     v25_current_stp<={4'b0,v25_current_stp[15:4]};
     v25_current_relation<={4'b1111,v25_current_relation[15:4]};
     v25_current_base<=v25_current_base+4;
    end
   end
   if(candidate.framer.block_valid_i && candidate.framer.block_ready_o) begin
    v25_in_pred={15'h7fff,v25_tail_valid};
    if(v25_in_pred[0] !== v25_tail_valid) $fatal(1,"V25_OBSERVER_OLD_PREDECESSOR");
    v25_in_stp[0]=v25_tail_stp;
    for(v25_i=0;v25_i<16;v25_i=v25_i+1) begin
     if(v25_i==0) v25_previous=v25_tail_encoded;
     else begin
      v25_previous=candidate.framer.input_predecode[(v25_i-1)*32+19+:13];
      v25_in_stp[v25_i]=candidate.framer.input_predecode[(v25_i-1)*32];
     end
     v25_in_relation[v25_i]=candidate.framer.input_predecode[v25_i*32+18] ||
       v25_previous!=candidate.framer.input_predecode[v25_i*32+5+:13];
    end
    if(!v25_tail_valid) v25_missing_predecessor_accepts=v25_missing_predecessor_accepts+1;
    if(!candidate.framer.current_valid || (candidate.framer.last_slice && !candidate.framer.next_valid)) begin
     v25_current_pred<=v25_in_pred;v25_current_stp<=v25_in_stp;
     v25_current_relation<=v25_in_relation;v25_current_base<=v25_accept_base;
    end else begin
     v25_next_pred<=v25_in_pred;v25_next_stp<=v25_in_stp;
     v25_next_relation<=v25_in_relation;v25_next_base<=v25_accept_base;
    end
    v25_tail_encoded<=candidate.framer.input_predecode[15*32+19+:13];
    v25_tail_stp<=candidate.framer.input_predecode[15*32];
    v25_accept_base<=v25_accept_base+16;
   end
  end
  if(flush_i || stream_start_i || (stream_abort_i && candidate.framer.active_o) || candidate.framer.fault_now) begin
   v25_tail_valid<=0;v25_accept_base<=0;v25_last_stp_id=-2;
  end else if(candidate.framer.enabled && candidate.framer.active_o &&
              candidate.framer.block_valid_i && candidate.framer.block_ready_o) v25_tail_valid<=1;
 end
end


integer v25_fault_command_events=0,v25_invalid_cache_change_events=0;
integer v25_cache_i,v25_cache_changed;reg v25_cache_fault_edge=0;
reg v25_cache_before[0:RING_DWORDS-1];
reg [3:0] v25_old_good_verdict;
always @(posedge clk_i) begin
 v25_cache_fault_edge=(rst_ni===1'b1 && candidate.framer.enabled===1'b1 &&
   candidate.framer.active_o===1'b1 && candidate.framer.command_valid===1'b1 &&
   candidate.framer.fault_now===1'b1);
 if(v25_cache_fault_edge) begin
  v25_old_good_verdict=candidate.framer.command_verdict_enable & candidate.framer.command_verdict_value;
  for(v25_cache_i=0;v25_cache_i<RING_DWORDS;v25_cache_i=v25_cache_i+1)
   v25_cache_before[v25_cache_i]=candidate.framer.slot_verdict[v25_cache_i];
 end
 #0.002;
 if(v25_cache_fault_edge) begin
  if({candidate.framer.command_valid,candidate.framer.visible_commit_ptr,
      candidate.framer.commit_ptr,candidate.framer.write_ptr,candidate.framer.read_ptr,
      candidate.framer.output_valid,candidate.framer.retire_valid,candidate.framer.active_o}!==0 ||
      candidate.framer.halted_o!==1)
   $fatal(1,"V25_FAULT_COMMAND_CACHE_QUARANTINE");
  if(v25_old_good_verdict!=0) begin
   v25_fault_command_events=v25_fault_command_events+1;v25_cache_changed=0;
   for(v25_cache_i=0;v25_cache_i<RING_DWORDS;v25_cache_i=v25_cache_i+1)
    if(candidate.framer.slot_verdict[v25_cache_i] !== v25_cache_before[v25_cache_i]) v25_cache_changed=1;
   if(v25_cache_changed) v25_invalid_cache_change_events=v25_invalid_cache_change_events+1;
  end
 end
end

generate if(1) begin:framer
wire retire_valid=candidate.framer.retire_valid;
wire retire_has_data=candidate.framer.retire_has_data;
wire output_valid=candidate.framer.output_valid;
wire retire_pop=candidate.framer.retire_pop;
wire retire=candidate.framer.retire;
wire fault_now=candidate.framer.fault_now;
wire command_valid=candidate.framer.command_valid;
wire [$clog2(RING_DWORDS)+1-1:0] read_ptr=candidate.framer.read_ptr;
wire [$clog2(RING_DWORDS)+1-1:0] write_ptr=candidate.framer.write_ptr;
wire [$clog2(RING_DWORDS)+1-1:0] commit_ptr=candidate.framer.commit_ptr;
wire [$clog2(RING_DWORDS)+1-1:0] visible_commit_ptr=candidate.framer.visible_commit_ptr;
end endgenerate
endmodule
// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Separate sustained fixed-Data-Block x4 development path. Raw input cannot
// pause; packet retirement is128 bits plus per-byte keep/boundary/type masks.
// No byte adapter, SKP search, CDC, serial receiver or complete PCS is implied.
`default_nettype none
module soc_pcie_gen3_continuous_rx_integrity_v25_core #(
 parameter integer MAX_ENCODED_BYTES=150,
 parameter integer RING_DWORDS=(1 << $clog2((MAX_ENCODED_BYTES+2)/4+16))
)(
 input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input wire [127:0] word_i,
 output wire valid_o,input wire ready_i,output wire [127:0] data_o,
 output wire [15:0] keep_o,sop_o,eop_o,dllp_o,
 output wire [47:0] sequence_o,
 output wire [3:0] packet_good_o,packet_nullified_o,packet_crc_bad_o,packet_dllp_o,
 output wire [47:0] packet_sequence_o,
 output wire framing_error_o,stream_end_o,active_o,halted_o,overflow_o
);
 wire raw_valid,raw_ready,raw_overflow,decoded_valid,decoded_ready;
 wire [7:0] raw_headers,decoded_headers;
 wire [511:0] raw_payload,decoded_payload;
 wire accepting,ring_overflow;
 reg overflow_sticky;
 assign overflow_o=(overflow_sticky || raw_overflow || ring_overflow) &&
                   rst_ni && !flush_i && !stream_start_i;
 // The framer owns its internal ring fault. Feeding its combinational fault
 // back into its abort input would create a combinational cancellation loop.
 wire abort_epoch=(stream_abort_i || raw_overflow) && !stream_start_i;
 wire transport_flush=flush_i || abort_epoch || (!accepting && !stream_start_i);
 soc_pcie_gen3_ingress_integrity_v11 #(.FIFO_DEPTH(4)) ingress(
   .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(transport_flush),.start_i(stream_start_i),
   .word_i(word_i),.block_valid_o(raw_valid),.block_ready_i(raw_ready),
   .headers_o(raw_headers),.payload_o(raw_payload),.active_o(),.overflow_o(raw_overflow));
 soc_pcie_gen3_data_descrambler descrambler(
   .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(transport_flush || stream_start_i),
   .valid_i(raw_valid),.ready_o(raw_ready),.headers_i(raw_headers),.payload_i(raw_payload),
   .valid_o(decoded_valid),.ready_i(decoded_ready),.headers_o(decoded_headers),.payload_o(decoded_payload));
 soc_pcie_gen3_framer_rx_integrity_v25 #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) framer(
   .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),.stream_start_i(stream_start_i),.stream_abort_i(abort_epoch),
   .block_valid_i(decoded_valid),.block_ready_o(decoded_ready),.headers_i(decoded_headers),.payload_i(decoded_payload),.block_error_i(1'b0),
   .valid_o(valid_o),.ready_i(ready_i),.data_o(data_o),.keep_o(keep_o),.sop_o(sop_o),.eop_o(eop_o),.dllp_o(dllp_o),.sequence_o(sequence_o),
   .packet_crc_bad_o(packet_crc_bad_o),.packet_dllp_o(packet_dllp_o),.packet_good_o(packet_good_o),.packet_nullified_o(packet_nullified_o),.packet_sequence_o(packet_sequence_o),
   .framing_error_o(framing_error_o),.overflow_o(ring_overflow),.stream_end_o(stream_end_o),.active_o(active_o),.halted_o(halted_o),.accepting_o(accepting));
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) overflow_sticky<=0;
   else if(flush_i || stream_start_i) overflow_sticky<=0;
   else if(raw_overflow || ring_overflow) overflow_sticky<=1;
 end
endmodule
`default_nettype wire
