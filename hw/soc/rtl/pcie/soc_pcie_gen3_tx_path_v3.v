// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Four logical lanes, one 128-bit payload and common two-bit header per lane.
// This is a fixed-block TX transport: explicit caller-owned byte policies,
// after-block reseed, scrambling then the real 130/32 gearbox. No automatic
// ordered-set policy, variable SKP, training, CDC, serializer or PMA is implied.
module soc_pcie_gen3_tx_path_v3 (
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
 wire [22:0] next_state [0:3];
 wire [511:0] transformed;
 reg [511:0] held_payload;
 reg [1:0] held_header;
 reg held_valid, pending_valid;
 reg [511:0] pending_payload;
 reg [1:0] pending_header;
 reg [63:0] pending_advance, pending_scramble;
 reg [3:0] pending_reseed;
 reg [4:0] pending_total [0:3];
 reg [4:0] pending_preceding [0:3][0:15];
 wire gearbox_ready;
 wire active=rst_ni && !flush_i;
 wire transform_ready=!held_valid || gearbox_ready;
 assign block_ready_o=active && (!pending_valid || transform_ready);
 // Each byte either advances eight times or holds. Compute the number of
 // preceding advancing bytes in a balanced tree, then select a constant GF(2)
 // transform of the original state. This removes the 128 conditional feedback
 // steps without changing caller-owned hold, XOR or reseed behavior.
 function [4:0] pop16;
   input [15:0] value;
   reg [1:0] pairs [0:7];
   reg [2:0] fours [0:3];
   reg [3:0] eights [0:1];
   integer j;
   begin
     for(j=0;j<8;j=j+1)
       pairs[j]={1'b0,value[2*j]}+{1'b0,value[2*j+1]};
     for(j=0;j<4;j=j+1)
       fours[j]={1'b0,pairs[2*j]}+{1'b0,pairs[2*j+1]};
     for(j=0;j<2;j=j+1)
       eights[j]={1'b0,fours[2*j]}+{1'b0,fours[2*j+1]};
     pop16={1'b0,eights[0]}+{1'b0,eights[1]};
   end
 endfunction
 // Elaboration-only basis expansion; no run-time LFSR chain is synthesized.
 function [22:0] power_mask;
   input integer steps;
   input integer output_bit;
   integer step;
   begin
     power_mask=23'b1<<output_bit;
     // Apply the transpose to the output selector. This is exactly the same
     // GF(2) row as basis expansion, with no 23-way repeated elaboration.
     for(step=0;step<steps;step=step+1)
       power_mask={^(power_mask&23'h210125),power_mask[22:1]};
   end
 endfunction
 genvar lane, count, state_bit, byte_index, bit_index;
 generate for(lane=0;lane<4;lane=lane+1) begin: lanes
   wire [22:0] candidate [0:16];
   wire [7:0] sequence_byte [0:15];
   wire [15:0] advance=pending_advance[lane*16+:16];
   wire [4:0] total=pending_total[lane];
   for(count=0;count<=16;count=count+1) begin: powers
     for(state_bit=0;state_bit<23;state_bit=state_bit+1) begin: bits
       localparam [22:0] MASK=power_mask(8*count,state_bit);
       assign candidate[count][state_bit]=^(state[lane]&MASK);
     end
   end
   for(count=0;count<16;count=count+1) begin: sequences
     for(bit_index=0;bit_index<8;bit_index=bit_index+1) begin: bits
       localparam [22:0] MASK=power_mask(8*count+bit_index,22);
       assign sequence_byte[count][bit_index]=^(state[lane]&MASK);
     end
   end
   for(byte_index=0;byte_index<16;byte_index=byte_index+1) begin: bytes
     wire [4:0] preceding=pending_preceding[lane][byte_index];
     wire [7:0] prng=advance[byte_index] ? sequence_byte[preceding]
                                            : {8{candidate[preceding][22]}};
     assign transformed[lane*128+byte_index*8+:8]=
       pending_payload[lane*128+byte_index*8+:8]^
       (prng&{8{pending_scramble[lane*16+byte_index]}});
   end
   assign next_state[lane]=pending_reseed[lane] ? lane_seed(lane) : candidate[total];
 end endgenerate
 // Register the byte counts before selection. Pending state is consumed only
 // when the output holding register can advance. Simultaneous consume/accept
 // uses the newly advanced LFSR for the next pending block on the next cycle.
 integer k, byte_number;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     pending_valid<=0;pending_payload<=0;pending_header<=0;
     pending_advance<=0;pending_scramble<=0;pending_reseed<=0;
     held_valid<=0;held_header<=0;held_payload<=0;
     for(k=0;k<4;k=k+1) begin
       state[k]<=lane_seed(k);pending_total[k]<=0;
       for(byte_number=0;byte_number<16;byte_number=byte_number+1)
         pending_preceding[k][byte_number]<=0;
     end
   end else if(flush_i) begin
     pending_valid<=0;
     held_valid<=0;held_header<=0;held_payload<=0;
     for(k=0;k<4;k=k+1) state[k]<=lane_seed(k);
   end else begin
     if(transform_ready) begin
       held_valid<=pending_valid;
       if(pending_valid) begin
         held_header<=pending_header;
         held_payload<=transformed;
         for(k=0;k<4;k=k+1) state[k]<=next_state[k];
       end
     end
     if(block_ready_o) begin
       pending_valid<=block_valid_i;
       if(block_valid_i) begin
         pending_payload<=payload_i;pending_header<=header_i;
         pending_advance<=advance_i;pending_scramble<=scramble_i;
         pending_reseed<=reseed_after_i;
         for(k=0;k<4;k=k+1) begin
           pending_total[k]<=pop16(advance_i[k*16+:16]);
           for(byte_number=0;byte_number<16;byte_number=byte_number+1)
             pending_preceding[k][byte_number]<=
               pop16(advance_i[k*16+:16]&((16'h1<<byte_number)-1));
         end
       end
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
