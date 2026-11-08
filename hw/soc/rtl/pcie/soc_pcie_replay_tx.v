// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Bounded complete encoded-TLP retry buffer. Original sequence/LCRC bytes are
// retained until a cumulative ACK in the fully transmitted window frees them.
// Base2.1 section3.5.2.1 ordering; timer is configurable local clock cycles,
// not a claimed line-rate REPLAY_TIMER limit. Recovery handshake is external.
// Two-entry valid/ready register slice. Every output and the upstream ready
// come from flops, so no combinational path crosses it in either direction.
// Accepted beats leave in order and an offered beat is never retracted.
module soc_pcie_stream_skid #(parameter integer W=8) (
    input wire clk_i,rst_ni,clear_i,
    input wire [W-1:0] s_data_i,
    input wire s_valid_i,
    output wire s_ready_o,
    output wire [W-1:0] m_data_o,
    output wire m_valid_o,
    input wire m_ready_i
);
    reg [W-1:0] main_data,spare_data;
    reg main_valid,spare_valid;
    assign s_ready_o=!spare_valid;
    assign m_data_o=main_data;
    assign m_valid_o=main_valid;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin main_valid<=0;spare_valid<=0;main_data<=0;spare_data<=0;end
        else if(clear_i) begin main_valid<=0;spare_valid<=0;end
        else if(m_ready_i || !main_valid) begin
            if(spare_valid) begin main_data<=spare_data;main_valid<=1;spare_valid<=0;end
            else begin main_valid<=s_valid_i;if(s_valid_i) main_data<=s_data_i;end
        end else if(s_valid_i && !spare_valid) begin spare_data<=s_data_i;spare_valid<=1;end
    end
