// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Classic VC0 credit advertisements. Limits describe real local storage, not
// remote transmit credits. Snapshot and sent counters commit at accepted EOP.
// REFRESH_CYCLES is a project-clock parameter; not a qualified link timer.
module soc_pcie_fc_tx #(
    parameter integer REFRESH_CYCLES=128
)(
    input wire clk_i,rst_ni,link_up_i,training_i,
    input wire peer_init1_done_i,peer_init2_seen_i,
    input wire [23:0] header_limit_i,
    input wire [35:0] data_limit_i,
    output reg local_init_done_o,
    output wire local_init2_sent_o,
    output reg [23:0] sent_header_o,
    output reg [35:0] sent_data_o,
    output reg sent_valid_o,
    output reg [1:0] sent_phase_o,sent_class_o,
    output wire [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,
    input wire tx_ready_i
);
    reg active;
    reg [2:0] index;
    reg [1:0] phase, class_index, frame_phase, frame_class;
    reg [7:0] header;
    reg [11:0] data_credit;
    reg [15:0] crc;
    reg [31:0] refresh;
    reg first_triplet,second_triplet;
    wire [7:0] current_header=header_limit_i[class_index*8 +: 8];
    wire [11:0] current_data=data_limit_i[class_index*12 +: 12];
    wire dirty=current_header!=sent_header_o[class_index*8 +: 8] ||
               current_data!=sent_data_o[class_index*12 +: 12];
    reg [7:0] octet;
    wire [15:0] next_crc;
    soc_pcie_crc16_byte step(.state_i(crc),.data_i(octet),.state_o(next_crc));
    always @* begin
        case(index)
            0: octet=(frame_phase==0 ? 8'h40 : frame_phase==1 ? 8'hc0 : 8'h80) |
                     {2'b00,frame_class,4'b0000};
            1: octet={2'b00,header[7:2]};
            2: octet={header[1:0],2'b00,data_credit[11:8]};
            3: octet=data_credit[7:0];
            4: octet=~crc[7:0];
            default: octet=~crc[15:8];
        endcase
    end
    assign local_init2_sent_o=second_triplet;
    assign tx_data_o=octet;
    assign tx_valid_o=rst_ni && link_up_i && active;
    assign tx_sop_o=active && index==0;
    assign tx_eop_o=active && index==5;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            active<=0;index<=0;phase<=0;class_index<=0;frame_phase<=0;frame_class<=0;
            header<=0;data_credit<=0;crc<=16'hffff;refresh<=0;
            first_triplet<=0;second_triplet<=0;local_init_done_o<=0;
            sent_header_o<=0;sent_data_o<=0;sent_valid_o<=0;sent_phase_o<=0;sent_class_o<=0;
        end else if(!link_up_i) begin
            active<=0;index<=0;phase<=0;class_index<=0;refresh<=0;
            first_triplet<=0;second_triplet<=0;local_init_done_o<=0;
            sent_header_o<=0;sent_data_o<=0;sent_valid_o<=0;
        end else begin
            sent_valid_o<=0;
            if(!training_i && refresh<REFRESH_CYCLES) refresh<=refresh+1;
            if(!active && !training_i) begin
                if(phase==0 && first_triplet && peer_init1_done_i) begin
                    phase<=1;class_index<=0;
                end else if(phase==1 && second_triplet && peer_init2_seen_i) begin
                    phase<=2;class_index<=0;local_init_done_o<=1;refresh<=REFRESH_CYCLES;
                end else if(phase!=2 || dirty || refresh>=REFRESH_CYCLES) begin
                    active<=1;index<=0;crc<=16'hffff;
                    frame_phase<=phase;frame_class<=class_index;
                    header<=current_header;data_credit<=current_data;
                end else class_index<=class_index==2 ? 0 : class_index+1'b1;
            end
            if(tx_valid_o && tx_ready_i) begin
                if(index<4) crc<=next_crc;
                if(index==5) begin
                    active<=0;index<=0;
                    sent_header_o[frame_class*8 +: 8]<=header;
                    sent_data_o[frame_class*12 +: 12]<=data_credit;
                    sent_valid_o<=1;sent_phase_o<=frame_phase;sent_class_o<=frame_class;
                    class_index<=frame_class==2 ? 0 : frame_class+1'b1;
                    if(frame_class==2) begin
                        if(frame_phase==0) first_triplet<=1;
                        if(frame_phase==1) second_triplet<=1;
                        if(frame_phase==2) refresh<=0;
                    end
                end else index<=index+1'b1;
            end
        end
    end
endmodule
`default_nettype wire
