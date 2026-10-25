// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none

// DWORD packet boundary adapter for soc_pcie_tlp_regs, not PIPE or a DLL.
// Only complete unprefixed 3/4-DW headers are submitted. Count actual payload
// beats, retain its first DWORD, and drain oversized/malformed packets.
// Upstream MUST supply packet boundaries and assert rx_error_i for integrity
// failures by the accepted EOP beat. No CRC, sequence, credit or lane logic.
module soc_pcie_tlp_stream #(
    parameter [15:0] VENDOR_ID = 16'hffff,
    parameter [15:0] DEVICE_ID = 16'h0000,
    parameter integer APB_TIMEOUT = 256
) (
    input wire clk_i, rst_ni,
    input wire [15:0] function_id_i,
    input wire [31:0] rx_data_i,
    input wire rx_sop_i, rx_eop_i, rx_error_i, rx_valid_i,
    output wire rx_ready_o,
    output reg [31:0] tx_data_o,
    output wire tx_sop_o, tx_eop_o, tx_valid_o,
    input wire tx_ready_i,
    output wire psel_o, penable_o,
    output wire [11:0] paddr_o,
    output wire pwrite_o,
    output wire [3:0] pstrb_o,
    output wire [31:0] pwdata_o,
    input wire pready_i, pslverr_i,
    input wire [31:0] prdata_i,
    output wire error_o, memory_enable_o,
    output wire [31:0] bar0_o
);
    localparam [1:0] IDLE=0, COLLECT=1, DROP=2, SUBMIT=3;
    reg [1:0] state;
    reg [127:0] header;
    reg [31:0] payload;
    reg [10:0] payload_count;
    reg [2:0] header_count, header_size;
    reg framing_error;
    wire descriptor_ready, backend_error;
    wire [95:0] completion_header;
    wire [31:0] unused_completion_reserved;
    wire [31:0] completion_data;
    wire completion_has_data, completion_valid;
    reg tx_busy, tx_payload;
    reg [1:0] tx_index;
    reg [95:0] tx_header;
    reg [31:0] tx_payload_data;

    assign rx_ready_o = rst_ni && state!=SUBMIT;
    assign tx_valid_o = rst_ni && tx_busy;
    assign tx_sop_o = tx_busy && tx_index==0;
    assign tx_eop_o = tx_busy && tx_index==(tx_payload ? 3 : 2);
    assign error_o = framing_error | backend_error;

    always @* begin
        case (tx_index)
            0: tx_data_o=tx_header[95:64];
            1: tx_data_o=tx_header[63:32];
            2: tx_data_o=tx_header[31:0];
            default: tx_data_o=tx_payload_data;
        endcase
    end

    soc_pcie_tlp_regs #(.VENDOR_ID(VENDOR_ID), .DEVICE_ID(DEVICE_ID),
                        .APB_TIMEOUT(APB_TIMEOUT)) regs (
        .clk_i(clk_i), .rst_ni(rst_ni), .function_id_i(function_id_i),
        .rx_hdr_i(header), .rx_data_i(payload), .rx_payload_dw_i(payload_count),
        .rx_valid_i(state==SUBMIT && rst_ni), .rx_ready_o(descriptor_ready),
        .tx_hdr_o({completion_header,unused_completion_reserved}), .tx_data_o(completion_data),
        .tx_has_data_o(completion_has_data), .tx_valid_o(completion_valid),
        .tx_ready_i(!tx_busy), .psel_o(psel_o), .penable_o(penable_o),
        .paddr_o(paddr_o), .pwrite_o(pwrite_o), .pstrb_o(pstrb_o),
        .pwdata_o(pwdata_o), .pready_i(pready_i), .pslverr_i(pslverr_i),
        .prdata_i(prdata_i), .error_o(backend_error),
        .memory_enable_o(memory_enable_o), .bar0_o(bar0_o)
    );

    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state<=IDLE; header<=0; payload<=0; payload_count<=0;
            header_count<=0; header_size<=0; framing_error<=0;
            tx_busy<=0; tx_payload<=0; tx_index<=0;
            tx_header<=0; tx_payload_data<=0;
        end else begin
            framing_error<=0;
            if (!tx_busy && completion_valid) begin
                tx_busy<=1; tx_index<=0; tx_header<=completion_header;
                tx_payload_data<=completion_data; tx_payload<=completion_has_data;
            end else if (tx_busy && tx_ready_i) begin
                if (tx_eop_o) tx_busy<=0;
                else tx_index<=tx_index+1'b1;
            end
            if (state==SUBMIT) begin
                if (descriptor_ready) state<=IDLE;
            end else if (rx_valid_i) begin
                if (rx_sop_i) begin
                    // A fresh SOP also resynchronizes an abandoned packet.
                    if (state==COLLECT) framing_error<=1;
                    header<={rx_data_i,96'b0}; payload<=0; payload_count<=0;
                    header_count<=1; header_size<=rx_data_i[29] ? 4 : 3;
                    if (rx_error_i || rx_eop_i || rx_data_i[31:29]>3) begin
                        framing_error<=1; state<=rx_eop_i ? IDLE : DROP;
                    end else state<=COLLECT;
                end else if (state==IDLE) begin
                    framing_error<=1; state<=rx_eop_i ? IDLE : DROP;
                end else if (state==DROP) begin
                    if (rx_eop_i) state<=IDLE;
                end else if (rx_error_i) begin
                    framing_error<=1; state<=rx_eop_i ? IDLE : DROP;
                end else if (header_count<header_size) begin
                    case (header_count)
                        1: header[95:64]<=rx_data_i;
                        2: header[63:32]<=rx_data_i;
                        3: header[31:0]<=rx_data_i;
                        default: header<=0;
                    endcase
                    header_count<=header_count+1'b1;
                    if (rx_eop_i) begin
                        if (header_count+1'b1==header_size) state<=SUBMIT;
                        else begin framing_error<=1; state<=IDLE; end
                    end
                end else if (payload_count==1024) begin
                    // No wrapping count can make an oversized TLP look small.
                    framing_error<=1; state<=rx_eop_i ? IDLE : DROP;
                end else begin
                    if (payload_count==0) payload<=rx_data_i;
                    payload_count<=payload_count+1'b1;
                    if (rx_eop_i) state<=SUBMIT;
                end
            end
        end
    end
endmodule
`default_nettype wire
