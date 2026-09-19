// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

module soc_can (
    input wire clk_i, rst_ni,
    input wire psel_i, penable_i, pwrite_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i,
    input wire [3:0] pstrb_i,
    output wire [31:0] prdata_o,
    output wire pready_o, pslverr_o,
    input wire rx_i,
    output wire tx_o, irq_o, bus_off_o
);
    wire cyc, stb, we, ack, irq_n, bus_off_n;
    wire [11:0] addr;
    wire [7:0] wdata, rdata;
    wire legal = paddr_i[11:8] == 0 &&
        (pstrb_i == 1 || pstrb_i == 2 || pstrb_i == 4 || pstrb_i == 8);
    wire ready, err;
    soc_apb_wb u_bridge (
        .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i && legal),
        .penable_i(penable_i), .paddr_i(paddr_i), .pwrite_i(pwrite_i),
        .pwdata_i(pwdata_i), .pstrb_i(pstrb_i), .prdata_o(prdata_o),
        .pready_o(ready), .pslverr_o(err), .cyc_o(cyc), .stb_o(stb),
        .we_o(we), .adr_o(addr), .dat_o(wdata), .sel_o(),
        .dat_i(rdata), .ack_i(ack), .err_i(1'b0), .rty_i(1'b0));
    assign pready_o = legal ? ready : 1'b1;
    assign pslverr_o = legal ? err : (psel_i && penable_i);
    assign irq_o = !irq_n;
    assign bus_off_o = !bus_off_n;
    can_top u_can (
        .wb_clk_i(clk_i), .wb_rst_i(!rst_ni), .wb_dat_i(wdata),
        .wb_dat_o(rdata), .wb_cyc_i(cyc), .wb_stb_i(stb), .wb_we_i(we),
        .wb_adr_i(addr[7:0]), .wb_ack_o(ack), .clk_i(clk_i),
        .rx_i(rx_i), .tx_o(tx_o), .bus_off_on(bus_off_n),
        .irq_on(irq_n), .clkout_o());
endmodule
