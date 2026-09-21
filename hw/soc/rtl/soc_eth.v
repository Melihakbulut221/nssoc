// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
`default_nettype none
// Gigabit-only GMII MAC, full duplex, external PHY and 125 MHz clocks.
// Packet bytes cross through upstream frame-aware asynchronous FIFOs.
// The 50 MHz APB PIO port cannot sustain wire-rate traffic indefinitely.
module soc_eth #(
    parameter integer FIFO_DEPTH = 2048
) (
    input wire clk_i, rst_ni,
    input wire psel_i, penable_i, pwrite_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i,
    input wire [3:0] pstrb_i,
    output reg [31:0] prdata_o,
    output wire pready_o,
    output wire pslverr_o,
    output wire irq_o,
    input wire rx_clk_i, tx_clk_i,
    input wire [7:0] rxd_i,
    input wire rx_dv_i, rx_er_i,
    output wire [7:0] txd_o,
    output wire tx_en_o, tx_er_o,
    // Software-controlled PHY management pins. MDIO input is synchronized.
    output wire mdc_o, mdio_o, mdio_oe_o,
    input wire mdio_i
);
localparam [11:0] R_CTRL = 12'h000; // regmap:eth:CTRL
localparam [11:0] R_STATUS = 12'h004; // regmap:eth:STATUS
localparam [11:0] R_TX = 12'h008; // regmap:eth:TX
localparam [11:0] R_RX = 12'h00C; // regmap:eth:RX
localparam [11:0] R_EVENTS = 12'h010; // regmap:eth:EVENTS
localparam [11:0] R_IRQEN = 12'h014; // regmap:eth:IRQEN
localparam [11:0] R_MDIO = 12'h018; // regmap:eth:MDIO
localparam [11:0] R_ID = 12'h0FC; // regmap:eth:ID
reg [1:0] enable_q;
reg flush_q;
wire mac_rst_n = rst_ni && !flush_q;
// Asynchronous assertion, synchronous release independently in all domains.
(* ASYNC_REG = "TRUE" *) reg [1:0] rx_reset, tx_reset, logic_reset;
always @(posedge rx_clk_i or negedge mac_rst_n)
    if (!mac_rst_n) rx_reset <= 2'b11; else rx_reset <= {rx_reset[0],1'b0};
always @(posedge tx_clk_i or negedge mac_rst_n)
    if (!mac_rst_n) tx_reset <= 2'b11; else tx_reset <= {tx_reset[0],1'b0};
always @(posedge clk_i or negedge mac_rst_n)
    if (!mac_rst_n) logic_reset <= 2'b11; else logic_reset <= {logic_reset[0],1'b0};
(* ASYNC_REG = "TRUE" *) reg [1:0] tx_enable_sync, rx_enable_sync;
always @(posedge tx_clk_i or posedge tx_reset[1])
    if (tx_reset[1]) tx_enable_sync <= 0;
    else tx_enable_sync <= {tx_enable_sync[0], enable_q[0]};
always @(posedge rx_clk_i or posedge rx_reset[1])
    if (rx_reset[1]) rx_enable_sync <= 0;
    else rx_enable_sync <= {rx_enable_sync[0], enable_q[1]};
(* ASYNC_REG = "TRUE" *) reg [1:0] mdio_sync;
reg [2:0] mdio_q;
always @(posedge clk_i or negedge rst_ni)
    if (!rst_ni) mdio_sync <= 2'b11; else mdio_sync <= {mdio_sync[0],mdio_i};
assign mdc_o=mdio_q[0];
assign mdio_o=mdio_q[1];
assign mdio_oe_o=mdio_q[2];
wire access = psel_i && penable_i;
wire tx_ready, rx_valid, rx_last, rx_user;
wire [7:0] rx_data;
wire [8:0] events;
reg [8:0] events_q;
reg [9:0] irqen_q;
wire known = paddr_i == R_CTRL || paddr_i == R_STATUS || paddr_i == R_TX ||
    paddr_i == R_RX || paddr_i == R_EVENTS || paddr_i == R_IRQEN ||
    paddr_i == R_MDIO || paddr_i == R_ID;
wire writeable = paddr_i == R_CTRL || paddr_i == R_TX ||
    paddr_i == R_EVENTS || paddr_i == R_IRQEN || paddr_i == R_MDIO;
wire bad_access = !known || (pwrite_i && (!writeable || !pstrb_i[0])) ||
    (pwrite_i && paddr_i == R_TX && (!tx_ready || !enable_q[0] || logic_reset[1])) ||
    (!pwrite_i && paddr_i == R_RX && !rx_valid);
assign pready_o = 1'b1;
assign pslverr_o = access && bad_access;
wire wr = access && pwrite_i && !bad_access;
wire rd = access && !pwrite_i && !bad_access;
wire tx_push = wr && paddr_i == R_TX;
wire rx_pop = rd && paddr_i == R_RX;
wire [8:0] clear_events = wr && paddr_i == R_EVENTS ?
    {pwdata_i[8] && pstrb_i[1],pwdata_i[7:0]} : 9'h000;
assign irq_o = |(events_q & irqen_q[8:0]) || (rx_valid && irqen_q[9]);
always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
        enable_q <= 0;
        flush_q <= 0;
        events_q <= 0;
        irqen_q <= 0;
        mdio_q <= 3'b010;
    end else begin
        flush_q <= 0;
        events_q <= (events_q & ~clear_events) | events;
        if (wr && paddr_i == R_CTRL) begin
            enable_q <= pwdata_i[1:0];
            flush_q <= pwdata_i[2];
        end
        if (wr && paddr_i == R_IRQEN) begin
            irqen_q[7:0] <= pwdata_i[7:0];
            if (pstrb_i[1]) irqen_q[9:8] <= pwdata_i[9:8];
        end
        if (wr && paddr_i == R_MDIO) mdio_q <= pwdata_i[2:0];
    end
end
always @* begin
    prdata_o = 0;
    case (paddr_i)
        R_CTRL: prdata_o = {30'b0,enable_q};
        R_STATUS: prdata_o = {27'b0,logic_reset[1],(rx_user && rx_valid),(rx_last && rx_valid),rx_valid,tx_ready};
        R_RX: prdata_o = rx_valid ? {1'b1,21'b0,rx_user,rx_last,rx_data} : 32'b0;
        R_EVENTS: prdata_o = {23'b0,events_q};
        R_IRQEN: prdata_o = {22'b0,irqen_q};
        R_MDIO: prdata_o = {23'b0,mdio_sync[1],5'b0,mdio_q};
        R_ID: prdata_o = 32'h474d4901; // "GMI", revision 1
        default: prdata_o = 0;
    endcase
end
eth_mac_1g_fifo #(
    .AXIS_DATA_WIDTH(8), .AXIS_KEEP_ENABLE(0),
    .TX_FIFO_DEPTH(FIFO_DEPTH), .RX_FIFO_DEPTH(FIFO_DEPTH),
    .TX_FRAME_FIFO(1), .RX_FRAME_FIFO(1), .ENABLE_PADDING(1),
    .MIN_FRAME_LENGTH(64), .RX_DROP_BAD_FRAME(1), .RX_DROP_WHEN_FULL(1)
) u_mac (
    .logic_clk(clk_i), .logic_rst(logic_reset[1]),
    .rx_clk(rx_clk_i), .rx_rst(rx_reset[1]),
    .tx_clk(tx_clk_i), .tx_rst(tx_reset[1]),
    .tx_axis_tdata(pwdata_i[7:0]), .tx_axis_tkeep(1'b1),
    .tx_axis_tvalid(tx_push), .tx_axis_tready(tx_ready),
    .tx_axis_tlast(pstrb_i[1] && pwdata_i[8]),
    .tx_axis_tuser(pstrb_i[1] && pwdata_i[9]),
    .rx_axis_tdata(rx_data), .rx_axis_tkeep(), .rx_axis_tvalid(rx_valid),
    .rx_axis_tready(rx_pop), .rx_axis_tlast(rx_last), .rx_axis_tuser(rx_user),
    .gmii_rxd(rxd_i), .gmii_rx_dv(rx_dv_i), .gmii_rx_er(rx_er_i),
    .gmii_txd(txd_o), .gmii_tx_en(tx_en_o), .gmii_tx_er(tx_er_o),
    .rx_clk_enable(1'b1), .tx_clk_enable(1'b1),
    .rx_mii_select(1'b0), .tx_mii_select(1'b0),
    .cfg_ifg(8'd12), .cfg_tx_enable(tx_enable_sync[1]),
    .cfg_rx_enable(rx_enable_sync[1]),
    .tx_fifo_good_frame(events[0]), .rx_fifo_good_frame(events[1]),
    .tx_fifo_bad_frame(events[2]), .rx_fifo_bad_frame(events[3]),
    .rx_fifo_overflow(events[4]), .tx_error_underflow(events[5]),
    .rx_error_bad_fcs(events[6]), .rx_error_bad_frame(events[7]),
    .tx_fifo_overflow(events[8])
);
// Oversized frames are discarded by the frame FIFO and raise event bit 8.
endmodule
`default_nettype wire
