// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Direct miter against the pinned, sv2v-converted upstream Ibex file.
// The DUT's internal assertions strengthen induction without assumptions
// about the codec. Its only environmental assumption is initial reset.
`default_nettype none
module regfile_equivalence_props #(
  parameter integer SCRUB = 1
) (
  input wire clk_i, rst_ni, we_a_i,
  input wire test_en_i, dummy_instr_id_i, dummy_instr_wb_i,
  input wire [3:0] cheriot_enable_i,
  input wire [4:0] raddr_a_i, raddr_b_i, waddr_a_i,
  input wire [31:0] wdata_a_i,
  input wire [34:0] wcap_a_i
);
  wire [31:0] gold_a, gold_b, gate_a, gate_b;
  wire [34:0] gold_cap_a, gold_cap_b, gate_cap_a, gate_cap_b;
  wire [2:0] errors;

`define RF_INPUTS \
    .clk_i(clk_i), .rst_ni(rst_ni), .we_a_i(we_a_i), \
    .test_en_i(test_en_i), .dummy_instr_id_i(dummy_instr_id_i), \
    .dummy_instr_wb_i(dummy_instr_wb_i), .cheriot_enable_i(cheriot_enable_i), \
    .raddr_a_i(raddr_a_i), .raddr_b_i(raddr_b_i), \
    .waddr_a_i(waddr_a_i), .wdata_a_i(wdata_a_i), .wcap_a_i(wcap_a_i)

  ibex_register_file_gold gold (
    `RF_INPUTS,
    .rdata_a_o(gold_a), .rdata_b_o(gold_b),
    .rcap_a_o(gold_cap_a), .rcap_b_o(gold_cap_b)
  );
  ibex_register_file_ff #(.SCRUB(SCRUB)) gate (
    `RF_INPUTS,
    .rdata_a_o(gate_a), .rdata_b_o(gate_b),
    .rcap_a_o(gate_cap_a), .rcap_b_o(gate_cap_b), .rf_ecc_err_o(errors)
  );
`undef RF_INPUTS

  reg past_valid = 1'b0;
  always @(posedge clk_i) begin
    past_valid <= 1'b1;
    if (past_valid && rst_ni) begin
      assert (gold_a == gate_a);
      assert (gold_b == gate_b);
      assert (gold_cap_a == gate_cap_a);
      assert (gold_cap_b == gate_cap_b);
      assert (errors == 0);
    end
  end
endmodule
`default_nettype wire
