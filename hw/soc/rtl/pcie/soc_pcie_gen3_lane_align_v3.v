// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// One recovered-clock lane; raw_i[0] arrives first. No input backpressure.
// Local SDS lock stops EIEOS search before any recovered-to-common CDC.
// Exact aligned SDS: OS header01, E1 then fifteen55 bytes (Base4.0 table4-14).
// Search control still gates acquisition; force/reset/loss clears local lock.
// eieos_o classifies every exact aligned EIEOS; realign_o reports acquisition.
// No LTSSM state enforcement or next-block-after-SDS policy in this component.
// Variable Gen3 SKP blocks: 4/8/12/16/20 AA symbols, E1, three opaque
// trailer bytes; preserve every received bit, including the two-bit header.
// No SKP insertion/deletion, trailer-LFSR check, deskew, CDC, polarity or LTSSM.
// See Intel PIPE7.1 sections6.1.4/8.14 and Altera683779 section4.4.3;
// the AA/E1 encoding is also described in CN103713689A. This is a bounded
// receive component; complete protocol and physical qualification are separate.
`default_nettype none
module soc_pcie_gen3_lane_align_v3 (
    input wire clk_i,
    input wire rst_ni,
    input wire raw_valid_i,
    input wire [31:0] raw_i,
    input wire block_align_control_i,
    input wire force_realign_i,
    output reg aligned_o,
    output reg block_valid_o,
    output reg [193:0] block_o,
    output reg [2:0] length_code_o,
    output reg skp_o,
    output reg eieos_o,
    output reg realign_o,
    output reg loss_o,
    output reg locked_o,
    output reg sds_o
);
    // Symbol0 is00, symbol15 isFF; OS header01 has wire-first bit1.
    localparam [129:0] EIEOS = {128'hff00ff00ff00ff00ff00ff00ff00ff00, 2'b01};
    localparam [129:0] SDS = {{15{8'h55}}, 8'he1, 2'b01};
    reg [128:0] history_q;
    reg [7:0] history_count_q;
    reg [193:0] pending_q;
    reg [7:0] pending_count_q;
    wire [160:0] search_window = {raw_i, history_q};
    reg match_found;
    reg match_multiple;
    reg [4:0] match_end;
    reg [225:0] appended;
    reg [8:0] appended_count;
    reg [7:0] consume_bits;
    reg [2:0] consume_code;
    reg candidate_skp, candidate_complete, candidate_bad, end_found;
    reg [193:0] block_mask;
    integer symbol;
    reg [7:0] character;
    integer i;
    always @* begin
        match_found = 1'b0;
        match_multiple = 1'b0;
        match_end = 5'd0;
        // Only windows whose last bit arrived in this raw word are considered.
        for (i = 0; i < 32; i = i + 1) begin
            if (block_align_control_i && !locked_o && (history_count_q + i >= 129) &&
                search_window[i +: 130] == EIEOS) begin
                if (match_found) match_multiple = 1'b1;
                match_found = 1'b1;
                match_end = i;
            end
        end
        appended = {32'd0, pending_q} | ({194'd0, raw_i} << pending_count_q);
        appended_count = {1'b0, pending_count_q} + 9'd32;
        consume_bits = 8'd130;
        consume_code = 3'd2;
        candidate_skp = 1'b0;
        candidate_bad = 1'b0;
        end_found = 1'b0;
        character = 0;
        if (appended[1:0] == 2'b01 && appended_count >= 10 &&
            appended[9:2] == 8'haa) begin
            candidate_skp = 1'b1;
            consume_bits = 0;
            // Inspect only complete received bytes. SKP_END is legal only at
            // a four-symbol boundary after at least four AA symbols. Trailer
            // bytes are opaque and must never become an additional SKP group.
            for (symbol = 0; symbol <= 20; symbol = symbol + 1) begin
                character = appended[2 + symbol*8 +: 8];
                if (!end_found && !candidate_bad && appended_count >= 10 + symbol*8) begin
                    if (symbol >= 4 && symbol % 4 == 0 && character == 8'he1) begin
                        end_found = 1'b1;
                        consume_bits = 2 + (symbol + 4)*8;
                        consume_code = (symbol - 4)/4;
                    end else if (character != 8'haa || symbol == 20) begin
                        candidate_bad = 1'b1;
                    end
                end
            end
        end else if (appended[1:0] != 2'b01 && appended[1:0] != 2'b10) begin
            candidate_bad = 1'b1;
        end
        candidate_complete = consume_bits != 0 && appended_count >= consume_bits;
        block_mask = {194{1'b1}} >> (194 - consume_bits);
    end
    always @(posedge clk_i) begin
        if (!rst_ni) begin
            history_q <= 129'd0;
            history_count_q <= 8'd0;
            pending_q <= 194'd0;
            pending_count_q <= 8'd0;
            aligned_o <= 1'b0;
            locked_o <= 1'b0;
            block_valid_o <= 1'b0;
            block_o <= 194'd0;
            length_code_o <= 0;
            skp_o <= 1'b0;
            eieos_o <= 1'b0;
            sds_o <= 1'b0;
            realign_o <= 1'b0;
            loss_o <= 1'b0;
        end else begin
            block_valid_o <= 1'b0;
            skp_o <= 1'b0;
            eieos_o <= 1'b0;
            sds_o <= 1'b0;
            realign_o <= 1'b0;
            loss_o <= 1'b0;
            if (force_realign_i || !raw_valid_i) begin
                history_q <= 129'd0;
                history_count_q <= 8'd0;
                pending_q <= 194'd0;
                pending_count_q <= 8'd0;
                aligned_o <= 1'b0;
                locked_o <= 1'b0;
                loss_o <= aligned_o;
            end else begin
                history_q <= search_window[160:32];
                history_count_q <= (history_count_q >= 97) ? 8'd129 : history_count_q + 8'd32;
                if (match_multiple) begin
                    pending_q <= 194'd0;
                    pending_count_q <= 8'd0;
                    aligned_o <= 1'b0;
                    locked_o <= 1'b0;
                    loss_o <= 1'b1;
                end else if (match_found) begin
                    block_o <= {64'd0, EIEOS};
                    length_code_o <= 3'd2;
                    block_valid_o <= 1'b1;
                    eieos_o <= 1'b1;
                    realign_o <= !aligned_o || pending_count_q < 98 || match_end != 129 - pending_count_q;
                    aligned_o <= 1'b1;
                    pending_q <= search_window >> (130 + match_end);
                    pending_count_q <= 31 - match_end;
                end else if (aligned_o) begin
                    if (candidate_bad) begin
                        aligned_o <= 1'b0;
                        locked_o <= 1'b0;
                        pending_q <= 194'd0;
                        pending_count_q <= 8'd0;
                        loss_o <= 1'b1;
                    end else if (candidate_complete) begin
                        block_o <= appended[193:0] & block_mask;
                        length_code_o <= consume_code;
                        skp_o <= candidate_skp;
                        eieos_o <= consume_bits == 130 && appended[129:0] == EIEOS;
                        sds_o <= consume_bits == 130 && appended[129:0] == SDS;
                        if (consume_bits == 130 && appended[129:0] == SDS)
                            locked_o <= 1'b1;
                        block_valid_o <= 1'b1;
                        pending_q <= appended >> consume_bits;
                        pending_count_q <= appended_count - consume_bits;
                    end else begin
                        pending_q <= appended[193:0];
                        pending_count_q <= appended_count;
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
