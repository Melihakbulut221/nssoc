// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Included inside the real register file by regfile_contract.sby only.
// These are ASSERTED strengthening invariants, not codec assumptions.
// No faults are injected; addresses, write data and write enable are free.

  reg f_contract_valid = 1'b0;
  always @(posedge clk_i) f_contract_valid <= 1'b1;
  always @(*) if (!f_contract_valid) assume (!rst_ni);

  wire [31:0] f_reference [0:31];
  assign f_reference[0] = 32'b0;
  genvar fc;
  generate for (fc = 1; fc < 32; fc = fc + 1) begin : g_contract
    reg [31:0] reference_q;
    always @(posedge clk_i or negedge rst_ni)
      if (!rst_ni) reference_q <= 32'b0;
      else if (waddr_a_i == fc[4:0] ? we_a_i : 1'b0) reference_q <= wdata_a_i;
    assign f_reference[fc] = reference_q;

    wire [7:0] expected_check;
    secded_enc u_reference_enc (
      .data_in({32'b0, g_plain_rf.rf_data[fc]}),
      .check_out(expected_check), .code_out()
    );
    always @(posedge clk_i) if (f_contract_valid && rst_ni) begin
      assert (g_plain_rf.rf_data[fc] == reference_q);
      assert (g_plain_rf.rf_chk[fc] == expected_check);
    end
  end endgenerate

  always @(posedge clk_i) if (f_contract_valid && rst_ni) begin
    assert (rdata_a_o == f_reference[raddr_a_i]);
    assert (rdata_b_o == f_reference[raddr_b_i]);
    assert (rf_ecc_err_o == 3'b0);
    assert (!(g_plain_rf.scrub_go && we_a_i));
    if (SCRUB != 0) begin
      assert (g_plain_rf.scrub_ptr != 0);
      cover (g_plain_rf.scrub_ptr == 31);
    end
    cover (we_a_i && waddr_a_i == 31 && raddr_b_i == 31);
    cover (we_a_i && waddr_a_i == 0 && raddr_a_i == 0);
  end
