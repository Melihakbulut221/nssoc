// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_soc_interfaces (
    input wire clk_i, rst_ni, psel_i, penable_i, pwrite_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i,
    input wire [3:0] pstrb_i,
    input wire [2:0] dev_i,
    output wire [31:0] prdata_o,
    output wire pready_o, pslverr_o,
    input wire scl_hold_i, sda_hold_i, spw_disconnect_i,
    input wire spi_external_i, spi_miso_i,
    output wire scl, sda, spi_sck, spi_mosi,
    output wire [1:0] spi_cs,
    output wire [5:0] irq,
    output wire can_bus,
    output wire lgpl_profile_o
);
wire scl_oe, sda_oe;
assign scl = !(scl_oe || scl_hold_i);
assign sda = !(sda_oe || sda_hold_i);
wire [1:0] spw_d, spw_s, can_tx;
assign can_bus = &can_tx;
wire [31:0] data [0:5];
wire [5:0] ready, err;
assign prdata_o = data[dev_i];
assign pready_o = ready[dev_i];
assign pslverr_o = err[dev_i];
soc_i2c #(.TIMEOUT_CYCLES(12000)) u_i2c0 (
 .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i && dev_i == 3'd0),
 .penable_i(penable_i), .pwrite_i(pwrite_i), .paddr_i(paddr_i),
 .pwdata_i(pwdata_i), .pstrb_i(pstrb_i), .prdata_o(data[0]),
 .pready_o(ready[0]), .pslverr_o(err[0]), .irq_o(irq[0]), .scl_i(scl), .sda_i(sda), .scl_oe_o(scl_oe), .sda_oe_o(sda_oe));
soc_spi u_spi1 (
 .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i && dev_i == 3'd1),
 .penable_i(penable_i), .pwrite_i(pwrite_i), .paddr_i(paddr_i),
 .pwdata_i(pwdata_i), .pstrb_i(pstrb_i), .prdata_o(data[1]),
 .pready_o(ready[1]), .pslverr_o(err[1]), .irq_o(irq[1]), .miso_i(spi_external_i ? spi_miso_i : spi_mosi), .mosi_o(spi_mosi), .sck_o(spi_sck), .cs_no(spi_cs));
`ifdef SOC_LGPL_INTERFACES
assign lgpl_profile_o = 1'b1;
soc_spw u_spw2 (
 .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i && dev_i == 3'd2),
 .penable_i(penable_i), .pwrite_i(pwrite_i), .paddr_i(paddr_i),
 .pwdata_i(pwdata_i), .pstrb_i(pstrb_i), .prdata_o(data[2]),
 .pready_o(ready[2]), .pslverr_o(err[2]), .irq_o(irq[2]), .di_i(spw_disconnect_i ? 1'b0 : spw_d[1]), .si_i(spw_disconnect_i ? 1'b0 : spw_s[1]), .do_o(spw_d[0]), .so_o(spw_s[0]));
soc_can u_can3 (
 .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i && dev_i == 3'd3),
 .penable_i(penable_i), .pwrite_i(pwrite_i), .paddr_i(paddr_i),
 .pwdata_i(pwdata_i), .pstrb_i(pstrb_i), .prdata_o(data[3]),
 .pready_o(ready[3]), .pslverr_o(err[3]), .irq_o(irq[3]), .rx_i(can_bus), .tx_o(can_tx[0]), .bus_off_o());
soc_can u_can4 (
 .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i && dev_i == 3'd4),
 .penable_i(penable_i), .pwrite_i(pwrite_i), .paddr_i(paddr_i),
 .pwdata_i(pwdata_i), .pstrb_i(pstrb_i), .prdata_o(data[4]),
 .pready_o(ready[4]), .pslverr_o(err[4]), .irq_o(irq[4]), .rx_i(can_bus), .tx_o(can_tx[1]), .bus_off_o());
soc_spw u_spw5 (
 .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i && dev_i == 3'd5),
 .penable_i(penable_i), .pwrite_i(pwrite_i), .paddr_i(paddr_i),
 .pwdata_i(pwdata_i), .pstrb_i(pstrb_i), .prdata_o(data[5]),
 .pready_o(ready[5]), .pslverr_o(err[5]), .irq_o(irq[5]), .di_i(spw_disconnect_i ? 1'b0 : spw_d[0]), .si_i(spw_disconnect_i ? 1'b0 : spw_s[0]), .do_o(spw_d[1]), .so_o(spw_s[1]));
`else
assign lgpl_profile_o = 1'b0;
assign can_tx = 2'b11;
assign spw_d = 2'b00;
assign spw_s = 2'b00;
assign irq[5:2] = 4'd0;
assign ready[5:2] = 4'hf;
assign err[5:2] = 4'hf;
assign data[2] = 32'd0;
assign data[3] = 32'd0;
assign data[4] = 32'd0;
assign data[5] = 32'd0;
`endif
endmodule
