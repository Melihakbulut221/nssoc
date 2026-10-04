// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Four logical lanes0..3, 32 payload bits per lane, bit0 first.
// G(x)=x^23+x^21+x^16+x^8+x^5+x^2+1; additive XOR also descrambles.
// Caller supplies byte advance/XOR masks and after-word EIEOS reseed events.
// Headers are outside this interface. No ordered-set classifier, DC-balance
// policy, lane assignment/deskew, LTSSM, block framing or serial PHY is supplied.
module soc_pcie_gen3_scrambler (
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire valid_i, output wire ready_o,
 input wire [127:0] data_i,
 input wire [15:0] advance_i, input wire [15:0] scramble_i,
 input wire [3:0] reseed_after_i,
 output wire valid_o, input wire ready_i,
 output wire [127:0] data_o
);
 function [22:0] seed;
   input integer lane;
   begin
     case(lane)
       0:seed=23'h1dbfbc;
       1:seed=23'h0607bb;
       2:seed=23'h1ec760;
       default:seed=23'h18c0db;
     endcase
   end
 endfunction
 reg [22:0] state [0:3];
 reg [22:0] next_state [0:3];
 reg [127:0] transformed;
 reg [127:0] held_data;
 reg held_valid;
 wire active=rst_ni && !flush_i;
 assign valid_o=active && held_valid;
 assign ready_o=active && (!held_valid || ready_i);
 assign data_o=held_data;
 integer lane, bit_index;
 always @* begin
   transformed=data_i;
   for(lane=0;lane<4;lane=lane+1) begin
     next_state[lane]=state[lane];
     for(bit_index=0;bit_index<32;bit_index=bit_index+1) begin
       if(scramble_i[lane*4+bit_index/8])
         transformed[lane*32+bit_index]=data_i[lane*32+bit_index]^next_state[lane][22];
       if(advance_i[lane*4+bit_index/8])
         next_state[lane]={next_state[lane][21:0],1'b0}^
           (next_state[lane][22] ? 23'h210125 : 23'b0);
     end
     if(reseed_after_i[lane]) next_state[lane]=seed(lane);
   end
 end
 integer k;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     held_valid<=0;held_data<=0;
     for(k=0;k<4;k=k+1) state[k]<=seed(k);
   end else if(flush_i) begin
     held_valid<=0;held_data<=0;
     for(k=0;k<4;k=k+1) state[k]<=seed(k);
   end else if(ready_o) begin
     held_valid<=valid_i;
     if(valid_i) begin
       held_data<=transformed;
       for(k=0;k<4;k=k+1) state[k]<=next_state[k];
     end
   end
 end
endmodule
