// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Serialize one classic ACK/NAK DLLP: type, zero reserved byte, sequence high
// nibble, sequence low byte, complemented reflected CRC low then high byte.
// This is a six-byte packet boundary, NOT Gen3 SDP/END coding or a PHY.
// Request lifetime is independent of downstream stalls; no coalescing/timer.
module soc_pcie_acknak_tx (
    input wire clk_i,rst_ni,
    input wire ack_valid_i,ack_nak_i,
    input wire [11:0] ack_sequence_i,
    output wire ack_ready_o,
    output reg [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,
    input wire tx_ready_i
);
    reg busy,nak;
    reg [11:0] sequence_reg;
    reg [2:0] index;
    reg [15:0] crc;
    wire [15:0] crc_next;
    soc_pcie_crc16_byte crc_byte(.state_i(crc),.data_i(tx_data_o),.state_o(crc_next));
    assign ack_ready_o=rst_ni && !busy;
    assign tx_valid_o=rst_ni && busy;
    assign tx_sop_o=busy && index==0;
    assign tx_eop_o=busy && index==5;
    always @* begin
        case(index)
            0:tx_data_o=nak ? 8'h10 : 8'h00;
            1:tx_data_o=0;
            2:tx_data_o={4'b0,sequence_reg[11:8]};
            3:tx_data_o=sequence_reg[7:0];
            4:tx_data_o=~crc[7:0];
            default:tx_data_o=~crc[15:8];
        endcase
    end
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            busy<=0;nak<=0;sequence_reg<=0;index<=0;crc<=16'hffff;
        end else if(!busy) begin
            if(ack_valid_i) begin
                busy<=1;nak<=ack_nak_i;sequence_reg<=ack_sequence_i;
                index<=0;crc<=16'hffff;
            end
        end else if(tx_ready_i) begin
            if(index<4) crc<=crc_next;
            if(index==5) begin busy<=0;index<=0;end
            else index<=index+1'b1;
        end
    end
endmodule
`default_nettype wire
