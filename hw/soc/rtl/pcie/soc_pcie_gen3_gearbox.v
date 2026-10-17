// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Four synchronous lanes; bit 0 is transmitted first. Fixed 130-bit blocks.
// A block header is common across TX lanes; RX returns each raw lane header.
// No scrambling, framing tokens, variable-size SKP, block search, lane deskew,
// CDC, LTSSM or serializer is implemented by this bit-preserving gearbox.
module soc_pcie_gen3_gearbox (
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire tx_block_valid_i, output wire tx_block_ready_o,
 input wire [1:0] tx_header_i, input wire [511:0] tx_payload_i,
 output wire tx_word_valid_o, input wire tx_word_ready_i,
 output wire [127:0] tx_word_o,
 input wire rx_word_valid_i, output wire rx_word_ready_o,
 input wire [127:0] rx_word_i,
 output wire rx_block_valid_o, input wire rx_block_ready_i,
 output wire [7:0] rx_header_o, output wire [511:0] rx_payload_o
);
 reg [159:0] tx_bits [0:3];
 reg [159:0] rx_bits [0:3];
 reg [7:0] tx_count, rx_count;
 wire active=rst_ni && !flush_i;
 assign tx_word_valid_o=active && tx_count>=8'd32;
 wire tx_pop=tx_word_valid_o && tx_word_ready_i;
 wire [7:0] tx_left=tx_count-(tx_pop ? 8'd32 : 8'd0);
 assign tx_block_ready_o=active && tx_left<=8'd30;
 wire tx_push=tx_block_valid_i && tx_block_ready_o;
 assign rx_block_valid_o=active && rx_count>=8'd130;
 wire rx_pop=rx_block_valid_o && rx_block_ready_i;
 wire [7:0] rx_left=rx_count-(rx_pop ? 8'd130 : 8'd0);
 assign rx_word_ready_o=active && rx_left<=8'd128;
 wire rx_push=rx_word_valid_i && rx_word_ready_o;
 genvar g;
 generate for(g=0;g<4;g=g+1) begin: lanes
   assign tx_word_o[g*32+:32]=tx_bits[g][31:0];
   assign rx_header_o[g*2+:2]=rx_bits[g][1:0];
   assign rx_payload_o[g*128+:128]=rx_bits[g][129:2];
 end endgenerate
 integer lane;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     tx_count<=0;rx_count<=0;
     for(lane=0;lane<4;lane=lane+1) begin tx_bits[lane]<=0;rx_bits[lane]<=0;end
   end else if(flush_i) begin
     tx_count<=0;rx_count<=0;
     for(lane=0;lane<4;lane=lane+1) begin tx_bits[lane]<=0;rx_bits[lane]<=0;end
   end else begin
     tx_count<=tx_left+(tx_push ? 8'd130 : 8'd0);
     rx_count<=rx_left+(rx_push ? 8'd32 : 8'd0);
     for(lane=0;lane<4;lane=lane+1) begin
       tx_bits[lane]<=(tx_pop ? tx_bits[lane]>>32 : tx_bits[lane]) |
         (tx_push ? ({30'b0,tx_payload_i[lane*128+:128],tx_header_i}<<tx_left) : 160'b0);
       rx_bits[lane]<=(rx_pop ? rx_bits[lane]>>130 : rx_bits[lane]) |
         (rx_push ? ({128'b0,rx_word_i[lane*32+:32]}<<rx_left) : 160'b0);
     end
   end
 end
endmodule
