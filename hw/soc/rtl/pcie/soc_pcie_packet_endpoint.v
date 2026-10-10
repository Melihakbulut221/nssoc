// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Standalone packet integrity/sequence + transaction endpoint, not a PCIe link.
// RX/TX byte streams include sequence and LCRC, but no physical framing symbols.
// ACK/NAK ready/valid outputs are requests only, not DLLPs. No replay/credits,
// AckNak latency timer, PIPE, LTSSM, SoC integration or PHY behavior is supplied.
module soc_pcie_packet_endpoint #(
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
    output wire ack_valid_o,ack_nak_o,
    output wire [11:0] ack_sequence_o,
    input wire ack_ready_i,
    output wire [7:0] tx_data_o,
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
    wire [31:0] completion_data;
    wire completion_sop,completion_eop,completion_valid,completion_ready,tx_bad,tx_sent;
    soc_pcie_sequence_rx #(.MAX_TLP_DWORDS(MAX_TLP_DWORDS)) receive_packet(
        .clk_i(clk_i),.rst_ni(rst_ni),.rx_data_i(rx_data_i),.rx_sop_i(rx_sop_i),
        .rx_eop_i(rx_eop_i),.rx_error_i(rx_error_i),.rx_valid_i(rx_valid_i),.rx_ready_o(rx_ready_o),
        .tlp_data_o(byte_data),.tlp_sop_o(byte_sop),.tlp_eop_o(byte_eop),.tlp_valid_o(byte_valid),
        .tlp_ready_i(!word_valid),.expected_sequence_o(rx_expected_sequence_o),
        .ack_valid_o(ack_valid_o),.ack_nak_o(ack_nak_o),.ack_sequence_o(ack_sequence_o),.ack_ready_i(ack_ready_i),
        .packet_accepted_o(packet_accepted_o),.packet_duplicate_o(packet_duplicate_o),.packet_rejected_o(packet_rejected_o));
    soc_pcie_lcrc_tx #(.MAX_TLP_DWORDS(MAX_TLP_DWORDS)) transmit_packet(
        .clk_i(clk_i),.rst_ni(rst_ni),.tlp_data_i(completion_data),.tlp_sop_i(completion_sop),
        .tlp_eop_i(completion_eop),.tlp_error_i(1'b0),.tlp_valid_i(completion_valid),.tlp_ready_o(completion_ready),
        .tx_data_o(tx_data_o),.tx_sop_o(tx_sop_o),.tx_eop_o(tx_eop_o),.tx_valid_o(tx_valid_o),.tx_ready_i(tx_ready_i),
        .next_sequence_o(tx_next_sequence_o),.packet_sent_o(tx_sent),.packet_bad_o(tx_bad));
    soc_pcie_tlp_stream #(.VENDOR_ID(VENDOR_ID),.DEVICE_ID(DEVICE_ID),.APB_TIMEOUT(APB_TIMEOUT)) transaction_stream(
        .clk_i(clk_i),.rst_ni(rst_ni),.function_id_i(function_id_i),.rx_data_i(word_data),
        .rx_sop_i(word_sop),.rx_eop_i(word_eop),.rx_error_i(1'b0),.rx_valid_i(word_valid),.rx_ready_o(word_ready),
        .tx_data_o(completion_data),.tx_sop_o(completion_sop),.tx_eop_o(completion_eop),.tx_valid_o(completion_valid),.tx_ready_i(completion_ready),
        .psel_o(psel_o),.penable_o(penable_o),.paddr_o(paddr_o),.pwrite_o(pwrite_o),.pstrb_o(pstrb_o),.pwdata_o(pwdata_o),
        .pready_i(pready_i),.pslverr_i(pslverr_i),.prdata_i(prdata_i),.error_o(backend_error),
        .memory_enable_o(memory_enable_o),.bar0_o(bar0_o));
    assign error_o=packet_rejected_o | backend_error | tx_bad;
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
