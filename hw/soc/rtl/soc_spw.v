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
    localparam [11:0] REG_CTRL = 12'h000; // regmap:spw:CTRL
    localparam [11:0] REG_STATUS = 12'h004; // regmap:spw:STATUS
    localparam [11:0] REG_DIV = 12'h008; // regmap:spw:DIV
    localparam [11:0] REG_TX = 12'h00C; // regmap:spw:TX
    localparam [11:0] REG_RX = 12'h010; // regmap:spw:RX
    localparam [11:0] REG_IRQEN = 12'h014; // regmap:spw:IRQEN
    localparam [11:0] REG_EVENTS = 12'h018; // regmap:spw:EVENTS
    localparam [11:0] REG_TIME_TX = 12'h01C; // regmap:spw:TIME_TX
    localparam [11:0] REG_TIME_RX = 12'h020; // regmap:spw:TIME_RX
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
    wire valid_addr = paddr_i == REG_CTRL || paddr_i == REG_STATUS || paddr_i == REG_DIV ||
                      paddr_i == REG_TX || paddr_i == REG_RX || paddr_i == REG_IRQEN ||
                      paddr_i == REG_EVENTS || paddr_i == REG_TIME_TX || paddr_i == REG_TIME_RX;
    wire bad = !valid_addr || (pwrite_i && pstrb_i != 4'hf) ||
               (pwrite_i && (paddr_i == REG_STATUS || paddr_i == REG_RX || paddr_i == REG_TIME_RX)) ||
               (!pwrite_i && paddr_i == REG_TX) ||
               (wr && paddr_i == REG_TX && !txready) ||
               (access && !pwrite_i && paddr_i == REG_RX && !rxvalid);
    assign pready_o = 1'b1;
    assign pslverr_o = access && bad;
    assign irq_o = |(pending & imask);
    wire txwrite = wr && !bad && paddr_i == REG_TX;
    wire rxread = access && !pwrite_i && !bad && paddr_i == REG_RX;
    wire tick_in = wr && !bad && paddr_i == REG_TIME_TX;
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
            cause <= (cause & ~((wr && !bad && paddr_i == REG_EVENTS) ? pwdata_i[7:0] : 8'b0))
                     | events | (tick ? 8'h10 : 8'h00);
            if (tick) time_rx <= {tc_ctrl, tc_time};
            if (wr && !bad) case (paddr_i)
                REG_CTRL: control <= pwdata_i[2:0];
                REG_DIV: divider <= pwdata_i[7:0] < 1 ? 8'd1 : pwdata_i[7:0];
                REG_IRQEN: imask <= pwdata_i[7:0];
                REG_TIME_TX: time_tx <= pwdata_i[7:0];
                default: ;
            endcase
        end
    end
    always @* begin
        prdata_o = 0;
        case (paddr_i)
            REG_CTRL: prdata_o = {29'b0, control};
            REG_STATUS: prdata_o = {25'b0, rxhalf, txhalf, rxvalid, txready, running, connecting, started};
            REG_DIV: prdata_o = {24'b0, divider};
            REG_RX: prdata_o = {23'b0, rxflag, rxdata};
            REG_IRQEN: prdata_o = {24'b0, imask};
            REG_EVENTS: prdata_o = {24'b0, pending};
            REG_TIME_TX: prdata_o = {24'b0, time_tx};
            REG_TIME_RX: prdata_o = {24'b0, time_rx};
            default: ;
        endcase
    end
endmodule

`default_nettype wire
