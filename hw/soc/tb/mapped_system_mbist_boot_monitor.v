// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
// Testbench-only observer. It drives no DUT signal and does not preload RAM.
module mapped_system_mbist_boot_monitor (
    input wire clk_i, rst_ni, busy_i, done_i, failed_i,
    output reg passed_o = 1'b0,
    output reg signed [31:0] busy_cycles_o = 0,
    output reg signed [31:0] done_cycle_o = -1
);
    integer cycles = 0;
    reg done_seen = 1'b0;
    // Match the existing mapped PCIe observer's reset-settling allowance.
    // The real8192-row March test is much longer than this32-cycle interval.
    always @(negedge clk_i) begin
        if (!rst_ni) begin
            cycles = 0; busy_cycles_o = 0; done_cycle_o = -1;
            done_seen = 1'b0; passed_o = 1'b0;
        end else begin
            cycles = cycles + 1;
            if (cycles > 32) begin
                if (((busy_i !== 1'b0) && (busy_i !== 1'b1)) || ((done_i !== 1'b0) && (done_i !== 1'b1)) || ((failed_i !== 1'b0) && (failed_i !== 1'b1)) )
                    $fatal(1,"MBIST_MONITOR unknown mapped status");
                if (failed_i !== 1'b0)
                    $fatal(1,"MBIST_MONITOR native SRAM test failure");
                if (done_seen && done_i !== 1'b1)
                    $fatal(1,"MBIST_MONITOR completion dropped without external reset");
                if (done_i === 1'b1) begin
                    if (busy_i !== 1'b0 || busy_cycles_o == 0)
                        $fatal(1,"MBIST_MONITOR invalid or unobserved test handover");
                    if (!done_seen) done_cycle_o = cycles;
                    done_seen = 1'b1;
                    passed_o = 1'b1;
                end else begin
                    if (busy_i !== 1'b1)
                        $fatal(1,"MBIST_MONITOR neither busy nor complete");
                    busy_cycles_o = busy_cycles_o + 1;
                end
            end
        end
    end
endmodule
