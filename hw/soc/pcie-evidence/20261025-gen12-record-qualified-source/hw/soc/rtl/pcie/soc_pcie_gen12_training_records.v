// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Per-physical-lane transport of complete 16-symbol candidate records.
// Collection is NOT protocol acceptance: all bytes/K/errors/internal COMs survive.
// RX has two complete-record slots; overflow stops new collection until flush,
// while already queued complete records remain drainable.
// TX rejects an illegal K anywhere before exposing any part of the record.
module soc_pcie_gen12_training_records (
 input wire rx_clk_i,rx_rst_ni,rx_enable_i,rx_force_realign_i,rx_polarity_i,rx_raw_valid_i,
 input wire [31:0] rx_raw_i,
 output wire rx_record_valid_o,input wire rx_record_ready_i,
 output wire [127:0] rx_record_data_o,
 output wire [15:0] rx_record_k_o,rx_record_code_error_o,rx_record_disparity_error_o,rx_record_comma_o,
 output reg rx_overflow_o,
 output wire rx_boundary_valid_o,rx_rd_o,
 input wire tx_clk_i,tx_rst_ni,tx_enable_i,tx_flush_i,
 input wire tx_record_valid_i,output wire tx_record_ready_o,
 input wire [127:0] tx_record_data_i,input wire [15:0] tx_record_k_i,
 input wire tx_record_force_negative_rd_i,
 output reg tx_record_error_o,tx_record_queued_o,
 output wire [31:0] tx_raw_o,output wire tx_raw_valid_o,
 input wire tx_raw_ready_i,tx_stream_active_i,
 output wire tx_underflow_o,tx_rd_o,tx_transport_error_o
);
 wire [31:0] rx_batch_data;
 wire [3:0] rx_batch_k,rx_batch_ce,rx_batch_de,rx_batch_comma;
 wire [2:0] rx_batch_count;
 wire rx_acquired;
 soc_pcie_gen12_raw32_rx rx_transport(
  .rx_clk_i(rx_clk_i),.rx_rst_ni(rx_rst_ni),.enable_i(rx_enable_i),
  .force_realign_i(rx_force_realign_i),.polarity_i(rx_polarity_i),
  .raw_valid_i(rx_raw_valid_i),.raw_i(rx_raw_i),
  .data_o(rx_batch_data),.k_o(rx_batch_k),.code_error_o(rx_batch_ce),
  .disparity_error_o(rx_batch_de),.comma_o(rx_batch_comma),
  .symbol_count_o(rx_batch_count),.boundary_valid_o(rx_boundary_valid_o),
  .acquired_o(rx_acquired),.rd_o(rx_rd_o));
 reg rx_previous_polarity;
 wire rx_flush=!rx_enable_i || rx_force_realign_i || rx_polarity_i!=rx_previous_polarity;
 wire rx_active=rx_rst_ni && !rx_flush;
 // Packed candidate: {comma[15:0], disparity[15:0], code[15:0], K[15:0], data[127:0]}.
 reg [191:0] rx_fifo [0:1];
 reg rx_read_ptr,rx_write_ptr;
 reg [1:0] rx_fill;
 reg [4:0] rx_partial_count,rx_next_count;
 reg [191:0] rx_partial,rx_next_partial,rx_complete;
 reg rx_complete_valid;
 integer s;
 always @* begin
  rx_next_count=rx_partial_count;rx_next_partial=rx_partial;
  rx_complete=0;rx_complete_valid=0;
  if(rx_active && !rx_overflow_o)begin
   for(s=0;s<4;s=s+1)begin
    if(s<rx_batch_count)begin
     if(rx_next_count!=0 ||
        (rx_batch_comma[s] && rx_batch_k[s] && !rx_batch_ce[s] && rx_batch_data[s*8+:8]==8'hbc))begin
      rx_next_partial[rx_next_count*8+:8]=rx_batch_data[s*8+:8];
      rx_next_partial[128+rx_next_count]=rx_batch_k[s];
      rx_next_partial[144+rx_next_count]=rx_batch_ce[s];
      rx_next_partial[160+rx_next_count]=rx_batch_de[s];
      rx_next_partial[176+rx_next_count]=rx_batch_comma[s];
      if(rx_next_count==15)begin
       rx_complete=rx_next_partial;rx_complete_valid=1;
       rx_next_count=0;rx_next_partial=0;
      end else rx_next_count=rx_next_count+1'b1;
     end
    end
   end
  end
 end
 assign rx_record_valid_o=rx_active && rx_fill!=0;
 wire [191:0] rx_visible=rx_record_valid_o ? rx_fifo[rx_read_ptr] : 192'b0;
 assign rx_record_data_o=rx_visible[127:0];
 assign rx_record_k_o=rx_visible[143:128];
 assign rx_record_code_error_o=rx_visible[159:144];
 assign rx_record_disparity_error_o=rx_visible[175:160];
 assign rx_record_comma_o=rx_visible[191:176];
 wire rx_pop=rx_record_valid_o && rx_record_ready_i;
 wire [1:0] rx_after_pop=rx_fill-(rx_pop ? 2'd1 : 2'd0);
 wire rx_push=rx_active && !rx_overflow_o && rx_complete_valid && rx_after_pop<2;
 always @(posedge rx_clk_i or negedge rx_rst_ni)begin
  if(!rx_rst_ni)begin
   rx_previous_polarity<=0;rx_read_ptr<=0;rx_write_ptr<=0;rx_fill<=0;
   rx_partial_count<=0;rx_partial<=0;rx_overflow_o<=0;rx_fifo[0]<=0;rx_fifo[1]<=0;
  end else begin
   rx_previous_polarity<=rx_polarity_i;
   if(rx_flush)begin
    rx_read_ptr<=0;rx_write_ptr<=0;rx_fill<=0;
    rx_partial_count<=0;rx_partial<=0;rx_overflow_o<=0;rx_fifo[0]<=0;rx_fifo[1]<=0;
   end else begin
    rx_fill<=rx_after_pop+(rx_push ? 2'd1 : 2'd0);
    if(rx_pop)rx_read_ptr<=!rx_read_ptr;
    if(rx_push)begin rx_fifo[rx_write_ptr]<=rx_complete;rx_write_ptr<=!rx_write_ptr;end
    if(!rx_overflow_o)begin
     if(rx_complete_valid && rx_after_pop==2)begin
      rx_overflow_o<=1;rx_partial_count<=0;rx_partial<=0;
     end else begin rx_partial_count<=rx_next_count;rx_partial<=rx_next_partial;end
    end
   end
  end
 end

 function legal_k;
  input [7:0] value;
  begin
   legal_k=(value[4:0]==5'd28) ||
    (value[7:5]==3'd7 && (value[4:0]==5'd23 || value[4:0]==5'd27 ||
                         value[4:0]==5'd29 || value[4:0]==5'd30));
  end
 endfunction
 reg tx_bad_k;
 integer k;
 always @* begin
  tx_bad_k=0;
  for(k=0;k<16;k=k+1)
   if(tx_record_k_i[k] && !legal_k(tx_record_data_i[k*8+:8]))tx_bad_k=1;
 end
 reg tx_pending,tx_force;
 reg [1:0] tx_group;
 reg [127:0] tx_data;
 reg [15:0] tx_k;
 wire tx_active=tx_rst_ni && tx_enable_i && !tx_flush_i;
 assign tx_record_ready_o=tx_active && !tx_pending;
 wire tx_batch_ready;
 wire tx_batch_error,tx_count_error,tx_k_error;
 wire [6:0] tx_fill;
 soc_pcie_gen12_tx_raw32 tx_transport(
  .tx_clk_i(tx_clk_i),.tx_rst_ni(tx_rst_ni),.enable_i(tx_enable_i),.flush_i(tx_flush_i),
  .batch_valid_i(tx_pending),.batch_ready_o(tx_batch_ready),.count_i(3'd4),
  .data_i(tx_data[tx_group*32+:32]),.k_i(tx_k[tx_group*4+:4]),
  .force_negative_rd_i(tx_force && tx_group==0),
  .raw_o(tx_raw_o),.raw_valid_o(tx_raw_valid_o),.raw_ready_i(tx_raw_ready_i),
  .stream_active_i(tx_stream_active_i),.underflow_o(tx_underflow_o),
  .batch_error_o(tx_batch_error),.count_error_o(tx_count_error),.k_error_o(tx_k_error),
  .rd_o(tx_rd_o),.buffered_bits_o(tx_fill));
 assign tx_transport_error_o=tx_batch_error || tx_count_error || tx_k_error;
 always @(posedge tx_clk_i or negedge tx_rst_ni)begin
  if(!tx_rst_ni)begin
   tx_pending<=0;tx_force<=0;tx_group<=0;tx_data<=0;tx_k<=0;
   tx_record_error_o<=0;tx_record_queued_o<=0;
  end else begin
   tx_record_error_o<=0;tx_record_queued_o<=0;
   if(!tx_enable_i || tx_flush_i)begin
    tx_pending<=0;tx_force<=0;tx_group<=0;tx_data<=0;tx_k<=0;
   end else begin
    if(tx_pending && tx_batch_ready)begin
     if(tx_group==3)begin
      tx_pending<=0;tx_record_queued_o<=1;tx_group<=0;tx_force<=0;
     end else tx_group<=tx_group+1'b1;
    end
    if(tx_record_valid_i && tx_record_ready_o)begin
     if(tx_bad_k)tx_record_error_o<=1;
     else begin
      tx_pending<=1;tx_group<=0;tx_data<=tx_record_data_i;tx_k<=tx_record_k_i;
      tx_force<=tx_record_force_negative_rd_i;
     end
    end
   end
  end
 end
endmodule
`default_nettype wire
