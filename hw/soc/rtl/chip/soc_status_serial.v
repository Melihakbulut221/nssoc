// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Read-only bundled-data mailbox. The host toggles request, waits until
// ready falls and rises, then samples data BEFORE each rising test-clock edge.
// Keep request fixed for the whole frame; clocks during the wait are required.
// The source captures atomically, holds the bus until the next request, and
// acknowledges through two synchronizer stages. No test signal controls the SoC.
// Physical implementation must constrain the held snapshot bus to arrive before
// acknowledgement; digital simulation alone does not establish CDC timing.
module soc_status_serial #(
    parameter integer WIDTH = 192
) (
    input wire clk_i, rst_ni,
    input wire [WIDTH-1:0] status_i,
    input wire test_clk_i, test_req_i,
    output wire test_ready_o, test_data_o
);
    (* ASYNC_REG = "TRUE" *) reg source_meta, source_release;
    (* ASYNC_REG = "TRUE" *) reg serial_meta, serial_release;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin source_meta <= 0; source_release <= 0; end
        else begin source_meta <= 1; source_release <= source_meta; end
    end
    always @(posedge test_clk_i or negedge rst_ni) begin
        if (!rst_ni) begin serial_meta <= 0; serial_release <= 0; end
        else begin serial_meta <= 1; serial_release <= serial_meta; end
    end
    wire source_rst_n = source_release;
    wire serial_rst_n = serial_release;
    (* ASYNC_REG = "TRUE" *) reg req_meta, req_sync;
    reg ack;
    reg [WIDTH-1:0] snapshot;
    always @(posedge clk_i or negedge source_rst_n) begin
        if (!source_rst_n) begin
            req_meta <= 0;
            req_sync <= 0;
            ack <= 0;
            snapshot <= 0;
        end else begin
            req_meta <= test_req_i;
            req_sync <= req_meta;
            if (req_sync != ack) begin
                snapshot <= status_i;
                ack <= req_sync;
            end
        end
    end
    (* ASYNC_REG = "TRUE" *) reg ack_meta, ack_sync;
    reg consumed, valid;
    reg [WIDTH-1:0] shift;
    always @(posedge test_clk_i or negedge serial_rst_n) begin
        if (!serial_rst_n) begin
            ack_meta <= 0;
            ack_sync <= 0;
            consumed <= 0;
            valid <= 0;
            shift <= 0;
        end else begin
            ack_meta <= ack;
            ack_sync <= ack_meta;
            if (ack_sync != consumed) begin
                shift <= snapshot;
                consumed <= ack_sync;
                valid <= 1;
            end else if (test_ready_o) begin
                shift <= {1'b0, shift[WIDTH-1:1]};
            end
        end
    end
    // A changed host request immediately marks the old frame unavailable.
    // This asynchronous expression is an external status indication only.
    assign test_ready_o = rst_ni && valid && (consumed == test_req_i);
    assign test_data_o = test_ready_o ? shift[0] : 1'b0;
endmodule
`default_nettype wire
