// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Classic six-byte DLLPs at a project-local SOP/EOP byte boundary.
// Base 2.1 section 3.4: CRC16 over four body bytes, bit0 first. No PCS symbols.
// Only ACK/NAK and unscaled VC0 flow-control messages are implemented.
module soc_pcie_dllp_rx (
    input wire clk_i,rst_ni,
    input wire [7:0] rx_data_i,
    input wire rx_sop_i,rx_eop_i,rx_error_i,rx_valid_i,
    output wire rx_ready_o,
    output reg ack_valid_o,ack_nak_o,
    output reg [11:0] ack_sequence_o,
    input wire ack_ready_i,
    output reg fc_valid_o,
    output reg [1:0] fc_phase_o,fc_class_o,
    output reg [7:0] fc_header_o,
    output reg [11:0] fc_data_o,
    output reg bad_dllp_o,unsupported_dllp_o
);
    reg active,bad;
    reg [2:0] count;
    reg [7:0] kind,b1,b2,b3,trailer;
    reg [15:0] crc;
    wire [15:0] next_crc;
    soc_pcie_crc16_byte crc_byte(.state_i(rx_sop_i ? 16'hffff : crc),
        .data_i(rx_data_i),.state_o(next_crc));
    assign rx_ready_o=rst_ni && !ack_valid_o;
    wire is_fc=(kind==8'h40 || kind==8'h50 || kind==8'h60 ||
                kind==8'hc0 || kind==8'hd0 || kind==8'he0 ||
                kind==8'h80 || kind==8'h90 || kind==8'ha0);
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            active<=0;bad<=0;count<=0;kind<=0;b1<=0;b2<=0;b3<=0;trailer<=0;crc<=16'hffff;
            ack_valid_o<=0;ack_nak_o<=0;ack_sequence_o<=0;
            fc_valid_o<=0;fc_phase_o<=0;fc_class_o<=0;fc_header_o<=0;fc_data_o<=0;
            bad_dllp_o<=0;unsupported_dllp_o<=0;
        end else begin
            bad_dllp_o<=0;unsupported_dllp_o<=0;fc_valid_o<=0;
            if(ack_valid_o && ack_ready_i) ack_valid_o<=0;
            if(rx_valid_i && rx_ready_o) begin
                if(rx_sop_i) begin
                    if(active || rx_eop_i) bad_dllp_o<=1;
                    active<=!rx_eop_i;bad<=rx_error_i;count<=1;kind<=rx_data_i;crc<=next_crc;
                end else if(!active) bad_dllp_o<=1;
                else begin
                    bad<=bad || rx_error_i;
                    if(count==1) b1<=rx_data_i;
                    if(count==2) b2<=rx_data_i;
                    if(count==3) b3<=rx_data_i;
                    if(count<4) crc<=next_crc;
                    if(count==4) trailer<=rx_data_i;
                    if(count<7) count<=count+1'b1;
                    if(count>=6) bad<=1;
                    if(rx_eop_i) begin
                        active<=0;
                        if(count!=5 || bad || rx_error_i || trailer!=~crc[7:0] || rx_data_i!=~crc[15:8])
                            bad_dllp_o<=1;
                        else if(kind==8'h00 || kind==8'h10) begin
                            if(b1!=0 || b2[7:4]!=0) unsupported_dllp_o<=1;
                            else begin ack_valid_o<=1;ack_nak_o<=kind[4];ack_sequence_o<={b2[3:0],b3};end
                        end else if(is_fc && b1[7:6]==0 && b2[5:4]==0) begin
                            fc_valid_o<=1;fc_header_o<={b1[5:0],b2[7:6]};fc_data_o<={b2[3:0],b3};
                            fc_phase_o<=kind[7:6]==2'b01 ? 0 : kind[7:6]==2'b11 ? 1 : 2;
                            fc_class_o<=kind[5:4]==0 ? 0 : kind[5:4]==1 ? 1 : 2;
                        end else unsupported_dllp_o<=1;
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
