// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Classic non-Flit sequence acceptance after complete LCRC quarantine.
// ACK/NAK are ready/valid REQUEST RECORDS, not encoded DLLPs or a link controller.
// Immediate ACK requests; no AckNak timer, credits, replay or DL state machine.
// Reset represents the local boundary becoming inactive; counters reset to zero.
module soc_pcie_sequence_rx #(parameter integer MAX_TLP_DWORDS=8) (
    input wire clk_i,rst_ni,
    input wire [7:0] rx_data_i,
    input wire rx_sop_i,rx_eop_i,rx_error_i,rx_valid_i,
    output wire rx_ready_o,
    output wire [7:0] tlp_data_o,
    output wire tlp_sop_o,tlp_eop_o,tlp_valid_o,
    input wire tlp_ready_i,
    output reg ack_valid_o,ack_nak_o,
    output reg [11:0] ack_sequence_o,
    input wire ack_ready_i,
    output reg [11:0] expected_sequence_o,
    output reg packet_accepted_o,packet_duplicate_o,packet_rejected_o
);
    wire [11:0] received_sequence;
    wire [3:0] unused_reserved;
    wire good,bad,raw_valid,raw_sop,raw_eop,raw_ready;
    reg decided,forward_packet,nak_scheduled;
`ifndef SOC_PCIE_SEQ_RX_REG
    wire allow_input=!ack_valid_o && !good && !bad;
`else
    // docs/combined-timing.md section 19 (default off): the input ready is
    // a register. input_open equals state!=EMIT && !ack_valid_o && !good
    // && !bad of the default build in every cycle (loaded with that
    // expression's next value, set by reset like it), so rx_ready_o is
    // rst_ni && input_open. allow_input may differ from the default only
    // while the quarantine emits, when it ignores rx_valid_i.
    reg input_open;
    wire quarantine_open_next;
    wire allow_input=input_open;
`endif
    // expected_sequence_o changes only when a packet is accepted, at most
    // once per received packet, and received_sequence is fixed from the
    // packet's second byte until its verdict. So the distance and the
    // sequence numbers one above and below are registered a cycle ahead and
    // equal their combinational values whenever a verdict is taken.
    reg [11:0] behind,expected_plus,expected_minus;
    always @(posedge clk_i) begin
        behind<=expected_sequence_o-received_sequence;
        expected_plus<=expected_sequence_o+1'b1;
        expected_minus<=expected_sequence_o-1'b1;
    end
`ifndef SOC_PCIE_SEQ_RX_REG
    wire expected=received_sequence==expected_sequence_o;
`else
    // Section 19: the sequence compare is registered a cycle ahead, like
    // behind. It is only used at a verdict (good), and in the cycle before
    // a verdict neither operand changes: received_sequence is written by
    // a packet's first two bytes, at least fifteen bytes before its end,
    // and expected_sequence_o only at a verdict, which is never in the
    // cycle before another.
    reg expected_q;
    always @(posedge clk_i) expected_q<=received_sequence==expected_sequence_o;
    wire expected=expected_q;
`endif
    wire duplicate=!expected && behind<=12'd2048;
`ifndef SOC_PCIE_SEQ_RX_REG
    assign rx_ready_o=raw_ready && allow_input;
`else
    assign rx_ready_o=rst_ni && input_open;
    // The next value of ack_valid_o (the block below).
    wire ack_next=good ? (expected || duplicate || !nak_scheduled || (ack_valid_o && !ack_ready_i)) :
        bad ? (!nak_scheduled || (ack_valid_o && !ack_ready_i)) : (ack_valid_o && !ack_ready_i);
    always @(posedge clk_i or negedge rst_ni)
        if (!rst_ni) input_open<=1'b1;
        else input_open<=quarantine_open_next && !ack_next;
`ifndef SYNTHESIS
    // Simulation only: the registers equal the expressions they replace.
    always @(posedge clk_i) if (rst_ni===1'b1) begin
        if (input_open!==(raw_ready && !ack_valid_o && !good && !bad)) begin
            $display("SEQ_RX_OPEN_MISMATCH t=%0t open=%b", $time, input_open);
            $fatal(1, "registered input ready differs");
        end
        if (good===1'b1 && expected_q!==(received_sequence==expected_sequence_o)) begin
            $display("SEQ_RX_EXPECTED_MISMATCH t=%0t", $time);
            $fatal(1, "registered sequence compare differs at a verdict");
        end
    end
`endif
`endif
    assign tlp_valid_o=raw_valid && decided && forward_packet;
    assign tlp_sop_o=raw_sop;
    assign tlp_eop_o=raw_eop;
    wire consume=decided && (!forward_packet || tlp_ready_i);
    soc_pcie_lcrc_rx #(.MAX_TLP_DWORDS(MAX_TLP_DWORDS)) quarantine(
        .clk_i(clk_i),.rst_ni(rst_ni),.rx_data_i(rx_data_i),.rx_sop_i(rx_sop_i),
        .rx_eop_i(rx_eop_i),.rx_error_i(rx_error_i),.rx_valid_i(rx_valid_i && allow_input),
        .rx_ready_o(raw_ready),.tlp_data_o(tlp_data_o),.tlp_sop_o(raw_sop),
        .tlp_eop_o(raw_eop),.tlp_valid_o(raw_valid),.tlp_ready_i(consume),
        .sequence_o(received_sequence),.reserved_o(unused_reserved),
        .packet_good_o(good),.packet_bad_o(bad)
`ifdef SOC_PCIE_SEQ_RX_REG
        ,.open_next_o(quarantine_open_next)
`endif
        );
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            ack_valid_o<=0;ack_nak_o<=0;ack_sequence_o<=12'hfff;
            expected_sequence_o<=0;packet_accepted_o<=0;packet_duplicate_o<=0;
            packet_rejected_o<=0;decided<=0;forward_packet<=0;nak_scheduled<=0;
        end else begin
            packet_accepted_o<=0;packet_duplicate_o<=0;packet_rejected_o<=0;
            if (ack_valid_o && ack_ready_i) ack_valid_o<=0;
            if (raw_valid && consume && raw_eop) begin decided<=0;forward_packet<=0;end
            if (good) begin
                decided<=1;forward_packet<=expected;
                if (expected) begin
                    packet_accepted_o<=1;expected_sequence_o<=expected_plus;
                    nak_scheduled<=0;ack_valid_o<=1;ack_nak_o<=0;
                    ack_sequence_o<=received_sequence;
                end else if (duplicate) begin
                    packet_duplicate_o<=1;ack_valid_o<=1;ack_nak_o<=0;
                    ack_sequence_o<=expected_minus;
                end else begin
                    packet_rejected_o<=1;
                    if (!nak_scheduled) begin
                        ack_valid_o<=1;ack_nak_o<=1;ack_sequence_o<=expected_minus;
                        nak_scheduled<=1;
                    end
                end
            end else if (bad) begin
                packet_rejected_o<=1;
                if (!nak_scheduled) begin
                    ack_valid_o<=1;ack_nak_o<=1;ack_sequence_o<=expected_minus;
                    nak_scheduled<=1;
                end
            end
        end
    end
endmodule
`default_nettype wire
