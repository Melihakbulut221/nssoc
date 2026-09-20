// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Functional mapped-SoC boot; no ROM or RAM preload. See sim_logic_boot_gl.py.
`timescale 1ns / 1ps

`ifndef ROM_HEX
  `define ROM_HEX "test_ibex.hex"
`endif
`ifndef TIMEOUT_CYCLES
  `define TIMEOUT_CYCLES 1000000
`endif
// 8 * (scaler + 1) system clocks per bit, which is GRLIB's definition of
// the APBUART scaler: it feeds an 8x oversampling clock. The program
// programs the scaler from the same -D.
`ifndef UART_BIT_CYCLES
  `define UART_BIT_CYCLES 8
`endif
`ifndef EXIT_CODE_ADDR
  `define EXIT_CODE_ADDR 32'h0
`endif
`ifndef EXIT_MAGIC_ADDR
  `define EXIT_MAGIC_ADDR 32'h0
`endif
`ifndef TRAP_MCAUSE_ADDR
  `define TRAP_MCAUSE_ADDR 32'h0
`endif
`ifndef TRAP_MEPC_ADDR
  `define TRAP_MEPC_ADDR 32'h0
`endif
`ifndef TRAP_COUNT_ADDR
  `define TRAP_COUNT_ADDR 32'h0
