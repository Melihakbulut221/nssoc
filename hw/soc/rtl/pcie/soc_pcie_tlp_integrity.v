// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Standalone classic-LCRC receive staging + existing transaction backend.
// See soc_pcie_lcrc_rx for the byte packet contract. Header octets become
// numeric DWs most-significant byte first; payload octets use APB byte order
// (first octet in bits 7:0). TX remains the existing DWORD completion stream:
// it has NO sequence/LCRC/credits/retry/PHY framing. TD/ECRC remains rejected
// by the existing backend. RX sequence/reserved metadata is valid only at
// packet_good_o, not throughout the later APB/completion transaction.
// This module is intentionally not in soc_top.
module soc_pcie_tlp_integrity #(
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
    output wire [11:0] rx_sequence_o,
    output wire [3:0] rx_reserved_o,
    output wire packet_good_o,packet_bad_o,
    output wire [31:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,
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
    wire [7:0] byte_data;
    wire byte_sop,byte_eop,byte_valid;
    reg [31:0] word_data;
    reg word_valid,word_sop,word_eop;
    reg [1:0] byte_index;
    localparam integer DW=$clog2(MAX_TLP_DWORDS+1);
    reg [DW-1:0] word_index;
    reg [2:0] header_words;
    wire word_ready,backend_error;
    soc_pcie_lcrc_rx #(.MAX_TLP_DWORDS(MAX_TLP_DWORDS)) receive_packet(
        .clk_i(clk_i),.rst_ni(rst_ni),.rx_data_i(rx_data_i),.rx_sop_i(rx_sop_i),
        .rx_eop_i(rx_eop_i),.rx_error_i(rx_error_i),.rx_valid_i(rx_valid_i),.rx_ready_o(rx_ready_o),
        .tlp_data_o(byte_data),.tlp_sop_o(byte_sop),.tlp_eop_o(byte_eop),.tlp_valid_o(byte_valid),
        .tlp_ready_i(!word_valid),.sequence_o(rx_sequence_o),.reserved_o(rx_reserved_o),
        .packet_good_o(packet_good_o),.packet_bad_o(packet_bad_o));
    soc_pcie_tlp_stream #(.VENDOR_ID(VENDOR_ID),.DEVICE_ID(DEVICE_ID),.APB_TIMEOUT(APB_TIMEOUT)) transaction_stream(
        .clk_i(clk_i),.rst_ni(rst_ni),.function_id_i(function_id_i),.rx_data_i(word_data),
        .rx_sop_i(word_sop),.rx_eop_i(word_eop),.rx_error_i(1'b0),.rx_valid_i(word_valid),.rx_ready_o(word_ready),
        .tx_data_o(tx_data_o),.tx_sop_o(tx_sop_o),.tx_eop_o(tx_eop_o),.tx_valid_o(tx_valid_o),.tx_ready_i(tx_ready_i),
        .psel_o(psel_o),.penable_o(penable_o),.paddr_o(paddr_o),.pwrite_o(pwrite_o),.pstrb_o(pstrb_o),.pwdata_o(pwdata_o),
        .pready_i(pready_i),.pslverr_i(pslverr_i),.prdata_i(prdata_i),.error_o(backend_error),
        .memory_enable_o(memory_enable_o),.bar0_o(bar0_o));
    assign error_o=packet_bad_o | backend_error;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            word_data<=0;word_valid<=0;word_sop<=0;word_eop<=0;
            byte_index<=0;word_index<=0;header_words<=3;
        end else begin
            if (word_valid && word_ready) word_valid<=0;
            if (byte_valid && !word_valid) begin
                if (byte_sop) begin
                    word_index<=0;header_words<=byte_data[5] ? 4 : 3;
                    word_data<={byte_data,24'b0};byte_index<=1;
                end else begin
                    if (word_index<header_words) begin
                        case (byte_index)
                            0:word_data[31:24]<=byte_data;
                            1:word_data[23:16]<=byte_data;
                            2:word_data[15:8]<=byte_data;
                            3:word_data[7:0]<=byte_data;
                        endcase
                    end else word_data[8*byte_index+:8]<=byte_data;
                    byte_index<=byte_index+1'b1;
                    if (byte_index==3) begin
                        word_valid<=1;word_sop<=word_index==0;word_eop<=byte_eop;
                        word_index<=word_index+1'b1;
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
