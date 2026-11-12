// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// 2048x16 FIFO memory: eight physical 256x16 true dual-port SRAMs.
// No switched clocks. POR -> March A -> B reads A's zeros -> March B ->
// A reads B's zeros -> release. Sticky completion/failure crosses via 2 FFs.
// Missing either clock prevents release. Functional reset/flush does not rerun
// the destructive test. All 16 physical bits are tested (including unused bits).
// SOC_ETH_FIFO_RDREG (docs/combined-timing.md): every bank's output is
// registered next to its macro and the bank multiplexer follows that
// register, so no logic follows a macro output in the cycle of the read.
// Reads then take two edges; the FIFO runs with one more RAM pipeline
// stage and the self-test engines with READ_LATENCY 2.
// SOC_ETH_FIFO_WRREG (docs/combined-timing.md section 15): the functional
// write (per-bank enable, address, data) is registered next to the macros
// and reaches port A one write-clock edge later. See the block below for
// why the frame FIFO cannot read a word before its delayed write.
module soc_eth_fifo_sram (
    input wire wclk_i, rclk_i, por_ni,
    input wire wreset_i, rreset_i,
    input wire wen_i, ren_i,
`ifdef SOC_ETH_FIFO_RDREG
    // Load enable of the registered read stage (read clock): the FIFO's
    // pipeline stage-1 enable. Ignored while the self-test owns port B.
    input wire rnext_i,
`endif
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
    // Separate the slow SRAM + bank mux response from March state updates.
`ifdef SOC_ETH_FIFO_RDREG
    soc_sram_mbist #(.WIDTH(16), .DEPTH(2048), .ADDR_WIDTH(11), .READ_LATENCY(2), .PIPELINE_COMPARE(1)) u_a (
`else
    soc_sram_mbist #(.WIDTH(16), .DEPTH(2048), .ADDR_WIDTH(11), .PIPELINE_COMPARE(1)) u_a (
`endif
        .clk_i(wclk_i), .rst_ni(wp[1]), .start_i(1'b1), .abort_i(1'b0),
        .rdata_i(aq), .req_o(areq), .we_o(awe), .addr_o(aa), .wdata_o(awd),
        .busy_o(), .done_o(adone), .failed_o(afail), .aborted_o(aabort),
        .fail_addr_o(), .fail_expected_o(), .fail_actual_o(), .fail_phase_o(), .fail_background_o());
`ifdef SOC_ETH_FIFO_RDREG
    soc_sram_zero_check #(.PIPELINE_COMPARE(1), .READ_LATENCY(2)) u_b_cross (
`else
    soc_sram_zero_check #(.PIPELINE_COMPARE(1)) u_b_cross (
`endif
        .clk_i(rclk_i), .rst_ni(rp[1]), .start_i(a_done_r[1] && !a_fail_r[1]),
        .rdata_i(bq), .req_o(bxreq), .addr_o(bxa), .done_o(bxdone), .failed_o(bxfail));
`ifdef SOC_ETH_FIFO_RDREG
    soc_sram_mbist #(.WIDTH(16), .DEPTH(2048), .ADDR_WIDTH(11), .READ_LATENCY(2), .PIPELINE_COMPARE(1)) u_b (
`else
    soc_sram_mbist #(.WIDTH(16), .DEPTH(2048), .ADDR_WIDTH(11), .PIPELINE_COMPARE(1)) u_b (
`endif
        .clk_i(rclk_i), .rst_ni(rp[1]), .start_i(bxdone && !bxfail), .abort_i(1'b0),
        .rdata_i(bq), .req_o(breq), .we_o(bwe), .addr_o(ba), .wdata_o(bwd),
        .busy_o(), .done_o(bdone), .failed_o(bfail), .aborted_o(babort),
        .fail_addr_o(), .fail_expected_o(), .fail_actual_o(), .fail_phase_o(), .fail_background_o());
`ifdef SOC_ETH_FIFO_RDREG
    soc_sram_zero_check #(.PIPELINE_COMPARE(1), .READ_LATENCY(2)) u_a_cross (
`else
    soc_sram_zero_check #(.PIPELINE_COMPARE(1)) u_a_cross (
`endif
        .clk_i(wclk_i), .rst_ni(wp[1]), .start_i(b_done_w[1] && !b_fail_w[1]),
        .rdata_i(aq), .req_o(axreq), .addr_o(axa), .done_o(axdone), .failed_o(axfail));
