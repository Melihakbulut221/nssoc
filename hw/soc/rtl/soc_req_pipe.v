// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// One-entry request register. Upstream grant transfers ownership of the
// complete request into this register; downstream grant releases it. There is
// no combinational downstream-ready -> upstream-grant path and no bypass.
// Responses retain their original ordered path outside this module. Reset
// must reset both endpoints too, as in soc_top's common system-reset domain.
module soc_req_pipe (
    input  wire        clk_i,
    input  wire        rst_ni,
    input  wire        req_i,
    output wire        gnt_o,
    input  wire [31:0] addr_i,
    input  wire        we_i,
    input  wire [3:0]  be_i,
    input  wire [31:0] wdata_i,
    output wire        req_o,
    input  wire        gnt_i,
    output wire [31:0] addr_o,
    output wire        we_o,
    output wire [3:0]  be_o,
    output wire [31:0] wdata_o
);
  reg valid_q;
  reg [68:0] payload_q;
  assign gnt_o = rst_ni && req_i && !valid_q;
  assign req_o = rst_ni && valid_q;
  assign {addr_o, we_o, be_o, wdata_o} = payload_q;

  always @(posedge clk_i or negedge rst_ni)
    if (!rst_ni) valid_q <= 1'b0;
    else if (gnt_o) valid_q <= 1'b1;
    else if (req_o && gnt_i) valid_q <= 1'b0;

  // Payload is observable only while req_o is asserted. Resetting every data
  // bit would add reset-tree load without changing the request contract.
  always @(posedge clk_i)
    if (gnt_o) payload_q <= {addr_i, we_i, be_i, wdata_i};
endmodule
`default_nettype wire
