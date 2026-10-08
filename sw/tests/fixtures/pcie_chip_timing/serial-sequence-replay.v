// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Bounded complete encoded-TLP retry buffer. Original sequence/LCRC bytes are
// retained until a cumulative ACK in the fully transmitted window frees them.
// Base2.1 section3.5.2.1 ordering; timer is configurable local clock cycles,
// not a claimed line-rate REPLAY_TIMER limit. Recovery handshake is external.
module soc_pcie_replay_tx #(
    parameter integer DEPTH=4,MAX_BYTES=38,
    parameter integer TIMEOUT_CYCLES=1024,MAX_REPLAYS=3
) (
    input wire clk_i,rst_ni,link_up_i,training_i,retrain_done_i,
    input wire [7:0] in_data_i,
    input wire in_sop_i,in_eop_i,in_valid_i,
    output wire in_ready_o,
    input wire ack_valid_i,ack_nak_i,
    input wire [11:0] ack_sequence_i,
    output wire ack_ready_o,
    output wire reserve_valid_o,
    input wire reserve_ready_i,
    output wire [1:0] reserve_class_o,
    output wire [10:0] reserve_payload_dw_o,
    output wire reserve_replay_o,
    output wire [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,tx_replay_o,
    input wire tx_ready_i,
    output wire [4:0] buffered_o,outstanding_o,
    output reg [11:0] acknowledged_sequence_o,
    output reg replay_started_o,timeout_o,protocol_error_o,
    output reg retry_exhausted_o,source_error_o,
    output wire retrain_request_o
);
    localparam integer PW=(DEPTH<=2 ? 1 : $clog2(DEPTH));
    localparam integer CW=$clog2(DEPTH+1);
    localparam integer BW=$clog2(MAX_BYTES+1);
    localparam integer TW=(TIMEOUT_CYCLES<=2 ? 1 : $clog2(TIMEOUT_CYCLES));
    reg [7:0] bytes [0:DEPTH*MAX_BYTES-1];
    reg [BW-1:0] lengths [0:DEPTH-1];
    reg [PW-1:0] head,tail,send_slot,replay_slot;
    reg [CW-1:0] count,sent_count,replay_left;
    reg [BW-1:0] write_pos,read_pos;
    reg capturing,sending,sending_replay,replay_active,replay_pending,replay_first,halt;
    reg [11:0] next_store_sequence;
    reg [31:0] input_crc;
    reg [TW-1:0] timer;
    reg timer_running;
    reg [2:0] retries;
    reg ack_observed,ack_was_allowed,ack_was_stale;
    wire [31:0] next_crc;
    soc_pcie_crc32_byte input_crc_byte(.state_i(in_sop_i ? 32'hffffffff : input_crc),
        .data_i(in_data_i),.state_o(next_crc));
    function [PW-1:0] advance;
        input [PW-1:0] pointer;
        input [CW:0] amount;
        reg [CW+1:0] sum;
        begin sum=pointer+amount;advance=(sum>=DEPTH) ? sum-DEPTH : sum;end
    endfunction
    wire [PW-1:0] new_slot=advance(head,{1'b0,sent_count});
    wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;
    // Classify at the first validated ACK presentation, even if frame atomicity
    // delays consumption. Backpressure cannot turn an early future ACK valid.
    wire current_ack_allowed=ack_delta==0 || (ack_delta<=sent_count && ack_delta!=0);
    wire ack_allowed=ack_observed ? ack_was_allowed : current_ack_allowed;
    wire ack_stale=ack_observed ? ack_was_stale : ack_delta>12'd2048;
    wire [7:0] first_header=bytes[new_slot*MAX_BYTES+2];
    wire [9:0] payload_length={bytes[new_slot*MAX_BYTES+4][1:0],bytes[new_slot*MAX_BYTES+5]};
    assign reserve_class_o=(first_header[4:0]==5'b01010 || first_header[4:0]==5'b01011) ? 2 :
        ((first_header[4:0]==0 && first_header[6]) || first_header[4:3]==2'b10) ? 0 : 1;
    assign reserve_payload_dw_o=!first_header[6] ? 0 : payload_length==0 ? 11'd1024 : {1'b0,payload_length};
    // Reservation is a cancellable request until handshake. A replay bypasses
    // it entirely: its receiver credit was reserved on original transmission.
    assign reserve_replay_o=0;
    wire timer_expiring=timer_running && !training_i && timer==TIMEOUT_CYCLES-1;
    assign reserve_valid_o=rst_ni && link_up_i && !training_i && !halt && !sending &&
        !capturing && !timer_expiring && !replay_active && !replay_pending && !ack_valid_i && count>sent_count;
    assign in_ready_o=rst_ni && link_up_i && !halt &&
        (capturing || (!replay_active && !replay_pending && !ack_valid_i && count<DEPTH));
    assign ack_ready_o=rst_ni && link_up_i && !sending && !capturing && !replay_active;
    assign tx_valid_o=rst_ni && link_up_i && sending;
    assign tx_data_o=bytes[send_slot*MAX_BYTES+read_pos];
    assign tx_sop_o=read_pos==0;
    assign tx_eop_o=read_pos==lengths[send_slot]-1'b1;
    assign tx_replay_o=sending_replay;
    assign buffered_o=count;
    assign outstanding_o=sent_count;
    assign retrain_request_o=halt;
    initial begin
        if(DEPTH<2 || DEPTH>16 || MAX_BYTES<18 || MAX_BYTES>2048 ||
            TIMEOUT_CYCLES<2 || MAX_REPLAYS<1 || MAX_REPLAYS>7) $error("Unsupported bounded replay parameters");
    end
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            head<=0;tail<=0;send_slot<=0;replay_slot<=0;count<=0;sent_count<=0;replay_left<=0;
            write_pos<=0;read_pos<=0;capturing<=0;sending<=0;sending_replay<=0;
            replay_active<=0;replay_pending<=0;replay_first<=0;halt<=0;
            next_store_sequence<=0;input_crc<=32'hffffffff;timer<=0;timer_running<=0;retries<=0;
            ack_observed<=0;ack_was_allowed<=0;ack_was_stale<=0;
            acknowledged_sequence_o<=12'hfff;replay_started_o<=0;timeout_o<=0;
            protocol_error_o<=0;retry_exhausted_o<=0;source_error_o<=0;
        end else if(!link_up_i) begin
            head<=0;tail<=0;count<=0;sent_count<=0;capturing<=0;sending<=0;
            replay_active<=0;replay_pending<=0;halt<=0;next_store_sequence<=0;
            ack_observed<=0;ack_was_allowed<=0;ack_was_stale<=0;
            timer<=0;timer_running<=0;retries<=0;acknowledged_sequence_o<=12'hfff;
            replay_started_o<=0;timeout_o<=0;protocol_error_o<=0;retry_exhausted_o<=0;source_error_o<=0;
        end else begin
            replay_started_o<=0;timeout_o<=0;protocol_error_o<=0;
            if(ack_valid_i && !ack_observed) begin
                ack_observed<=1;ack_was_allowed<=current_ack_allowed;ack_was_stale<=ack_delta>12'd2048;
            end
            if(ack_valid_i && ack_ready_o) ack_observed<=0;
            if(timer_running && !training_i && !halt) begin
                if(timer==TIMEOUT_CYCLES-1) begin
                    timer_running<=0;timer<=0;replay_pending<=1;timeout_o<=1;
                end else timer<=timer+1'b1;
            end
            if(halt && retrain_done_i && !source_error_o) begin
                halt<=0;retry_exhausted_o<=0;retries<=0;replay_pending<=sent_count!=0;
            end
            if(in_valid_i && in_ready_o) begin
                input_crc<=next_crc;
                if(in_sop_i) begin
                    if(capturing || in_eop_i || in_data_i[7:4]!=0) begin
                        source_error_o<=1;halt<=1;capturing<=0;
                    end else begin bytes[tail*MAX_BYTES]<=in_data_i;write_pos<=1;capturing<=1;end
                end else if(!capturing || write_pos>=MAX_BYTES) begin
                    source_error_o<=1;halt<=1;capturing<=0;
                end else begin
                    bytes[tail*MAX_BYTES+write_pos]<=in_data_i;write_pos<=write_pos+1'b1;
                    if(in_eop_i) begin
                        capturing<=0;
                        if(write_pos<17 || next_crc!=32'hdebb20e3 ||
                           {bytes[tail*MAX_BYTES][3:0],bytes[tail*MAX_BYTES+1]}!=next_store_sequence) begin
                            source_error_o<=1;halt<=1;
                        end else begin
                            lengths[tail]<=write_pos+1'b1;count<=count+1'b1;
                            tail<=advance(tail,1);next_store_sequence<=next_store_sequence+1'b1;
                        end
                    end
                end
            end
            if(ack_valid_i && ack_ready_o) begin
                if(ack_allowed) begin
                    if(ack_delta!=0) begin
                        head<=advance(head,ack_delta[CW:0]);count<=count-ack_delta;
                        sent_count<=sent_count-ack_delta;acknowledged_sequence_o<=ack_sequence_i;
                        retries<=0;timer<=0;timer_running<=sent_count!=ack_delta;
                        replay_pending<=0;
                    end
                    if(ack_nak_i) begin
                        replay_pending<=sent_count!=ack_delta;timer_running<=0;timer<=0;
                    end
                end else if(!ack_stale) protocol_error_o<=1;
                // Older acknowledgments outside our small forward window are stale.
            end else if(!sending && !capturing && !training_i && !halt) begin
                if(replay_pending && !replay_active) begin
                    replay_pending<=0;
                    if(sent_count!=0) begin
                        if(retries==MAX_REPLAYS) begin halt<=1;retry_exhausted_o<=1;timer_running<=0;end
                        else begin
                            replay_active<=1;replay_slot<=head;replay_left<=sent_count;
                            replay_first<=1;retries<=retries+1'b1;replay_started_o<=1;
                        end
                    end
                end else if(replay_active) begin
                    sending<=1;sending_replay<=1;send_slot<=replay_slot;read_pos<=0;
                end else if(reserve_valid_o && reserve_ready_i) begin
                    sending<=1;sending_replay<=0;send_slot<=new_slot;read_pos<=0;
                end
            end
            if(tx_valid_o && tx_ready_i) begin
                if(tx_eop_o) begin
                    sending<=0;
                    if(sending_replay) begin
                        if(replay_first) begin timer<=0;timer_running<=1;replay_first<=0;end
                        if(replay_left==1) replay_active<=0;
                        else begin replay_left<=replay_left-1'b1;replay_slot<=advance(replay_slot,1);end
                    end else begin
                        sent_count<=sent_count+1'b1;
                        if(!timer_running) begin timer<=0;timer_running<=1;end
                    end
                end else read_pos<=read_pos+1'b1;
            end
        end
    end
endmodule
`default_nettype wire
