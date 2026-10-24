// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// One accepted batch contains1..4 symbols. Slot0/bit0 is earliest.
// No fall-through: input accepted at edgeN becomes eligible at edgeN+1.
// Rejected batches append nothing and preserve RD; independent output pop
// still retires the existing word. force_negative_rd_i belongs to the batch.
// stream_active_i qualifies underflow demand only, never invents a word.
module soc_pcie_gen12_tx_raw32 (
 input wire tx_clk_i,tx_rst_ni,enable_i,flush_i,
 input wire batch_valid_i,
 output wire batch_ready_o,
 input wire [2:0] count_i,
 input wire [31:0] data_i,
 input wire [3:0] k_i,
 input wire force_negative_rd_i,
 output wire [31:0] raw_o,
 output wire raw_valid_o,
 input wire raw_ready_i,stream_active_i,
 output wire underflow_o,
 output reg batch_error_o,count_error_o,k_error_o,
 output reg rd_o,
 output wire [6:0] buffered_bits_o
);
 reg [71:0] fifo_q;
 reg [6:0] count_q;
 wire [39:0] encoded,selected;
 wire [3:0] encoder_error,next_rd;
 wire [4:0] chain_rd;
 assign chain_rd[0]=force_negative_rd_i ? 1'b0 : rd_o;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:encoders
  soc_pcie_gen12_8b10b_encode enc(
   .data_i(data_i[g*8+:8]),.k_i(k_i[g]),.rd_i(chain_rd[g]),
   .code_o(encoded[g*10+:10]),.rd_o(next_rd[g]),.k_error_o(encoder_error[g]));
  assign chain_rd[g+1]=(count_i>g) ? next_rd[g] : chain_rd[g];
  assign selected[g*10+:10]=(count_i>g) ? encoded[g*10+:10] : 10'b0;
 end endgenerate
 wire bad_count=(count_i<1 || count_i>4);
 wire bad_k=(count_i>0 && encoder_error[0]) ||
            (count_i>1 && encoder_error[1]) ||
            (count_i>2 && encoder_error[2]) ||
            (count_i>3 && encoder_error[3]);
 wire bad=bad_count || bad_k;
 wire active=tx_rst_ni && enable_i && !flush_i;
 assign raw_valid_o=active && count_q>=7'd32;
 assign raw_o=raw_valid_o ? fifo_q[31:0] : 32'b0;
 wire pop=raw_valid_o && raw_ready_i;
 wire [6:0] after_pop=count_q-(pop ? 7'd32 : 7'd0);
 wire [6:0] input_bits={4'b0,count_i}*7'd10;
 wire [6:0] free_bits=7'd72-after_pop;
 // Invalid requests are consumed/reported even when no payload space exists.
 assign batch_ready_o=active && (bad || free_bits>=input_bits);
 wire request=batch_valid_i && batch_ready_o;
 wire push=request && !bad;
 assign underflow_o=active && stream_active_i && raw_ready_i && !raw_valid_o;
 assign buffered_bits_o=count_q;
 wire [71:0] after_pop_bits=pop ? (fifo_q>>32) : fifo_q;
 wire [71:0] append_bits={32'b0,selected}<<after_pop;
 always @(posedge tx_clk_i or negedge tx_rst_ni)begin
  if(!tx_rst_ni)begin
   fifo_q<=0;count_q<=0;rd_o<=0;
   batch_error_o<=0;count_error_o<=0;k_error_o<=0;
  end else begin
   batch_error_o<=0;count_error_o<=0;k_error_o<=0;
   if(!enable_i || flush_i)begin
    fifo_q<=0;count_q<=0;rd_o<=0;
   end else begin
    fifo_q<=after_pop_bits;count_q<=after_pop;
    if(push)begin
     fifo_q<=after_pop_bits | append_bits;
     count_q<=after_pop+input_bits;
     rd_o<=chain_rd[4];
    end
    if(request && bad)begin
     batch_error_o<=1;
     count_error_o<=bad_count;
     k_error_o<=!bad_count && bad_k;
    end
   end
  end
 end
endmodule
`default_nettype wire
