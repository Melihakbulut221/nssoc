// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Whole active-Data-Stream blocks. All128 bits/lane advance and XOR.
// A new SDS-owned epoch externally flushes to the lane seeds. Raw headers pass
// unchanged; the consumer must reject non-Data Blocks. No OS policy is implied.
module soc_pcie_gen3_data_descrambler (
 input wire clk_i,rst_ni,flush_i,
 input wire valid_i,output wire ready_o,
 input wire [7:0] headers_i,input wire [511:0] payload_i,
 output wire valid_o,input wire ready_i,
 output reg [7:0] headers_o,output reg [511:0] payload_o
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
 function [22:0] mask;
   input integer steps,bit_number;
   integer n;
   begin
     mask=23'b1<<bit_number;
     for(n=0;n<steps;n=n+1) mask={^(mask&23'h210125),mask[22:1]};
   end
 endfunction
 reg [22:0] state [0:3];
 reg held;
 wire [511:0] decoded;
 wire [22:0] advanced [0:3];
 wire enabled=rst_ni && !flush_i;
 assign ready_o=enabled && (!held || ready_i);
 assign valid_o=enabled && held;
 genvar lane,bit_number;
 generate for(lane=0;lane<4;lane=lane+1) begin: lanes
   for(bit_number=0;bit_number<128;bit_number=bit_number+1) begin: data_bits
     assign decoded[lane*128+bit_number]=payload_i[lane*128+bit_number]^
       ^(state[lane]&mask(bit_number,22));
   end
   for(bit_number=0;bit_number<23;bit_number=bit_number+1) begin: state_bits
     assign advanced[lane][bit_number]=^(state[lane]&mask(128,bit_number));
   end
 end endgenerate
 integer k;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     held<=0;headers_o<=0;payload_o<=0;
     for(k=0;k<4;k=k+1) state[k]<=seed(k);
   end else if(flush_i) begin
     held<=0;headers_o<=0;payload_o<=0;
     for(k=0;k<4;k=k+1) state[k]<=seed(k);
   end else if(ready_o) begin
     held<=valid_i;
     if(valid_i) begin
       headers_o<=headers_i;payload_o<=decoded;
       for(k=0;k<4;k=k+1) state[k]<=advanced[k];
     end
   end
 end
endmodule
