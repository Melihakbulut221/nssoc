// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Elastic, aligned x4 active-Data-Stream receive seam. Each word contains the
// next32 serial bits per lane, bit0 first. Caller owns block alignment, lane
// deskew and the common scrambler epoch. This is not a backpressurable PMA.
// Only Data Blocks are supported; OS/SKP/training are external responsibilities.
module soc_pcie_gen3_packet_rx_path #(
 parameter integer MAX_ENCODED_BYTES=150
)(
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire stream_start_i, input wire stream_abort_i,
 input wire word_valid_i, output wire word_ready_o,
 input wire [127:0] word_i,
 output wire valid_o, input wire ready_i, output wire [7:0] data_o,
 output wire sop_o, output wire eop_o, output wire dllp_o,
 output wire packet_good_o, output wire packet_nullified_o,
 output wire [11:0] sequence_o,
 output wire framing_error_o, output wire stream_end_o,
 output wire active_o, output wire halted_o
);
 wire transport_flush=flush_i || stream_start_i || stream_abort_i || !active_o;
 wire enabled=rst_ni && !transport_flush;
 wire recovered_valid,recovered_ready,gearbox_ready;
 wire [511:0] recovered_payload;
 wire [7:0] recovered_headers;
 assign word_ready_o=enabled && gearbox_ready;
 soc_pcie_gen3_gearbox gearbox(
  .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(transport_flush),
  .tx_block_valid_i(1'b0),.tx_block_ready_o(),.tx_header_i(2'b0),
  .tx_payload_i(512'b0),.tx_word_valid_o(),.tx_word_ready_i(1'b0),.tx_word_o(),
  .rx_word_valid_i(word_valid_i && enabled),.rx_word_ready_o(gearbox_ready),
  .rx_word_i(word_i),.rx_block_valid_o(recovered_valid),
  .rx_block_ready_i(recovered_ready),.rx_header_o(recovered_headers),
  .rx_payload_o(recovered_payload));

 reg raw_pending,decoded_valid;
 reg [511:0] raw_payload,decoded_payload;
 reg [7:0] raw_headers,decoded_headers;
 reg [2:0] feed_index;
 reg [1:0] collect_index;
 wire descramble_ready,descrambled_valid;
 wire [127:0] descramble_input,descrambled;
 wire decoded_ready;
 assign recovered_ready=enabled && !raw_pending && !decoded_valid;
 genvar lane;
 generate for(lane=0;lane<4;lane=lane+1) begin: input_lanes
   assign descramble_input[lane*32+:32]=raw_payload[lane*128+feed_index*32+:32];
 end endgenerate
 soc_pcie_gen3_scrambler descrambler(
  .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(transport_flush),
  .valid_i(raw_pending && feed_index<4),.ready_o(descramble_ready),
  .data_i(descramble_input),.advance_i(16'hffff),.scramble_i(16'hffff),
  .reseed_after_i(4'b0),.valid_o(descrambled_valid),
  .ready_i(raw_pending && !decoded_valid),.data_o(descrambled));
 integer k;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     raw_pending<=0;decoded_valid<=0;feed_index<=0;collect_index<=0;
     raw_payload<=0;decoded_payload<=0;raw_headers<=0;decoded_headers<=0;
   end else if(transport_flush) begin
     raw_pending<=0;decoded_valid<=0;feed_index<=0;collect_index<=0;
     raw_payload<=0;decoded_payload<=0;raw_headers<=0;decoded_headers<=0;
   end else begin
     if(decoded_valid && decoded_ready) decoded_valid<=0;
     if(recovered_valid && recovered_ready) begin
       raw_pending<=1;raw_payload<=recovered_payload;raw_headers<=recovered_headers;
       feed_index<=0;collect_index<=0;
     end
     if(raw_pending && feed_index<4 && descramble_ready) feed_index<=feed_index+1'b1;
     if(descrambled_valid && raw_pending && !decoded_valid) begin
       for(k=0;k<4;k=k+1)
         decoded_payload[k*128+collect_index*32+:32]<=descrambled[k*32+:32];
       if(collect_index==3) begin
         raw_pending<=0;decoded_valid<=1;decoded_headers<=raw_headers;
         collect_index<=0;
       end else collect_index<=collect_index+1'b1;
     end
   end
 end
 soc_pcie_gen3_framer_rx #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) framer(
  .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),
  .stream_start_i(stream_start_i),.stream_abort_i(stream_abort_i),
  .block_valid_i(decoded_valid),.block_ready_o(decoded_ready),
  .headers_i(decoded_headers),.payload_i(decoded_payload),.block_error_i(1'b0),
  .valid_o(valid_o),.ready_i(ready_i),.data_o(data_o),
  .sop_o(sop_o),.eop_o(eop_o),.dllp_o(dllp_o),
  .packet_good_o(packet_good_o),.packet_nullified_o(packet_nullified_o),
  .sequence_o(sequence_o),.framing_error_o(framing_error_o),
  .stream_end_o(stream_end_o),.active_o(active_o),.halted_o(halted_o));
endmodule
