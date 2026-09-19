// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

// Single-command I2C master, with bounded recovery from a stuck bus.
// Pin outputs are open-drain enables: 1 drives LOW, 0 releases the pad.
module soc_i2c #(parameter integer TIMEOUT_CYCLES = 500000) (
    input wire clk_i, rst_ni,
    input wire psel_i, penable_i, pwrite_i,
    input wire [11:0] paddr_i,
    input wire [31:0] pwdata_i,
    input wire [3:0] pstrb_i,
    output reg [31:0] prdata_o,
    output wire pready_o, pslverr_o,
    input wire scl_i, sda_i,
    output wire scl_oe_o, sda_oe_o, irq_o
);
    reg [15:0] prescale;
    reg [6:0] address;
    reg [7:0] txdata;
    reg [3:0] command;
    reg cmd_valid, tx_valid, active, seen_busy, busy_q, abort_q;
    reg [3:0] cause, imask;
    reg scl_meta, scl_sync, sda_meta, sda_sync;
    localparam integer TW = $clog2(TIMEOUT_CYCLES+1);
    reg [TW-1:0] timer;
    wire cmd_ready, tx_ready, rx_valid, busy, bus_control, bus_active, nack;
    wire [7:0] rxdata;
    wire scl_t, sda_t;
    wire access = psel_i && penable_i;
    wire wr = access && pwrite_i;
    wire valid_addr = paddr_i == 0 || paddr_i == 4 || paddr_i == 8 ||
                      paddr_i == 12 || paddr_i == 16 || paddr_i == 20 ||
                      paddr_i == 24 || paddr_i == 28;
    wire bad_cmd = paddr_i == 12 && (!pwdata_i[4]) &&
                   (active || rx_valid || pwdata_i[1:0] == 2'b11 || pwdata_i[3:0] == 0);
    wire bad = !valid_addr || (pwrite_i && pstrb_i != 4'hf) ||
               (pwrite_i && (paddr_i == 0 || paddr_i == 28)) ||
               (pwrite_i && (paddr_i == 4 || paddr_i == 8 || paddr_i == 16) && active) ||
               (pwrite_i && bad_cmd) ||
               (!pwrite_i && paddr_i == 16 && !rx_valid) ||
               (pwrite_i && paddr_i == 4 && pwdata_i[15:0] < 4);
    wire launch = wr && !bad && paddr_i == 12 && !pwdata_i[4];
    wire abort = wr && !bad && paddr_i == 12 && pwdata_i[4];
    wire timeout_hit = active && timer == TIMEOUT_CYCLES-1;
    wire done = active && seen_busy && busy_q && !busy;
    wire [3:0] events = {timeout_hit, rx_valid, nack, done};
    assign pready_o = 1'b1;
    assign pslverr_o = access && bad;
    assign irq_o = |(cause & imask);
    assign scl_oe_o = !scl_t && !abort_q && rst_ni;
    assign sda_oe_o = !sda_t && !abort_q && rst_ni;
    i2c_master u_master (
        .clk(clk_i), .rst(!rst_ni || abort_q),
        .s_axis_cmd_address(address), .s_axis_cmd_start(command[2]),
        .s_axis_cmd_read(command[0]), .s_axis_cmd_write(command[1]),
        .s_axis_cmd_write_multiple(1'b0), .s_axis_cmd_stop(command[3]),
        .s_axis_cmd_valid(cmd_valid), .s_axis_cmd_ready(cmd_ready),
        .s_axis_data_tdata(txdata), .s_axis_data_tvalid(tx_valid),
        .s_axis_data_tready(tx_ready), .s_axis_data_tlast(1'b1),
        .m_axis_data_tdata(rxdata), .m_axis_data_tvalid(rx_valid),
        .m_axis_data_tready(access && !pwrite_i && !bad && paddr_i == 16),
        .m_axis_data_tlast(), .scl_i(scl_sync), .scl_o(), .scl_t(scl_t),
        .sda_i(sda_sync), .sda_o(), .sda_t(sda_t),
        .busy(busy), .bus_control(bus_control), .bus_active(bus_active),
        .missed_ack(nack), .prescale(prescale), .stop_on_idle(1'b0));
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            scl_meta <= 1; scl_sync <= 1; sda_meta <= 1; sda_sync <= 1;
            prescale <= 125; address <= 0; txdata <= 0; command <= 0;
            cmd_valid <= 0; tx_valid <= 0; active <= 0; seen_busy <= 0;
            busy_q <= 0; abort_q <= 0; cause <= 0; imask <= 0; timer <= 0;
        end else begin
            scl_meta <= scl_i; scl_sync <= scl_meta;
            sda_meta <= sda_i; sda_sync <= sda_meta;
            busy_q <= busy; abort_q <= 0;
            cause <= (cause & ~((wr && !bad && paddr_i == 24) ? pwdata_i[3:0] : 4'b0)) | events;
            if (cmd_ready) cmd_valid <= 0;
            if (tx_ready) tx_valid <= 0;
            if (active) begin
                timer <= timer + 1'b1;
                if (busy) seen_busy <= 1;
                if (done) begin active <= 0; tx_valid <= 0; end
            end
            if (wr && !bad) case (paddr_i)
                4: prescale <= pwdata_i[15:0];
                8: address <= pwdata_i[6:0];
                16: txdata <= pwdata_i[7:0];
                20: imask <= pwdata_i[3:0];
                default: ;
            endcase
            if (launch) begin
                command <= pwdata_i[3:0]; cmd_valid <= 1;
                tx_valid <= pwdata_i[1]; active <= 1; seen_busy <= 0; timer <= 0;
            end
            if (timeout_hit || abort) begin
                abort_q <= 1; cmd_valid <= 0; tx_valid <= 0;
                active <= 0; seen_busy <= 0;
            end
        end
    end
    always @* begin
        prdata_o = 0;
        case (paddr_i)
            0: prdata_o = {27'b0, rx_valid, bus_active, bus_control, busy, active};
            4: prdata_o = {16'b0, prescale};
            8: prdata_o = {25'b0, address};
            12: prdata_o = {28'b0, command};
            16: prdata_o = {24'b0, rxdata};
            20: prdata_o = {28'b0, imask};
            24: prdata_o = {28'b0, cause};
            28: prdata_o = TIMEOUT_CYCLES;
            default: ;
        endcase
    end
endmodule
