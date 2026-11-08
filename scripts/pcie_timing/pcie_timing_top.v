// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Timing-analysis wrapper, not part of the design. It reproduces the
// packet-async PCIe instantiation of hw/soc/rtl/soc_top.v (SOC_PCIE_PACKET
// and SOC_PCIE_ASYNC): the packet reset release, the link status input
// registers, u_pcie with only the ports soc_top connects, and the APB
// mailbox u_pcie_cdc. The system-clock side of the mailbox is brought out
// to ports, so the pcie_clk_i domain is the same logic soc_top maps.
module pcie_timing_top (
    input wire clk_i, rst_sys_n, pcie_clk_i,
    input wire pcie_link_up_i, pcie_training_i, pcie_retrain_done_i,
    input wire [15:0] pcie_function_id_i,
    input wire [7:0] pcie_rx_data_i,
    input wire pcie_rx_sop_i, pcie_rx_eop_i, pcie_rx_error_i,
    input wire pcie_rx_valid_i, pcie_rx_dllp_i, pcie_tx_ready_i,
    output wire pcie_rx_ready_o,
    output wire [7:0] pcie_tx_data_o,
    output wire pcie_tx_sop_o, pcie_tx_eop_o, pcie_tx_valid_o,
    output wire pcie_tx_dllp_o, pcie_tx_replay_o,
    output wire pcie_initialized_o, pcie_error_o, pcie_retrain_request_o,
    output wire ep_psel, ep_penable, ep_pwrite,
    output wire [11:0] ep_paddr,
    output wire [31:0] ep_pwdata,
    output wire [3:0] ep_pstrb,
    input wire ep_pready, ep_pslverr,
    input wire [31:0] ep_prdata
);
  parameter integer APB_TIMEOUT = 256;
  wire ep_bad_strobe = ep_pwrite && ep_pstrb != 4'hf;
  wire packet_psel, packet_penable, packet_pwrite, packet_pready, packet_pslverr;
  wire [11:0] packet_paddr;
  wire [31:0] packet_pwdata, packet_prdata;
  wire [3:0] packet_pstrb;
  wire packet_clk = pcie_clk_i;
  (* ASYNC_REG="TRUE" *) reg [1:0] packet_reset_release;
  always @(posedge pcie_clk_i or negedge rst_sys_n)
    if (!rst_sys_n) packet_reset_release <= 0;
    else packet_reset_release <= {packet_reset_release[0], 1'b1};
  wire packet_rst_n = packet_reset_release[1];
  soc_pcie_apb_cdc u_pcie_cdc (
    .source_clk_i(pcie_clk_i), .destination_clk_i(clk_i),
    .reset_ni(rst_sys_n && pcie_link_up_i && !pcie_retrain_done_i),
    .s_psel_i(packet_psel), .s_penable_i(packet_penable), .s_pwrite_i(packet_pwrite),
    .s_paddr_i(packet_paddr), .s_pwdata_i(packet_pwdata), .s_pstrb_i(packet_pstrb),
    .s_pready_o(packet_pready), .s_pslverr_o(packet_pslverr), .s_prdata_o(packet_prdata),
    .m_psel_o(ep_psel), .m_penable_o(ep_penable), .m_pwrite_o(ep_pwrite),
    .m_paddr_o(ep_paddr), .m_pwdata_o(ep_pwdata), .m_pstrb_o(ep_pstrb),
    .m_pready_i(ep_bad_strobe || ep_pready),
    .m_pslverr_i(ep_bad_strobe || ep_pslverr), .m_prdata_i(ep_prdata));
  reg pcie_link_up_q, pcie_training_q, pcie_retrain_done_q;
  always @(posedge packet_clk or negedge packet_rst_n)
    if (!packet_rst_n) {pcie_link_up_q, pcie_training_q, pcie_retrain_done_q} <= 3'b0;
    else {pcie_link_up_q, pcie_training_q, pcie_retrain_done_q} <= {pcie_link_up_i, pcie_training_i, pcie_retrain_done_i};
  soc_pcie_buffered_flow_packets #(.APB_TIMEOUT(APB_TIMEOUT)) u_pcie (
      .clk_i(packet_clk), .rst_ni(packet_rst_n), .link_up_i(pcie_link_up_q),
      .training_i(pcie_training_q), .retrain_done_i(pcie_retrain_done_q),
      .function_id_i(pcie_function_id_i), .rx_data_i(pcie_rx_data_i),
      .rx_sop_i(pcie_rx_sop_i), .rx_eop_i(pcie_rx_eop_i),
      .rx_error_i(pcie_rx_error_i), .rx_valid_i(pcie_rx_valid_i),
      .rx_dllp_i(pcie_rx_dllp_i), .rx_ready_o(pcie_rx_ready_o),
      .tx_data_o(pcie_tx_data_o), .tx_sop_o(pcie_tx_sop_o),
      .tx_eop_o(pcie_tx_eop_o), .tx_valid_o(pcie_tx_valid_o),
      .tx_dllp_o(pcie_tx_dllp_o), .tx_replay_o(pcie_tx_replay_o),
      .tx_ready_i(pcie_tx_ready_i), .initialized_o(pcie_initialized_o),
      .error_o(pcie_error_o), .retrain_request_o(pcie_retrain_request_o),
      .psel_o(packet_psel), .penable_o(packet_penable), .paddr_o(packet_paddr),
      .pwrite_o(packet_pwrite), .pstrb_o(packet_pstrb), .pwdata_o(packet_pwdata),
      .pready_i(packet_pready), .pslverr_i(packet_pslverr), .prdata_i(packet_prdata));
endmodule
`default_nettype wire
