// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps

// Self-checking bench for the execute-path knobs of
// hw/soc/rtl/ibex_regfile_secded.v (docs/ibex-execute-timing.md):
// CHKDEFER (deferred check bits), RDPRE (predecoded read address) and the
// RDRAW measurement, against a golden architectural model.
//
// Every cycle: a random write (often to the register written the cycle
// before), two reads biased to the register written the cycle before and
// to the one being written now, and, at random, a single or double upset
// injected into a data or check flip-flop of a random register,
// including the pending one. Checked every cycle:
//   * read data equals the architectural value (except RDRAW on an upset
//     register, which is the measurement's documented hole);
//   * no SEC or DED report on reads of clean registers;
//   * DED reported on a same-cycle read of a register with two upsets
//     that is not pending;
//   * SEC reported on a same-cycle read of a register with one upset
//     that is not pending (correcting builds).
// At the end the writes stop, the scrub runs, and every register must
// read clean and correct. BADPRE=1 corrupts the predecode once and must
// stop the run (negative control of the RDPRE cross-check).
module tb_regfile_exec;
  parameter integer CORRPRE  = 0;
  parameter integer CHKDEFER = 0;
  parameter integer RDPRE    = 0;
  parameter integer RDRAW    = 0;
  parameter integer SCRUB    = 1;
  parameter integer CYCLES   = 20000;
  parameter integer SEED     = 1;
  parameter integer BADPRE   = 0;

  reg clk = 1'b0;
  always #5 clk = ~clk;
  reg rst_n = 1'b0;

  reg  [4:0]  ra, rb, wa;
  reg  [31:0] wd;
  reg         we;
  wire [31:0] rda, rdb;
  wire [2:0]  err;
  reg         bad_pre = 1'b0;

  function [11:0] pre;
    input [4:0] a;
    pre = {(8'd1 << a[2:0]), (4'd1 << a[4:3])};
  endfunction
  wire [34:0] wcap = {11'h0, pre(rb), pre(ra)} ^ {34'h0, bad_pre};

  ibex_register_file_ff #(
      .BaseIsa(0), .RV32E(0), .DataWidth(32), .DummyInstructions(0),
      .SCRUB(SCRUB), .CORRPRE(CORRPRE), .CHKDEFER(CHKDEFER),
      .RDPRE(RDPRE), .RDRAW(RDRAW)
  ) dut (
      .clk_i(clk), .rst_ni(rst_n), .test_en_i(1'b0),
      .dummy_instr_id_i(1'b0), .dummy_instr_wb_i(1'b0),
      .cheriot_enable_i(4'b1010),
      .raddr_a_i(ra), .rdata_a_o(rda), .rcap_a_o(),
      .raddr_b_i(rb), .rdata_b_o(rdb), .rcap_b_o(),
      .waddr_a_i(wa), .wdata_a_i(wd), .wcap_a_i(wcap), .we_a_i(we),
      .rf_ecc_err_o(err));

  // ---- golden model ------------------------------------------------
  reg [31:0] arch [0:31];
  // 0 clean, 1 one upset outstanding, 2 two upsets (value unknown until
  // rewritten). An upset is "outstanding" until the register is written;
  // the scrub may repair a single one earlier, which the checks allow.
  reg [1:0]  bad  [0:31];
  integer i, cyc, nerr, n_sec_seen, n_ded_seen, n_inj1, n_inj2, n_hazard;
  integer seed;

  // ---- injection: flip one bit of a data or check flip-flop ----------
  reg        inj_go;
  reg [4:0]  inj_reg;
  reg        inj_chk;
  reg [5:0]  inj_bit;
  reg        inj_two;
  reg [4:0]  inj_bit2;
  genvar gr;
  generate
    for (gr = 1; gr < 32; gr = gr + 1) begin : g_inj
      // #1 after the edge: the stimulus below is chosen at the edge itself.
      always @(negedge clk) begin
        #1;
        if (inj_go && inj_reg == gr) begin
          if (inj_chk)
            dut.g_plain_rf.g_rf_flops[gr].g_chk.rf_chk_q[inj_bit[2:0]] =
              ~dut.g_plain_rf.g_rf_flops[gr].g_chk.rf_chk_q[inj_bit[2:0]];
          else begin
            dut.g_plain_rf.g_rf_flops[gr].rf_reg_q[inj_bit[4:0]] =
              ~dut.g_plain_rf.g_rf_flops[gr].rf_reg_q[inj_bit[4:0]];
            if (inj_two)
              dut.g_plain_rf.g_rf_flops[gr].rf_reg_q[inj_bit2] =
                ~dut.g_plain_rf.g_rf_flops[gr].rf_reg_q[inj_bit2];
          end
        end
      end
    end
  endgenerate

  // Which register is pending (CHKDEFER) in the current cycle.
  wire       pend_v;
  wire [4:0] pend_a;
  generate
    if (CHKDEFER != 0) begin : g_peek
      assign pend_v = dut.g_plain_rf.g_chkdefer.pend_v_q;
      assign pend_a = dut.g_plain_rf.g_chkdefer.pend_a_q;
    end else begin : g_nopeek
      assign pend_v = 1'b0;
      assign pend_a = 5'd0;
    end
  endgenerate

  // Stimulus for the next cycle, chosen at the negedge.
  reg [4:0] prev_wa;
  reg       prev_we;
  reg       dbl_pending;    // a double upset was injected this cycle
  reg [4:0] dbl_reg;
  reg       sgl_now;        // a single upset was injected this cycle
  reg [4:0] sgl_reg;
  reg       inject;

  task fail;
    input [8*80-1:0] what;
    begin
      $display("FAIL cycle %0d: %0s  ra=%0d rda=%h exp=%h bad=%0d  rb=%0d rdb=%h exp=%h bad=%0d  err=%b pend=%b/%0d",
               cyc, what, ra, rda, arch[ra], bad[ra], rb, rdb, arch[rb], bad[rb], err, pend_v, pend_a);
      nerr = nerr + 1;
      if (nerr > 10) $fatal(1, "too many failures");
    end
  endtask

  // ---- checks at the end of each cycle ------------------------------
  wire pa = pend_v && (pend_a == ra);
  wire pb = pend_v && (pend_a == rb);
  always @(posedge clk) if (rst_n) begin
    // data
    if (!(RDRAW && bad[ra] != 0) && bad[ra] != 2 && rda !== arch[ra]) fail("port a data");
    if (!(RDRAW && bad[rb] != 0) && bad[rb] != 2 && rdb !== arch[rb]) fail("port b data");
    // no false read reports
    if (bad[ra] == 0 && bad[rb] == 0 && err[1]) fail("SEC on a clean read");
    if (err[2]) begin
      n_ded_seen = n_ded_seen + 1;
      if (!dbl_pending && !any_double(0)) fail("DED with no double upset anywhere");
    end
    if (err[1]) n_sec_seen = n_sec_seen + 1;
    // required reports on same-cycle reads of a freshly upset register
    if (dbl_pending && ((ra == dbl_reg && !pa) || (rb == dbl_reg && !pb)) && !err[2])
      fail("double upset read without DED");
    if (sgl_now && !RDRAW && ((ra == sgl_reg && !pa && bad[ra] == 1) ||
                              (rb == sgl_reg && !pb && bad[rb] == 1)) && !err[1])
      fail("single upset read without SEC");
    // golden update
    if (we && wa != 5'd0) begin
      arch[wa] = wd;
      bad[wa]  = 2'd0;
    end
    cyc = cyc + 1;
  end

  function any_double;
    input dummy;
    integer k;
    begin
      any_double = 1'b0;
      for (k = 1; k < 32; k = k + 1) if (bad[k] == 2) any_double = 1'b1;
    end
  endfunction

  // ---- stimulus ------------------------------------------------------
  initial begin
    seed = SEED;
    nerr = 0; cyc = 0; n_sec_seen = 0; n_ded_seen = 0; n_inj1 = 0; n_inj2 = 0; n_hazard = 0;
    for (i = 0; i < 32; i = i + 1) begin arch[i] = 32'h0; bad[i] = 2'd0; end
    ra = 0; rb = 0; wa = 0; wd = 0; we = 0; inj_go = 0; inj_reg = 1; inj_chk = 0; inj_bit = 0;
    inj_two = 0; inj_bit2 = 0;
    prev_wa = 0; prev_we = 0; dbl_pending = 0; dbl_reg = 0; sgl_now = 0; sgl_reg = 0;
    repeat (3) @(negedge clk);
    rst_n = 1'b1;
    while (cyc < CYCLES) begin
      @(negedge clk);
      // a double injected last cycle is now rewritten: write it back.
      dbl_pending = 1'b0;
      sgl_now = 1'b0;
      inj_go = 1'b0;
      if (BADPRE && cyc == CYCLES / 2) bad_pre = 1'b1; else bad_pre = 1'b0;
      // write
      we = ($random(seed) & 3) != 0;
      wa = (($random(seed) & 3) == 0 && prev_we) ? prev_wa : ($random(seed) & 31);
      wd = $random(seed);
      // reads: back-to-back hazards on purpose
      case ($random(seed) & 3)
        0: ra = prev_wa;
        1: ra = wa;
        default: ra = $random(seed) & 31;
      endcase
      case ($random(seed) & 3)
        0: rb = prev_wa;
        1: rb = wa;
        default: rb = $random(seed) & 31;
      endcase
      if (prev_we && (ra == prev_wa || rb == prev_wa)) n_hazard = n_hazard + 1;
      // injection
      inject = (($random(seed) & 15) == 0) && (cyc < CYCLES - 300);
      if (inject) begin
        inj_reg = 1 + ({$random(seed)} % 31);
        inj_two = 1'b0;
        if (bad[inj_reg] == 0 && ($random(seed) & 7) != 0) begin
          // single: one data bit or one of the seven used check bits
          inj_chk = ($random(seed) & 3) == 0;
          inj_bit = inj_chk ? ({$random(seed)} % 7) : ({$random(seed)} % 32);
          inj_go = 1'b1;
          bad[inj_reg] = 2'd1;
          sgl_now = 1'b1; sgl_reg = inj_reg;
          if ($random(seed) & 1) ra = inj_reg;
          n_inj1 = n_inj1 + 1;
        end else if (bad[inj_reg] == 0) begin
          // double: two distinct data bits at once, read in the same
          // cycle; a core write elsewhere keeps the scrub off it, and the
          // register is rewritten in the next cycle.
          inj_chk = 1'b0; inj_two = 1'b1;
          inj_bit = {$random(seed)} % 32;
          inj_bit2 = (inj_bit[4:0] + 5'd1 + ({$random(seed)} % 31)) % 32;
          inj_go = 1'b1;
          bad[inj_reg] = 2'd2;
          dbl_pending = 1'b1; dbl_reg = inj_reg;
          ra = inj_reg; rb = inj_reg;
          we = 1'b1; wa = (inj_reg == 5'd31) ? 5'd30 : inj_reg + 5'd1;
          n_inj2 = n_inj2 + 1;
        end
      end
      // a register with a double upset is rewritten in the next cycle
      if (!dbl_pending) begin : g_fix
        integer k;
        for (k = 1; k < 32; k = k + 1)
          if (bad[k] == 2 && !(we && wa == k)) begin we = 1'b1; wa = k; wd = $random(seed); end
      end
      prev_wa = wa; prev_we = we && (wa != 0);
    end
    // ---- the end: no writes, let the scrub run, then read everything --
    @(negedge clk);
    we = 1'b0; inj_go = 1'b0; dbl_pending = 1'b0; sgl_now = 1'b0;
    repeat (SCRUB ? 400 : 2) @(negedge clk);
    for (i = 1; i < 32; i = i + 1) begin
      @(negedge clk);
      ra = i; rb = 32 - i;
      #1;
      if (rda !== arch[i] && !(RDRAW && bad[i] != 0)) fail("final read");
      if (SCRUB && (err[1] || err[2])) fail("final read not clean after scrub");
    end
    @(negedge clk);
    $display("SUMMARY cycles=%0d single=%0d double=%0d hazards=%0d sec_reports=%0d ded_reports=%0d failures=%0d",
             cyc, n_inj1, n_inj2, n_hazard, n_sec_seen, n_ded_seen, nerr);
    if (nerr == 0 && n_inj1 > 50 && n_inj2 > 5 && n_hazard > 100) $display("PASS");
    else $fatal(1, "FAILED");
    $finish;
  end
endmodule
