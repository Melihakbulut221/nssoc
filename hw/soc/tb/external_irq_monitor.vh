// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Asynchronous board-level source, including assertion only after WFI sleep.
  wire [15:0] ext_probe_gpio;
  reg ext_probe_irq=0;
  integer ext_assertions=0, ext_sleep_wakes=0;
  always @(ext_probe_gpio) begin
    case(ext_probe_gpio[3:0])
      1,3: begin #3; ext_probe_irq=1; ext_assertions=ext_assertions+1; end
      5,7: begin wait(core_sleep===1'b1); #3; ext_probe_irq=1; ext_assertions=ext_assertions+1; ext_sleep_wakes=ext_sleep_wakes+1; end
      2,4,6,8: begin #3; ext_probe_irq=0; end
      default: begin end
    endcase
  end
