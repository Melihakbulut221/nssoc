// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Reset cone extracted from soc_top at 510483547a81a5ccc124fe00e0c81f31f1f520f7.
module soc_pcie_packet_reset(pcie_clk_i, rst_sys_n, packet_rst_n, release_state);
input wire pcie_clk_i, rst_sys_n;
output packet_rst_n;
output wire [1:0] release_state;
  (* ASYNC_REG="TRUE" *) reg [1:0] packet_reset_release;
  always @(posedge pcie_clk_i or negedge rst_sys_n)
    if(!rst_sys_n) packet_reset_release<=0;
    else packet_reset_release<={packet_reset_release[0],1'b1};
  wire packet_rst_n=rst_sys_n && packet_reset_release[1];
assign release_state=packet_reset_release;
endmodule
