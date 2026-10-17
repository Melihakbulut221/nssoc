// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Merge complete LCRC TLP byte packets and generated ACK/NAK DLLPs.
// Packet-level round robin prevents starvation. Selection locks even when the
// first byte stalls, and remains locked across bubbles until accepted EOP.
// tx_dllp_o distinguishes DLLPs for a future PCS; framing symbols absent.
// Upstream TLP source must supply legal stable SOP/EOP framing. No credits,
// replay, ACK latency limit, lane encoding or line-rate performance is implied.
module soc_pcie_packet_tx (
    input wire clk_i,rst_ni,
    input wire ack_valid_i,ack_nak_i,
    input wire [11:0] ack_sequence_i,
    output wire ack_ready_o,
    input wire [7:0] tlp_data_i,
    input wire tlp_sop_i,tlp_eop_i,tlp_valid_i,
    output wire tlp_ready_o,
    output wire [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,tx_dllp_o,
    input wire tx_ready_i
);
    wire [7:0] dllp_data;
    wire dllp_sop,dllp_eop,dllp_valid,dllp_ready;
    reg locked,select_dllp,prefer_dllp;
    wire chosen=locked ? select_dllp :
        (dllp_valid && (prefer_dllp || !tlp_valid_i));
    soc_pcie_acknak_tx ack_encoder(
        .clk_i(clk_i),.rst_ni(rst_ni),.ack_valid_i(ack_valid_i),
        .ack_nak_i(ack_nak_i),.ack_sequence_i(ack_sequence_i),.ack_ready_o(ack_ready_o),
        .tx_data_o(dllp_data),.tx_sop_o(dllp_sop),.tx_eop_o(dllp_eop),
        .tx_valid_o(dllp_valid),.tx_ready_i(dllp_ready));
    assign tx_data_o=chosen ? dllp_data : tlp_data_i;
    assign tx_sop_o=chosen ? dllp_sop : tlp_sop_i;
    assign tx_eop_o=chosen ? dllp_eop : tlp_eop_i;
    assign tx_valid_o=rst_ni && (chosen ? dllp_valid : tlp_valid_i);
    assign tx_dllp_o=chosen;
    assign dllp_ready=rst_ni && chosen && tx_ready_i;
    assign tlp_ready_o=rst_ni && !chosen && tx_ready_i;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin locked<=0;select_dllp<=0;prefer_dllp<=1;end
        else if(tx_valid_o) begin
            if(tx_ready_i && tx_eop_o) begin locked<=0;prefer_dllp<=!chosen;end
            else begin locked<=1;select_dllp<=chosen;end
        end
    end
endmodule
`default_nettype wire
