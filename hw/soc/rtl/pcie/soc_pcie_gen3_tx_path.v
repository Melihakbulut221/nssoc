// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Four logical lanes, one 128-bit payload and common two-bit header per lane.
// This is a fixed-block TX transport: explicit caller-owned byte policies,
// after-block reseed, scrambling then the real 130/32 gearbox. No automatic
// ordered-set policy, variable SKP, training, CDC, serializer or PMA is implied.
module soc_pcie_gen3_tx_path (
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire block_valid_i, output wire block_ready_o,
 input wire [1:0] header_i, input wire [511:0] payload_i,
 input wire [63:0] advance_i, input wire [63:0] scramble_i,
 input wire [3:0] reseed_after_i,
 output wire word_valid_o, input wire word_ready_i,
 output wire [127:0] word_o
);
 function [22:0] lane_seed;
   input integer lane;
   begin
     case(lane)
       0:lane_seed=23'h1dbfbc;
       1:lane_seed=23'h0607bb;
       2:lane_seed=23'h1ec760;
       default:lane_seed=23'h18c0db;
     endcase
   end
 endfunction
 reg [22:0] state [0:3];
 reg [22:0] next_state [0:3];
 reg [511:0] transformed, held_payload;
 reg [1:0] held_header;
 reg held_valid;
 wire gearbox_ready;
 wire active=rst_ni && !flush_i;
 assign block_ready_o=active && (!held_valid || gearbox_ready);
 integer lane, bit_index;
 always @* begin
   transformed=payload_i;
   for(lane=0;lane<4;lane=lane+1) begin
     next_state[lane]=state[lane];
     for(bit_index=0;bit_index<128;bit_index=bit_index+1) begin
       if(scramble_i[lane*16+bit_index/8])
         transformed[lane*128+bit_index]=payload_i[lane*128+bit_index]^next_state[lane][22];
       if(advance_i[lane*16+bit_index/8])
         next_state[lane]={next_state[lane][21:0],1'b0}^
           (next_state[lane][22] ? 23'h210125 : 23'b0);
     end
     if(reseed_after_i[lane]) next_state[lane]=lane_seed(lane);
   end
 end
 integer k;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     held_valid<=0;held_header<=0;held_payload<=0;
     for(k=0;k<4;k=k+1) state[k]<=lane_seed(k);
   end else if(flush_i) begin
     held_valid<=0;held_header<=0;held_payload<=0;
     for(k=0;k<4;k=k+1) state[k]<=lane_seed(k);
   end else if(block_ready_o) begin
     held_valid<=block_valid_i;
     if(block_valid_i) begin
       held_header<=header_i;
       held_payload<=transformed;
       for(k=0;k<4;k=k+1) state[k]<=next_state[k];
     end
   end
 end
 soc_pcie_gen3_gearbox transport (
   .clk_i(clk_i),.rst_ni(rst_ni),.flush_i(flush_i),
   .tx_block_valid_i(active && held_valid),.tx_block_ready_o(gearbox_ready),
   .tx_header_i(held_header),.tx_payload_i(held_payload),
   .tx_word_valid_o(word_valid_o),.tx_word_ready_i(word_ready_i),.tx_word_o(word_o),
   .rx_word_valid_i(1'b0),.rx_word_ready_o(),.rx_word_i(128'b0),
   .rx_block_valid_o(),.rx_block_ready_i(1'b0),.rx_header_o(),.rx_payload_o()
 );
endmodule
