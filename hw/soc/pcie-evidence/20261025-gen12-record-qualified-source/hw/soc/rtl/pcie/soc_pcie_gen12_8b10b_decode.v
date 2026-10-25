// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// A symbol is already aligned: code_i[0] is wire-first a.
// Invalid code has precedence: deterministic zero data/K, no additional
// disparity assertion. RD advances from the received 6b then 4b sub-blocks
// even on invalid codes, as required for receive-error recovery.
// No comma acquisition, link-state inference or error suppression is implied.
module soc_pcie_gen12_8b10b_decode (
 input wire [9:0] code_i, input wire rd_i,
 output wire [7:0] data_o, output wire k_o, rd_o,
 output wire code_error_o, disparity_error_o
);
 wire [8:0] decoded;
 wire unused_native_rd, bad_code, bad_disparity;
 nssoc_benz_8b10b_decode native_codec(
  .datain(code_i),.dispin(rd_i),.dataout(decoded),.dispout(unused_native_rd),
  .code_err(bad_code),.disp_err(bad_disparity));
 wire [2:0] ones6={2'b0,code_i[0]}+{2'b0,code_i[1]}+
   {2'b0,code_i[2]}+{2'b0,code_i[3]}+{2'b0,code_i[4]}+{2'b0,code_i[5]};
 wire [2:0] ones4={2'b0,code_i[6]}+{2'b0,code_i[7]}+
   {2'b0,code_i[8]}+{2'b0,code_i[9]};
 // Constants are reversed relative to printed wire-first abcdei/fghj tables.
 wire rd6=(ones6>3'd3 || code_i[5:0]==6'b111000) ? 1'b1 :
   (ones6<3'd3 || code_i[5:0]==6'b000111) ? 1'b0 : rd_i;
 assign rd_o=(ones4>3'd2 || code_i[9:6]==4'b1100) ? 1'b1 :
   (ones4<3'd2 || code_i[9:6]==4'b0011) ? 1'b0 : rd6;
 assign code_error_o=bad_code;
 assign disparity_error_o=!bad_code && bad_disparity;
 assign data_o=bad_code ? 8'b0 : decoded[7:0];
 assign k_o=!bad_code && decoded[8];
endmodule
`default_nettype wire
