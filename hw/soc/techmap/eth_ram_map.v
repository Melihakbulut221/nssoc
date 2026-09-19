// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
module $__SOC_ETH_RAM_ (
    input PORT_W_CLK, PORT_W_WR_EN,
    input [7:0] PORT_W_ADDR,
    input [15:0] PORT_W_WR_DATA,
    input PORT_R_CLK, PORT_R_RD_EN,
    input [7:0] PORT_R_ADDR,
    output [15:0] PORT_R_RD_DATA
);
RM_IHPSG13_2P_256x16_c2_bm_bist _TECHMAP_REPLACE_ (
    .A_CLK(PORT_W_CLK), .A_MEN(PORT_W_WR_EN), .A_WEN(PORT_W_WR_EN), .A_REN(1'b0),
    .A_ADDR(PORT_W_ADDR), .A_DIN(PORT_W_WR_DATA), .A_BM(16'hffff), .A_DLY(1'b0), .A_DOUT(),
    .A_BIST_CLK(1'b0), .A_BIST_EN(1'b0), .A_BIST_MEN(1'b0), .A_BIST_WEN(1'b0),
    .A_BIST_REN(1'b0), .A_BIST_ADDR(8'b0), .A_BIST_DIN(16'b0), .A_BIST_BM(16'b0),
    .B_CLK(PORT_R_CLK), .B_MEN(PORT_R_RD_EN), .B_REN(PORT_R_RD_EN), .B_WEN(1'b0),
    .B_ADDR(PORT_R_ADDR), .B_DIN(16'b0), .B_BM(16'b0), .B_DLY(1'b0), .B_DOUT(PORT_R_RD_DATA),
    .B_BIST_CLK(1'b0), .B_BIST_EN(1'b0), .B_BIST_MEN(1'b0), .B_BIST_WEN(1'b0),
    .B_BIST_REN(1'b0), .B_BIST_ADDR(8'b0), .B_BIST_DIN(16'b0), .B_BIST_BM(16'b0)
);
endmodule
