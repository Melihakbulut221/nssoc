// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Complete-packet TX framing for an already active x4 Gen3 Data Stream.
// Input TLP: reserved4/sequence[11:8], sequence[7:0], TLP, caller's LCRC.
// Input DLLP: six complete bytes including caller's CRC16.
// Normal 3DW/4DW TLP headers with optional data/digest are supported; no TLP
// Prefix/PMUX. CRC generation, nullification LCRC semantics, replay, ordered
// sets, SKP, LTSSM and PMA scheduling remain outside this module.
// nullify_i is sampled at SOP: append EDB after the COMPLETE supplied TLP;
// it never changes, regenerates or complements any caller-supplied CRC byte.
// Output byte4*k+lane is payload_o[lane*128+k*8+:8]. All unused symbols
// are IDL. The always-valid output holds its registered block during stalls.
module soc_pcie_gen3_framer_tx #(
 parameter integer MAX_ENCODED_BYTES = 150
) (
 input wire clk_i, input wire rst_ni, input wire flush_i,
 input wire [7:0] data_i, input wire valid_i, output wire ready_o,
 input wire sop_i, input wire eop_i, input wire dllp_i,
 input wire error_i, input wire nullify_i,
 output wire block_valid_o, input wire block_ready_i,
 output wire [1:0] header_o, output reg [511:0] payload_o,
 output reg packet_good_o, output reg packet_error_o,
 output wire busy_o
);
 localparam integer BLOCKS = (MAX_ENCODED_BYTES + 6 + 63) / 64;
 localparam integer CW = $clog2(MAX_ENCODED_BYTES + 1);
 localparam integer BW = (BLOCKS < 2) ? 1 : $clog2(BLOCKS + 1);
 localparam [2:0] IDLE=0, RECEIVE=1, DROP=2, EMIT=3, DRAIN=4;
 reg [2:0] state;
 reg [511:0] blocks [0:BLOCKS-1];
 reg [CW-1:0] received;
 reg [BW-1:0] emit_index, emit_blocks;
 reg is_dllp, nullify;
 reg [11:0] sequence_number;
 reg [2:0] fmt;
 reg digest;
 reg [9:0] tlp_length;
 wire active = rst_ni && !flush_i;
 assign ready_o = active && (state==IDLE || state==RECEIVE || state==DROP);
 assign busy_o = state!=IDLE;
 assign block_valid_o = active;
 assign header_o = 2'b10;
 wire [12:0] final_bytes = {1'b0,received} + 13'd1;
 wire [12:0] payload_bytes = !fmt[1] ? 13'd0 :
                              tlp_length==0 ? 13'd4096 : {1'b0,tlp_length,2'b00};
 wire [12:0] expected_bytes = 13'd18 + (fmt[0] ? 13'd4 : 13'd0)
                              + payload_bytes + (digest ? 13'd4 : 13'd0);
 wire [12:0] framed_bytes = final_bytes + 13'd2;
 wire [10:0] framed_dw = framed_bytes[12:2];
 wire [31:0] stp;
 soc_pcie_gen3_stp token(.length_dw_i(framed_dw),
                        .sequence_i(sequence_number),.token_o(stp));
 integer b, k;
 integer symbol_index;
 function integer slot;
  input integer index;
  begin slot = (index % 4)*128 + ((index % 64)/4)*8; end
 endfunction
 // Capacity is explicit. Larger payload testing does not qualify a mapped
 // default-size instance at other parameter values.
 initial begin
  if (MAX_ENCODED_BYTES < 18 || MAX_ENCODED_BYTES > 4118)
   $error("MAX_ENCODED_BYTES must be18..4118");
 end
 always @(posedge clk_i or negedge rst_ni) begin
  if (!rst_ni) begin
   state<=IDLE; received<=0; emit_index<=0; emit_blocks<=0;
   is_dllp<=0; nullify<=0; sequence_number<=0; fmt<=0; digest<=0; tlp_length<=0;
   payload_o<=0; packet_good_o<=0; packet_error_o<=0;
  end else if (flush_i) begin
   state<=IDLE; received<=0; emit_index<=0; emit_blocks<=0;
   is_dllp<=0; nullify<=0; sequence_number<=0; fmt<=0; digest<=0; tlp_length<=0;
   payload_o<=0; packet_good_o<=0; packet_error_o<=0;
  end else begin
   packet_good_o<=0; packet_error_o<=0;
   if (block_ready_i) begin
    if (state==EMIT) begin
     payload_o<=blocks[emit_index];
     emit_index<=emit_index+1'b1;
     if (emit_index+1'b1==emit_blocks) state<=DRAIN;
    end else begin
     payload_o<=0;
     if (state==DRAIN) state<=IDLE;
    end
   end
   if (valid_i && ready_o) begin
    if (sop_i) begin
     // A new SOP replaces a partial frame, with an explicit old-frame error.
     if (state==RECEIVE) packet_error_o<=1;
     received<=1; is_dllp<=dllp_i; nullify<=nullify_i;
     sequence_number<={data_i[3:0],8'b0}; fmt<=0; digest<=0; tlp_length<=0;
     emit_index<=0; emit_blocks<=0;
     for (b=0;b<BLOCKS;b=b+1) blocks[b]<=0;
     if (dllp_i) begin
      blocks[0][0+:8]<=8'hf0;
      blocks[0][128+:8]<=8'hac;
      blocks[0][256+:8]<=data_i;
     end
     if (error_i || eop_i || (dllp_i && nullify_i) ||
         (!dllp_i && data_i[7:4]!=0)) begin
      packet_error_o<=1; state<=eop_i ? IDLE : DROP;
     end else state<=RECEIVE;
    end else if (state==RECEIVE) begin
     if (error_i || dllp_i!=is_dllp || received>=MAX_ENCODED_BYTES) begin
      packet_error_o<=1; state<=eop_i ? IDLE : DROP;
     end else begin
      received<=received+1'b1;
      if (!is_dllp) begin
       if (received==1) sequence_number[7:0]<=data_i;
       if (received==2) fmt<=data_i[7:5];
       if (received==4) begin digest<=data_i[7]; tlp_length[9:8]<=data_i[1:0]; end
       if (received==5) tlp_length[7:0]<=data_i;
      end
      if (is_dllp || received>=2) begin
       symbol_index=received+2;
       blocks[symbol_index/64][slot(symbol_index)+:8]<=data_i;
      end
      if (eop_i) begin
       if ((is_dllp && final_bytes!=6) ||
           (!is_dllp && (final_bytes<18 || framed_bytes[1:0]!=0 ||
                        fmt[2] || final_bytes!=expected_bytes))) begin
        packet_error_o<=1; state<=IDLE;
       end else begin
        if (!is_dllp) begin
         for (k=0;k<4;k=k+1) blocks[0][k*128+:8]<=stp[k*8+:8];
         if (nullify) begin
          for (k=0;k<4;k=k+1) begin
           symbol_index=framed_bytes+k;
           blocks[symbol_index/64][slot(symbol_index)+:8]<=8'hc0;
          end
         end
        end
        emit_blocks<=(framed_bytes+(!is_dllp && nullify ? 4 : 0)+63)/64;
        emit_index<=0; state<=EMIT; packet_good_o<=1;
       end
      end
     end
    end else if (state==DROP) begin
     if (eop_i) state<=IDLE;
    end else begin
     packet_error_o<=1; state<=eop_i ? IDLE : DROP;
    end
   end
  end
 end
endmodule
