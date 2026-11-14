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
`ifdef SOC_PCIE_RESET_COPIES
    // docs/combined-timing.md section 14: a second registered copy of
    // rst_ni, equal to it at all times (the parent releases both from the
    // same reset in the same cycle). It is the asynchronous reset of the
    // replay read cursor and of the transmit slice, so they have a reset
    // tree of their own.
    input wire rst_copy_ni,
`endif
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
    wire [AW-1:0] capture_address=AW'(tail*MAX_BYTES+(in_sop_i ? 32'd0 : 32'(write_pos)));
`ifdef SOC_PCIE_REPLAY_WRITE_PREDECODE
    // The same capture decisions register a qualified high-address select.
    // Low address decoding runs in parallel with write_data. Neither stage
    // adds a cycle: every byte still commits one edge after acceptance.
    localparam integer WRITE_GROUPS=(DEPTH*MAX_BYTES+15)/16;
    reg [WRITE_GROUPS-1:0] write_group;
    reg [15:0] write_low;
    always @(posedge clk_i) begin
        write_data<=in_data_i;
        write_low<=16'b1 << capture_address[3:0];
    end
    genvar write_byte;
    generate for(write_byte=0;write_byte<DEPTH*MAX_BYTES;write_byte=write_byte+1) begin: decoded_write
        always @(posedge clk_i)
            if(write_group[write_byte/16] && write_low[write_byte%16])
                bytes[write_byte]<=write_data;
    end endgenerate
`else
    always @(posedge clk_i) begin
        write_address<=capture_address;write_data<=in_data_i;
        if(write_valid) bytes[write_address]<=write_data;
    end
