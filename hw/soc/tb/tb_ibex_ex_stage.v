// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps

// Core-level directed and differential tests for the separate execute
// stage (hw/soc/flow/ibex_ex_stage.py, docs/ibex-ex-stage.md).
//
// The core runs a program image (+prog=<readmemh file>) from a 16 KiB
// memory with randomised instruction and data latencies, optional
// interrupts and debug requests, and a fetch-error and a data-error
// region. Each trial resets the core, reloads the image and runs it to
// the halt write. The architectural trace of the MAIN program, i.e. every
// retired instruction's PC, every register-file write and every store
// whose instruction is outside the interrupt and debug handlers, is
// folded into one hash. Interrupts and debug entries are transparent to
// the main program, so with precise mepc/dpc and correct hazard handling
// every trial of a program must print the same hash, and the same hash
// as the unpatched core. The pytest driver compares them.
//
// Memory map (byte addresses):
//   0x0000-0x007f  trap vector table (handler range, not traced)
//   0x0080         reset entry (boot_addr 0)
//   0x0400-0x04ff  interrupt handler (not traced)
//   0x0800-0x08ff  debug handler, DmHaltAddr 0x800 (not traced)
//   0x3800-0x38ff  instruction fetches return a bus error
//   0x0010_0000    write: putc        0x0010_0004 write: halt, exit code
//   0x0010_0008    write: acknowledge the interrupt (re-raised after
//                  +irq_period cycles when that is nonzero)
//   0x0020_0000-0x002f_ffff  data accesses return a bus error
//   0x3f00         debug single-step budget, set by the testbench per trial
//
// Plusargs: prog, trials, seed, ilat, dlat (max extra response latency,
// 0 = fixed one cycle), irq_at/irq_step/irq_period, dbg_at/dbg_step/
// dbg_period, steps (single-step budget), max_cycles.
module tb_ibex_ex_stage;
  localparam integer MEM_WORDS = 4096;
  reg clk = 1'b0;
  always #5 clk = ~clk;
  // Starts high so that the first trial's reset is a real falling edge in
  // every simulator (the core's flip-flops reset asynchronously).
  reg rst_n = 1'b1;

  reg [31:0] mem   [0:MEM_WORDS-1];
  reg [31:0] image [0:MEM_WORDS-1];

  integer trials, trial, seed, ilat, dlat, irq_at0, irq_step, irq_period;
  integer dbg_at0, dbg_step, dbg_period, steps, max_cycles;
  integer cycle, irq_next, dbg_next, i, verbose;
  reg [1023:0] prog;

  // ---------------- instruction port ----------------
  wire        instr_req;
  wire [31:0] instr_addr;
  reg         instr_gnt, instr_rvalid, instr_err;
  reg  [31:0] instr_rdata;
  reg  [31:0] iq_data [0:7];
  reg         iq_err  [0:7];
  integer     iq_due  [0:7];
  integer     iq_head, iq_count, iq_last;

  // ---------------- data port ----------------
  wire        data_req, data_we;
  wire [3:0]  data_be;
  wire [31:0] data_addr, data_wdata;
  reg         data_gnt, data_rvalid, data_err;
  reg  [31:0] data_rdata;
  reg  [31:0] dq_data [0:7];
  reg         dq_err  [0:7];
  integer     dq_due  [0:7];
  integer     dq_head, dq_count, dq_last;

  reg irq_ext, dbg_req, halted;
  reg [31:0] exit_code;

  function in_ram(input [31:0] a);
    in_ram = a < (MEM_WORDS * 4);
  endfunction

  // Latency decisions are made at the falling edge from the request the
  // core holds since the rising edge; the core samples them at the next
  // rising edge.
  always @(negedge clk) begin
    instr_gnt = instr_req && (ilat == 0 || ($random(seed) & 3) != 0);
    data_gnt  = data_req  && (dlat == 0 || ($random(seed) & 3) != 0);
    instr_rvalid = (iq_count > 0) && (iq_due[iq_head] <= cycle);
    instr_rdata  = instr_rvalid ? iq_data[iq_head] : 32'hxxxxxxxx;
    instr_err    = instr_rvalid ? iq_err[iq_head] : 1'b0;
    data_rvalid  = (dq_count > 0) && (dq_due[dq_head] <= cycle);
    data_rdata   = data_rvalid ? dq_data[dq_head] : 32'hxxxxxxxx;
    data_err     = data_rvalid ? dq_err[dq_head] : 1'b0;
  end

  integer d, slot, widx;
  always @(posedge clk) begin
    if (!rst_n) begin
      iq_head = 0; iq_count = 0; iq_last = 0;
      dq_head = 0; dq_count = 0; dq_last = 0;
    end else begin
      if (instr_rvalid) begin iq_head = (iq_head + 1) % 8; iq_count = iq_count - 1; end
      if (data_rvalid)  begin dq_head = (dq_head + 1) % 8; dq_count = dq_count - 1; end
      if (instr_req && instr_gnt) begin
        if (iq_count == 8) $fatal(1, "instruction response queue overflow");
        d = cycle + 1 + (ilat == 0 ? 0 : ($random(seed) & 32'h7fffffff) % (ilat + 1));
        if (d < iq_last) d = iq_last;
        iq_last = d;
        slot = (iq_head + iq_count) % 8;
        iq_due[slot]  = d;
        iq_err[slot]  = (instr_addr >= 32'h3800 && instr_addr < 32'h3900);
        iq_data[slot] = (in_ram(instr_addr) && !iq_err[slot]) ? mem[instr_addr[13:2]] : 32'h0;
        iq_count = iq_count + 1;
      end
      if (data_req && data_gnt) begin
        if (dq_count == 8) $fatal(1, "data response queue overflow");
        d = cycle + 1 + (dlat == 0 ? 0 : ($random(seed) & 32'h7fffffff) % (dlat + 1));
        if (d < dq_last) d = dq_last;
        dq_last = d;
        slot = (dq_head + dq_count) % 8;
        dq_due[slot]  = d;
        dq_err[slot]  = (data_addr >= 32'h0020_0000 && data_addr < 32'h0030_0000);
        dq_data[slot] = 32'h0;
        if (in_ram(data_addr)) begin
          widx = data_addr[13:2];
          if (data_we) begin
            if (data_be[0]) mem[widx][7:0]   = data_wdata[7:0];
            if (data_be[1]) mem[widx][15:8]  = data_wdata[15:8];
            if (data_be[2]) mem[widx][23:16] = data_wdata[23:16];
            if (data_be[3]) mem[widx][31:24] = data_wdata[31:24];
          end else
            dq_data[slot] = mem[widx];
        end else if (data_we && data_addr == 32'h0010_0000) begin
          $write("%c", data_wdata[7:0]);
        end else if (data_we && data_addr == 32'h0010_0004) begin
          halted = 1'b1;
          exit_code = data_wdata;
        end else if (data_we && data_addr == 32'h0010_0008) begin
          irq_ext = 1'b0;
          if (irq_period > 0) irq_next = cycle + irq_period;
        end
        dq_count = dq_count + 1;
      end
      if (irq_next >= 0 && cycle == irq_next) begin irq_ext = 1'b1; irq_next = -1; end
      if (dbg_next >= 0 && cycle == dbg_next) begin dbg_req = 1'b1; dbg_next = -1; end
      if (dbg_req && dut.u_ibex_core.debug_mode) begin
        dbg_req = 1'b0;
        if (dbg_period > 0) dbg_next = cycle + dbg_period;
      end
    end
  end

  // ---------------- the core ----------------
  // soc_top's configuration: RV32IMC (RV32MFast, Zca), PMP with four
  // regions, no writeback stage, no branch-target ALU, SecureIbex off.
  ibex_top #(
      .BaseIsa(0), .PMPEnable(1), .PMPGranularity(0), .PMPNumRegions(4),
      .MHPMCounterNum(0), .MHPMCounterWidth(40), .RV32E(0), .RV32M(2), .RV32B(0),
      .RV32ZC(0), .RegFile(0), .BranchTargetALU(0), .WritebackStage(0), .ICache(0),
      .ICacheECC(0), .BranchPredictor(0), .DbgTriggerEn(0), .SecureIbex(0),
      .ICacheScramble(0), .DmHaltAddr(32'h0000_0800), .DmExceptionAddr(32'h0000_0808)
  ) dut (
      .clk_i(clk), .rst_ni(rst_n), .test_en_i(1'b0),
      .ram_cfg_icache_tag_i(24'h0), .ram_cfg_icache_tag_o(),
      .ram_cfg_icache_data_i(24'h0), .ram_cfg_icache_data_o(),
      .cheriot_enable_i(4'b1010), .hart_id_i(32'h0), .boot_addr_i(32'h0),
      .trvk_heap_base_addr_i(32'h0),
      .instr_req_o(instr_req), .instr_gnt_i(instr_gnt), .instr_rvalid_i(instr_rvalid),
      .instr_addr_o(instr_addr), .instr_rdata_i(instr_rdata), .instr_rdata_intg_i(7'h0),
      .instr_err_i(instr_err),
      .data_req_o(data_req), .data_gnt_i(data_gnt), .data_rvalid_i(data_rvalid),
      .data_we_o(data_we), .data_be_o(data_be), .data_addr_o(data_addr),
      .data_wdata_o(data_wdata), .data_wdata_intg_o(), .data_tag_o(),
      .data_rdata_i(data_rdata), .data_rdata_intg_i(7'h0), .data_tag_i(1'b0),
      .data_err_i(data_err),
      .trvk_revbm_req_o(), .trvk_revbm_gnt_i(1'b0), .trvk_revbm_rvalid_i(1'b0),
      .trvk_revbm_addr_o(), .trvk_revbm_rdata_i(32'h0), .trvk_revbm_rdata_intg_i(7'h0),
      .trvk_revbm_err_i(1'b0),
      .irq_software_i(1'b0), .irq_timer_i(1'b0), .irq_external_i(irq_ext),
      .irq_fast_i(15'h0), .irq_nm_i(1'b0),
      .scramble_key_valid_i(1'b0), .scramble_key_i(128'h0), .scramble_nonce_i(64'h0),
      .scramble_req_o(),
      .debug_req_i(dbg_req), .crash_dump_o(), .double_fault_seen_o(),
      .fetch_enable_i(4'b0101), .mcounteren_writable_i(4'b1010),
      .alert_minor_o(), .alert_major_internal_o(), .alert_major_bus_o(), .core_sleep_o(),
      .scan_rst_ni(1'b1),
      .lockstep_cmp_en_o(), .data_req_shadow_o(), .data_we_shadow_o(), .data_be_shadow_o(),
      .data_addr_shadow_o(), .data_wdata_shadow_o(), .data_wdata_intg_shadow_o(),
      .instr_req_shadow_o(), .instr_addr_shadow_o()
  );

  // The project's register file with the execute-path knobs of
  // docs/ibex-execute-timing.md (needs -DSOC_RF_EXEC, the SECDED file and
  // flow/ibex_rf_predecode.py's IF stage and core).
`ifdef TB_RF_KNOBS
  defparam dut.gen_regfile_ff.register_file_i.CORRPRE = 1;
  defparam dut.gen_regfile_ff.register_file_i.CHKDEFER = 1;
  defparam dut.gen_regfile_ff.register_file_i.RDPRE = 1;
`ifdef VERILATOR
  // Two-state start-up. The IF/ID registers have no reset at ResetAll = 0;
  // instr_rdata_id starts at zero here, so its predecode must start at the
  // predecode of zero, or the register file's RDPRE check fires before the
  // first fetch. (Icarus starts both unknown and the check skips them.)
  initial dut.u_ibex_core.if_stage_i.rf_raddr_pre_id_o = 24'h011011;
`endif
`endif

  // ---------------- main-program trace ----------------
  function handler_pc(input [31:0] pc);
    handler_pc = (pc < 32'h80) || (pc >= 32'h400 && pc < 32'h500) ||
                 (pc >= 32'h800 && pc < 32'h900);
  endfunction

  reg [31:0] hash;
  integer n_retired, n_writes, n_stores, n_irq, n_dbg, n_exc, n_alert;
  task mix(input [31:0] v);
    hash = (hash ^ v) * 32'h01000193;
  endtask

  // Tracing stops at the halt store: what the core does after it (the
  // final `j .` loop) depends on timing.
  reg trace_on;
  wire [31:0] pc_ex = dut.u_ibex_core.pc_id;
  always @(posedge clk)
    if (!rst_n) trace_on <= 1'b1;
    else if (data_req && data_gnt && data_we && data_addr == 32'h0010_0004) trace_on <= 1'b0;
  always @(posedge clk) if (rst_n && trace_on) begin
    if (dut.u_ibex_core.rf_we_wb && dut.u_ibex_core.rf_waddr_wb != 5'd0 && !handler_pc(pc_ex)) begin
      mix({27'h57, dut.u_ibex_core.rf_waddr_wb}); mix(dut.u_ibex_core.rf_wdata_wb);
      n_writes = n_writes + 1;
    end
    if (dut.u_ibex_core.instr_id_done && !handler_pc(pc_ex)) begin
      mix(32'h52455431); mix(pc_ex);
      n_retired = n_retired + 1;
    end
    if (data_req && data_gnt && data_we && !handler_pc(pc_ex)) begin
      mix({28'h5354000, data_be}); mix(data_addr);
      mix(data_wdata & {{8{data_be[3]}}, {8{data_be[2]}}, {8{data_be[1]}}, {8{data_be[0]}}});
      n_stores = n_stores + 1;
    end
    // Handler entries, counted at the first handler instruction.
    if (dut.u_ibex_core.instr_id_done) begin
      if (pc_ex == 32'h400) n_irq = n_irq + 1;
      if (pc_ex == 32'h810) n_dbg = n_dbg + 1;
      if (pc_ex == 32'h500) n_exc = n_exc + 1;
    end
    if (dut.alert_major_internal_o || dut.alert_major_bus_o || dut.double_fault_seen_o)
      n_alert = n_alert + 1;
  end

  always @(posedge clk) cycle <= rst_n ? cycle + 1 : 0;

  // +verbose=1: one line per retired instruction and per request edge.
  always @(posedge clk) if (rst_n && verbose != 0) begin
    if (dut.u_ibex_core.instr_id_done)
      $display("%0d retire pc=%h irq=%b dbg=%b dmode=%b", cycle, pc_ex, irq_ext, dbg_req,
               dut.u_ibex_core.debug_mode);
    if (dut.u_ibex_core.csr_save_cause)
      $display("%0d trap cause=%h save_if=%b save_id=%b mepc_in_if=%h pc_id=%h dbg=%b", cycle,
               dut.u_ibex_core.exc_cause, dut.u_ibex_core.csr_save_if, dut.u_ibex_core.csr_save_id,
               dut.u_ibex_core.cs_registers_i.pc_if_i, pc_ex, dut.u_ibex_core.debug_csr_save);
  end

  integer irq_at, dbg_at;
  initial begin
    if (!$value$plusargs("prog=%s", prog)) $fatal(1, "+prog=<image.hex> is required");
    if (!$value$plusargs("trials=%d", trials)) trials = 1;
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    if (!$value$plusargs("ilat=%d", ilat)) ilat = 0;
    if (!$value$plusargs("dlat=%d", dlat)) dlat = 0;
    if (!$value$plusargs("irq_at=%d", irq_at0)) irq_at0 = -1;
    if (!$value$plusargs("irq_step=%d", irq_step)) irq_step = 1;
    if (!$value$plusargs("irq_period=%d", irq_period)) irq_period = 0;
    if (!$value$plusargs("dbg_at=%d", dbg_at0)) dbg_at0 = -1;
    if (!$value$plusargs("dbg_step=%d", dbg_step)) dbg_step = 1;
    if (!$value$plusargs("dbg_period=%d", dbg_period)) dbg_period = 0;
    if (!$value$plusargs("steps=%d", steps)) steps = 0;
    if (!$value$plusargs("max_cycles=%d", max_cycles)) max_cycles = 200000;
    if (!$value$plusargs("verbose=%d", verbose)) verbose = 0;
    $readmemh(prog, image);
    for (trial = 0; trial < trials; trial = trial + 1) begin
      #1 rst_n = 1'b0;
      for (i = 0; i < MEM_WORDS; i = i + 1) mem[i] = image[i];
      mem[32'h3f00 >> 2] = steps;
      hash = 32'h811c9dc5;
      n_retired = 0; n_writes = 0; n_stores = 0; n_irq = 0; n_dbg = 0; n_exc = 0; n_alert = 0;
      halted = 1'b0; exit_code = 32'hffffffff;
      irq_ext = 1'b0; dbg_req = 1'b0;
      irq_at = irq_at0 < 0 ? -1 : irq_at0 + trial * irq_step;
      dbg_at = dbg_at0 < 0 ? -1 : dbg_at0 + trial * dbg_step;
      irq_next = irq_at; dbg_next = dbg_at;
      repeat (5) @(negedge clk);
      rst_n = 1'b1;
      for (i = 0; i < max_cycles && !halted; i = i + 1) @(negedge clk);
      // Drain: let the halting store's instruction retire.
      repeat (4) @(negedge clk);
      $display("TRIAL %0d irq_at=%0d dbg_at=%0d seed=%0d halted=%0d exit=%h cycles=%0d hash=%h retired=%0d writes=%0d stores=%0d irqs=%0d dbg=%0d exc=%0d alerts=%0d",
               trial, irq_at, dbg_at, seed, halted, exit_code, i, hash, n_retired, n_writes,
               n_stores, n_irq, n_dbg, n_exc, n_alert);
    end
    $finish;
  end
endmodule
