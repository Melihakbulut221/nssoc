// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
module soc_req_pipe_formal(input wire clk_i);
  (* anyseq *) reg rst_ni;
  (* anyseq *) reg req_i, gnt_i;
  (* anyseq *) reg [68:0] payload;
  wire gnt_o, req_o;
  wire [68:0] result;
  soc_req_pipe dut (
      .clk_i(clk_i), .rst_ni(rst_ni), .req_i(req_i), .gnt_o(gnt_o),
      .addr_i(payload[68:37]), .we_i(payload[36]),
      .be_i(payload[35:32]), .wdata_i(payload[31:0]),
      .req_o(req_o), .gnt_i(gnt_i), .addr_o(result[68:37]),
      .we_o(result[36]), .be_o(result[35:32]), .wdata_o(result[31:0])
  );
  reg past_valid = 0;
  reg [7:0] accepted, delivered;
  reg [68:0] token;
  reg [3:0] stalled;
  wire [7:0] balance = accepted - delivered;
  always @(posedge clk_i) begin
    past_valid <= 1;
    if (!past_valid) assume(!rst_ni);
    if (!rst_ni) begin
      accepted <= 0;
      delivered <= 0;
      stalled <= 0;
      assert(!gnt_o && !req_o);
      if (past_valid) cover($past(rst_ni && req_o && !gnt_i));
    end else if (past_valid) begin
      // All inputs, including payload during backpressure and downstream
      // grants when no request exists, remain unconstrained.
      assert(balance <= 1);
      assert(req_o == (balance == 1));
      assert(gnt_o == (req_i && balance == 0));
      assert(!(gnt_o && req_o));
      if (gnt_o) begin
        accepted <= accepted + 1;
        token <= payload;
      end
      if (req_o) assert(result == token);
      if (req_o && gnt_i) delivered <= delivered + 1;
      if (req_o && !gnt_i && stalled != 15) stalled <= stalled + 1;
      else if (!req_o) stalled <= 0;
      if ($past(rst_ni && req_o && !gnt_i)) begin
        assert(req_o);
        assert($stable(result));
      end
      if ($past(rst_ni && gnt_o)) assert(req_o);
      if ($past(rst_ni && req_o && gnt_i)) assert(!req_o);
      cover(req_o && gnt_i && stalled >= 3);
      cover(delivered >= 2 && balance == 0);
      cover(gnt_o && gnt_i);
    end
  end
endmodule
