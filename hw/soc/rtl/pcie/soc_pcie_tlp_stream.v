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
`ifdef SOC_PCIE_TX_WORD_REG
    // docs/combined-timing.md section 17 (default off): the transmitted
    // word and its SOP/EOP markers come from registers (block below)
    // instead of the tx_index multiplexer and compares, and tx_valid_o
    // from a copy of tx_busy that drives only the transmit interface
    // (loaded with tx_busy's next value, cleared by the same reset, so it
    // equals tx_busy in every cycle; keep_hierarchy keeps it apart).
    reg [31:0] tx_word_q;
    reg tx_sop_q, tx_eop_q;
    wire tx_busy_copy;
    wire tx_busy_d = (!tx_busy && completion_valid) ? 1'b1 :
                     (tx_busy && tx_ready_i && tx_eop_o) ? 1'b0 : tx_busy;
    soc_pcie_tlp_stream_flag_copy busy_copy (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(tx_busy_d), .q_o(tx_busy_copy));
    // Section 18: a second copy for the word and marker registers' load
    // and advance selects only (r_cut8z: tx_busy -> tx_word_q, -0.57 ns,
    // 0.80 ns from clock to output on the master's fanout). It equals
    // tx_busy in every cycle like busy_copy.
    wire tx_busy_word;
    soc_pcie_tlp_stream_flag_copy busy_word_copy (.clk_i(clk_i), .rst_ni(rst_ni), .d_i(tx_busy_d), .q_o(tx_busy_word));
    assign tx_valid_o = rst_ni && tx_busy_copy;
    assign tx_sop_o = tx_sop_q;
    assign tx_eop_o = tx_eop_q;
`else
    assign tx_valid_o = rst_ni && tx_busy;
    assign tx_sop_o = tx_busy && tx_index==0;
    assign tx_eop_o = tx_busy && tx_index==(tx_payload ? 3 : 2);
`endif
    assign error_o = framing_error | backend_error;

`ifdef SOC_PCIE_TX_WORD_REG
    always @* tx_data_o=tx_word_q;
    // The registers load, at a completion load and at each accepted beat
    // that is not the last, what the next tx_index selects, under the same
    // conditions as tx_busy and tx_index below. tx_header, tx_payload_data
    // and tx_payload change only at a load, where tx_index becomes 0, and
    // tx_index changes only at a load or an accepted beat, so in every
    // cycle the registers equal the default build's multiplexer and
    // compares (reset: all 0, as tx_header is 0 and tx_busy is 0). The
    // word select then no longer precedes the wire to the LCRC
    // transmitter's write register.
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            tx_word_q<=0; tx_sop_q<=0; tx_eop_q<=0;
        end else if (!tx_busy_word && completion_valid) begin
            tx_word_q<=completion_header[95:64]; tx_sop_q<=1; tx_eop_q<=0;
        end else if (tx_busy_word && tx_ready_i) begin
            tx_sop_q<=0;
            if (tx_eop_o) tx_eop_q<=0;
            else begin
                case (tx_index)
                    0: tx_word_q<=tx_header[63:32];
                    1: tx_word_q<=tx_header[31:0];
                    2: tx_word_q<=tx_payload_data;
                    default: tx_word_q<=tx_header[95:64];
                endcase
                tx_eop_q<=tx_index+1'b1==(tx_payload ? 2'd3 : 2'd2);
            end
        end
    end
`else
    always @* begin
        case (tx_index)
            0: tx_data_o=tx_header[95:64];
            1: tx_data_o=tx_header[63:32];
            2: tx_data_o=tx_header[31:0];
            default: tx_data_o=tx_payload_data;
        endcase
    end
`endif

    // A collected descriptor is presented to the register backend from the
    // second SUBMIT cycle on (armed), so it is stable for a cycle before it
    // is presented and the backend decodes it from registers (PREDECODE).
    reg armed;
    soc_pcie_tlp_regs #(.VENDOR_ID(VENDOR_ID), .DEVICE_ID(DEVICE_ID),
                        .APB_TIMEOUT(APB_TIMEOUT), .PREDECODE(1)) regs (
        .clk_i(clk_i), .rst_ni(rst_ni), .function_id_i(function_id_i),
        .rx_hdr_i(header), .rx_data_i(payload), .rx_payload_dw_i(payload_count),
        .rx_valid_i(state==SUBMIT && armed && rst_ni), .rx_ready_o(descriptor_ready),
        .tx_hdr_o({completion_header,unused_completion_reserved}), .tx_data_o(completion_data),
        .tx_has_data_o(completion_has_data), .tx_valid_o(completion_valid),
        .tx_ready_i(!tx_busy), .psel_o(psel_o), .penable_o(penable_o),
        .paddr_o(paddr_o), .pwrite_o(pwrite_o), .pstrb_o(pstrb_o),
        .pwdata_o(pwdata_o), .pready_i(pready_i), .pslverr_i(pslverr_i),
        .prdata_i(prdata_i), .error_o(backend_error),
        .memory_enable_o(memory_enable_o), .bar0_o(bar0_o)
    );

