// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

// Two actual table instances, with independent request/write/control payloads
// and byte/high address aliases. No property reads hierarchical DUT signals.
// Proves response latency, write error policy, reset, and noninterference of
// ignored inputs across every table word. Generated record contents are checked
// separately against memmap.yaml by test_memmap.py; equality of two copies is
// NOT an independent oracle for their shared contents. The identity/endianness
// signature here is the fixed discovery ABI, not a copied table case statement.
module soc_pnp_props (
    input wire clk_i, rst_ni, req_i, we_i,
    input wire [31:0] addr_i, wdata_i,
    input wire [3:0] be_i,
    input wire [21:0] alias_i,
    input wire psel_i, penable_i, pwrite_i,
    input wire [31:0] pwdata_i
);
  wire [31:0] aliased_addr = {alias_i[21:2], addr_i[11:2], alias_i[1:0]};
  wire grant, response, error, ref_grant, ref_response, ref_error;
  wire [31:0] data, ref_data, apb_data, apb_ref_data;
  soc_pnp dut (
    .clk_i(clk_i), .rst_ni(rst_ni), .req_i(req_i), .addr_i(addr_i),
    .we_i(we_i), .be_i(be_i), .wdata_i(wdata_i), .gnt_o(grant),
    .rvalid_o(response), .rdata_o(data), .err_o(error)
  );
  soc_pnp reference (
    .clk_i(clk_i), .rst_ni(rst_ni), .req_i(1'b1), .addr_i(aliased_addr),
    .we_i(1'b0), .be_i(4'b0), .wdata_i(32'b0), .gnt_o(ref_grant),
    .rvalid_o(ref_response), .rdata_o(ref_data), .err_o(ref_error)
  );
  wire ready, apb_error, ref_ready, apb_ref_error;
  soc_apb_pnp apb_dut (
    .psel_i(psel_i), .penable_i(penable_i), .paddr_i(addr_i[11:0]),
    .pwrite_i(pwrite_i), .pwdata_i(pwdata_i), .prdata_o(apb_data),
    .pready_o(ready), .pslverr_o(apb_error)
  );
  soc_apb_pnp apb_reference (
    .psel_i(1'b0), .penable_i(1'b0), .paddr_i(aliased_addr[11:0]),
    .pwrite_i(1'b0), .pwdata_i(32'b0), .prdata_o(apb_ref_data),
    .pready_o(ref_ready), .pslverr_o(apb_ref_error)
  );
  reg valid = 0;
  always @(posedge clk_i) valid <= 1;
  initial assume (!rst_ni);
  always @(*) begin
    assert (grant == req_i && ref_grant);
    assert (ready && ref_ready && !apb_error && !apb_ref_error);
    assert (apb_data == apb_ref_data);
    if (valid) begin
      assert (data == ref_data);
      assert (!ref_error);
      if (!rst_ni) assert (!response && !error && data == 0);
    end
  end
  always @(posedge clk_i) if (valid && rst_ni && $past(rst_ni)) begin
    assert (response == $past(req_i));
    assert (error == $past(req_i && we_i));
    assert (ref_response);
    if ($past(addr_i[11:2]) == 10'h3FC) assert (data == 32'h4E530001);
    if ($past(addr_i[11:2]) == 10'h3FD) assert (data == 32'h1);
    cover (response && error && data != 0);
    cover (response && !error && data == 32'h4E530001);
    cover (!response && $past(response));
    cover (psel_i && penable_i && pwrite_i && apb_data != 0);
  end
endmodule
