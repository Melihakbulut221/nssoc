// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
// One recovered-clock lane; raw_i[0] arrives first. No input backpressure.
// Exact Gen3 EIEOS acquisition only. External MAC owns search/lock control.
// Fixed130 blocks only: no variable SKP, deskew, CDC, polarity or LTSSM.
module soc_pcie_gen3_lane_align_v1 (
    input wire clk_i,
    input wire rst_ni,
    input wire raw_valid_i,
    input wire [31:0] raw_i,
    input wire block_align_control_i,
    input wire force_realign_i,
    output reg aligned_o,
    output reg block_valid_o,
    output reg [129:0] block_o,
    output reg eieos_o,
    output reg realign_o,
    output reg loss_o
);
    // Symbol0 is00, symbol15 isFF; OS header01 has wire-first bit1.
    localparam [129:0] EIEOS = {128'hff00ff00ff00ff00ff00ff00ff00ff00, 2'b01};
    reg [128:0] history_q;
    reg [7:0] history_count_q;
    reg [129:0] pending_q;
    reg [7:0] pending_count_q;
    wire [160:0] search_window = {raw_i, history_q};
    reg match_found;
    reg match_multiple;
    reg [4:0] match_end;
    reg [161:0] appended;
    integer i;
    always @* begin
        match_found = 1'b0;
        match_multiple = 1'b0;
        match_end = 5'd0;
        // Only windows whose last bit arrived in this raw word are considered.
        for (i = 0; i < 32; i = i + 1) begin
            if (block_align_control_i && (history_count_q + i >= 129) &&
                search_window[i +: 130] == EIEOS) begin
                if (match_found) match_multiple = 1'b1;
                match_found = 1'b1;
                match_end = i;
            end
        end
        appended = {32'd0, pending_q} | ({130'd0, raw_i} << pending_count_q);
    end
    always @(posedge clk_i) begin
        if (!rst_ni) begin
            history_q <= 129'd0;
            history_count_q <= 8'd0;
            pending_q <= 130'd0;
            pending_count_q <= 8'd0;
            aligned_o <= 1'b0;
            block_valid_o <= 1'b0;
            block_o <= 130'd0;
            eieos_o <= 1'b0;
            realign_o <= 1'b0;
            loss_o <= 1'b0;
        end else begin
            block_valid_o <= 1'b0;
            eieos_o <= 1'b0;
            realign_o <= 1'b0;
            loss_o <= 1'b0;
            if (force_realign_i || !raw_valid_i) begin
                history_q <= 129'd0;
                history_count_q <= 8'd0;
                pending_q <= 130'd0;
                pending_count_q <= 8'd0;
                aligned_o <= 1'b0;
                loss_o <= aligned_o;
            end else begin
                history_q <= search_window[160:32];
                history_count_q <= (history_count_q >= 97) ? 8'd129 : history_count_q + 8'd32;
                if (match_multiple) begin
                    pending_q <= 130'd0;
                    pending_count_q <= 8'd0;
                    aligned_o <= 1'b0;
                    loss_o <= 1'b1;
                end else if (match_found) begin
                    block_o <= EIEOS;
                    block_valid_o <= 1'b1;
                    eieos_o <= 1'b1;
                    realign_o <= !aligned_o || pending_count_q < 98 || match_end != 129 - pending_count_q;
                    aligned_o <= 1'b1;
                    pending_q <= search_window >> (130 + match_end);
                    pending_count_q <= 31 - match_end;
                end else if (aligned_o) begin
                    if (pending_count_q >= 98) begin
                        if (appended[1:0] == 2'b01 || appended[1:0] == 2'b10) begin
                            block_o <= appended[129:0];
                            block_valid_o <= 1'b1;
                            pending_q <= appended >> 130;
                            pending_count_q <= pending_count_q - 8'd98;
                        end else begin
                            // Explicit loss; never reacquire while search remains disabled.
                            aligned_o <= 1'b0;
                            pending_q <= 130'd0;
                            pending_count_q <= 8'd0;
                            loss_o <= 1'b1;
                        end
                    end else begin
                        pending_q <= appended[129:0];
                        pending_count_q <= pending_count_q + 8'd32;
                    end
                end
            end
        end
    end
endmodule
