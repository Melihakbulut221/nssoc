// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Serial stimulus touches only board-level RX and the GPIO phase handshake.
  wire [15:0] rx_probe_gpio;
  reg [15:0] rx_probe_ack=0;
  reg rx_probe_pin=1;
  integer rx_probe_frames=0, rx_probe_sleep_wakes=0;
  task rx_probe_frame(input [7:0] data, input stop);
    integer b;
    begin
      #3; // deliberately asynchronous to the SoC clock
      rx_probe_pin=0; #BIT_TIME;
      for(b=0;b<8;b=b+1) begin rx_probe_pin=data[b]; #BIT_TIME; end
      rx_probe_pin=stop; #BIT_TIME;
      rx_probe_pin=1; #BIT_TIME;
      rx_probe_frames=rx_probe_frames+1;
    end
  endtask
  always @(rx_probe_gpio) begin
    case(rx_probe_gpio[3:0])
      1: rx_probe_frame(8'h35,1'b1);
      2: begin
        wait(core_sleep===1'b1);
        rx_probe_sleep_wakes=rx_probe_sleep_wakes+1;
        rx_probe_frame(8'h96,1'b1);
      end
      3: begin rx_probe_frame(8'hc3,1'b1); rx_probe_frame(8'h5a,1'b1); end
      4: rx_probe_frame(8'h72,1'b0);
      5: rx_probe_frame(8'ha5,1'b1);
      default: begin end
    endcase
    rx_probe_ack=rx_probe_gpio;
  end
