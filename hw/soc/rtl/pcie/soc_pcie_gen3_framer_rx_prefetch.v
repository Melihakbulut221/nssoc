// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Active x4 Data Stream only. Input is already aligned, deskewed, descrambled.
// External SDS/OS owner starts the stream; EDS ends it. This block does not train,
// descramble, validate LCRC/CRC16, or supply a line-rate PMA input queue.
// A TLP is quarantined until its immediate successor token establishes whether
// it is nullified. Exact EDB discards it with sequence sideband, never good data.
module soc_pcie_gen3_framer_rx_prefetch #(
 parameter integer MAX_ENCODED_BYTES=150
)(
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire stream_start_i, input wire stream_abort_i,
 input wire block_valid_i, output wire block_ready_o,
 input wire [7:0] headers_i, input wire [511:0] payload_i,
 input wire block_error_i,
 output wire valid_o, input wire ready_i, output wire [7:0] data_o,
 output wire sop_o, output wire eop_o, output wire dllp_o,
 output reg packet_good_o, output reg packet_nullified_o,
 output reg [11:0] sequence_o,
 output reg framing_error_o, output reg stream_end_o,
 output reg active_o, output reg halted_o
);
 localparam [2:0] TOKEN=0, TLP=1, LOOK=2, DLLP=3, EMIT=4;
 reg [2:0] state;
 reg [511:0] block_data;
 reg block_pending;
 reg [3:0] word_index;
 reg [7:0] packet [0:MAX_ENCODED_BYTES-1];
 // Accepted STP length is bounded by the actual instantiated packet buffer.
 localparam integer POS_W=$clog2(MAX_ENCODED_BYTES+1);
 reg [POS_W-1:0] write_pos, packet_bytes, read_pos;
 // One-byte-ahead address removes carry propagation from the packet mux path.
 // It changes only the stored address, never the public byte/valid latency.
 reg [POS_W-1:0] read_next_pos;
 reg [12:0] header_bytes;
 reg [7:0] read_data;
 reg [10:0] remaining_dw;
 reg header_bad, packet_dllp;
 wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;
 assign block_ready_o=enabled && active_o && !block_pending && state!=EMIT;
 assign valid_o=enabled && active_o && state==EMIT;
 assign data_o=valid_o ? read_data : 8'b0;
 assign sop_o=valid_o && read_pos==0;
 assign eop_o=valid_o && read_pos+1==packet_bytes;
 assign dllp_o=packet_dllp;
 // Lane-local shift registers expose a constant byte position; no 16:1
 // selector driven by word_index is in the CRC/token acceptance path.
 wire [31:0] word={block_data[391:384],block_data[263:256],
                         block_data[135:128],block_data[7:0]};
 wire [10:0] length_dw={word[14:8],word[7:4]};
 wire [3:0] frame_crc;
 assign frame_crc[0]=length_dw[10]^length_dw[7]^length_dw[6]^length_dw[4]^length_dw[2]^length_dw[1]^length_dw[0];
 assign frame_crc[1]=length_dw[10]^length_dw[9]^length_dw[7]^length_dw[5]^length_dw[4]^length_dw[3]^length_dw[2];
 assign frame_crc[2]=length_dw[9]^length_dw[8]^length_dw[6]^length_dw[4]^length_dw[3]^length_dw[2]^length_dw[1];
 assign frame_crc[3]=length_dw[8]^length_dw[7]^length_dw[5]^length_dw[3]^length_dw[2]^length_dw[1]^length_dw[0];
 wire [12:0] encoded_bytes={length_dw,2'b00}-13'd2;
 wire stp_ok=word[3:0]==4'hf && length_dw>=5 && length_dw<1152 &&
                  encoded_bytes<=MAX_ENCODED_BYTES && frame_crc==word[23:20] &&
                  (^{length_dw,word[23:20],word[15]})==1'b0;
 wire sdp_ok=word[15:0]==16'hacf0;
 wire idl_ok=word==32'b0;
 wire eds_ok=word==32'h0090801f && word_index==15;
 wire edb_ok=word==32'hc0c0c0c0;
 wire successor_ok=stp_ok || sdp_ok || idl_ok || eds_ok;
 wire [2:0] fmt=word[7:5];
 wire [9:0] tlp_length={word[17:16],word[31:24]};
 wire [12:0] payload_bytes=tlp_length==0 ? 13'd4096 : {1'b0,tlp_length,2'b00};
 wire [12:0] expected_bytes=13'd18+(fmt[0]?13'd4:13'd0)+
                  (fmt[1]?payload_bytes:13'd0)+(word[23]?13'd4:13'd0);
 integer lane;
 task consume_word;
 begin
   block_data <= {8'b0,block_data[511:392],8'b0,block_data[383:264],
                  8'b0,block_data[255:136],8'b0,block_data[127:8]};
   if(word_index==15) begin block_pending<=0;word_index<=0;end
   else word_index<=word_index+1'b1;
 end
 endtask
 task framing_failure;
 begin
   framing_error_o<=1;halted_o<=1;active_o<=0;
   block_pending<=0;state<=TOKEN;read_pos<=0;read_next_pos<=1;
 end
 endtask
 initial begin
   if(MAX_ENCODED_BYTES<18 || MAX_ENCODED_BYTES>4118)
     $error("MAX_ENCODED_BYTES must be18..4118; 4122-byte digest maximum unsupported");
 end
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     state<=TOKEN;block_pending<=0;block_data<=0;word_index<=0;
     write_pos<=0;packet_bytes<=0;read_pos<=0;read_next_pos<=1;header_bytes<=0;read_data<=0;
     remaining_dw<=0;header_bad<=0;packet_dllp<=0;sequence_o<=0;
     packet_good_o<=0;packet_nullified_o<=0;framing_error_o<=0;
     stream_end_o<=0;active_o<=0;halted_o<=0;
   end else begin
     packet_good_o<=0;packet_nullified_o<=0;framing_error_o<=0;stream_end_o<=0;
     if(flush_i || stream_start_i) begin
       state<=TOKEN;block_pending<=0;word_index<=0;read_pos<=0;read_next_pos<=1;
       write_pos<=0;packet_bytes<=0;remaining_dw<=0;packet_dllp<=0;
       active_o<=stream_start_i && !flush_i;halted_o<=0;
     end else if(stream_abort_i) begin
       if(active_o) framing_failure();
     end else if(active_o) begin
       if(block_valid_i && block_ready_o) begin
         if(headers_i!=8'haa || block_error_i) framing_failure();
         else begin block_data<=payload_i;block_pending<=1;word_index<=0;end
       end
       if(state==EMIT) begin
         if(valid_o && ready_i) begin
           if(eop_o) begin state<=TOKEN;read_pos<=0;read_next_pos<=1;end
           else begin read_pos<=read_pos+1'b1;read_next_pos<=read_next_pos+1'b1;read_data<=packet[read_next_pos];end
         end
       end else if(block_pending) begin
         case(state)
           TOKEN:begin
             if(idl_ok) consume_word();
             else if(eds_ok) begin
               consume_word();active_o<=0;stream_end_o<=1;
             end else if(stp_ok) begin
               packet[0]<={4'b0,word[19:16]};packet[1]<=word[31:24];
               sequence_o<={word[19:16],word[31:24]};
               packet_bytes<=encoded_bytes;write_pos<=2;read_pos<=0;read_next_pos<=1;
               remaining_dw<=length_dw-1'b1;packet_dllp<=0;
               header_bad<=0;header_bytes<=0;state<=TLP;consume_word();
             end else if(sdp_ok) begin
               packet[0]<=word[23:16];packet[1]<=word[31:24];
               packet_bytes<=6;packet_dllp<=1;read_pos<=0;read_next_pos<=1;
               state<=DLLP;consume_word();
             end else framing_failure();
           end
           TLP:begin
             for(lane=0;lane<4;lane=lane+1) packet[write_pos+lane]<=word[lane*8+:8];
             if(write_pos==2) begin header_bad<=fmt[2];header_bytes<=expected_bytes;end
             write_pos<=write_pos+4;remaining_dw<=remaining_dw-1'b1;
             consume_word();
             if(remaining_dw==1) begin
               if(header_bad || packet_bytes!=header_bytes) framing_failure();
               else state<=LOOK;
             end
           end
           LOOK:begin
             if(edb_ok) begin
               packet_nullified_o<=1;state<=TOKEN;consume_word();
             end else if(successor_ok) begin
               // Do not consume the successor: it must be processed after the
               // held complete packet is delivered, even if in the same block.
               packet_good_o<=1;state<=EMIT;read_pos<=0;read_next_pos<=1;read_data<=packet[0];
             end else framing_failure();
           end
           DLLP:begin
             for(lane=0;lane<4;lane=lane+1) packet[2+lane]<=word[lane*8+:8];
             consume_word();packet_good_o<=1;state<=EMIT;read_pos<=0;read_next_pos<=1;read_data<=packet[0];
           end
           default:framing_failure();
         endcase
       end
     end
   end
 end
endmodule
