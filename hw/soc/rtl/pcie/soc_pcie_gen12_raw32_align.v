// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Raw PMA word bit 0 is earliest on the wire. This block establishes only
// a symbol boundary, never polarity, LTSSM state, code validity or link-up.
module soc_pcie_gen12_raw32_align (
    input wire rx_clk_i,
    input wire rx_rst_ni,
    input wire enable_i,
    input wire force_realign_i,
    input wire polarity_i,
    input wire raw_valid_i,
    input wire [31:0] raw_i,
    output reg [39:0] symbols_o,
    output reg [2:0] symbol_count_o,
    output reg [3:0] comma_o,
    output reg boundary_valid_o,
    output reg acquired_o,
    output reg acquired_rd_o
);
    localparam [9:0] COM_NEG = 10'h17c;
    localparam [9:0] COM_POS = 10'h283;
    reg [8:0] tail_q, tail_d;
    reg [3:0] tail_count_q, tail_count_d;
    reg polarity_q;
    reg boundary_d, acquired_d, acquired_rd_d;
    reg [39:0] symbols_d;
    reg [2:0] count_d;
    reg [3:0] comma_d;
    reg [40:0] window_bits, shifted;
    integer available, offset, count, used, i;
    reg found;

    always @* begin
        tail_d = tail_q;
        tail_count_d = tail_count_q;
        boundary_d = boundary_valid_o;
        acquired_d = 1'b0;
        acquired_rd_d = 1'b0;
        symbols_d = 40'b0;
        count_d = 3'd0;
        comma_d = 4'b0;
        window_bits = 41'b0;
        shifted = 41'b0;
        available = 0;
        offset = 0;
        count = 0;
        used = 0;
        found = 1'b0;
        // Control changes flush all partial data and discard the current word.
        // The owner must flush for electrical idle, rate changes or bit slips.
        if (!enable_i || force_realign_i || polarity_i != polarity_q) begin
            tail_d = 9'b0;
            tail_count_d = 4'd0;
            boundary_d = 1'b0;
        end else if (raw_valid_i) begin
            window_bits = {32'b0, tail_q}
                        | ({9'b0, (raw_i ^ {32{polarity_i}})} << tail_count_q);
            available = 32 + tail_count_q;
            if (!boundary_valid_o) begin
                // Earliest complete COM wins. Nine bits are retained so that
                // every comma crossing a 32-bit word boundary is examined.
                for (i = 0; i < 32; i = i + 1) begin
                    shifted = window_bits >> i;
                    if (!found && i + 10 <= available &&
                        (shifted[9:0] == COM_NEG || shifted[9:0] == COM_POS)) begin
                        found = 1'b1;
                        offset = i;
                        acquired_rd_d = (shifted[9:0] == COM_POS);
                    end
                end
                if (found) begin
                    boundary_d = 1'b1;
                    acquired_d = 1'b1;
                end
            end
            if (boundary_valid_o || found) begin
                shifted = window_bits >> offset;
                count = (available - offset) / 10;
                count_d = count;
                for (i = 0; i < 4; i = i + 1) begin
                    if (i < count) begin
                        symbols_d[i*10 +: 10] = shifted[i*10 +: 10];
                        comma_d[i] = (shifted[i*10 +: 10] == COM_NEG ||
                                      shifted[i*10 +: 10] == COM_POS);
                    end
                end
                used = offset + count * 10;
                tail_d = window_bits >> used;
                tail_count_d = available - used;
            end else begin
                tail_d = window_bits >> (available - 9);
                tail_count_d = 4'd9;
            end
        end
    end

    always @(posedge rx_clk_i or negedge rx_rst_ni) begin
        if (!rx_rst_ni) begin
            tail_q <= 9'b0;
            tail_count_q <= 4'd0;
            polarity_q <= 1'b0;
            symbols_o <= 40'b0;
            symbol_count_o <= 3'd0;
            comma_o <= 4'b0;
            boundary_valid_o <= 1'b0;
            acquired_o <= 1'b0;
            acquired_rd_o <= 1'b0;
        end else begin
            polarity_q <= polarity_i;
            tail_q <= tail_d;
            tail_count_q <= tail_count_d;
            symbols_o <= symbols_d;
            symbol_count_o <= count_d;
            comma_o <= comma_d;
            boundary_valid_o <= boundary_d;
            acquired_o <= acquired_d;
            acquired_rd_o <= acquired_rd_d;
        end
    end
endmodule
