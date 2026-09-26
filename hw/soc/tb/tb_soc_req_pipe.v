// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_soc_req_pipe;
  reg clk = 0;
  always #5 clk = !clk;
  reg rst_n = 0, req = 0, downstream_grant = 0;
  reg [68:0] payload = 0;
  wire grant, downstream_req;
  wire [68:0] downstream_payload;
  soc_req_pipe dut (
      .clk_i(clk), .rst_ni(rst_n), .req_i(req), .gnt_o(grant),
      .addr_i(payload[68:37]), .we_i(payload[36]),
      .be_i(payload[35:32]), .wdata_i(payload[31:0]),
      .req_o(downstream_req), .gnt_i(downstream_grant),
      .addr_o(downstream_payload[68:37]), .we_o(downstream_payload[36]),
      .be_o(downstream_payload[35:32]), .wdata_o(downstream_payload[31:0])
  );
  reg [68:0] expected;
  integer occupancy = 0, accepted = 0, emitted = 0, discarded = 0;
  integer stalled = 0, resets_with_pending = 0, cycle;
  reg previous_stall = 0;
  reg [68:0] previous_payload;
  always @(posedge clk) begin
    if (!rst_n) begin
      if (grant !== 0 || downstream_req !== 0) $fatal(1, "Transfer during reset");
      if (occupancy != 0) begin
        discarded = discarded + 1;
        resets_with_pending = resets_with_pending + 1;
      end
      occupancy = 0;
      previous_stall = 0;
    end else begin
      if (previous_stall && (!downstream_req || downstream_payload !== previous_payload))
        $fatal(1, "Request changed while stalled");
      if (grant && !req) $fatal(1, "Grant without request");
      if (downstream_req) begin
        if (occupancy != 1 || downstream_payload !== expected)
          $fatal(1, "Lost, reordered or corrupted request");
        if (downstream_grant) begin
          occupancy = occupancy - 1;
          emitted = emitted + 1;
        end else stalled = stalled + 1;
      end
      if (grant) begin
        if (occupancy != 0 || downstream_req) $fatal(1, "Overwrite or combinational bypass");
        expected = payload;
        occupancy = occupancy + 1;
        accepted = accepted + 1;
      end
      previous_stall = downstream_req && !downstream_grant;
      previous_payload = downstream_payload;
    end
  end
  initial begin
    repeat (3) @(negedge clk);
    rst_n = 1;
    for (cycle = 0; cycle < 1200; cycle = cycle + 1) begin
      @(negedge clk);
      req = (cycle < 80) ? 1 : ($urandom_range(0, 3) != 0);
      downstream_grant = (cycle < 40) ? 0 : ($urandom_range(0, 3) == 0);
      payload = {$urandom, 1'b1, 4'hf, $urandom};
      if (cycle == 32 || cycle == 600) rst_n = 0;
      if (cycle == 34 || cycle == 603) rst_n = 1;
    end
    @(negedge clk); req = 0; downstream_grant = 1;
    repeat (4) @(negedge clk);
    if (occupancy != 0 || downstream_req || accepted != emitted + discarded)
      $fatal(1, "Drain/accounting failed");
    if (emitted < 100 || stalled < 100 || resets_with_pending < 1)
      $fatal(1, "Vacuous traffic or reset test");
    $display("PASS accepted=%0d emitted=%0d discarded=%0d stalled=%0d reset_pending=%0d",
             accepted, emitted, discarded, stalled, resets_with_pending);
    $finish;
  end
endmodule
