// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// 2048x16 FIFO memory: eight physical 256x16 true dual-port SRAMs.
// No switched clocks. POR -> March A -> B reads A's zeros -> March B ->
// A reads B's zeros -> release. Sticky completion/failure crosses via 2 FFs.
// Missing either clock prevents release. Functional reset/flush does not rerun
// the destructive test. All 16 physical bits are tested (including unused bits).
module soc_eth_fifo_sram (
    input wire wclk_i, rclk_i, por_ni,
    input wire wreset_i, rreset_i,
    input wire wen_i, ren_i,
    input wire [10:0] waddr_i, raddr_i,
    input wire [15:0] wdata_i,
    output wire [15:0] rdata_o,
    // Outputs in wclk domain; receiver must synchronize them.
    output wire done_o, failed_o
);
    (* ASYNC_REG = "TRUE" *) reg [1:0] wp, rp;
    always @(posedge wclk_i or negedge por_ni)
        if (!por_ni) wp <= 0; else wp <= {wp[0],1'b1};
    always @(posedge rclk_i or negedge por_ni)
        if (!por_ni) rp <= 0; else rp <= {rp[0],1'b1};
    wire adone, afail, aabort, bdone, bfail, babort;
    wire axdone, axfail, bxdone, bxfail;
    (* ASYNC_REG = "TRUE" *) reg [1:0] a_done_r, a_fail_r, b_done_w, b_fail_w, release_r;
    wire a_finished = adone;
    wire a_failed = afail || aabort;
    wire b_finished = (bxdone && bxfail) || bdone;
    wire b_failed = bxfail || bfail || babort;
    always @(posedge rclk_i or negedge por_ni) begin
        if (!por_ni) begin a_done_r<=0; a_fail_r<=0; release_r<=0; end
        else begin
            a_done_r <= {a_done_r[0],a_finished};
            a_fail_r <= {a_fail_r[0],a_failed};
            release_r <= {release_r[0],done_o && !failed_o};
        end
    end
    always @(posedge wclk_i or negedge por_ni) begin
        if (!por_ni) begin b_done_w<=0; b_fail_w<=0; end
        else begin
            b_done_w <= {b_done_w[0],b_finished};
            b_fail_w <= {b_fail_w[0],b_failed};
        end
    end
    assign done_o = adone && (a_failed || (b_done_w[1] && (b_fail_w[1] || axdone)));
    assign failed_o = a_failed || b_fail_w[1] || axfail;
    wire a_functional = wp[1] && done_o && !failed_o && !wreset_i;
    wire b_functional = rp[1] && release_r[1] && !rreset_i;
    wire areq, awe, breq, bwe, axreq, bxreq;
    wire [10:0] aa, ba, axa, bxa;
    wire [15:0] awd, bwd;
    wire [15:0] aq, bq;
    soc_sram_mbist #(.WIDTH(16), .DEPTH(2048), .ADDR_WIDTH(11)) u_a (
        .clk_i(wclk_i), .rst_ni(wp[1]), .start_i(1'b1), .abort_i(1'b0),
        .rdata_i(aq), .req_o(areq), .we_o(awe), .addr_o(aa), .wdata_o(awd),
        .busy_o(), .done_o(adone), .failed_o(afail), .aborted_o(aabort),
        .fail_addr_o(), .fail_expected_o(), .fail_actual_o(), .fail_phase_o(), .fail_background_o());
    soc_sram_zero_check u_b_cross (
        .clk_i(rclk_i), .rst_ni(rp[1]), .start_i(a_done_r[1] && !a_fail_r[1]),
        .rdata_i(bq), .req_o(bxreq), .addr_o(bxa), .done_o(bxdone), .failed_o(bxfail));
    soc_sram_mbist #(.WIDTH(16), .DEPTH(2048), .ADDR_WIDTH(11)) u_b (
        .clk_i(rclk_i), .rst_ni(rp[1]), .start_i(bxdone && !bxfail), .abort_i(1'b0),
        .rdata_i(bq), .req_o(breq), .we_o(bwe), .addr_o(ba), .wdata_o(bwd),
        .busy_o(), .done_o(bdone), .failed_o(bfail), .aborted_o(babort),
        .fail_addr_o(), .fail_expected_o(), .fail_actual_o(), .fail_phase_o(), .fail_background_o());
    soc_sram_zero_check u_a_cross (
        .clk_i(wclk_i), .rst_ni(wp[1]), .start_i(b_done_w[1] && !b_fail_w[1]),
        .rdata_i(aq), .req_o(axreq), .addr_o(axa), .done_o(axdone), .failed_o(axfail));
    wire am = areq || axreq || (a_functional && wen_i);
    wire bm = breq || bxreq || (b_functional && ren_i);
    wire aw = awe || (a_functional && wen_i);
    wire bw = bwe;
    wire [10:0] addr_a = a_functional ? waddr_i : (adone ? axa : aa);
    wire [10:0] addr_b = b_functional ? raddr_i : (bxdone ? ba : bxa);
    wire [15:0] data_a = a_functional ? wdata_i : awd;
    wire [15:0] bank_a [0:7];
    wire [15:0] bank_b [0:7];
    reg [2:0] sel_a, sel_b;
    // Select only on read; preserve macro output-hold behavior between requests.
    always @(posedge wclk_i or negedge por_ni)
        if (!por_ni) sel_a<=0; else if (am && !aw) sel_a<=addr_a[10:8];
    always @(posedge rclk_i or negedge por_ni)
        if (!por_ni) sel_b<=0; else if (bm && !bw) sel_b<=addr_b[10:8];
    assign aq = bank_a[sel_a];
    assign bq = bank_b[sel_b];
    assign rdata_o = bq;
    genvar bank;
    generate for (bank=0; bank<8; bank=bank+1) begin: g_bank
        RM_IHPSG13_2P_256x16_c2_bm_bist u_mem (
            .A_CLK(wclk_i), .A_MEN(am && addr_a[10:8]==3'(bank)),
            .A_WEN(aw), .A_REN(!aw), .A_ADDR(addr_a[7:0]), .A_DIN(data_a),
            .A_BM(16'hffff), .A_DLY(1'b0), .A_DOUT(bank_a[bank]),
            .A_BIST_CLK(1'b0), .A_BIST_EN(1'b0), .A_BIST_MEN(1'b0), .A_BIST_WEN(1'b0),
            .A_BIST_REN(1'b0), .A_BIST_ADDR(8'b0), .A_BIST_DIN(16'b0), .A_BIST_BM(16'b0),
            .B_CLK(rclk_i), .B_MEN(bm && addr_b[10:8]==3'(bank)),
            .B_WEN(bw), .B_REN(!bw), .B_ADDR(addr_b[7:0]), .B_DIN(bwd),
            .B_BM(16'hffff), .B_DLY(1'b0), .B_DOUT(bank_b[bank]),
            .B_BIST_CLK(1'b0), .B_BIST_EN(1'b0), .B_BIST_MEN(1'b0), .B_BIST_WEN(1'b0),
            .B_BIST_REN(1'b0), .B_BIST_ADDR(8'b0), .B_BIST_DIN(16'b0), .B_BIST_BM(16'b0));
    end endgenerate
endmodule
`default_nettype wire