`endif

module tb_logicrom_gl;

  localparam integer CLK_HALF   = 10;     // 50 MHz, functional only
  localparam integer BIT_CYCLES = `UART_BIT_CYCLES;
  localparam integer BIT_TIME   = BIT_CYCLES * 2 * CLK_HALF;

  localparam [31:0] EXIT_CODE_ADDR  = `EXIT_CODE_ADDR;
  localparam [31:0] EXIT_MAGIC_ADDR = `EXIT_MAGIC_ADDR;
  localparam [31:0] TRAP_MCAUSE_ADDR = `TRAP_MCAUSE_ADDR;
  localparam [31:0] TRAP_MEPC_ADDR   = `TRAP_MEPC_ADDR;
  localparam [31:0] TRAP_COUNT_ADDR  = `TRAP_COUNT_ADDR;
  localparam [31:0] EXIT_MAGIC       = 32'h600d_c0de;

  reg clk   = 1'b0;
  reg rst_n = 1'b0;
  always #CLK_HALF clk = ~clk;

  // Declared here rather than beside the pass criterion because the
  // power-up model and the hand-over detector below both report in
  // cycles and Verilog wants the declaration first.
  integer cycles = 0;
  always @(posedge clk) if (rst_n) cycles = cycles + 1;

  wire spw_loop_d, spw_loop_s, spi_loop, i2c_scl_oe, i2c_sda_oe;
  wire uart_tx, uart_irq;
  reg eth_clk = 1'b0;
  always #4 eth_clk = !eth_clk;
  wire [7:0] eth_txd;
  wire eth_tx_en, eth_tx_er;
  wire wdog_n, wdog_rst, nmi, irq_timer, irq_soft, gptimer_irq;
  wire alert_minor, alert_major_internal, alert_major_bus;
  wire double_fault_seen, core_sleep;

  // -------------------------------------------------------------------
  // The GPIO pads and the board they are soldered to (docs/65).
  //
  // soc_top has no pad ring, so each pin leaves it as three wires --
  // what to drive, whether to drive, what the pad sees -- and the pad
  // is modelled HERE, as the one place outside the design where the
  // three meet. A pad whose output buffer is enabled shows the SoC's
  // own value; one whose buffer is disabled shows whatever the board
  // drives.
  //
  // The board is a loopback: pads 8..15 are wired to pads 0..7, so a
  // value the program drives on pin k arrives on pin k+8 as an INPUT.
  // That is what makes check 28 of the bring-up program a test of the
  // pin path rather than of a register: DATA reads back through the
  // pad model and the wire, never through the OUTPUT register, which
  // soc_gpio.v refuses to fold in for exactly this reason. Pins 0..7
  // are driven low by the board when the SoC does not drive them.
  //
  // Contention -- the SoC driving a looped-back pad against the pin it
  // is wired to, with a different value -- resolves to X, as it would
  // on a scope. The program never does it; a program that did would
  // read X out of DATA and fail its own check.
  // -------------------------------------------------------------------
  wire [15:0] gpio_o, gpio_oe, gpio_pad;
  wire        gpio_irq;
  genvar gp;
  generate
    for (gp = 0; gp < 8; gp = gp + 1) begin : g_pad
      assign gpio_pad[gp] = gpio_oe[gp] ? gpio_o[gp] : 1'b0;
      assign gpio_pad[gp + 8] = !gpio_oe[gp + 8]            ? gpio_pad[gp]
                              : (gpio_o[gp + 8] === gpio_pad[gp]) ? gpio_o[gp + 8]
                              : 1'bx;
    end
  endgenerate

  // -------------------------------------------------------------------
  // The QSPI flash on the board (docs/66).
  //
  // The controller's four IO lanes leave soc_top as three wires each,
  // as the GPIO pins do, and meet here on a pulled-up net: `tri1`, the
  // pull-up a board carries on /WP and /HOLD so that a released lane
  // is not a floating one. A W25Q128JV model hangs on chip select 0
  // and is loaded from +flash0=<hex>, which flow/sim_soc.sh passes and
  // flow/gen_flash_image.py writes: the byte pattern checks 29 reads
  // through the controller, and the weight image check 30 loads the
  // NPU from. Chip select 1 goes to nothing, so a frame the program
  // sent there would read the pull-ups: all ones.
  //
  // The model's busy times are scaled from milliseconds to two
  // microseconds, as in tb_soc_qspi.v, and it counts every departure
  // from the part's datasheet in `violations`; the count is printed at
  // the end and is part of the pass criterion.
  // -------------------------------------------------------------------
  wire        qspi_sck;
  wire [1:0]  qspi_cs_n;
  wire [3:0]  qspi_io_o, qspi_io_oe;
  wire        qspi_irq;
  tri1 [3:0]  qspi_io;
  genvar ql;
  generate
    for (ql = 0; ql < 4; ql = ql + 1) begin : g_qspi_lane
      assign qspi_io[ql] = qspi_io_oe[ql] ? qspi_io_o[ql] : 1'bz;
    end
  endgenerate

  flash_w25q128jv #(.T_W_NS(2000.0), .T_PP_NS(2000.0), .T_SE_NS(2000.0),
                    .T_RST_NS(2000.0)) u_flash0 (
      .cs_n (qspi_cs_n[0]), .sck (qspi_sck), .io (qspi_io)
  );

  reg [8*256-1:0] flash_fname;
  initial begin
    #1;   // after the model's own fill with FFh at time zero
    if ($value$plusargs("flash0=%s", flash_fname))
      $readmemh(flash_fname, u_flash0.mem);
    else
      $display("[TB] no +flash0= image: the flash is erased");
  end

  // -------------------------------------------------------------------
  // The bootstrap pins (docs/68).
  //
  // A board's static wiring, so a register here and not a driver: it is
  // set from +strap=<n> before reset is released and never moves again,
  // which is exactly what soc_boot.v samples. Zero is the board this
  // repository models -- boot from the flash on chip select 0 -- and the
  // NOBOOT demonstration passes 4.
  // -------------------------------------------------------------------
  reg [3:0] strap = 4'h0;
  integer   strap_arg;
  initial begin
    if ($value$plusargs("strap=%d", strap_arg)) strap = strap_arg[3:0];
  end

  // The watchdog bootstrap pin is held LOW, which is the armed state.
  // A run with it high would have no watchdog at all and every watchdog
  // check in the program would pass vacuously, so it is a constant here
  // and hw/soc/tb/cocotb/test_soc_wdog.py is where the disabled case is
  // driven.
  soc_top dut (
      .spw_di_i(spw_loop_d), .spw_si_i(spw_loop_s),
      .spw_do_o(spw_loop_d), .spw_so_o(spw_loop_s),
      .i2c_scl_i(!i2c_scl_oe), .i2c_sda_i(!i2c_sda_oe),
      .i2c_scl_oe_o(i2c_scl_oe), .i2c_sda_oe_o(i2c_sda_oe),
      .can_rx_i(1'b1), .spi_miso_i(spi_loop), .spi_mosi_o(spi_loop),
      .clk_i  (clk),
      .rst_ni (rst_n),
      .irq_external_i(1'b0),
      .wdog_dis_i (1'b0),
      .strap_i    (strap),
      .uart_tx_o  (uart_tx),
      .uart_irq_o (uart_irq),
      .gpio_i     (gpio_pad),
      .gpio_o     (gpio_o),
      .gpio_oe_o  (gpio_oe),
      .gpio_irq_o (gpio_irq),
      .qspi_sck_o   (qspi_sck),
      .qspi_cs_no   (qspi_cs_n),
      .qspi_io_o    (qspi_io_o),
      .qspi_io_oe_o (qspi_io_oe),
      .qspi_io_i    (qspi_io),
      .qspi_irq_o   (qspi_irq),
      .wdog_no       (wdog_n),
      .eth_rx_clk_i(eth_clk), .eth_tx_clk_i(eth_clk),
      .eth_rxd_i(eth_txd), .eth_rx_dv_i(eth_tx_en), .eth_rx_er_i(eth_tx_er),
      .eth_txd_o(eth_txd), .eth_tx_en_o(eth_tx_en), .eth_tx_er_o(eth_tx_er),
      .eth_gtx_clk_o(), .eth_mdio_i(1'b1), .eth_mdc_o(), .eth_mdio_o(),
      .eth_mdio_oe_o(), .eth_irq_o(),
      .wdog_rst_o    (wdog_rst),
      .nmi_o         (nmi),
      .irq_timer_o   (irq_timer),
      .irq_soft_o    (irq_soft),
      .gptimer_irq_o (gptimer_irq),
      .alert_minor_o          (alert_minor),
      .alert_major_internal_o (alert_major_internal),
      .alert_major_bus_o      (alert_major_bus),
      .double_fault_seen_o    (double_fault_seen),
      .core_sleep_o           (core_sleep)
  );


  function [31:0] ram_word;
    input [31:0] addr;
    reg [12:0] widx;
    reg [63:0] row;
    begin
      widx = addr[14:2];
      case (widx[12:11])
        2'd0: row = dut.\u_ram.g_ram_2048x64_ecc.u_b0 .i_SRAM_1P_behavioral_bm_bist.memory[widx[10:0]];
        2'd1: row = dut.\u_ram.g_ram_2048x64_ecc.u_b1 .i_SRAM_1P_behavioral_bm_bist.memory[widx[10:0]];
        2'd2: row = dut.\u_ram.g_ram_2048x64_ecc.u_b2 .i_SRAM_1P_behavioral_bm_bist.memory[widx[10:0]];
        default: row = dut.\u_ram.g_ram_2048x64_ecc.u_b3 .i_SRAM_1P_behavioral_bm_bist.memory[widx[10:0]];
      endcase
      ram_word = row[31:0];
    end
  endfunction
  reg nmi_q = 1'b0, wdog_rst_q = 1'b0, wdog_n_q = 1'b1;
  integer wdog_stage1 = 0, wdog_stage2 = 0, wdog_stage3 = 0;
  integer wdog_first_cycle = -1;
  always @(posedge clk) if (rst_n) begin
    if (nmi && !nmi_q) begin
      wdog_stage1 = wdog_stage1 + 1;
      if (wdog_first_cycle < 0) wdog_first_cycle = cycles;
    end
    if (wdog_rst && !wdog_rst_q) begin
      wdog_stage2 = wdog_stage2 + 1;
      if (wdog_first_cycle < 0) wdog_first_cycle = cycles;
    end
    if (!wdog_n && wdog_n_q) begin
      wdog_stage3 = wdog_stage3 + 1;
      if (wdog_first_cycle < 0) wdog_first_cycle = cycles;
    end
    nmi_q      <= nmi;
    wdog_rst_q <= wdog_rst;
    wdog_n_q   <= wdog_n;
  end


  reg saw_alert_minor     = 1'b0;
  reg saw_alert_major_int = 1'b0;
  reg saw_alert_major_bus = 1'b0;
  reg saw_double_fault    = 1'b0;
  always @(posedge clk) if (rst_n) begin
    if (alert_minor)          saw_alert_minor     <= 1'b1;
    if (alert_major_internal) saw_alert_major_int <= 1'b1;
    if (alert_major_bus)      saw_alert_major_bus <= 1'b1;
    if (double_fault_seen)    saw_double_fault    <= 1'b1;
  end


  integer rx_chars = 0;
  integer rx_framing_errors = 0;
  reg [7:0] rx_byte;
  reg [87:0] rx_tail = 88'h0;      // last 11 characters
  reg rx_seen_pass = 1'b0;
  integer bit_i;

  initial begin
    @(posedge rst_n);
    // One clock so the UART's own reset has been applied and the line is
    // driven to its idle high before the first edge is looked for.
    @(posedge clk);
    forever begin
      @(negedge uart_tx);
      #(BIT_TIME + BIT_TIME / 2);
      for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
        rx_byte[bit_i] = uart_tx;
        #(BIT_TIME);
      end
      // Now in the middle of the stop bit.
      if (uart_tx !== 1'b1) begin
        rx_framing_errors = rx_framing_errors + 1;
        $display("[TB] framing error after %0d characters", rx_chars);
      end
      rx_chars = rx_chars + 1;
      $write("%c", rx_byte);
      rx_tail = {rx_tail[79:0], rx_byte};
      if (rx_tail == "RESULT PASS") rx_seen_pass = 1'b1;
    end
  end



  integer finished=0;
  initial begin
    $display("LOGICROM_GL begin: immutable gates, no ROM or RAM preload");
    repeat(20) @(negedge clk);
    rst_n=1;
    while(!finished && cycles<`TIMEOUT_CYCLES)begin
      @(negedge clk);
      finished=(core_sleep===1'b1 && ram_word(EXIT_MAGIC_ADDR)===EXIT_MAGIC);
      if(cycles%10000==0) begin
        $display("LOGICROM_GL progress cycles=%0d uart=%0d flash_frames=%0d crash=%040x ram_sec=%04x ram_ded=%04x",
                 cycles,rx_chars,u_flash0.frames,dut.\u_ibex.crash_dump_o ,
                 dut.\u_scrub.cnt[0] ,dut.\u_scrub.cnt[2] );
        $fflush();
      end
    end
    #(BIT_TIME*12);
    $display("LOGICROM_GL cycles=%0d checks=%0d fails=%08x code=%08x magic=%08x watchdog=%0d/%0d/%0d flash_violations=%0d uart_pass=%0d framing=%0d",cycles,ram_word(`CHECKS_ADDR),ram_word(`FAILS_ADDR),ram_word(EXIT_CODE_ADDR),ram_word(EXIT_MAGIC_ADDR),wdog_stage1,wdog_stage2,wdog_stage3,u_flash0.violations,rx_seen_pass,rx_framing_errors);
    if(!finished || !rx_seen_pass || rx_framing_errors!=0 ||
       ram_word(`CHECKS_ADDR)!==32'd28 || ram_word(`FAILS_ADDR)!==0 ||
       ram_word(EXIT_CODE_ADDR)!==0 || ram_word(EXIT_MAGIC_ADDR)!==EXIT_MAGIC ||
       wdog_stage1!=1 || wdog_stage2!=0 || wdog_stage3!=0 ||
       u_flash0.violations!=0 || saw_alert_minor || saw_alert_major_int ||
       saw_alert_major_bus || saw_double_fault)
      $fatal(1,"Whole mapped SoC logic-ROM boot failed");
    $display("LOGICROM_GL PASS checks=28");
    $finish;
  end
endmodule
