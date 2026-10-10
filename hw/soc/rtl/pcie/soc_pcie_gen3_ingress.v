// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Continuous x4 recovered-word ingress, 32 serial bits/lane/cycle, LSB first.
// start_i discards its current word and establishes bit0 of the NEXT word as
// a block boundary. It is an explicit externally aligned/deskewed epoch.
// A full FIFO cannot pause the PMA: overflow halts and invalidates the epoch.
// Fixed130 blocks only: no variable SKP, alignment search, deskew or CDC.
module soc_pcie_gen3_ingress #(
 parameter integer FIFO_DEPTH=4
)(
 input wire clk_i, input wire rst_ni, input wire flush_i, input wire start_i,
 input wire [127:0] word_i,
 output wire block_valid_o, input wire block_ready_i,
 output wire [7:0] headers_o, output wire [511:0] payload_o,
 output wire active_o, output reg overflow_o
);
 localparam integer PTR_W=(FIFO_DEPTH>1) ? $clog2(FIFO_DEPTH) : 1;
 localparam integer COUNT_W=$clog2(FIFO_DEPTH+1);
 reg running;
 reg [7:0] residual_count;
 reg [127:0] residual [0:3];
 reg [519:0] blocks [0:FIFO_DEPTH-1];
 reg [PTR_W-1:0] rd_ptr,wr_ptr;
 reg [COUNT_W-1:0] queued;
 wire enabled=rst_ni && !flush_i && !start_i && running;
 assign active_o=enabled;
 assign block_valid_o=enabled && queued!=0;
 assign headers_o=blocks[rd_ptr][7:0];
 assign payload_o=blocks[rd_ptr][519:8];
 wire pop=block_valid_o && block_ready_i;
 wire complete_block=residual_count>=8'd98;
 wire room=queued<FIFO_DEPTH || pop;
 wire push=enabled && complete_block && room;
 wire fault=enabled && complete_block && !room;
 wire [7:0] next_count=residual_count+8'd32;
 wire [159:0] assembled [0:3];
 wire [519:0] completed;
 genvar lane;
 generate for(lane=0;lane<4;lane=lane+1) begin: lanes
   assign assembled[lane]={32'b0,residual[lane]} |
     ({128'b0,word_i[lane*32+:32]}<<residual_count);
   assign completed[lane*2+:2]=assembled[lane][1:0];
   assign completed[8+lane*128+:128]=assembled[lane][129:2];
 end endgenerate
 integer k;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     running<=0;overflow_o<=0;residual_count<=0;
     queued<=0;rd_ptr<=0;wr_ptr<=0;
     for(k=0;k<4;k=k+1) residual[k]<=0;
   end else if(flush_i || start_i) begin
     running<=start_i && !flush_i;overflow_o<=0;residual_count<=0;
     queued<=0;rd_ptr<=0;wr_ptr<=0;
     for(k=0;k<4;k=k+1) residual[k]<=0;
   end else if(fault) begin
     running<=0;overflow_o<=1;residual_count<=0;
     queued<=0;rd_ptr<=0;wr_ptr<=0;
     for(k=0;k<4;k=k+1) residual[k]<=0;
   end else if(enabled) begin
     residual_count<=next_count-(complete_block ? 8'd130 : 8'd0);
     for(k=0;k<4;k=k+1)
       residual[k]<=complete_block ? assembled[k]>>130 : assembled[k][127:0];
     case({push,pop})
       2'b10:queued<=queued+1'b1;
       2'b01:queued<=queued-1'b1;
       default:queued<=queued;
     endcase
     if(push) begin
       blocks[wr_ptr]<=completed;
       wr_ptr<=(wr_ptr==FIFO_DEPTH-1) ? 0 : wr_ptr+1'b1;
     end
     if(pop) rd_ptr<=(rd_ptr==FIFO_DEPTH-1) ? 0 : rd_ptr+1'b1;
   end
 end
endmodule
