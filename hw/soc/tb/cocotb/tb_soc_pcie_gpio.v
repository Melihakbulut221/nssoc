// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
`default_nettype none
// Integration fixture only: real project APB3 GPIO behind the TLP backend.
module tb_soc_pcie_gpio;
    reg clk_i, rst_ni, rx_valid_i, tx_ready_i;
    reg [15:0] function_id_i, gpio_i;
    reg [127:0] rx_hdr_i;
    reg [31:0] rx_data_i;
    reg [10:0] rx_payload_dw_i;
    wire rx_ready_o, tx_valid_o, tx_has_data_o, error_o, memory_enable_o;
    wire [127:0] tx_hdr_o;
    wire [31:0] tx_data_o, bar0_o;
    wire psel_o, penable_o, pwrite_o, pready_i, pslverr_i;
    wire [11:0] paddr_o;
    wire [3:0] pstrb_o;
    wire [31:0] pwdata_o, prdata_i;
    wire [15:0] gpio_o, gpio_oe_o;
    wire irq_o, gpio_error;
    wire bad_strobe=pwrite_o && pstrb_o!=4'hf;
    assign pslverr_i=bad_strobe || gpio_error;
    soc_pcie_tlp_regs #(.VENDOR_ID(16'h1234), .DEVICE_ID(16'h5678), .APB_TIMEOUT(8)) backend (
        .clk_i(clk_i), .rst_ni(rst_ni), .function_id_i(function_id_i),
        .rx_hdr_i(rx_hdr_i), .rx_data_i(rx_data_i), .rx_payload_dw_i(rx_payload_dw_i),
        .rx_valid_i(rx_valid_i), .rx_ready_o(rx_ready_o),
        .tx_hdr_o(tx_hdr_o), .tx_data_o(tx_data_o), .tx_has_data_o(tx_has_data_o),
        .tx_valid_o(tx_valid_o), .tx_ready_i(tx_ready_i),
        .psel_o(psel_o), .penable_o(penable_o), .paddr_o(paddr_o),
        .pwrite_o(pwrite_o), .pstrb_o(pstrb_o), .pwdata_o(pwdata_o),
        .pready_i(pready_i), .pslverr_i(pslverr_i), .prdata_i(prdata_i),
        .error_o(error_o), .memory_enable_o(memory_enable_o), .bar0_o(bar0_o)
    );
    soc_gpio gpio (
        .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_o && !bad_strobe),
        .penable_i(penable_o), .paddr_i(paddr_o), .pwrite_i(pwrite_o),
        .pwdata_i(pwdata_o), .prdata_o(prdata_i), .pready_o(pready_i),
        .pslverr_o(gpio_error), .gpio_i(gpio_i), .gpio_o(gpio_o),
        .gpio_oe_o(gpio_oe_o), .irq_o(irq_o)
    );
endmodule
`default_nettype wire
