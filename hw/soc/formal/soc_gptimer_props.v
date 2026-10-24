// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

// Architectural scoreboard for two general timers, including their shared
// prescaler. All state is reconstructed from public APB writes. The timer
// fields implement the documented control ABI: load is a strobe, IP is W1C,
// expiry wins over IP clear, writes win over counter expiry, and chain uses
// predecessor expiry (not its interrupt enable). No internal DUT references.
// The real watchdog is elaborated but its separate reset-domain policy is
// covered by soc_wdog.sby, not claimed by this timer proof. No FI assumptions.
module soc_gptimer_props #(
    parameter integer TW = 4, SW = 3
) (
    input wire clk_i, rst_ni, rst_por_ni,
    input wire psel_i, penable_i, pwrite_i, wdog_dis_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i
);
  wire [31:0] data;
  wire ready, error, irq, nmi, reset_req, watchdog, tmr_event;
  soc_gptimer #(.NGEN(2), .TWIDTH(TW), .SWIDTH(SW), .IRQ_NUM(5'd8)) dut (
    .clk_i(clk_i), .rst_ni(rst_ni), .rst_por_ni(rst_por_ni),
    .psel_i(psel_i), .penable_i(penable_i), .pwrite_i(pwrite_i),
    .paddr_i(paddr_i), .pwdata_i(pwdata_i), .wdog_dis_i(wdog_dis_i),
    .prdata_o(data), .pready_o(ready), .pslverr_o(error),
    .irq_o(irq), .nmi_o(nmi), .rst_req_o(reset_req),
    .wdog_no(watchdog), .tmr_ev_o(tmr_event)
  );
  reg valid = 0;
  always @(posedge clk_i) valid <= 1;
  initial begin assume (!rst_ni); assume (!rst_por_ni); end
  wire write_access = psel_i && penable_i && pwrite_i;
  reg [SW-1:0] prescale, prescale_reload;
  reg [TW-1:0] count [0:1];
  reg [TW-1:0] reload [0:1];
  reg [5:0] control [0:1];
  wire [1:0] step, expire;
  assign step[0] = (prescale == 0);
  assign step[1] = control[1][5] ? expire[0] : step[0];
  assign expire[0] = control[0][0] && step[0] && (count[0] == 0);
  assign expire[1] = control[1][0] && step[1] && (count[1] == 0);

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin prescale <= 0; prescale_reload <= 0; end
    else begin
      if (write_access && paddr_i == 0) prescale <= pwdata_i[SW-1:0];
      else prescale <= (prescale == 0) ? prescale_reload : prescale - 1'b1;
      if (write_access && paddr_i == 4) prescale_reload <= pwdata_i[SW-1:0];
    end
  end
  genvar k;
  generate for (k = 0; k < 2; k = k + 1) begin : timer
    wire selected = paddr_i[11:4] == k + 1;
    wire write_counter = write_access && selected && paddr_i[3:2] == 0;
    wire write_reload = write_access && selected && paddr_i[3:2] == 1;
    wire write_control = write_access && selected && paddr_i[3:2] == 2;
    always @(posedge clk_i or negedge rst_ni) begin
      if (!rst_ni) begin count[k] <= 0; reload[k] <= 0; control[k] <= 0; end
      else begin
        if (write_counter) count[k] <= pwdata_i[TW-1:0];
        else if (write_control && pwdata_i[2]) count[k] <= reload[k];
        else if (control[k][0] && step[k])
          count[k] <= expire[k] ? reload[k] : count[k] - 1'b1;
        if (write_reload) reload[k] <= pwdata_i[TW-1:0];
        if (write_control) begin
          control[k][0] <= pwdata_i[0];
          control[k][1] <= pwdata_i[1];
          control[k][3] <= pwdata_i[3];
          control[k][5] <= (k == 0) ? 1'b0 : pwdata_i[5];
        end else if (expire[k] && !control[k][1]) control[k][0] <= 0;
        control[k][2] <= 0;
        control[k][4] <= expire[k] ||
                        (control[k][4] && !(write_control && pwdata_i[4]));
      end
    end
    always @(*) if (valid && selected) begin
      case (paddr_i[3:2])
        0: assert (data == {{(32-TW){1'b0}}, count[k]});
        1: assert (data == {{(32-TW){1'b0}}, reload[k]});
        2: assert (data == {26'b0, control[k]});
        3: assert (data == 0);
      endcase
    end
    always @(posedge clk_i) if (valid && rst_ni) begin
      cover (expire[k] && !control[k][1]); // one-shot
      cover (expire[k] && control[k][1]); // restart
      cover (expire[k] && write_control && pwdata_i[4]); // W1C collision
      cover (write_control && pwdata_i[2] && reload[k] != 0);
      cover ($past(control[k][4]) && !control[k][4]);
    end
  end endgenerate
  always @(*) begin
    assert (ready && !error);
    if (valid) begin
      assert (irq == ((control[0][4] && control[0][3]) ||
                      (control[1][4] && control[1][3])));
      // Watchdog slot 0x30..0x3f and its exact status offset 0x40 have
      // separate semantics. All other absent addresses must read zero.
      if (paddr_i[11:4] != 1 && paddr_i[11:4] != 2 &&
          paddr_i[11:4] != 3 && paddr_i != 12'h040) begin
        case (paddr_i)
          12'h000: assert (data == {{(32-SW){1'b0}}, prescale});
          12'h004: assert (data == {{(32-SW){1'b0}}, prescale_reload});
          12'h008: assert (data == ((32'd8 << 3) | 3));
          default: assert (data == 0);
        endcase
      end
    end
  end
  always @(posedge clk_i) if (valid && rst_ni) begin
    cover (control[1][5] && expire[0] && expire[1]);
    cover (irq && !$past(irq));
    cover (!irq && $past(irq));
  end
endmodule
