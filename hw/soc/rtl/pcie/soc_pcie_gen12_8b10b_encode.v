// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Bit 0 is wire-first a; code[9:0]={j,h,g,f,i,e,d,c,b,a}.
// Explicit RD: 0 negative, 1 positive. Invalid K is never emitted.
module soc_pcie_gen12_8b10b_encode (
 input wire [7:0] data_i, input wire k_i, rd_i,
 output wire [9:0] code_o, output wire rd_o, k_error_o
);
 wire [9:0] encoded;
 wire next_rd;
 wire legal_k=(data_i[4:0]==5'd28) ||
   (data_i[7:5]==3'd7 && (data_i[4:0]==5'd23 ||
    data_i[4:0]==5'd27 || data_i[4:0]==5'd29 || data_i[4:0]==5'd30));
 nssoc_benz_8b10b_encode native_codec(
  .datain({k_i,data_i}),.dispin(rd_i),.dataout(encoded),.dispout(next_rd));
 assign k_error_o=k_i && !legal_k;
 assign code_o=k_error_o ? 10'b0 : encoded;
 assign rd_o=k_error_o ? rd_i : next_rd;
endmodule
`default_nettype wire