`ifdef SOC_ETH_FIFO_WRREG
    // The functional write is taken into registers in its cycle (one-hot
    // bank enable, row, data) and written at the next write-clock edge, so
    // the FIFO's full/drop logic ends at these flip-flops instead of at the
    // write and read enables of all eight macros. The self-test owns port
    // A only before release (done_o) and never again until power-on reset,
    // which also clears the enables, so its accesses are unchanged and are
    // never mixed with a registered write.
    // A word is read only after its frame is committed. With this define
    // the adapted frame FIFO (hw/soc/flow/adapt_eth_mbist.py) publishes the
    // commit to the read domain one write-clock edge later too: the read
    // side samples a registered copy of the commit toggle, which changes at
    // the edge that writes the frame's last word here. The read domain then
    // sees a commit only after the data under it is written, at any clock
    // ratio. A write in the last functional cycle before a functional
    // reset lands one edge into the reset; the FIFO's pointers are reset
    // and the word is not read.
    reg [7:0] wq_men;
    reg [7:0] wq_row;
    reg [15:0] wq_data;
    always @(posedge wclk_i or negedge por_ni)
        if (!por_ni) wq_men <= 8'd0;
        else wq_men <= (a_functional && wen_i) ? (8'd1 << waddr_i[10:8]) : 8'd0;
    always @(posedge wclk_i) begin
        wq_row <= waddr_i[7:0];
        wq_data <= wdata_i;
    end
    wire wq_val = |wq_men;
    wire am = areq || axreq || wq_val;
    wire bm = breq || bxreq || (b_functional && ren_i);
    wire aw = awe || wq_val;
    wire bw = bwe;
    wire [10:0] addr_a = adone ? axa : aa;
    wire [10:0] addr_b = b_functional ? raddr_i : (bxdone ? ba : bxa);
    wire [15:0] data_a = wq_val ? wq_data : awd;
`else
    wire am = areq || axreq || (a_functional && wen_i);
    wire bm = breq || bxreq || (b_functional && ren_i);
    wire aw = awe || (a_functional && wen_i);
    wire bw = bwe;
    wire [10:0] addr_a = a_functional ? waddr_i : (adone ? axa : aa);
    wire [10:0] addr_b = b_functional ? raddr_i : (bxdone ? ba : bxa);
    wire [15:0] data_a = a_functional ? wdata_i : awd;
`endif
    wire [15:0] bank_a [0:7];
    wire [15:0] bank_b [0:7];
    reg [2:0] sel_a, sel_b;
    // Select only on read; preserve macro output-hold behavior between requests.
    // (With SOC_ETH_FIFO_WRREG, am && !aw is a self-test read, whose
    // address is addr_a.)
    always @(posedge wclk_i or negedge por_ni)
        if (!por_ni) sel_a<=0; else if (am && !aw) sel_a<=addr_a[10:8];
    always @(posedge rclk_i or negedge por_ni)
        if (!por_ni) sel_b<=0; else if (bm && !bw) sel_b<=addr_b[10:8];
`ifdef SOC_ETH_FIFO_RDREG
    // The macro holds its output between reads, so a register that loads
    // in every cycle after a read holds the word the read returned. Port A
    // is read only by the self-test and loads every cycle. Port B is the
    // FIFO's stage 1 in functional mode (it loads with the FIFO's stage-1
    // enable, together with the bank select of the word) and loads every
    // cycle under the self-test. Data flops have no reset: nothing reads
    // them before a read has loaded them.
    // The bank select of the registered word is kept one-hot, so the
    // output is an AND-OR of eight registers with registered selects.
    reg [7:0] sel_a_oh_q, sel_b_oh_q;
    wire b_load = !b_functional || rnext_i;
    always @(posedge wclk_i or negedge por_ni)
        if (!por_ni) sel_a_oh_q<=8'd1; else sel_a_oh_q<=8'd1<<sel_a;
    always @(posedge rclk_i or negedge por_ni)
        if (!por_ni) sel_b_oh_q<=8'd1; else if (b_load) sel_b_oh_q<=8'd1<<sel_b;
    wire [15:0] or_a [0:8];
    wire [15:0] or_b [0:8];
    assign or_a[0] = 16'h0;
    assign or_b[0] = 16'h0;
    genvar rbank;
    generate for (rbank=0; rbank<8; rbank=rbank+1) begin: g_rdreg
        reg [15:0] qa, qb;
        always @(posedge wclk_i) qa <= bank_a[rbank];
        always @(posedge rclk_i) if (b_load) qb <= bank_b[rbank];
        assign or_a[rbank+1] = or_a[rbank] | (qa & {16{sel_a_oh_q[rbank]}});
        assign or_b[rbank+1] = or_b[rbank] | (qb & {16{sel_b_oh_q[rbank]}});
    end endgenerate
    assign aq = or_a[8];
    assign bq = or_b[8];
`else
    assign aq = bank_a[sel_a];
    assign bq = bank_b[sel_b];
`endif
    assign rdata_o = bq;
    genvar bank;
    generate for (bank=0; bank<8; bank=bank+1) begin: g_bank
        RM_IHPSG13_2P_256x16_c2_bm_bist u_mem (
`ifdef SOC_ETH_FIFO_WRREG
            .A_CLK(wclk_i), .A_MEN(((areq || axreq) && addr_a[10:8]==3'(bank)) || wq_men[bank]),
            .A_WEN(aw), .A_REN(!aw), .A_ADDR(wq_val ? wq_row : addr_a[7:0]), .A_DIN(data_a),
`else
            .A_CLK(wclk_i), .A_MEN(am && addr_a[10:8]==3'(bank)),
            .A_WEN(aw), .A_REN(!aw), .A_ADDR(addr_a[7:0]), .A_DIN(data_a),
`endif
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
