// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Included inside the actual register file, with real encoders/decoders.
// The reference-array and codeword relations are proved assertions.
`include "ibex_regfile_contract_props.v"

  (* anyconst *) reg [4:0] f_scrub_idx;
  (* anyconst *) reg [31:0] f_scrub_val;
  always @(*) assume (f_scrub_idx != 0);
  reg f_scrub_armed = 1'b0;
  always @(posedge clk_i or negedge rst_ni)
    if (!rst_ni) f_scrub_armed <= 1'b0;
    else if (we_a_i && waddr_a_i == f_scrub_idx)
      f_scrub_armed <= (wdata_a_i == f_scrub_val);
  // Precisely the original write-once R1 premise; other writes stay free.
  always @(*) if (f_scrub_armed && we_a_i)
    assume (waddr_a_i != f_scrub_idx);

  reg [5:0] f_scrub_visits;
  reg [31:1] f_scrub_seen;
  always @(posedge clk_i or negedge rst_ni)
    if (!rst_ni) f_scrub_seen <= 0;
    else if (!f_scrub_armed) f_scrub_seen <= 0;
    else if (g_plain_rf.scrub_go)
      f_scrub_seen <= f_scrub_seen | (31'b1 << (g_plain_rf.scrub_ptr - 5'd1));
  always @(posedge clk_i or negedge rst_ni)
    if (!rst_ni) f_scrub_visits <= 0;
    else if (!f_scrub_armed) f_scrub_visits <= 0;
    else if (g_plain_rf.scrub_go && f_scrub_visits < 32)
      f_scrub_visits <= f_scrub_visits + 1'b1;

  always @(posedge clk_i) if (f_contract_valid && rst_ni) begin
    // One concrete trace must visit ALL 31 words after the monitored write,
    // cross the wrap, and read the nonzero word through both ports.
    cover (f_scrub_armed && f_scrub_val != 0 && f_scrub_visits == 32 &&
           &f_scrub_seen &&
           raddr_a_i == f_scrub_idx && raddr_b_i == f_scrub_idx);
    cover (f_scrub_armed && we_a_i && waddr_a_i != f_scrub_idx);
    if ($past(rst_ni)) begin
      if ($past(we_a_i))
        assert (g_plain_rf.scrub_ptr == $past(g_plain_rf.scrub_ptr));
      else
        assert (g_plain_rf.scrub_ptr ==
                ($past(g_plain_rf.scrub_ptr) == 31 ? 1 :
                 $past(g_plain_rf.scrub_ptr) + 5'd1));
    end
  end

  genvar fs;
  generate for (fs = 1; fs < 32; fs = fs + 1) begin : g_scrub_visit
    always @(posedge clk_i) if (f_contract_valid && rst_ni) begin
      if (f_scrub_armed && f_scrub_idx == fs[4:0]) begin
        assert (f_reference[fs] == f_scrub_val);
        assert (g_plain_rf.rf_data[fs] == f_scrub_val);
        if (raddr_a_i == fs[4:0]) assert (rdata_a_o == f_scrub_val);
        if (raddr_b_i == fs[4:0]) assert (rdata_b_o == f_scrub_val);
      end
    end
  end endgenerate
