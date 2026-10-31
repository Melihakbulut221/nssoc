// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Shared raw32-to-complete-record front, before any descrambler or training owner.
// One aligner and one original record CDC per physical lane. No input backpressure.
// record_* and common_* belong to common_clk_i; lane_* belongs to that lane's
// recovered clock. align_control_i/force_realign_i must already belong to the
// corresponding recovered domain. This module supplies no cross-domain command
// mailbox, stopped-clock detector, LTSSM, logical-lane mapping or PHY acceptance.
// reset_i is the original clean coordinated level reset. Each lane retains its
// own startup/fault barrier; a consumer is responsible for an all-lane barrier.
// A valid prefix may retire before the synchronized lane fault arrives.
module soc_pcie_gen3_recovered_front_x4_v1 #(parameter FIFO_DEPTH=32) (
    input wire por_ni, reset_i,
    input wire [3:0] recovered_clk_i,
    input wire common_clk_i,
    input wire [3:0] raw_valid_i,
    input wire [127:0] raw_i,
    input wire [3:0] align_control_i, force_realign_i,
    output wire [3:0] lane_running_o, lane_aligned_o, lane_locked_o, lane_fault_o,
    output wire [3:0] common_running_o, common_fault_o,
    output wire [3:0] record_valid_o,
    input wire [3:0] record_ready_i,
    output wire [775:0] record_block_o,
    output wire [11:0] record_length_code_o,
    output wire [3:0] record_skp_o, record_eieos_o, record_realign_o
);
    genvar lane;
    generate for (lane=0; lane<4; lane=lane+1) begin: lanes
        wire aligned, locked, block_valid, skp, eieos, realign, loss;
        wire [193:0] block_data;
        wire [2:0] block_length;
        assign lane_aligned_o[lane]=lane_running_o[lane] && aligned;
        assign lane_locked_o[lane]=lane_running_o[lane] && locked;
        soc_pcie_gen3_lane_align_v3 aligner (
            .clk_i(recovered_clk_i[lane]), .rst_ni(lane_running_o[lane]),
            .raw_valid_i(raw_valid_i[lane]), .raw_i(raw_i[lane*32 +: 32]),
            .block_align_control_i(align_control_i[lane]),
            .force_realign_i(force_realign_i[lane]),
            .aligned_o(aligned), .block_valid_o(block_valid),
            .block_o(block_data), .length_code_o(block_length),
            .skp_o(skp), .eieos_o(eieos), .realign_o(realign), .loss_o(loss),
            .locked_o(locked), .sds_o()
        );
        soc_pcie_gen3_block_cdc_v1 #(.DEPTH(FIFO_DEPTH)) crossing (
            .por_ni(por_ni), .wr_clk_i(recovered_clk_i[lane]),
            .rd_clk_i(common_clk_i), .wr_reset_i(reset_i), .rd_reset_i(reset_i),
            .wr_valid_i(block_valid), .wr_block_i(block_data),
            .wr_length_code_i(block_length), .wr_skp_i(skp),
            .wr_eieos_i(eieos), .wr_realign_i(realign), .wr_loss_i(loss),
            .wr_running_o(lane_running_o[lane]), .wr_accept_o(),
            .wr_fault_o(lane_fault_o[lane]), .wr_overflow_o(),
            .rd_running_o(common_running_o[lane]), .rd_fault_o(common_fault_o[lane]),
            .rd_valid_o(record_valid_o[lane]), .rd_ready_i(record_ready_i[lane]),
            .rd_block_o(record_block_o[lane*194 +: 194]),
            .rd_length_code_o(record_length_code_o[lane*3 +: 3]),
            .rd_skp_o(record_skp_o[lane]), .rd_eieos_o(record_eieos_o[lane]),
            .rd_realign_o(record_realign_o[lane])
        );
    end endgenerate
endmodule
`default_nettype wire
