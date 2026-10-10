// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Read-only cross-port check after the other port has completed its March test.
// One-cycle synchronous SRAM, no backpressure. No writes can mask a stale port.
module soc_sram_zero_check #(
    parameter integer ADDR_WIDTH = 11,
    parameter integer WIDTH = 16
) (
    input wire clk_i, rst_ni, start_i,
    input wire [WIDTH-1:0] rdata_i,
    output wire req_o,
    output reg [ADDR_WIDTH-1:0] addr_o,
    output reg done_o, failed_o
);
    localparam [1:0] IDLE=0, ISSUE=1, CHECK=2, DONE=3;
    reg [1:0] state_q;
    assign req_o = rst_ni && state_q == ISSUE;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q <= IDLE;
            addr_o <= 0;
            done_o <= 0;
            failed_o <= 0;
        end else case (state_q)
            IDLE: if (start_i) state_q <= ISSUE;
            ISSUE: state_q <= CHECK;
            CHECK: begin
                if (rdata_i !== {WIDTH{1'b0}}) begin
                    failed_o <= 1;
                    done_o <= 1;
                    state_q <= DONE;
                end else if (&addr_o) begin
                    done_o <= 1;
                    state_q <= DONE;
                end else begin
                    addr_o <= addr_o + 1'b1;
                    state_q <= ISSUE;
                end
            end
            DONE: begin end
            default: begin
                failed_o <= 1;
                done_o <= 1;
                state_q <= DONE;
            end
        endcase
    end
endmodule
`default_nettype wire
