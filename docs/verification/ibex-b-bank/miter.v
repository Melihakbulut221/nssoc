// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
module m(input [1023:0] data,input [255:0] checks,syndromes,input [4:0] raddr_b_i,output ok);
localparam CHK_W=8, NUM_WORDS=32;
genvar gj;
wire [31:0] rf_data[0:31]; wire [7:0] rf_chk[0:31],rf_syn[0:31];wire [7:0] use_syn_b;
for(gj=0;gj<32;gj=gj+1) begin
assign rf_data[gj]=data[gj*32+:32]; assign rf_chk[gj]=checks[gj*8+:8]; assign rf_syn[gj]=syndromes[gj*8+:8];
end
    wire [31:0] raw_b;
    wire [CHK_W-1:0] chk_b;
    wire [31+CHK_W:0] b_even [0:NUM_WORDS/2-1];
    wire [31+CHK_W:0] b_odd [0:NUM_WORDS/2-1];
    for (gj = 0; gj < NUM_WORDS/2; gj = gj + 1) begin : g_b_bank
      assign b_even[gj] = {rf_chk[2*gj], rf_data[2*gj]};
      assign b_odd[gj] = {rf_chk[2*gj+1], rf_data[2*gj+1]};
    end
    wire [31+CHK_W:0] b_pair [0:1];
    assign b_pair[0] = b_even[raddr_b_i[4:1]];
    assign b_pair[1] = b_odd[raddr_b_i[4:1]];
    assign {chk_b, raw_b} = b_pair[raddr_b_i[0]];
          wire [CHK_W-1:0] syn_even [0:NUM_WORDS/2-1];
          wire [CHK_W-1:0] syn_odd [0:NUM_WORDS/2-1];
          for (gj = 0; gj < NUM_WORDS/2; gj = gj + 1) begin : g_b_syn_bank
            assign syn_even[gj] = rf_syn[2*gj];
            assign syn_odd[gj] = rf_syn[2*gj+1];
          end
          wire [CHK_W-1:0] syn_pair [0:1];
          assign syn_pair[0] = syn_even[raddr_b_i[4:1]];
          assign syn_pair[1] = syn_odd[raddr_b_i[4:1]];
          assign use_syn_b = syn_pair[raddr_b_i[0]];
assign ok=({raw_b,chk_b,use_syn_b}=={rf_data[raddr_b_i],rf_chk[raddr_b_i],rf_syn[raddr_b_i]});endmodule