`endif
    reg [31:0] input_crc;
    // The frame-end checks start at registers. The upper 24 bits of the
    // residue comparison are tracked with the CRC state itself; the stored
    // sequence bytes 0 and 1 and the expected sequence are compared every
    // cycle, a cycle ahead (both are fixed for the last sixteen bytes or
    // more of any frame that passes the length check).
    reg crc_upper_match,sequence_mismatch;
    always @(posedge clk_i)
        sequence_mismatch<={bytes[tail*MAX_BYTES][3:0],bytes[tail*MAX_BYTES+1]}!=next_store_sequence;
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
    // At a frame end in_sop_i is low (an SOP there is an error anyway).
    wire replay_crc_residue_ok=crc_upper_match && (input_crc[7:0]^in_data_i)==8'hed;
    soc_pcie_crc32_byte input_crc_byte(.state_i(in_sop_i ? 32'hffffffff : input_crc),
        .data_i(in_data_i),.state_o(next_crc));
    function [PW-1:0] advance;
        input [PW-1:0] pointer;
        input [CW:0] amount;
        reg [CW+1:0] sum;
        begin sum=(CW+2)'(pointer)+(CW+2)'(amount);advance=PW'((32'(sum)>=DEPTH) ? 32'(sum)-DEPTH : 32'(sum));end
    endfunction
    // ACK retirement moves head forward and sent_count backward equally.
    // Only an original transmitted EOP advances their modulo sum. Keep that
    // frontier directly, removing the adder from credit reservation metadata.
    reg [PW-1:0] new_slot;
    wire [11:0] ack_delta=ack_sequence_i-acknowledged_sequence_o;
    // Classify at the first validated ACK presentation, even if frame atomicity
    // delays consumption. Backpressure cannot turn an early future ACK valid.
    wire current_ack_allowed=ack_delta==0 || (ack_delta<=12'(sent_count) && ack_delta!=0);
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
    // Both candidate slots' decodes are selected from registers; whether
    // new_slot moves selects one of them as the last step.
    wire new_slot_moves=core_valid && core_ready && core_eop && !sending_replay;
    wire [PW-1:0] kept_slot=!link_up_i ? {PW{1'b0}} : new_slot;
    wire [PW-1:0] moved_slot=!link_up_i ? {PW{1'b0}} : advance(new_slot,1);
    reg [1:0] reserve_class_q;
    reg [10:0] reserve_payload_dw_q;
    always @(posedge clk_i) begin
        reserve_class_q<=new_slot_moves ? slot_class[moved_slot] : slot_class[kept_slot];
        reserve_payload_dw_q<=new_slot_moves ? slot_payload_dw[moved_slot] : slot_payload_dw[kept_slot];
    end
    assign reserve_class_o=reserve_class_q;
    assign reserve_payload_dw_o=reserve_payload_dw_q;
    // Reservation is a cancellable request until handshake. A replay bypasses
    // it entirely: its receiver credit was reserved on original transmission.
    assign reserve_replay_o=0;
    wire timer_expiring=timer_running && !training_i && 32'(timer)==TIMEOUT_CYCLES-1;
    assign reserve_valid_o=rst_ni && link_up_i && !training_i && !halt && !sending &&
        !capturing && !timer_expiring && !replay_active && !replay_pending && !ack_valid_i && count>sent_count;
    assign in_ready_o=rst_ni && link_up_i && !halt &&
        (capturing || (!replay_active && !replay_pending && !ack_valid_i && 32'(count)<DEPTH));
    assign ack_ready_o=rst_ni && link_up_i && ack_observed && !sending && !capturing && !replay_active;
    // The transmit stream leaves through a register slice, so the replay
    // read path ends at a flop instead of continuing into the link layer.
    assign core_valid=rst_ni && link_up_i && sending;
    // Each bank's byte at the read position is a register, so the store
    // read ends at a flop and the transmit slice takes a bank select of
    // registers. While no frame is being sent every bank register is loaded
    // with its byte 0; when a byte is taken mid-frame it is loaded with the
    // byte at the next position, selected as an AND-OR by the rotated
    // one-hot cursor. A sent slot is committed (its bytes written) before
    // its send starts, and only the free tail slot is written while a frame
    // is sent, so the register always equals the store's byte at read_pos
    // for the slot being sent. Cross-bank addresses are included as before;
    // addresses past the end of the store read as zero.
    wire [READ_CHOICES-1:0] replay_next_onehot={replay_read_onehot[READ_CHOICES-2:0],replay_read_onehot[READ_CHOICES-1]};
    wire core_taken=core_valid && core_ready && !core_eop;
`ifdef SOC_PCIE_REPLAY_AHEAD
    // docs/combined-timing.md section 18 (default off): the store read is
    // one cycle ahead. Per bank, `ahead` loads in every cycle the byte two
    // positions past the cursor (the AND-OR below, selected by the cursor
    // rotated by two, with no enable and no handshake), `kept` holds the
    // byte one position past it, and the byte a bank register takes is
    // replay_took ? ahead : kept, from registers. replay_took is
    // core_taken one cycle earlier. Proof that replay_took ? ahead : kept
    // equals the default build's `following` (the byte at cursor+1) in
    // every sending cycle: in the first sending cycle the cursor is 0,
    // replay_took is 0 (core_taken needs sending) and kept holds byte 1,
    // loaded while not sending. Later, if a byte was taken in the previous
    // cycle the cursor moved by one and `ahead` holds the byte at the new
    // cursor+1; otherwise the cursor did not move and kept holds the
    // previous cycle's value. The sent slot's bytes do not change from the
    // first sending cycle on (its last byte is written at the latest at
    // the edge that starts the send; only the free tail slot is written
    // while a frame is sent), so the one-cycle-old reads are current. The
    // cursor stays at or below MAX_BYTES-1, so cursor+2 does not wrap.
    // The other banks' registers may differ from the default build's while
    // a frame is sent; they are not read, and every bank register reloads
    // byte 0 before the next send starts. The transmit interface and every
    // other output are cycle-identical.
    wire [READ_CHOICES-1:0] replay_ahead_onehot={replay_read_onehot[READ_CHOICES-3:0],replay_read_onehot[READ_CHOICES-1:READ_CHOICES-2]};
    reg replay_took;
    always @(posedge clk_i) replay_took<=core_taken;
`endif
    wire [7:0] replay_bank_byte [0:DEPTH-1];
    genvar replay_bank,replay_bit,replay_offset;
    generate for(replay_bank=0;replay_bank<DEPTH;replay_bank=replay_bank+1) begin: read_replay_bank
        wire [7:0] following;
        reg [7:0] registered;
        for(replay_bit=0;replay_bit<8;replay_bit=replay_bit+1) begin: read_bit
            wire [READ_CHOICES-1:0] selected;
            for(replay_offset=0;replay_offset<READ_CHOICES;replay_offset=replay_offset+1) begin: read_byte
`ifdef SOC_PCIE_REPLAY_INBANK
                // docs/combined-timing.md section 16: only the bank's own
                // MAX_BYTES bytes. A byte is taken mid-frame only below the
                // frame's last position (send_last = length-1 <= MAX_BYTES-1,
                // the capture bound), so the next position is inside the
                // bank whenever the bank being sent loads it; the other
                // banks' registers are reloaded with byte 0 before any send
                // starts. Every byte that leaves is the default build's.
                if(replay_offset<MAX_BYTES) begin: present
`else
                if(replay_bank*MAX_BYTES+replay_offset<DEPTH*MAX_BYTES) begin: present
`endif
`ifdef SOC_PCIE_REPLAY_AHEAD
                    assign selected[replay_offset]=replay_ahead_onehot[replay_offset] & bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit];
`else
                    assign selected[replay_offset]=replay_next_onehot[replay_offset] & bytes[replay_bank*MAX_BYTES+replay_offset][replay_bit];
