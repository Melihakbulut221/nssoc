// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Four-lane bit-preserving TX transport, bit0 first. Length codes0..4 mean
// 66/98/130/162/194 total bits, including the unchanged two-bit sync header.
// Normal blocks use code2; the other lengths accommodate variable SKP payloads.
// The caller owns legal ordered-set content, header selection and scrambling.
// This does not insert/remove SKP, compensate clock rates or implement RX PCS.
module soc_pcie_gen3_variable_tx (
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire block_valid_i, output wire block_ready_o,
 input wire [2:0] length_code_i,
 input wire [1:0] header_i, input wire [767:0] payload_i,
 output wire length_error_o,
 output wire word_valid_o, input wire word_ready_i,
 output wire [127:0] word_o
);
 reg [255:0] bits [0:3];
 reg [8:0] count;
 reg [8:0] block_bits;
 reg [193:0] mask;
 always @* begin
   case(length_code_i)
     3'd0:begin block_bits=9'd66;mask={128'b0,{66{1'b1}}};end
     3'd1:begin block_bits=9'd98;mask={96'b0,{98{1'b1}}};end
     3'd2:begin block_bits=9'd130;mask={64'b0,{130{1'b1}}};end
     3'd3:begin block_bits=9'd162;mask={32'b0,{162{1'b1}}};end
     3'd4:begin block_bits=9'd194;mask={194{1'b1}};end
     default:begin block_bits=0;mask=0;end
   endcase
 end
 wire active=rst_ni && !flush_i;
 wire legal=length_code_i<=3'd4;
 assign length_error_o=active && block_valid_i && !legal;
 assign word_valid_o=active && count>=9'd32;
 wire pop=word_valid_o && word_ready_i;
 wire [8:0] left=count-(pop ? 9'd32 : 9'd0);
 // A ten-bit sum prevents wraparound from manufacturing free space.
 assign block_ready_o=active && legal && ({1'b0,left}+{1'b0,block_bits}<=10'd256);
 wire push=block_valid_i && block_ready_o;
 genvar g;
 generate for(g=0;g<4;g=g+1) begin: lanes
   assign word_o[g*32+:32]=bits[g][31:0];
 end endgenerate
 integer lane;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     count<=0;
     for(lane=0;lane<4;lane=lane+1) bits[lane]<=0;
   end else if(flush_i) begin
     count<=0;
     for(lane=0;lane<4;lane=lane+1) bits[lane]<=0;
   end else begin
     count<=left+(push ? block_bits : 9'd0);
     for(lane=0;lane<4;lane=lane+1)
       bits[lane]<=(pop ? bits[lane]>>32 : bits[lane]) |
         (push ? ({62'b0,({payload_i[lane*192+:192],header_i}&mask)}<<left) : 256'b0);
   end
 end
endmodule
