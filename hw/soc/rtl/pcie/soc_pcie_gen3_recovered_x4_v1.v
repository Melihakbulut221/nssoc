// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Four independent recovered 32-bit lanes to complete common-clock records.
// Outputs retain lane identity; they are NOT yet deskewed or SKP-compensated.
// Each align_control/force_realign/raw input belongs to its recovered clock.
// reset_i is a clean coordinated level reset, asynchronously asserted in all
// domains. CDC blocks synchronize release and exchange startup acknowledgments.
// A synchronized fault aborts the entire output epoch. A valid buffered prefix
// may retire before fault crosses; the downstream parser must discard the epoch.
module soc_pcie_gen3_recovered_x4_v1 #(
    parameter FIFO_DEPTH = 32
) (
    input wire por_ni, reset_i,
    input wire [3:0] recovered_clk_i,
    input wire common_clk_i,
    input wire [3:0] raw_valid_i,
    input wire [127:0] raw_i,
    input wire [3:0] align_control_i, force_realign_i,
    output wire [3:0] lane_running_o, lane_aligned_o, lane_fault_o,
    output wire active_o, fault_o,
    output wire [3:0] valid_o,
    input wire [3:0] ready_i,
    output wire [775:0] block_o,
    output wire [11:0] length_code_o,
    output wire [3:0] skp_o, eieos_o, realign_o
);
    wire [3:0] common_running, common_fault;
    assign fault_o = por_ni && !reset_i && (|common_fault);
    assign active_o = por_ni && !reset_i && (&common_running) && !fault_o;
    genvar lane;
    generate for (lane=0; lane<4; lane=lane+1) begin: lanes
        wire aligned, block_valid, skp, eieos, realign, loss;
        wire [193:0] block_data;
        wire [2:0] block_length;
        wire common_valid;
        assign lane_aligned_o[lane] = lane_running_o[lane] && aligned;
        assign valid_o[lane] = active_o && common_valid;
        soc_pcie_gen3_lane_align_v2 aligner (
            .clk_i(recovered_clk_i[lane]),
            .rst_ni(lane_running_o[lane]),
            .raw_valid_i(raw_valid_i[lane]), .raw_i(raw_i[lane*32 +: 32]),
            .block_align_control_i(align_control_i[lane]),
            .force_realign_i(force_realign_i[lane]),
            .aligned_o(aligned), .block_valid_o(block_valid),
            .block_o(block_data), .length_code_o(block_length),
            .skp_o(skp), .eieos_o(eieos), .realign_o(realign), .loss_o(loss)
        );
        soc_pcie_gen3_block_cdc_v1 #(.DEPTH(FIFO_DEPTH)) crossing (
            .por_ni(por_ni), .wr_clk_i(recovered_clk_i[lane]),
            .rd_clk_i(common_clk_i), .wr_reset_i(reset_i), .rd_reset_i(reset_i),
            .wr_valid_i(block_valid), .wr_block_i(block_data),
            .wr_length_code_i(block_length), .wr_skp_i(skp),
            .wr_eieos_i(eieos), .wr_realign_i(realign), .wr_loss_i(loss),
            .wr_running_o(lane_running_o[lane]), .wr_accept_o(),
            .wr_fault_o(lane_fault_o[lane]), .wr_overflow_o(),
            .rd_running_o(common_running[lane]), .rd_fault_o(common_fault[lane]),
            .rd_valid_o(common_valid), .rd_ready_i(active_o && ready_i[lane]),
            .rd_block_o(block_o[lane*194 +: 194]),
            .rd_length_code_o(length_code_o[lane*3 +: 3]),
            .rd_skp_o(skp_o[lane]), .rd_eieos_o(eieos_o[lane]),
            .rd_realign_o(realign_o[lane])
        );
    end endgenerate
endmodule
`default_nettype wire
