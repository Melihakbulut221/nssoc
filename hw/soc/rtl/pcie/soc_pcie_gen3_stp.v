// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// PCIe Base 4.0 section 4.2.2.3.1, Figure 4-13: logical byte0 in bits7:0.
// The caller validates length; this primitive only encodes the STP token.
module soc_pcie_gen3_stp (
 input wire [10:0] length_dw_i,
 input wire [11:0] sequence_i,
 output wire [31:0] token_o
);
 wire [10:0] l = length_dw_i;
 wire [3:0] c;
 assign c[0] = l[10]^l[7]^l[6]^l[4]^l[2]^l[1]^l[0];
 assign c[1] = l[10]^l[9]^l[7]^l[5]^l[4]^l[3]^l[2];
 assign c[2] = l[9]^l[8]^l[6]^l[4]^l[3]^l[2]^l[1];
 assign c[3] = l[8]^l[7]^l[5]^l[3]^l[2]^l[1]^l[0];
 wire parity = ^{l,c};
 assign token_o = {sequence_i[7:0],c,sequence_i[11:8],
                   parity,l[10:4],l[3:0],4'hf};
endmodule
