// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Continuous, already aligned/deskewed x4 fixed-Data-Block development path.
// No word_ready signal: every active clock consumes32 bits per lane. Overflow
// aborts the complete epoch, never silently skips a word. Whole-IDL bypass
// supports continuous idle traffic while a packet output stalls. Dense packet
// throughput remains bounded by the byte output and finite input queue.
// No SKP/OS search, CDC, CDR, PCS/LTSSM completion or real serial PMA is implied.
module soc_pcie_gen3_continuous_rx #(
 parameter integer MAX_ENCODED_BYTES=150
)(
 input wire clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input wire [127:0] word_i,
 output wire valid_o,input wire ready_i,output wire [7:0] data_o,
 output wire sop_o,eop_o,dllp_o,packet_good_o,packet_nullified_o,
 output wire [11:0] sequence_o,
 output wire framing_error_o,stream_end_o,active_o,halted_o,
 output wire overflow_o
);
 wire raw_valid,raw_ready,raw_overflow;
 wire [7:0] raw_headers,decoded_headers;
 wire [511:0] raw_payload,decoded_payload;
 wire decoded_valid,decoded_ready;
 reg overflow_sticky;
 // Report the same-cycle ingress fault that invalidates held packet data.
 assign overflow_o=(overflow_sticky || raw_overflow) && rst_ni && !flush_i && !stream_start_i;
 wire abort_epoch=(stream_abort_i || overflow_o || raw_overflow) && !stream_start_i;
 wire transport_flush=flush_i || abort_epoch || (!active_o && !stream_start_i);
 // Sixteen blocks absorb the default150-byte parser's finite processing
 // burst. This does not make the byte-wide output a saturated x4 consumer.
 soc_pcie_gen3_ingress #(.FIFO_DEPTH(16)) ingress(
   .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(transport_flush),.start_i(stream_start_i),
   .word_i(word_i),.block_valid_o(raw_valid),.block_ready_i(raw_ready),
   .headers_o(raw_headers),.payload_o(raw_payload),.active_o(),.overflow_o(raw_overflow));
 soc_pcie_gen3_data_descrambler descrambler(
   .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(transport_flush || stream_start_i),
   .valid_i(raw_valid),.ready_o(raw_ready),.headers_i(raw_headers),.payload_i(raw_payload),
   .valid_o(decoded_valid),.ready_i(decoded_ready),
   .headers_o(decoded_headers),.payload_o(decoded_payload));
 soc_pcie_gen3_framer_rx_v3 #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) framer(
   .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),
   .stream_start_i(stream_start_i),.stream_abort_i(abort_epoch),
   .block_valid_i(decoded_valid),.block_ready_o(decoded_ready),
   .headers_i(decoded_headers),.payload_i(decoded_payload),.block_error_i(1'b0),
   .valid_o(valid_o),.ready_i(ready_i),.data_o(data_o),.sop_o(sop_o),.eop_o(eop_o),
   .dllp_o(dllp_o),.packet_good_o(packet_good_o),.packet_nullified_o(packet_nullified_o),
   .sequence_o(sequence_o),.framing_error_o(framing_error_o),.stream_end_o(stream_end_o),
   .active_o(active_o),.halted_o(halted_o));
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) overflow_sticky<=0;
   else if(flush_i || stream_start_i) overflow_sticky<=0;
   else if(raw_overflow) overflow_sticky<=1;
 end
endmodule
