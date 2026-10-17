// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
`default_nettype none
// Test fixture only: real soc_top and CPU, no driven internal nets/registers.
module tb_soc_pcie_packet(
 input wire clk_i,rst_ni,link_up_i,training_i,retrain_done_i,
 input wire [15:0] function_id_i,
 input wire [7:0] rx_data_i,
 input wire rx_sop_i,rx_eop_i,rx_error_i,rx_valid_i,rx_dllp_i,tx_ready_i,
 output wire rx_ready_o,
 output wire [7:0] tx_data_o,
 output wire tx_sop_o,tx_eop_o,tx_valid_o,tx_dllp_o,tx_replay_o,
 output wire initialized_o,error_o,retrain_request_o,
 output wire [15:0] gpio_o,gpio_oe_o,
 output wire [3:0] alerts_o,
 output wire cpu_access_o,pcie_access_o,contention_o,
 output wire [19:0] bus_addr_o,
 output wire bus_write_o,bus_ready_o,
 output wire [31:0] bus_data_o
);
 soc_top #(.ROM_INIT(`ROM_HEX)) dut (
  .clk_i(clk_i),.rst_ni(rst_ni),
  .pcie_link_up_i(link_up_i),.pcie_training_i(training_i),
  .pcie_retrain_done_i(retrain_done_i),.pcie_function_id_i(function_id_i),
  .pcie_rx_data_i(rx_data_i),.pcie_rx_sop_i(rx_sop_i),.pcie_rx_eop_i(rx_eop_i),
  .pcie_rx_error_i(rx_error_i),.pcie_rx_valid_i(rx_valid_i),.pcie_rx_dllp_i(rx_dllp_i),
  .pcie_rx_ready_o(rx_ready_o),.pcie_tx_data_o(tx_data_o),.pcie_tx_sop_o(tx_sop_o),
  .pcie_tx_eop_o(tx_eop_o),.pcie_tx_valid_o(tx_valid_o),.pcie_tx_dllp_o(tx_dllp_o),
  .pcie_tx_replay_o(tx_replay_o),.pcie_tx_ready_i(tx_ready_i),
  .pcie_initialized_o(initialized_o),.pcie_error_o(error_o),
  .pcie_retrain_request_o(retrain_request_o),
  .eth_rx_clk_i(clk_i),.eth_tx_clk_i(clk_i),.eth_rxd_i(8'b0),
  .eth_rx_dv_i(1'b0),.eth_rx_er_i(1'b0),.eth_mdio_i(1'b1),
  .spw_di_i(1'b0),.spw_si_i(1'b0),.i2c_scl_i(1'b1),.i2c_sda_i(1'b1),
  .can_rx_i(1'b1),.spi_miso_i(1'b0),.irq_external_i(1'b0),
  .wdog_dis_i(1'b0),.strap_i(4'b0),.uart_rx_i(1'b1),
  .gpio_i(gpio_o & gpio_oe_o),.gpio_o(gpio_o),.gpio_oe_o(gpio_oe_o),
  .qspi_io_i(4'hf),.alert_minor_o(alerts_o[0]),
  .alert_major_internal_o(alerts_o[1]),.alert_major_bus_o(alerts_o[2]),
  .double_fault_seen_o(alerts_o[3])
 );
 // Read-only witnesses of actual handshakes; these cannot stimulate hardware.
 assign cpu_access_o=dut.cpu_pready && dut.cpu_psel && dut.cpu_penable;
 assign pcie_access_o=dut.ep_pready && dut.ep_psel && dut.ep_penable;
 assign contention_o=dut.cpu_psel && dut.ep_psel;
 assign bus_addr_o=dut.paddr;
 assign bus_write_o=dut.pwrite;
 assign bus_data_o=dut.pwdata;
 assign bus_ready_o=dut.psel && dut.penable && dut.pready;
endmodule
`default_nettype wire
