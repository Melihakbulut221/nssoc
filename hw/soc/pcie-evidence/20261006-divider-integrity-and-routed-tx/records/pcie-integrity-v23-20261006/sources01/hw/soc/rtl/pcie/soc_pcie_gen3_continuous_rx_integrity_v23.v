// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Separate sustained fixed-Data-Block x4 development path. Raw input cannot
// pause; packet retirement is128 bits plus per-byte keep/boundary/type masks.
// No byte adapter, SKP search, CDC, serial receiver or complete PCS is implied.
`default_nettype none
module soc_pcie_gen3_continuous_rx_integrity_v23 #(
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
 soc_pcie_gen3_framer_rx_integrity_v23 #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) framer(
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
