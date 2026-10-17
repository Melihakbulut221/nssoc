// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Buffer an entire DWORD TLP before emitting prefix, octets, and LCRC.
// Header DWs are MSB-first; data DWs are LSB-first. Reserved prefix bits are 0.
// Output SOP/EOP are project-local packet markers, NOT physical STP/END symbols.
// There is no replay buffer, credit accounting or ACK processing. Sequence
// increments only when the final LCRC byte is accepted; reset discards partials.
module soc_pcie_lcrc_tx #(parameter integer MAX_TLP_DWORDS=8) (
    input wire clk_i,rst_ni,
    input wire [31:0] tlp_data_i,
    input wire tlp_sop_i,tlp_eop_i,tlp_error_i,tlp_valid_i,
    output wire tlp_ready_o,
    output reg [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,
    input wire tx_ready_i,
    output reg [11:0] next_sequence_o,
    output reg packet_sent_o,packet_bad_o
);
    localparam integer CW=$clog2(MAX_TLP_DWORDS+1);
    localparam [2:0] IDLE=0,COLLECT=1,DROP=2,PREFIX0=3,PREFIX1=4,DATA=5,CRC=6;
    reg [2:0] state,header_words;
    reg [CW-1:0] count,length,index;
    reg [1:0] byte_index;
    reg [31:0] words [0:MAX_TLP_DWORDS-1];
    reg [31:0] crc;
    wire [31:0] crc_next;
    assign tlp_ready_o=rst_ni && (state==IDLE || state==COLLECT || state==DROP);
    assign tx_valid_o=rst_ni && state>=PREFIX0;
    assign tx_sop_o=state==PREFIX0;
    assign tx_eop_o=state==CRC && byte_index==3;
    soc_pcie_crc32_byte crc_step(.state_i(crc),.data_i(tx_data_o),.state_o(crc_next));
    always @* begin
        tx_data_o=0;
        case (state)
            PREFIX0:tx_data_o={4'b0,next_sequence_o[11:8]};
            PREFIX1:tx_data_o=next_sequence_o[7:0];
            DATA:begin
                if (index<header_words) tx_data_o=words[index] >> (8*(3-byte_index));
                else tx_data_o=words[index] >> (8*byte_index);
            end
            CRC:tx_data_o=(~crc) >> (8*byte_index);
            default:tx_data_o=0;
        endcase
    end
    generate if (MAX_TLP_DWORDS<4 || MAX_TLP_DWORDS>1028) begin: invalid_capacity
        initial $error("MAX_TLP_DWORDS must be 4..1028");
    end endgenerate
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state<=IDLE;count<=0;length<=0;index<=0;byte_index<=0;
            header_words<=3;crc<=32'hffffffff;next_sequence_o<=0;
            packet_sent_o<=0;packet_bad_o<=0;
        end else begin
            packet_sent_o<=0;packet_bad_o<=0;
            if (tx_valid_o && tx_ready_i) begin
                if (state!=CRC) crc<=crc_next;
                case(state)
                    PREFIX0:state<=PREFIX1;
                    PREFIX1:begin state<=DATA;index<=0;byte_index<=0;end
                    DATA:begin
                        byte_index<=byte_index+1'b1;
                        if (byte_index==3) begin
                            if (index==length-1'b1) state<=CRC;
                            else index<=index+1'b1;
                        end
                    end
                    CRC:begin
                        byte_index<=byte_index+1'b1;
                        if (byte_index==3) begin
                            state<=IDLE;next_sequence_o<=next_sequence_o+1'b1;packet_sent_o<=1;
                        end
                    end
                    default:state<=IDLE;
                endcase
            end else if (tlp_valid_i && tlp_ready_o) begin
                if (tlp_sop_i) begin
                    if (state==COLLECT) packet_bad_o<=1;
                    words[0]<=tlp_data_i;count<=1;header_words<=tlp_data_i[29] ? 4 : 3;
                    if (tlp_eop_i || tlp_error_i) begin
                        packet_bad_o<=1;state<=tlp_eop_i ? IDLE : DROP;
                    end else state<=COLLECT;
                end else if (state==IDLE) begin
                    packet_bad_o<=1;state<=tlp_eop_i ? IDLE : DROP;
                end else if (state==DROP) begin
                    if (tlp_eop_i) state<=IDLE;
                end else if (tlp_error_i || count==MAX_TLP_DWORDS) begin
                    packet_bad_o<=1;state<=tlp_eop_i ? IDLE : DROP;
                end else begin
                    words[count]<=tlp_data_i;count<=count+1'b1;
                    if (tlp_eop_i) begin
                        if (count+1>=header_words) begin
                            length<=count+1'b1;state<=PREFIX0;crc<=32'hffffffff;byte_index<=0;
                        end else begin packet_bad_o<=1;state<=IDLE;end
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
