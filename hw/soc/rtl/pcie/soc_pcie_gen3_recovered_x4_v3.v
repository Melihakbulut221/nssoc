// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Four raw 32-bit recovered lanes -> locally SDS-locked blocks -> four CDCs
// -> OS-aware descrambling -> common-clock SDS cohort / DATA ordinal deskew. DATA and lossless
// variable SKP records remain separate outputs. SKP state/parity diagnostics are
// sticky status; only format/transport faults abort. No EDS/strictSKPcohort policy,
// complete LTSSM/equalization or physical clock qualification.
// reset_i is a clean coordinated level reset across all domains. The MAC arms
// once after lanes_ready_o, in an SDS-eligible state and before fresh training.
// active_o deassertion or fault_o aborts the entire downstream packet epoch.
// lane_* signals belong to their respective recovered clocks, not common_clk_i.
module soc_pcie_gen3_recovered_x4_v3 #(
    parameter FIFO_DEPTH=32,
    parameter MAX_SKEW_CYCLES=64
) (
    input wire por_ni, reset_i,
    input wire [3:0] recovered_clk_i,
    input wire common_clk_i,
    input wire [3:0] raw_valid_i,
    input wire [127:0] raw_i,
    input wire [3:0] align_control_i, force_realign_i,
    input wire arm_i,
    output wire [3:0] lane_running_o, lane_aligned_o, lane_locked_o, lane_fault_o,
    output wire lanes_ready_o, stream_start_o, active_o, fault_o,
    output wire data_valid_o,
    input wire data_ready_i,
    output wire [511:0] data_o,
    output wire [3:0] lane_error_o, lfsr_mismatch_o,
    output wire [3:0] skp_valid_o,
    input wire [3:0] skp_ready_i,
    output wire [775:0] skp_block_o,
    output wire [11:0] skp_length_code_o
);
    wire [3:0] common_running, common_fault, common_valid, common_ready;
    wire [3:0] raw_valid, raw_ready, raw_skp, raw_eieos, raw_realign, decode_fault;
    wire [775:0] raw_block;
    wire [11:0] raw_length;
    wire [775:0] common_block;
    wire [11:0] common_length;
    wire [3:0] common_skp, common_eieos, common_realign;
    wire cohort_fault;
    wire front_fault=por_ni && !reset_i && (|common_fault) || (por_ni && !reset_i && (|decode_fault));
    wire front_ready=por_ni && !reset_i && (&common_running) && !front_fault;
    assign lanes_ready_o=front_ready && !cohort_fault;
    assign fault_o=por_ni && !reset_i && (front_fault || cohort_fault);
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
            .rd_running_o(common_running[lane]), .rd_fault_o(common_fault[lane]),
            .rd_valid_o(raw_valid[lane]), .rd_ready_i(front_ready && raw_ready[lane]),
            .rd_block_o(raw_block[lane*194 +: 194]),
            .rd_length_code_o(raw_length[lane*3 +: 3]),
            .rd_skp_o(raw_skp[lane]), .rd_eieos_o(raw_eieos[lane]),
            .rd_realign_o(raw_realign[lane])
        );
        soc_pcie_gen3_record_descrambler_v1 #(.LANE_ID(lane)) decoder (
            .clk_i(common_clk_i), .rst_ni(por_ni && !reset_i), .flush_i(1'b0),
            .valid_i(raw_valid[lane] && front_ready), .ready_o(raw_ready[lane]),
            .block_i(raw_block[lane*194 +: 194]), .length_code_i(raw_length[lane*3 +: 3]),
            .skp_i(raw_skp[lane]), .eieos_i(raw_eieos[lane]), .realign_i(raw_realign[lane]),
            .valid_o(common_valid[lane]), .ready_i(common_ready[lane] && front_ready),
            .block_o(common_block[lane*194 +: 194]), .length_code_o(common_length[lane*3 +: 3]),
            .skp_o(common_skp[lane]), .eieos_o(common_eieos[lane]), .realign_o(common_realign[lane]),
            .format_fault_o(decode_fault[lane]), .lane_error_o(lane_error_o[lane]),
            .lfsr_mismatch_o(lfsr_mismatch_o[lane])
        );
    end endgenerate
    soc_pcie_gen3_sds_deskew_v1 #(.MAX_SKEW_CYCLES(MAX_SKEW_CYCLES)) cohort (
        .clk_i(common_clk_i), .rst_ni(por_ni && !reset_i),
        .arm_i(arm_i), .upstream_fault_i(front_fault || (arm_i && !front_ready)),
        .valid_i(common_valid & {4{front_ready}}), .ready_o(common_ready),
        .block_i(common_block), .length_code_i(common_length),
        .skp_i(common_skp), .eieos_i(common_eieos), .realign_i(common_realign),
        .stream_start_o(stream_start_o), .active_o(active_o), .fault_o(cohort_fault),
        .data_valid_o(data_valid_o), .data_ready_i(data_ready_i), .data_o(data_o),
        .skp_valid_o(skp_valid_o), .skp_ready_i(skp_ready_i),
        .skp_block_o(skp_block_o), .skp_length_code_o(skp_length_code_o)
    );
endmodule
`default_nettype wire
