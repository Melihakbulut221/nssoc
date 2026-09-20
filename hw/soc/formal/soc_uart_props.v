// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

// Port-only contract for the UART, including arbitrary asynchronous RX input. The reference
// registers consume bus transactions, never DUT state. No constraint on
// address/data or APB sequencing: even stray SETUP/idle writes must be inert.
// This proves control/readback/interrupt/status semantics, not serial timing,
// active reception, analog pads, or a fault model. Pin-level serialization has its
// independent cocotb suite. Reset may recur at any step after initial reset.
module soc_uart_props (
    input wire clk_i, rst_ni, psel_i, penable_i, pwrite_i, rx_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i
);
  wire [31:0] data;
  wire ready, error, tx, irq;
  soc_uart dut (
    .clk_i(clk_i), .rst_ni(rst_ni), .psel_i(psel_i),
    .penable_i(penable_i), .pwrite_i(pwrite_i), .paddr_i(paddr_i),
    .pwdata_i(pwdata_i), .prdata_o(data), .pready_o(ready),
    .pslverr_o(error), .rx_i(rx_i), .tx_o(tx), .irq_o(irq)
  );

  reg valid = 0;
  always @(posedge clk_i) valid <= 1;
  initial assume (!rst_ni);
  wire write_access = psel_i && penable_i && pwrite_i;
  reg [31:0] control, divider;
  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin control <= 0; divider <= 0; end
    else if (write_access) begin
      if (paddr_i == 12'h008) control <= pwdata_i & 32'hF;
      if (paddr_i == 12'h00C) divider <= pwdata_i & 32'hFFF;
    end
  end

  always @(*) begin
    assert (ready && !error);
    if (valid) begin
      case (paddr_i)
        12'h008: assert (data == control);
        12'h00C: assert (data == divider);
        12'h004: begin
          assert ((data & ~32'hD7) == 0);
          assert (data[2] == !data[7]); // TE and TF are complements.
          assert (!data[1] || (data[2] && tx)); // TS implies empty + idle.
          assert (irq == ((control[3] && data[2]) ||
                          (control[2] && (data[0] || data[4] || data[6]))));
        end
        12'h000: assert ((data & 32'hFFFFFF00) == 0);
        default: assert (data == 0);
      endcase
      assert (control[3] || control[2] || !irq);
      if (!rst_ni) begin
        assert (tx && !irq);
        if (paddr_i == 12'h004) assert (data == 32'h6);
      end
    end
  end

  always @(posedge clk_i) if (valid && rst_ni) begin
    cover (paddr_i == 12'h008 && data == 32'hA);
    cover (paddr_i == 12'h00C && data == 32'hFFF);
    cover (paddr_i == 12'h004 && data[7]);
    cover (paddr_i == 12'h004 && data[2] && !data[1] && !tx);
    cover (paddr_i == 12'h004 && data[0]);
    cover (paddr_i == 12'h004 && data[4]);
    cover (paddr_i == 12'h004 && data[6]);
    cover (irq);
    cover ($past(irq) && !irq);
    cover ($past(write_access && paddr_i == 12'h008 && pwdata_i == 0)
           && paddr_i == 12'h008 && data == 0);
  end
endmodule
