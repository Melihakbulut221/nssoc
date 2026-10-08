// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none

// Destructive, raw-word SRAM March engine. The owner must isolate every other
// memory port and bypass ECC throughout the test. This is not wired to soc_top.
// Each background runs {up(wB), up(rB,w~B), up(r~B,wB),
// down(rB,w~B), down(r~B,wB), down(rB)}. Bit-partition backgrounds
// exercise unequal bits within a word; the last all-zero pass clears the array.
// READ_LATENCY counts rising edges from request sampling to valid read data.
// A one-edge synchronous RAM therefore uses READ_LATENCY=1. No ready/stall bus.
module soc_sram_mbist #(
    parameter integer WIDTH = 16,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = (DEPTH > 1) ? $clog2(DEPTH) : 1,
    parameter integer READ_LATENCY = 1
) (
    input wire clk_i,
    input wire rst_ni,
    input wire start_i,
    input wire abort_i,
    input wire [WIDTH-1:0] rdata_i,
    output wire req_o,
    output wire we_o,
    output wire [ADDR_WIDTH-1:0] addr_o,
    output wire [WIDTH-1:0] wdata_o,
    output wire busy_o,
    output reg done_o,
    output reg failed_o,
    output reg aborted_o,
    output reg [ADDR_WIDTH-1:0] fail_addr_o,
    output reg [WIDTH-1:0] fail_expected_o,
    output reg [WIDTH-1:0] fail_actual_o,
    output reg [2:0] fail_phase_o,
    output reg [7:0] fail_background_o
);
    localparam integer PARTITIONS = $clog2(WIDTH);
    localparam integer WAIT_WIDTH = (READ_LATENCY > 1) ? $clog2(READ_LATENCY) : 1;
    localparam [1:0] IDLE = 0, ISSUE = 1, READ = 2;
    reg [1:0] state_q;
    reg [2:0] phase_q;
    reg [7:0] background_q;
    reg [ADDR_WIDTH-1:0] address_q;
    reg [WAIT_WIDTH-1:0] wait_q;
    reg write_q, start_q;
    reg [WIDTH-1:0] background;
    integer bit_index;

    always @* begin
        background = {WIDTH{1'b0}};
        if (background_q > 0 && background_q <= 8'(PARTITIONS))
            for (bit_index = 0; bit_index < WIDTH; bit_index = bit_index + 1)
                background[bit_index] = ((bit_index >> (background_q - 1)) & 1) != 0;
    end
    wire [WIDTH-1:0] expected = (phase_q == 2 || phase_q == 4) ? ~background : background;
    assign busy_o = (state_q != IDLE);
    assign req_o = rst_ni && !abort_i && (state_q == ISSUE);
    assign we_o = req_o && (phase_q == 0 || write_q);
    assign addr_o = address_q;
    assign wdata_o = (phase_q == 1 || phase_q == 3) ? ~background : background;

    // Called only after a complete word's operations, never between read/write.
    task advance_word;
        begin
            write_q <= 1'b0;
            state_q <= ISSUE;
            if ((phase_q < 3 && address_q == ADDR_WIDTH'(DEPTH-1)) ||
                (phase_q >= 3 && address_q == 0)) begin
                if (phase_q == 5) begin
                    if (background_q == 8'(PARTITIONS + 1)) begin
                        state_q <= IDLE;
                        done_o <= 1'b1;
                    end else begin
                        background_q <= background_q + 1'b1;
                        phase_q <= 0;
                        address_q <= 0;
                    end
                end else begin
                    phase_q <= phase_q + 1'b1;
                    address_q <= (phase_q >= 2) ? ADDR_WIDTH'(DEPTH-1) : 0;
                end
            end else if (phase_q >= 3)
                address_q <= address_q - 1'b1;
            else
                address_q <= address_q + 1'b1;
        end
    endtask

    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q <= IDLE;
            phase_q <= 0;
            background_q <= 0;
            address_q <= 0;
            wait_q <= 0;
            write_q <= 0;
            start_q <= 0;
            done_o <= 0;
            failed_o <= 0;
            aborted_o <= 0;
            fail_addr_o <= 0;
            fail_expected_o <= 0;
            fail_actual_o <= 0;
            fail_phase_o <= 0;
            fail_background_o <= 0;
        end else begin
            start_q <= start_i;
            if (busy_o && abort_i) begin
                state_q <= IDLE;
                done_o <= 1;
                aborted_o <= 1;
            end else case (state_q)
                IDLE: if (start_i && !start_q && !abort_i) begin
                    state_q <= ISSUE;
                    phase_q <= 0;
                    background_q <= 0;
                    address_q <= 0;
                    write_q <= 0;
                    done_o <= 0;
                    failed_o <= 0;
                    aborted_o <= 0;
                    fail_addr_o <= 0;
                    fail_expected_o <= 0;
                    fail_actual_o <= 0;
                    fail_phase_o <= 0;
                    fail_background_o <= 0;
                end
                ISSUE: if (we_o) advance_word();
                       else begin
                           state_q <= READ;
                           wait_q <= WAIT_WIDTH'(READ_LATENCY-1);
                       end
                READ: if (wait_q != 0) wait_q <= wait_q - 1'b1;
                      else if (rdata_i !== expected) begin
                          // Case inequality also rejects X/Z in RTL simulation.
                          // Silicon comparison remains a binary comparator.
                          failed_o <= 1;
                          done_o <= 1;
                          state_q <= IDLE;
                          fail_addr_o <= address_q;
                          fail_expected_o <= expected;
                          fail_actual_o <= rdata_i;
                          fail_phase_o <= phase_q;
                          fail_background_o <= background_q;
                      end else if (phase_q == 5) advance_word();
                      else begin
                          write_q <= 1;
                          state_q <= ISSUE;
                      end
                default: begin
                    state_q <= IDLE;
                    done_o <= 1;
                    aborted_o <= 1;
                end
            endcase
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (WIDTH < 1 || DEPTH < 1 || READ_LATENCY < 1 ||
            ADDR_WIDTH < ((DEPTH > 1) ? $clog2(DEPTH) : 1))
            $fatal(1, "Invalid SRAM MBIST parameters");
    end
`endif
endmodule
`default_nettype wire
