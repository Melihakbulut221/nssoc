// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Single-clock raw SRAM port arbiter. test_mode_i is an explicit destructive-test
// ownership grant, not a software enable. The integrator must quiesce the CPU,
// ECC/scrubber and every other port first. Do not switch clocks with this mux.
// Dropping test mode aborts a running test before releasing the functional port.
// A successful test leaves raw zeros, which may require ECC reinitialization.
module soc_sram_test_port #(
    parameter integer WIDTH = 16,
    parameter integer DEPTH = 256,
    parameter integer ADDR_WIDTH = (DEPTH > 1) ? $clog2(DEPTH) : 1,
    parameter integer READ_LATENCY = 1
) (
    input wire clk_i, rst_ni,
    input wire test_mode_i, start_i, abort_i,
    input wire func_req_i, func_we_i,
    input wire [ADDR_WIDTH-1:0] func_addr_i,
    input wire [WIDTH-1:0] func_wdata_i, func_wmask_i,
    output wire functional_ready_o,
    output wire mem_req_o, mem_we_o,
    output wire [ADDR_WIDTH-1:0] mem_addr_o,
    output wire [WIDTH-1:0] mem_wdata_o, mem_wmask_o,
    input wire [WIDTH-1:0] mem_rdata_i,
    output wire busy_o, done_o, failed_o, aborted_o,
    output wire [ADDR_WIDTH-1:0] fail_addr_o,
    output wire [WIDTH-1:0] fail_expected_o, fail_actual_o,
    output wire [2:0] fail_phase_o,
    output wire [7:0] fail_background_o
);
    wire bist_req, bist_we;
    wire [ADDR_WIDTH-1:0] bist_addr;
    wire [WIDTH-1:0] bist_data;
    soc_sram_mbist #(.WIDTH(WIDTH), .DEPTH(DEPTH), .ADDR_WIDTH(ADDR_WIDTH),
                    .READ_LATENCY(READ_LATENCY)) u_mbist (
        .clk_i(clk_i), .rst_ni(rst_ni), .start_i(start_i && test_mode_i),
        .abort_i(abort_i || !test_mode_i), .rdata_i(mem_rdata_i),
        .req_o(bist_req), .we_o(bist_we), .addr_o(bist_addr), .wdata_o(bist_data),
        .busy_o(busy_o), .done_o(done_o), .failed_o(failed_o), .aborted_o(aborted_o),
        .fail_addr_o(fail_addr_o), .fail_expected_o(fail_expected_o),
        .fail_actual_o(fail_actual_o), .fail_phase_o(fail_phase_o),
        .fail_background_o(fail_background_o));
    assign functional_ready_o = rst_ni && !test_mode_i && !busy_o;
    assign mem_req_o = bist_req || (functional_ready_o && func_req_i);
    assign mem_we_o = bist_we || (functional_ready_o && func_req_i && func_we_i);
    assign mem_addr_o = functional_ready_o ? func_addr_i : bist_addr;
    assign mem_wdata_o = functional_ready_o ? func_wdata_i : bist_data;
    assign mem_wmask_o = mem_we_o ? (functional_ready_o ? func_wmask_i : {WIDTH{1'b1}})
                                  : {WIDTH{1'b0}};
endmodule
`default_nettype wire
