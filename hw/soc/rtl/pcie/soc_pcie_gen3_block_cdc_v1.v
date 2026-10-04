// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// One recovered-clock lane of complete aligned blocks to a common clock.
// No input backpressure: an unaccepted live block permanently faults the epoch.
// Preserve all 194 bits, length and three metadata bits. No SKP compensation,
// lane deskew, packet integrity policy or physical CDC qualification is implied.
// Either reset request is a clean level reset of BOTH clock domains. Assertion
// is asynchronous; each release is synchronized. A stopped clock holds startup.
// Fault crosses as a held bit: a valid buffered prefix may retire before the
// common domain observes fault. It then invalidates pending output until reset.
module soc_pcie_gen3_block_cdc_v1 #(
    parameter DEPTH = 32
) (
    input wire por_ni,
    input wire wr_clk_i, rd_clk_i,
    input wire wr_reset_i, rd_reset_i,
    input wire wr_valid_i,
    input wire [193:0] wr_block_i,
    input wire [2:0] wr_length_code_i,
    input wire wr_skp_i, wr_eieos_i, wr_realign_i, wr_loss_i,
    output wire wr_running_o,
    output wire wr_accept_o,
    output reg wr_fault_o,
    output reg wr_overflow_o,
    output wire rd_running_o,
    output wire rd_fault_o,
    output wire rd_valid_o,
    input wire rd_ready_i,
    output wire [193:0] rd_block_o,
    output wire [2:0] rd_length_code_o,
    output wire rd_skp_o, rd_eieos_o, rd_realign_o
);
    generate if (DEPTH < 4 || (DEPTH & (DEPTH-1)) != 0) begin: bad_depth
        ERROR_block_cdc_DEPTH_must_be_power_of_two_ge_4 invalid();
    end endgenerate
    wire reset_request = !por_ni || wr_reset_i || rd_reset_i;
    (* ASYNC_REG = "TRUE" *) reg [2:0] wr_reset_q, rd_reset_q;
    always @(posedge wr_clk_i or posedge reset_request)
        if (reset_request) wr_reset_q <= 3'b111;
        else wr_reset_q <= {wr_reset_q[1:0],1'b0};
    always @(posedge rd_clk_i or posedge reset_request)
        if (reset_request) rd_reset_q <= 3'b111;
        else rd_reset_q <= {rd_reset_q[1:0],1'b0};
    wire wr_reset = wr_reset_q[2];
    wire rd_reset = rd_reset_q[2];
    reg [3:0] wr_boot_q, rd_boot_q;
    always @(posedge wr_clk_i or posedge reset_request)
        if (reset_request) wr_boot_q <= 0;
        else if (wr_reset) wr_boot_q <= 0;
        else wr_boot_q <= {wr_boot_q[2:0],1'b1};
    always @(posedge rd_clk_i or posedge reset_request)
        if (reset_request) rd_boot_q <= 0;
        else if (rd_reset) rd_boot_q <= 0;
        else rd_boot_q <= {rd_boot_q[2:0],1'b1};
    (* ASYNC_REG = "TRUE" *) reg [1:0] rd_up_in_wr, wr_up_in_rd, fault_in_rd;
    always @(posedge wr_clk_i or posedge reset_request)
        if (reset_request) rd_up_in_wr <= 0;
        else rd_up_in_wr <= {rd_up_in_wr[0],rd_boot_q[3]};
    always @(posedge rd_clk_i or posedge reset_request)
        if (reset_request) begin wr_up_in_rd <= 0; fault_in_rd <= 0; end
        else begin
            wr_up_in_rd <= {wr_up_in_rd[0],wr_boot_q[3]};
            fault_in_rd <= {fault_in_rd[0],wr_fault_o};
        end
    assign wr_running_o = !reset_request && wr_boot_q[3] && rd_up_in_wr[1] && !wr_fault_o;
    assign rd_fault_o = !reset_request && fault_in_rd[1];
    assign rd_running_o = !reset_request && rd_boot_q[3] && wr_up_in_rd[1] && !rd_fault_o;
    wire [199:0] source_record = {wr_realign_i,wr_eieos_i,wr_skp_i,wr_length_code_i,wr_block_i};
    wire [199:0] sink_record;
    wire source_ready, sink_valid;
    wire legal_length = wr_length_code_i <= 3'd4;
    wire source_valid = wr_running_o && wr_valid_i && legal_length && !wr_loss_i;
    assign wr_accept_o = source_valid && source_ready;
    always @(posedge wr_clk_i or posedge reset_request) begin
        if (reset_request) begin wr_fault_o <= 0; wr_overflow_o <= 0; end
        else if (wr_running_o) begin
            if (wr_loss_i || (wr_valid_i && !legal_length)) wr_fault_o <= 1'b1;
            if (wr_valid_i && legal_length && !wr_loss_i && !source_ready) begin
                wr_fault_o <= 1'b1;
                wr_overflow_o <= 1'b1;
            end
        end
    end
    assign rd_valid_o = rd_running_o && sink_valid;
    assign {rd_realign_o,rd_eieos_o,rd_skp_o,rd_length_code_o,rd_block_o} = sink_record;
    // Existing MIT-licensed Alex Forencich core. Pin exactly one vendor copy in
    // the build; Ethernet and standalone verilog-axis copies share module name.
    // DEPTH RAM records plus RAM_PIPELINE+1 = 2 prefetched read records.
    axis_async_fifo #(
        .DEPTH(DEPTH), .DATA_WIDTH(200), .KEEP_ENABLE(0), .KEEP_WIDTH(1),
        .LAST_ENABLE(0), .ID_ENABLE(0), .ID_WIDTH(1), .DEST_ENABLE(0),
        .DEST_WIDTH(1), .USER_ENABLE(0), .USER_WIDTH(1),
        .RAM_PIPELINE(1), .OUTPUT_FIFO_ENABLE(0), .FRAME_FIFO(0),
        .DROP_OVERSIZE_FRAME(0), .DROP_BAD_FRAME(0), .DROP_WHEN_FULL(0),
        .MARK_WHEN_FULL(0), .PAUSE_ENABLE(0), .FRAME_PAUSE(0)
    ) u_fifo (
        .s_clk(wr_clk_i), .s_rst(wr_reset),
        .s_axis_tdata(source_record), .s_axis_tkeep(1'b1),
        .s_axis_tvalid(source_valid), .s_axis_tready(source_ready),
        .s_axis_tlast(1'b0), .s_axis_tid(1'b0), .s_axis_tdest(1'b0), .s_axis_tuser(1'b0),
        .m_clk(rd_clk_i), .m_rst(rd_reset),
        .m_axis_tdata(sink_record), .m_axis_tkeep(),
        .m_axis_tvalid(sink_valid), .m_axis_tready(rd_running_o && rd_ready_i),
        .m_axis_tlast(), .m_axis_tid(), .m_axis_tdest(), .m_axis_tuser(),
        .s_pause_req(1'b0), .s_pause_ack(), .m_pause_req(1'b0), .m_pause_ack(),
        .s_status_depth(), .s_status_depth_commit(), .s_status_overflow(),
        .s_status_bad_frame(), .s_status_good_frame(), .m_status_depth(),
        .m_status_depth_commit(), .m_status_overflow(), .m_status_bad_frame(),
        .m_status_good_frame()
    );
endmodule
`default_nettype wire
