// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

`default_nettype none

// PIO SpaceWire endpoint. Register contract: docs/88-interface-integration.md.
// All core clocks are clk_i; the generic receiver supports up to clk_i/2.
module soc_spw #(parameter integer CLOCK_HZ = 50000000) (
    input wire clk_i, rst_ni,
    input wire psel_i, penable_i, pwrite_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i,
    input wire [3:0] pstrb_i,
    output reg [31:0] prdata_o,
    output wire pready_o, pslverr_o,
    input wire di_i, si_i,
    output wire do_o, so_o, irq_o
);
    reg [2:0] control;
    reg [7:0] divider, imask, cause, time_tx, time_rx;
    wire started, connecting, running, txready, rxvalid;
    wire txhalf, rxhalf, rxflag, tick;
    wire [7:0] rxdata;
    wire [1:0] tc_ctrl;
    wire [5:0] tc_time;
    wire disc, parity, escape_err, credit_err;
    wire access = psel_i && penable_i;
    wire wr = access && pwrite_i;
    wire [7:0] events = {4'b0, credit_err, escape_err, parity, disc};
    wire [7:0] pending = cause | {2'b0, rxvalid, 5'b0};
    wire valid_addr = paddr_i == 0 || paddr_i == 4 || paddr_i == 8 ||
                      paddr_i == 12 || paddr_i == 16 || paddr_i == 20 ||
                      paddr_i == 24 || paddr_i == 28 || paddr_i == 32;
    wire bad = !valid_addr || (pwrite_i && pstrb_i != 4'hf) ||
               (pwrite_i && (paddr_i == 4 || paddr_i == 16 || paddr_i == 32)) ||
               (!pwrite_i && paddr_i == 12) ||
               (wr && paddr_i == 12 && !txready) ||
               (access && !pwrite_i && paddr_i == 16 && !rxvalid);
    assign pready_o = 1'b1;
    assign pslverr_o = access && bad;
    assign irq_o = |(pending & imask);
    wire txwrite = wr && !bad && paddr_i == 12;
    wire rxread = access && !pwrite_i && !bad && paddr_i == 16;
    wire tick_in = wr && !bad && paddr_i == 28;
    spwstream #(.SYS_CLOCK_HZ(CLOCK_HZ), .TX_CLOCK_HZ(CLOCK_HZ),
        .RXIMPL(0), .TXIMPL(0), .RXFIFOSIZE_BITS(6), .TXFIFOSIZE_BITS(4),
        .STRICT_TIMECODES(1)) u_link (
        .clk(clk_i), .rxclk(clk_i), .txclk(clk_i), .rst(!rst_ni),
        .autostart(control[0]), .linkstart(control[1]), .linkdis(control[2]),
        .txdivcnt(divider), .tick_in(tick_in),
        .ctrl_in(pwdata_i[7:6]), .time_in(pwdata_i[5:0]),
        .txwrite(txwrite), .txflag(pwdata_i[8]), .txdata(pwdata_i[7:0]),
        .txrdy(txready), .txhalff(txhalf),
        .tick_out(tick), .ctrl_out(tc_ctrl), .time_out(tc_time),
        .rxvalid(rxvalid), .rxhalff(rxhalf), .rxflag(rxflag), .rxdata(rxdata),
        .rxread(rxread), .started(started), .connecting(connecting),
        .running(running), .errdisc(disc), .errpar(parity),
        .erresc(escape_err), .errcred(credit_err),
        .spw_di(di_i), .spw_si(si_i), .spw_do(do_o), .spw_so(so_o));
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            control <= 3'b100; divider <= 8'd4; imask <= 0;
            cause <= 0; time_tx <= 0; time_rx <= 0;
        end else begin
            // New events win over simultaneous W1C.
            cause <= (cause & ~((wr && !bad && paddr_i == 24) ? pwdata_i[7:0] : 8'b0))
                     | events | (tick ? 8'h10 : 8'h00);
            if (tick) time_rx <= {tc_ctrl, tc_time};
            if (wr && !bad) case (paddr_i)
                0: control <= pwdata_i[2:0];
                8: divider <= pwdata_i[7:0] < 1 ? 8'd1 : pwdata_i[7:0];
                20: imask <= pwdata_i[7:0];
                28: time_tx <= pwdata_i[7:0];
                default: ;
            endcase
        end
    end
    always @* begin
        prdata_o = 0;
        case (paddr_i)
            0: prdata_o = {29'b0, control};
            4: prdata_o = {25'b0, rxhalf, txhalf, rxvalid, txready, running, connecting, started};
            8: prdata_o = {24'b0, divider};
            16: prdata_o = {23'b0, rxflag, rxdata};
            20: prdata_o = {24'b0, imask};
            24: prdata_o = {24'b0, pending};
            28: prdata_o = {24'b0, time_tx};
            32: prdata_o = {24'b0, time_rx};
            default: ;
        endcase
    end
endmodule

`default_nettype wire
