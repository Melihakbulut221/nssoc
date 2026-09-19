// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

// Eight-bit SPI master, modes 0..3, two active-low chip selects.
// CTRL bits: CPOL=0, CPHA=1, CS index=2, interrupt enable=3, hold CS between bytes=4.
// DIV is the number of system clocks per half SCK period (minimum 2).
// DATA write starts a byte; DATA read returns the last received byte.
// STATUS bit 0=busy, bit 1=done (W1C). Writes while busy fail atomically.
module soc_spi (
    input wire clk_i, rst_ni,
    input wire psel_i, penable_i, pwrite_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i,
    input wire [3:0] pstrb_i,
    output reg [31:0] prdata_o,
    output wire pready_o, pslverr_o,
    input wire miso_i,
    output reg sck_o, mosi_o,
    output wire [1:0] cs_no,
    output wire irq_o
);
    reg [4:0] control;
    reg [15:0] divider, count;
    reg [7:0] txshift, rxshift, result;
    reg [4:0] edges;
    reg busy, done, cs_active;
    wire access = psel_i && penable_i;
    wire wr = access && pwrite_i;
    wire bad = (paddr_i != 0 && paddr_i != 4 && paddr_i != 8 && paddr_i != 12) ||
               (pwrite_i && pstrb_i != 4'hf) ||
               (pwrite_i && busy && paddr_i != 12) ||
               (pwrite_i && paddr_i == 0 && cs_active && pwdata_i[2:0] != control[2:0]) ||
               (pwrite_i && paddr_i == 4 && pwdata_i[15:0] < 2);
    wire leading = !edges[0];
    wire sample_edge = leading != control[1];
    assign pready_o = 1'b1;
    assign pslverr_o = access && bad;
    assign cs_no = cs_active ? (control[2] ? 2'b01 : 2'b10) : 2'b11;
    assign irq_o = done && control[3];
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            control <= 0; divider <= 4; count <= 0;
            txshift <= 0; rxshift <= 0; result <= 0; edges <= 0;
            busy <= 0; done <= 0; cs_active <= 0; sck_o <= 0; mosi_o <= 0;
        end else begin
            if (wr && !bad) case (paddr_i)
                0: begin
                    control <= pwdata_i[4:0]; sck_o <= pwdata_i[0];
                    if (!pwdata_i[4]) cs_active <= 0;
                end
                4: divider <= pwdata_i[15:0];
                8: begin
                    busy <= 1; done <= 0; cs_active <= 1; count <= divider-1'b1; edges <= 0;
                    txshift <= pwdata_i[7:0]; rxshift <= 0;
                    mosi_o <= control[1] ? 1'b0 : pwdata_i[7];
                end
                12: if (pwdata_i[1]) done <= 0;
                default: ;
            endcase
            if (busy) begin
                if (count != 0) count <= count-1'b1;
                else if (edges == 16) begin
                    // Hold CS for a full half-period after the final sample.
                    busy <= 0; done <= 1; result <= rxshift;
                    if (!control[4]) cs_active <= 0;
                end else begin
                    count <= divider-1'b1; edges <= edges+1'b1; sck_o <= !sck_o;
                    if (sample_edge) rxshift <= {rxshift[6:0], miso_i};
                    else begin
                        if (control[1]) begin
                            mosi_o <= txshift[7]; txshift <= {txshift[6:0], 1'b0};
                        end else begin
                            mosi_o <= txshift[6]; txshift <= {txshift[6:0], 1'b0};
                        end
                    end
                end
            end
        end
    end
    always @* begin
        prdata_o = 0;
        case (paddr_i)
            0: prdata_o = {27'b0, control};
            4: prdata_o = {16'b0, divider};
            8: prdata_o = {24'b0, result};
            12: prdata_o = {29'b0, cs_active, done, busy};
            default: ;
        endcase
    end
endmodule