`endif
                end else begin: absent
                    assign selected[replay_offset]=1'b0;
                end
            end
            assign following[replay_bit]=|selected;
        end
`ifdef SOC_PCIE_REPLAY_AHEAD
        // `following` is the byte at cursor+2 here (see replay_took above).
        reg [7:0] ahead,kept;
        wire [7:0] next_byte=replay_took ? ahead : kept;
        always @(posedge clk_i) begin
            ahead<=following;
            kept<=!sending ? bytes[replay_bank*MAX_BYTES+1] : next_byte;
            registered<=!sending ? bytes[replay_bank*MAX_BYTES] : core_taken ? next_byte : registered;
        end
`else
        always @(posedge clk_i)
            registered<=!sending ? bytes[replay_bank*MAX_BYTES] : core_taken ? following : registered;
`endif
        assign replay_bank_byte[replay_bank]=registered;
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
`ifdef SOC_PCIE_RESET_COPIES
        .clk_i(clk_i),.rst_ni(rst_copy_ni),.clear_i(!link_up_i),
`else
        .clk_i(clk_i),.rst_ni(rst_ni),.clear_i(!link_up_i),
`endif
        .s_data_i({core_data,core_sop,core_eop,sending_replay,sending_replay && replay_first}),.s_valid_i(core_valid),.s_ready_o(core_ready),
        .m_data_o({tx_data_o,tx_sop_o,tx_eop_o,tx_replay_o,tx_first}),.m_valid_o(tx_valid_o),.m_ready_i(tx_ready_i));
    assign buffered_o=5'(count);
    assign outstanding_o=5'(sent_count);
    assign retrain_request_o=halt;
    initial begin
        if(DEPTH<2 || DEPTH>16 || MAX_BYTES<18 || MAX_BYTES>2048 ||
            TIMEOUT_CYCLES<2 || MAX_REPLAYS<1 || MAX_REPLAYS>7) $error("Unsupported bounded replay parameters");
    end
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            head<=0;tail<=0;new_slot<=0;send_slot<=0;send_last<=0;replay_slot<=0;count<=0;sent_count<=0;replay_left<=0;
`ifndef SOC_PCIE_RESET_COPIES
            write_pos<=0;read_pos<=0;replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};capturing<=0;sending<=0;sending_replay<=0;
`else
            write_pos<=0;read_pos<=0;capturing<=0;sending<=0;sending_replay<=0;
`endif
            replay_active<=0;replay_pending<=0;replay_first<=0;halt<=0;
            next_store_sequence<=0;input_crc<=32'hffffffff;crc_upper_match<=0;timer<=0;timer_running<=0;retries<=0;
            ack_observed<=0;ack_was_allowed<=0;ack_was_stale<=0;ack_delta_q<=0;write_valid<=0;
`ifdef SOC_PCIE_REPLAY_WRITE_PREDECODE
            write_group<=0;
`endif

            acknowledged_sequence_o<=12'hfff;replay_started_o<=0;timeout_o<=0;
            protocol_error_o<=0;retry_exhausted_o<=0;source_error_o<=0;
        end else if(!link_up_i) begin
            head<=0;tail<=0;new_slot<=0;count<=0;sent_count<=0;capturing<=0;sending<=0;write_valid<=0;
`ifdef SOC_PCIE_REPLAY_WRITE_PREDECODE
            write_group<=0;
`endif

            replay_active<=0;replay_pending<=0;halt<=0;next_store_sequence<=0;
            ack_observed<=0;ack_was_allowed<=0;ack_was_stale<=0;
            timer<=0;timer_running<=0;retries<=0;acknowledged_sequence_o<=12'hfff;
            replay_started_o<=0;timeout_o<=0;protocol_error_o<=0;retry_exhausted_o<=0;source_error_o<=0;
        end else begin
            replay_started_o<=0;timeout_o<=0;protocol_error_o<=0;write_valid<=0;