`ifdef SOC_PCIE_TX_WORD_REG
    // docs/combined-timing.md section 19 (inside SOC_PCIE_TX_WORD_REG):
    // the receive header's word select as a register. header_sel[k-1] is
    // header_count==k && header_count<header_size: set to word 1 at a
    // start, moved with header_count at each header word, cleared by
    // reset. header_count<header_size implies header_count is 1, 2 or 3
    // (both are 0 until a start, which sets 1 and 3 or 4, and the count
    // only steps by one up to the size), so |header_sel equals that
    // compare and the case's default is never taken. The header bytes'
    // load enables then no longer start with the count compare.
    reg [2:0] header_sel;
`ifndef SYNTHESIS
    always @(posedge clk_i) if (rst_ni===1'b1 &&
        header_sel!=={header_count==3 && 3<header_size, header_count==2 && 2<header_size,
                      header_count==1 && 1<header_size}) begin
        $display("TLP_STREAM_HEADER_SEL_MISMATCH t=%0t sel=%b count=%0d size=%0d", $time, header_sel, header_count, header_size);
        $fatal(1, "registered header select differs");
    end
`endif
`endif
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state<=IDLE; header<=0; payload<=0; payload_count<=0;
            header_count<=0; header_size<=0; framing_error<=0;
`ifdef SOC_PCIE_TX_WORD_REG
            header_sel<=0;
`endif
            tx_busy<=0; tx_payload<=0; tx_index<=0;
            tx_header<=0; tx_payload_data<=0; armed<=0;
        end else begin
            framing_error<=0;
            armed<=state==SUBMIT && !(armed && descriptor_ready);
            if (!tx_busy && completion_valid) begin
                tx_busy<=1; tx_index<=0; tx_header<=completion_header;
                tx_payload_data<=completion_data; tx_payload<=completion_has_data;
            end else if (tx_busy && tx_ready_i) begin
                if (tx_eop_o) tx_busy<=0;
                else tx_index<=tx_index+1'b1;
            end
            if (state==SUBMIT) begin
                if (armed && descriptor_ready) state<=IDLE;
            end else if (rx_valid_i) begin
                if (rx_sop_i) begin
                    // A fresh SOP also resynchronizes an abandoned packet.
                    if (state==COLLECT) framing_error<=1;
                    header<={rx_data_i,96'b0}; payload<=0; payload_count<=0;
                    header_count<=1; header_size<=rx_data_i[29] ? 4 : 3;
`ifdef SOC_PCIE_TX_WORD_REG
                    header_sel<=3'b001;
`endif
                    if (rx_error_i || rx_eop_i || rx_data_i[31:29]>3) begin
                        framing_error<=1; state<=rx_eop_i ? IDLE : DROP;
                    end else state<=COLLECT;
                end else if (state==IDLE) begin
                    framing_error<=1; state<=rx_eop_i ? IDLE : DROP;
                end else if (state==DROP) begin
                    if (rx_eop_i) state<=IDLE;
                end else if (rx_error_i) begin
                    framing_error<=1; state<=rx_eop_i ? IDLE : DROP;
`ifdef SOC_PCIE_TX_WORD_REG
                end else if (|header_sel) begin
                    if (header_sel[0]) header[95:64]<=rx_data_i;
                    if (header_sel[1]) header[63:32]<=rx_data_i;
                    if (header_sel[2]) header[31:0]<=rx_data_i;
                    header_sel<={header_count==2 && header_size==4, header_count==1, 1'b0};
`else
                end else if (header_count<header_size) begin
                    case (header_count)
                        1: header[95:64]<=rx_data_i;
                        2: header[63:32]<=rx_data_i;
                        3: header[31:0]<=rx_data_i;
                        default: header<=0;
                    endcase
`endif
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
`ifdef SOC_PCIE_TX_WORD_REG
// Section 17: a copy of one control flag, kept apart from its master by
// keep_hierarchy (opt_merge does not merge instances of a user module);
// the SoC flow's final flatten removes the boundary after mapping.
(* keep_hierarchy *)
module soc_pcie_tlp_stream_flag_copy (
    input wire clk_i, rst_ni, d_i,
    output reg q_o
);
    always @(posedge clk_i or negedge rst_ni)
        if (!rst_ni) q_o <= 1'b0; else q_o <= d_i;
endmodule
`endif
`default_nettype wire
