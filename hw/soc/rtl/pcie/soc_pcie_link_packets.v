// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Standalone packet boundary with actual ACK/NAK DLLPs and LCRC TLPs sharing
// one byte output. tx_dllp_o marks frame type for a future PCS. SOP/EOP are
// project-local boundaries, not physical framing symbols. This module supplies
// no replay, credits, AckNak timer, LTSSM, PHY or SoC/layout integration.
module soc_pcie_link_packets #(
    parameter [15:0] VENDOR_ID=16'hffff,
    parameter [15:0] DEVICE_ID=16'h0000,
    parameter integer APB_TIMEOUT=256,
    parameter integer MAX_TLP_DWORDS=8
) (
    input wire clk_i,rst_ni,
    input wire [15:0] function_id_i,
    input wire [7:0] rx_data_i,
    input wire rx_sop_i,rx_eop_i,rx_error_i,rx_valid_i,
    output wire rx_ready_o,
    output wire [11:0] rx_expected_sequence_o,tx_next_sequence_o,
    output wire packet_accepted_o,packet_duplicate_o,packet_rejected_o,
    output wire [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,tx_dllp_o,
    input wire tx_ready_i,
    output wire psel_o,penable_o,
    output wire [11:0] paddr_o,
    output wire pwrite_o,
    output wire [3:0] pstrb_o,
    output wire [31:0] pwdata_o,
    input wire pready_i,pslverr_i,
    input wire [31:0] prdata_i,
    output wire error_o,memory_enable_o,
    output wire [31:0] bar0_o
);
    wire ack_valid,ack_ready,ack_nak;
    wire [11:0] ack_sequence;
    wire [7:0] tlp_data;
    wire tlp_sop,tlp_eop,tlp_valid,tlp_ready;
    soc_pcie_packet_endpoint #(.VENDOR_ID(VENDOR_ID),.DEVICE_ID(DEVICE_ID),
        .APB_TIMEOUT(APB_TIMEOUT),.MAX_TLP_DWORDS(MAX_TLP_DWORDS)) endpoint(
        .clk_i(clk_i),.rst_ni(rst_ni),.function_id_i(function_id_i),
        .rx_data_i(rx_data_i),.rx_sop_i(rx_sop_i),.rx_eop_i(rx_eop_i),
        .rx_error_i(rx_error_i),.rx_valid_i(rx_valid_i),.rx_ready_o(rx_ready_o),
        .rx_expected_sequence_o(rx_expected_sequence_o),.tx_next_sequence_o(tx_next_sequence_o),
        .packet_accepted_o(packet_accepted_o),.packet_duplicate_o(packet_duplicate_o),.packet_rejected_o(packet_rejected_o),
        .ack_valid_o(ack_valid),.ack_ready_i(ack_ready),.ack_nak_o(ack_nak),.ack_sequence_o(ack_sequence),
        .tx_data_o(tlp_data),.tx_sop_o(tlp_sop),.tx_eop_o(tlp_eop),.tx_valid_o(tlp_valid),.tx_ready_i(tlp_ready),
        .psel_o(psel_o),.penable_o(penable_o),.paddr_o(paddr_o),.pwrite_o(pwrite_o),.pstrb_o(pstrb_o),
        .pwdata_o(pwdata_o),.pready_i(pready_i),.pslverr_i(pslverr_i),.prdata_i(prdata_i),
        .error_o(error_o),.memory_enable_o(memory_enable_o),.bar0_o(bar0_o));
    soc_pcie_packet_tx transmitter(
        .clk_i(clk_i),.rst_ni(rst_ni),.ack_valid_i(ack_valid),.ack_nak_i(ack_nak),
        .ack_sequence_i(ack_sequence),.ack_ready_o(ack_ready),
        .tlp_data_i(tlp_data),.tlp_sop_i(tlp_sop),.tlp_eop_i(tlp_eop),.tlp_valid_i(tlp_valid),.tlp_ready_o(tlp_ready),
        .tx_data_o(tx_data_o),.tx_sop_o(tx_sop_o),.tx_eop_o(tx_eop_o),.tx_valid_o(tx_valid_o),
        .tx_dllp_o(tx_dllp_o),.tx_ready_i(tx_ready_i));
endmodule
`default_nettype wire