endmodule
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
    localparam integer READ_CHOICES=(1<<BW);
    (* keep = 1 *) reg [READ_CHOICES-1:0] replay_read_onehot;
    reg capturing,sending,sending_replay,replay_active,replay_pending,replay_first,halt;
    reg [11:0] next_store_sequence;
    // Look ahead continuously. An accepted EOP ends capture, so the next
    // packet cannot commit on the immediately following clock. The cached
    // increment settles before the next commit without delaying any transfer.
    reg [11:0] next_store_sequence_plus_one;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) next_store_sequence_plus_one<=12'd1;
        else if(!link_up_i) next_store_sequence_plus_one<=12'd1;
        else next_store_sequence_plus_one<=next_store_sequence+12'd1;
    end
    // Captured bytes are written one cycle after they are accepted, from
    // registers. No byte is read within a cycle of its write: header and
    // sequence bytes are read at least eleven cycles later, and a slot is
    // read for transmission only after its commit, at least one cycle after
    // its last byte was accepted. The accept decision therefore no longer
    // drives the write enables of the whole store.
    localparam integer AW=$clog2(DEPTH*MAX_BYTES);
    reg write_valid;
    reg [AW-1:0] write_address;
    reg [7:0] write_data;
    wire [AW-1:0] capture_address=tail*MAX_BYTES+(in_sop_i ? {BW{1'b0}} : write_pos);
    always @(posedge clk_i) begin
        write_address<=capture_address;write_data<=in_data_i;
        if(write_valid) bytes[write_address]<=write_data;
    end
    reg [31:0] input_crc;
    reg [TW-1:0] timer;
    reg timer_running;
    reg [2:0] retries;
    reg ack_observed,ack_was_allowed,ack_was_stale;
    // The sequence distance of the presented ACK is registered with its
    // classification at the first presentation, and an ACK is consumed only
    // once it is classified, one cycle or more after it appears. The ACK
    // stays fixed until consumed, and the acknowledged sequence changes only
    // when an ACK is consumed, so the registered distance is exact.
    reg [11:0] ack_delta_q;
    wire [31:0] next_crc;
    wire replay_crc_residue_ok=((in_sop_i ? 32'hffffffff : input_crc) ^
                              {24'b0,in_data_i})==32'h00be26ed;
    soc_pcie_crc32_byte input_crc_byte(.state_i(in_sop_i ? 32'hffffffff : input_crc),
        .data_i(in_data_i),.state_o(next_crc));
    function [PW-1:0] advance;
        input [PW-1:0] pointer;
        input [CW:0] amount;
        reg [CW+1:0] sum;
        begin sum=pointer+amount;advance=(sum>=DEPTH) ? sum-DEPTH : sum;end
    endfunction
    // ACK retirement moves head forward and sent_count backward equally.
    // Only an original transmitted EOP advances their modulo sum. Keep that
    // frontier directly, removing the adder from credit reservation metadata.
    reg [PW-1:0] new_slot;
    wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;
    // Classify at the first validated ACK presentation, even if frame atomicity
    // delays consumption. Backpressure cannot turn an early future ACK valid.
    wire current_ack_allowed=ack_delta==0 || (ack_delta<=sent_count && ack_delta!=0);
    wire ack_allowed=ack_was_allowed;
    wire ack_stale=ack_was_stale;
    // Reservation metadata in registers, decoded one cycle ahead from the
    // header bytes of the slot new_slot will hold in the next cycle. A slot
    // is offered for reservation only after its accepted EOP, which follows
    // the writes of header bytes 2, 4 and 5 by at least eleven cycles, and an
    // offered slot is never rewritten (only the tail slot is captured, and
    // the tail equals an offered slot only when the store is full). While a
    // reservation is offered the registers therefore equal the decode of the
    // current slot's bytes, and the request no longer starts with a byte
    // multiplexer and header decode.
    wire core_valid,core_ready,core_eop;
    wire [PW-1:0] next_new_slot=!link_up_i ? {PW{1'b0}} :
        (core_valid && core_ready && core_eop && !sending_replay) ? advance(new_slot,1) : new_slot;
    // Every slot's header is decoded in parallel from its own bytes; the
    // next slot only selects a decoded result, so the frame-end condition
    // that picks the slot no longer runs through a byte multiplexer and the
    // decode.
    wire [1:0] slot_class [0:DEPTH-1];
    wire [10:0] slot_payload_dw [0:DEPTH-1];
    genvar meta_slot;
    generate for(meta_slot=0;meta_slot<DEPTH;meta_slot=meta_slot+1) begin: reserve_meta
        wire [7:0] header=bytes[meta_slot*MAX_BYTES+2];
        wire [9:0] length={bytes[meta_slot*MAX_BYTES+4][1:0],bytes[meta_slot*MAX_BYTES+5]};
        assign slot_class[meta_slot]=(header[4:0]==5'b01010 || header[4:0]==5'b01011) ? 2'd2 :
            ((header[4:0]==0 && header[6]) || header[4:3]==2'b10) ? 2'd0 : 2'd1;
        assign slot_payload_dw[meta_slot]=!header[6] ? 11'd0 : length==0 ? 11'd1024 : {1'b0,length};
    end endgenerate
    reg [1:0] reserve_class_q;
    reg [10:0] reserve_payload_dw_q;
    always @(posedge clk_i) begin
        reserve_class_q<=slot_class[next_new_slot];
        reserve_payload_dw_q<=slot_payload_dw[next_new_slot];
    end
    assign reserve_class_o=reserve_class_q;
    assign reserve_payload_dw_o=reserve_payload_dw_q;
    // Reservation is a cancellable request until handshake. A replay bypasses
    // it entirely: its receiver credit was reserved on original transmission.
    assign reserve_replay_o=0;
    wire timer_expiring=timer_running && !training_i && timer==TIMEOUT_CYCLES-1;
    assign reserve_valid_o=rst_ni && link_up_i && !training_i && !halt && !sending &&
        !capturing && !timer_expiring && !replay_active && !replay_pending && !ack_valid_i && count>sent_count;
    assign in_ready_o=rst_ni && link_up_i && !halt &&
        (capturing || (!replay_active && !replay_pending && !ack_valid_i && count<DEPTH));
    assign ack_ready_o=rst_ni && link_up_i && ack_observed && !sending && !capturing && !replay_active;
    // The transmit stream leaves through a register slice, so the replay
    // read path ends at a flop instead of continuing into the link layer.
    assign core_valid=rst_ni && link_up_i && sending;
    // A registered one-hot cursor removes binary-address decoding from
    // the memory-to-transmit path. Include cross-bank addresses exactly as
    // the flat reference does; unaddressable array reads remain undefined.
    wire [7:0] replay_bank_byte [0:DEPTH-1];
    genvar replay_bank,replay_bit,replay_offset;
    generate for(replay_bank=0;replay_bank<DEPTH;replay_bank=replay_bank+1) begin: read_replay_bank
        for(replay_bit=0;replay_bit<8;replay_bit=replay_bit+1) begin: read_bit
            wire [READ_CHOICES-1:0] selected;
            for(replay_offset=0;replay_offset<READ_CHOICES;replay_offset=replay_offset+1) begin: read_byte
                if(replay_bank*MAX_BYTES+replay_offset<DEPTH*MAX_BYTES) begin: present
                    assign selected[replay_offset]=replay_read_onehot[replay_offset] & bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit];
                end else begin: absent
                    assign selected[replay_offset]=1'b0;
                end
            end
            assign replay_bank_byte[replay_bank][replay_bit]=(read_pos<(DEPTH-replay_bank)*MAX_BYTES) ? |selected : 1'bx;
        end
    end endgenerate
    wire [7:0] core_data=replay_bank_byte[send_slot];
    wire core_sop=read_pos==0;
    // The last read position of the frame being sent is registered when the
    // send starts; a slot's length is written at its commit, before any
    // send of that slot, so this equals lengths[send_slot]-1 throughout.
    reg [BW-1:0] send_last;
    assign core_eop=read_pos==send_last;
    // The replay timer still starts when the last byte leaves on the wire:
    // the first-replayed-frame mark travels with the bytes.
    wire tx_first;
    soc_pcie_stream_skid #(.W(12)) transmit_slice(
        .clk_i(clk_i),.rst_ni(rst_ni),.clear_i(!link_up_i),
        .s_data_i({core_data,core_sop,core_eop,sending_replay,sending_replay && replay_first}),.s_valid_i(core_valid),.s_ready_o(core_ready),
        .m_data_o({tx_data_o,tx_sop_o,tx_eop_o,tx_replay_o,tx_first}),.m_valid_o(tx_valid_o),.m_ready_i(tx_ready_i));
    assign buffered_o=count;
    assign outstanding_o=sent_count;
    assign retrain_request_o=halt;
    initial begin
        if(DEPTH<2 || DEPTH>16 || MAX_BYTES<18 || MAX_BYTES>2048 ||
            TIMEOUT_CYCLES<2 || MAX_REPLAYS<1 || MAX_REPLAYS>7) $error("Unsupported bounded replay parameters");
    end
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            head<=0;tail<=0;new_slot<=0;send_slot<=0;send_last<=0;replay_slot<=0;count<=0;sent_count<=0;replay_left<=0;
            write_pos<=0;read_pos<=0;replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};capturing<=0;sending<=0;sending_replay<=0;
            replay_active<=0;replay_pending<=0;replay_first<=0;halt<=0;
            next_store_sequence<=0;input_crc<=32'hffffffff;timer<=0;timer_running<=0;retries<=0;
            ack_observed<=0;ack_was_allowed<=0;ack_was_stale<=0;ack_delta_q<=0;write_valid<=0;
            acknowledged_sequence_o<=12'hfff;replay_started_o<=0;timeout_o<=0;
            protocol_error_o<=0;retry_exhausted_o<=0;source_error_o<=0;
        end else if(!link_up_i) begin
            head<=0;tail<=0;new_slot<=0;count<=0;sent_count<=0;capturing<=0;sending<=0;write_valid<=0;
            replay_active<=0;replay_pending<=0;halt<=0;next_store_sequence<=0;
            ack_observed<=0;ack_was_allowed<=0;ack_was_stale<=0;
            timer<=0;timer_running<=0;retries<=0;acknowledged_sequence_o<=12'hfff;
            replay_started_o<=0;timeout_o<=0;protocol_error_o<=0;retry_exhausted_o<=0;source_error_o<=0;
        end else begin
            replay_started_o<=0;timeout_o<=0;protocol_error_o<=0;write_valid<=0;
            if(ack_valid_i && !ack_observed) begin
                ack_observed<=1;ack_was_allowed<=current_ack_allowed;ack_was_stale<=ack_delta>12'd2048;
                ack_delta_q<=ack_delta;
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
                    end else begin write_valid<=1;write_pos<=1;capturing<=1;end
                end else if(!capturing || write_pos>=MAX_BYTES) begin
                    source_error_o<=1;halt<=1;capturing<=0;
                end else begin
                    write_valid<=1;write_pos<=write_pos+1'b1;
                    if(in_eop_i) begin
                        capturing<=0;
                        if(write_pos<17 || !replay_crc_residue_ok ||
                           {bytes[tail*MAX_BYTES][3:0],bytes[tail*MAX_BYTES+1]}!=next_store_sequence) begin
                            source_error_o<=1;halt<=1;
                        end else begin
                            lengths[tail]<=write_pos+1'b1;count<=count+1'b1;
                            tail<=advance(tail,1);next_store_sequence<=next_store_sequence_plus_one;
                        end
                    end
                end
            end
            if(ack_valid_i && ack_ready_o) begin
                if(ack_allowed) begin
                    if(ack_delta_q!=0) begin
                        head<=advance(head,ack_delta_q[CW:0]);count<=count-ack_delta_q;
                        sent_count<=sent_count-ack_delta_q;acknowledged_sequence_o<=ack_sequence_i;
                        retries<=0;timer<=0;timer_running<=sent_count!=ack_delta_q;
                        replay_pending<=0;
                    end
                    if(ack_nak_i) begin
                        replay_pending<=sent_count!=ack_delta_q;timer_running<=0;timer<=0;
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
                    sending<=1;sending_replay<=1;send_slot<=replay_slot;send_last<=lengths[replay_slot]-1'b1;read_pos<=0;replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};
                end else if(reserve_valid_o && reserve_ready_i) begin
                    sending<=1;sending_replay<=0;send_slot<=new_slot;send_last<=lengths[new_slot]-1'b1;read_pos<=0;replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};
                end
            end
            if(core_valid && core_ready) begin
                if(core_eop) begin
                    sending<=0;
                    if(sending_replay) begin
                        if(replay_first) replay_first<=0;
                        if(replay_left==1) replay_active<=0;
                        else begin replay_left<=replay_left-1'b1;replay_slot<=advance(replay_slot,1);end
                    end else begin
                        sent_count<=sent_count+1'b1;new_slot<=advance(new_slot,1);
                    end
                end else begin read_pos<=read_pos+1'b1;replay_read_onehot<={replay_read_onehot[READ_CHOICES-2:0],replay_read_onehot[READ_CHOICES-1]};end
            end
            if(tx_valid_o && tx_ready_i && tx_eop_o && (tx_replay_o ? tx_first : !timer_running)) begin
                timer<=0;timer_running<=1;
            end
        end
    end
endmodule
`default_nettype wire
