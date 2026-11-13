// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Read-only cross-port check after the other port has completed its March test.
// One-cycle synchronous SRAM, no backpressure. No writes can mask a stale port.
// Optional capture separates SRAM/bank-mux delay from comparison and address
// advancement. It adds one idle clock per read; requests and failure address
// are unchanged, and the captured word remains authoritative until checked.
// SOC_ETH_FIFO_RDREG adds READ_LATENCY (1 or 2 edges from request to data):
// at 2 one wait state follows the request, for a registered read port.
module soc_sram_zero_check #(
    parameter integer ADDR_WIDTH = 11,
    parameter integer WIDTH = 16,
`ifdef SOC_ETH_FIFO_RDREG
    parameter integer READ_LATENCY = 1,
`endif
    parameter integer PIPELINE_COMPARE = 0
) (
    input wire clk_i, rst_ni, start_i,
    input wire [WIDTH-1:0] rdata_i,
    output wire req_o,
    output reg [ADDR_WIDTH-1:0] addr_o,
    output reg done_o, failed_o
);
    localparam [2:0] IDLE=0, ISSUE=1, CHECK=2, DONE=3, CAPTURE=4;
`ifdef SOC_ETH_FIFO_RDREG
    localparam [2:0] WAIT=5;
`endif
    reg [2:0] state_q;
    reg [WIDTH-1:0] read_data_q;
    wire [WIDTH-1:0] compare_data = (PIPELINE_COMPARE != 0) ? read_data_q : rdata_i;
    assign req_o = rst_ni && state_q == ISSUE;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q <= IDLE;
            read_data_q <= 0;
            addr_o <= 0;
            done_o <= 0;
            failed_o <= 0;
        end else case (state_q)
            IDLE: if (start_i) state_q <= ISSUE;
`ifdef SOC_ETH_FIFO_RDREG
            ISSUE: state_q <= (READ_LATENCY > 1) ? WAIT : (PIPELINE_COMPARE != 0) ? CAPTURE : CHECK;
            WAIT: state_q <= (PIPELINE_COMPARE != 0) ? CAPTURE : CHECK;
`else
            ISSUE: state_q <= (PIPELINE_COMPARE != 0) ? CAPTURE : CHECK;
`endif
            CAPTURE: begin
                read_data_q <= rdata_i;
                state_q <= CHECK;
            end
            CHECK: begin
                if (compare_data !== {WIDTH{1'b0}}) begin
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
`ifdef SOC_ETH_FIFO_RDREG
`ifndef SYNTHESIS
    initial if (READ_LATENCY != 1 && READ_LATENCY != 2)
        $fatal(1, "soc_sram_zero_check supports READ_LATENCY 1 or 2");
`endif
`endif
endmodule
`default_nettype wire
