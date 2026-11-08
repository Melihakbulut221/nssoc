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
    // The LCRC is accumulated while the TLP is collected, one DWORD per
    // accepted word, in transmission byte order: the two sequence prefix
    // bytes first (folded in at SOP), header DWORDs MSB-first, data DWORDs
    // LSB-first. Each word is folded in one cycle after it is accepted,
    // from registers; the last fold lands during PREFIX0, long before the
    // CRC state reads the result. Every collected DWORD is transmitted, so
    // at the CRC state the register holds exactly the state the byte-serial
    // update reached before. The transmit byte select no longer feeds a
    // CRC step, and the collected word no longer feeds the CRC tree.
    reg [31:0] crc;
    function [31:0] crc_byte;
        input [31:0] crc_state;
        input [7:0] data;
        integer bit_index;
        begin
            crc_byte=crc_state;
            for (bit_index=0;bit_index<8;bit_index=bit_index+1)
                crc_byte=(crc_byte>>1)^({32{crc_byte[0]^data[bit_index]}} & 32'hedb88320);
        end
    endfunction
    function [31:0] crc_word;
        input [31:0] crc_state;
        input [31:0] word;
        input msb_first;
        begin
            crc_word=msb_first ?
                crc_byte(crc_byte(crc_byte(crc_byte(crc_state,word[31:24]),word[23:16]),word[15:8]),word[7:0]) :
                crc_byte(crc_byte(crc_byte(crc_byte(crc_state,word[7:0]),word[15:8]),word[23:16]),word[31:24]);
        end
    endfunction
    // The LCRC state after the two prefix bytes depends on the sequence
    // number only. It is registered every cycle: the sequence advances at the
    // last LCRC byte, a new SOP is accepted at the earliest in the following
    // cycle and folded one cycle after that, so the fold reads the register
    // of the current sequence number.
    reg [31:0] prefix_crc;
    always @(posedge clk_i)
        prefix_crc<=crc_byte(crc_byte(32'hffffffff,{4'b0,next_sequence_o[11:8]}),next_sequence_o[7:0]);
    reg fold_valid,fold_first,fold_msb_first;
    reg [31:0] fold_word;
    // The DWORD update is linear in the CRC state and the word, so each next
    // state bit is the parity of the state and word bits selected by
    // constant masks (columns of crc_word applied to unit vectors). Written
    // this way each bit is one balanced parity tree instead of 32 serial
    // shift-and-XOR steps.
    wire [31:0] fold_state=fold_first ? prefix_crc : crc;
    wire [31:0] fold_next;
    genvar fold_bit,fold_input;
    generate for(fold_bit=0;fold_bit<32;fold_bit=fold_bit+1) begin: fold_parity
        wire [31:0] state_mask,msb_mask,lsb_mask;
        for(fold_input=0;fold_input<32;fold_input=fold_input+1) begin: fold_mask
            wire [31:0] state_column=crc_word(32'd1<<fold_input,32'd0,1'b1);
            wire [31:0] msb_column=crc_word(32'd0,32'd1<<fold_input,1'b1);
            wire [31:0] lsb_column=crc_word(32'd0,32'd1<<fold_input,1'b0);
            assign state_mask[fold_input]=state_column[fold_bit];
            assign msb_mask[fold_input]=msb_column[fold_bit];
            assign lsb_mask[fold_input]=lsb_column[fold_bit];
        end
        assign fold_next[fold_bit]=(^(fold_state & state_mask)) ^
            (fold_msb_first ? ^(fold_word & msb_mask) : ^(fold_word & lsb_mask));
    end endgenerate
    always @(posedge clk_i) if (fold_valid) crc<=fold_next;
    assign tlp_ready_o=rst_ni && (state==IDLE || state==COLLECT || state==DROP);
    assign tx_valid_o=rst_ni && state>=PREFIX0;
    assign tx_sop_o=state==PREFIX0;
    assign tx_eop_o=state==CRC && byte_index==3;
    // The transmitted byte comes from a register loaded with the byte the
    // next state presents: the sequence prefix when PREFIX0 is entered, and
    // on each accepted byte the following prefix, data or LCRC byte. Words,
    // header size, length, sequence and the folded LCRC do not change while
    // a frame is sent, so the register always equals the byte the state,
    // index and byte index select, and the word multiplexer sits before the
    // register instead of in front of the merge and transmit slice.
    // Byte b (transmission order) of collected word w.
    function [7:0] word_byte;
        input [31:0] word;
        input msb_first;
        input [1:0] b;
        begin word_byte=msb_first ? word >> (8*(3-b)) : word >> (8*b); end
    endfunction
    wire [7:0] selected_word_byte [0:MAX_TLP_DWORDS-1];
    wire last_byte=byte_index==3;
    wire [CW-1:0] next_index=(state==PREFIX1) ? {CW{1'b0}} : last_byte ? index+1'b1 : index;
    wire [1:0] next_byte_index=(state==PREFIX1) ? 2'd0 : byte_index+1'b1;
    genvar tx_word;
    generate for(tx_word=0;tx_word<MAX_TLP_DWORDS;tx_word=tx_word+1) begin: read_tx_word
        assign selected_word_byte[tx_word]=word_byte(words[tx_word],tx_word<header_words,next_byte_index);
    end endgenerate
    reg [7:0] tx_byte;
    wire tx_shown=state>=PREFIX0;
    always @* tx_data_o=tx_shown ? tx_byte : 8'd0;
    wire [7:0] crc_next_byte=(~crc) >> (8*(state==CRC ? byte_index+2'd1 : 2'd0));
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) tx_byte<=0;
        else if (tx_valid_o && tx_ready_i) begin
            case (state)
                PREFIX0:tx_byte<=next_sequence_o[7:0];
                PREFIX1:tx_byte<=selected_word_byte[0];
                DATA:tx_byte<=(last_byte && index==length-1'b1) ? crc_next_byte : selected_word_byte[next_index];
                CRC:tx_byte<=last_byte ? 8'd0 : crc_next_byte;
                default:tx_byte<=0;
            endcase
        end else if (state==COLLECT && tlp_valid_i && tlp_ready_o && !tlp_sop_i && !tlp_error_i &&
                     count!=MAX_TLP_DWORDS && tlp_eop_i && count+1>=header_words)
            tx_byte<={4'b0,next_sequence_o[11:8]};
    end
    generate if (MAX_TLP_DWORDS<4 || MAX_TLP_DWORDS>1028) begin: invalid_capacity
        initial $error("MAX_TLP_DWORDS must be 4..1028");
    end endgenerate
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state<=IDLE;count<=0;length<=0;index<=0;byte_index<=0;
            header_words<=3;next_sequence_o<=0;fold_valid<=0;
            packet_sent_o<=0;packet_bad_o<=0;
        end else begin
            packet_sent_o<=0;packet_bad_o<=0;fold_valid<=0;
            if (tx_valid_o && tx_ready_i) begin
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
                    fold_valid<=1;fold_first<=1;fold_word<=tlp_data_i;fold_msb_first<=1;
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
                    fold_valid<=1;fold_first<=0;fold_word<=tlp_data_i;fold_msb_first<=count<header_words;
                    if (tlp_eop_i) begin
                        if (count+1>=header_words) begin
                            length<=count+1'b1;state<=PREFIX0;byte_index<=0;
                        end else begin packet_bad_o<=1;state<=IDLE;end
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