`ifdef SOC_PCIE_REPLAY_WRITE_PREDECODE
            write_group<=0;
`endif

            if(ack_valid_i && !ack_observed) begin
                ack_observed<=1;ack_was_allowed<=current_ack_allowed;ack_was_stale<=ack_delta>12'd2048;
                ack_delta_q<=ack_delta;
            end
            if(ack_valid_i && ack_ready_o) ack_observed<=0;
            if(timer_running && !training_i && !halt) begin
                if(32'(timer)==TIMEOUT_CYCLES-1) begin
                    timer_running<=0;timer<=0;replay_pending<=1;timeout_o<=1;
                end else timer<=timer+1'b1;
            end
            if(halt && retrain_done_i && !source_error_o) begin
                halt<=0;retry_exhausted_o<=0;retries<=0;replay_pending<=sent_count!=0;
            end
            if(in_valid_i && in_ready_o) begin
                input_crc<=next_crc;crc_upper_match<=next_crc[31:8]==24'h00be26;
                if(in_sop_i) begin
                    if(capturing || in_eop_i || in_data_i[7:4]!=0) begin
                        source_error_o<=1;halt<=1;capturing<=0;
                    end else begin write_valid<=1;
`ifdef SOC_PCIE_REPLAY_WRITE_PREDECODE
            write_group<={{(WRITE_GROUPS-1){1'b0}},1'b1} << (capture_address >> 4);
`endif
write_pos<=1;capturing<=1;end
                end else if(!capturing || 32'(write_pos)>=MAX_BYTES) begin
                    source_error_o<=1;halt<=1;capturing<=0;
                end else begin
                    write_valid<=1;
`ifdef SOC_PCIE_REPLAY_WRITE_PREDECODE
            write_group<={{(WRITE_GROUPS-1){1'b0}},1'b1} << (capture_address >> 4);
`endif
write_pos<=write_pos+1'b1;
                    if(in_eop_i) begin
                        capturing<=0;
                        if(write_pos<17 || !replay_crc_residue_ok ||
                           sequence_mismatch) begin
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
                        head<=advance(head,ack_delta_q[CW:0]);count<=CW'(12'(count)-ack_delta_q);
                        sent_count<=CW'(12'(sent_count)-ack_delta_q);acknowledged_sequence_o<=ack_sequence_i;
                        retries<=0;timer<=0;timer_running<=12'(sent_count)!=ack_delta_q;
                        replay_pending<=0;
                    end
                    if(ack_nak_i) begin
                        replay_pending<=12'(sent_count)!=ack_delta_q;timer_running<=0;timer<=0;
                    end
                end else if(!ack_stale) protocol_error_o<=1;
                // Older acknowledgments outside our small forward window are stale.
            end else if(!sending && !capturing && !training_i && !halt) begin
                if(replay_pending && !replay_active) begin
                    replay_pending<=0;
                    if(sent_count!=0) begin
                        if(32'(retries)==MAX_REPLAYS) begin halt<=1;retry_exhausted_o<=1;timer_running<=0;end
                        else begin
                            replay_active<=1;replay_slot<=head;replay_left<=sent_count;
                            replay_first<=1;retries<=retries+1'b1;replay_started_o<=1;
                        end
                    end
                end else if(replay_active) begin
`ifndef SOC_PCIE_RESET_COPIES
                    sending<=1;sending_replay<=1;send_slot<=replay_slot;send_last<=lengths[replay_slot]-1'b1;read_pos<=0;replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};
`else
                    sending<=1;sending_replay<=1;send_slot<=replay_slot;send_last<=lengths[replay_slot]-1'b1;read_pos<=0;
`endif
                end else if(reserve_valid_o && reserve_ready_i) begin
`ifndef SOC_PCIE_RESET_COPIES
                    sending<=1;sending_replay<=0;send_slot<=new_slot;send_last<=lengths[new_slot]-1'b1;read_pos<=0;replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};
`else
                    sending<=1;sending_replay<=0;send_slot<=new_slot;send_last<=lengths[new_slot]-1'b1;read_pos<=0;
`endif
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
`ifndef SOC_PCIE_RESET_COPIES
                end else begin read_pos<=read_pos+1'b1;replay_read_onehot<={replay_read_onehot[READ_CHOICES-2:0],replay_read_onehot[READ_CHOICES-1]};end
`else
                end else read_pos<=read_pos+1'b1;
`endif
            end
            if(tx_valid_o && tx_ready_i && tx_eop_o && (tx_replay_o ? tx_first : !timer_running)) begin
                timer<=0;timer_running<=1;
            end
        end
    end
`ifdef SOC_PCIE_RESET_COPIES
    // The replay read cursor on rst_copy_ni, with the next-state function
    // of the block above: back to position 0 when a send starts (no ACK
    // consumed, not sending or capturing, not training or halted, no
    // replay being started, and a replay in progress or a reservation
    // handshake), rotated when a byte is taken mid-frame. Link loss leaves
    // it unchanged there as well.
    wire replay_send_start=!(ack_valid_i && ack_ready_o) && !sending && !capturing &&
        !training_i && !halt && !(replay_pending && !replay_active) &&
        (replay_active || (reserve_valid_o && reserve_ready_i));
    always @(posedge clk_i or negedge rst_copy_ni) begin
        if(!rst_copy_ni) replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};
        else if(link_up_i) begin
            if(replay_send_start) replay_read_onehot<={{(READ_CHOICES-1){1'b0}},1'b1};
            if(core_valid && core_ready && !core_eop)
                replay_read_onehot<={replay_read_onehot[READ_CHOICES-2:0],replay_read_onehot[READ_CHOICES-1]};
        end
    end
`endif
endmodule
`default_nettype wire
