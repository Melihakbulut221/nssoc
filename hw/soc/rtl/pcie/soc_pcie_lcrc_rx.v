// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Project-local, single-clock receive boundary, NOT a PCIe DLL or PIPE.
// Input bytes: {reserved[3:0],sequence[11:8]}, sequence[7:0], complete TLP,
// then four wire-order LCRC bytes. SOP/EOP delimit this entire byte packet.
// Coverage includes both prefix bytes and EVERY TLP bit, including reserved
// fields; framing symbols are absent. rx_error_i marks other upstream faults.
// No output byte is valid until a clean accepted EOP passes length and LCRC.
// Output omits the two prefix and four CRC bytes. Sequence/reserved outputs
// are valid at packet_good_o only, not as an APB/completion transaction tag.
// No sequence acceptance, ACK/NAK, credits or replay is implemented here.
// At most MAX_TLP_DWORDS aligned DWORDs (default 8), minimum three. Overflow
// drains until EOP/new SOP; a new SOP abandons the old partial packet. An
// indefinitely paused packet needs SOP or reset; no receive timeout exists.
module soc_pcie_lcrc_rx #(
    parameter integer MAX_TLP_DWORDS=8
) (
    input wire clk_i,rst_ni,
    input wire [7:0] rx_data_i,
    input wire rx_sop_i,rx_eop_i,rx_error_i,rx_valid_i,
    output wire rx_ready_o,
    output wire [7:0] tlp_data_o,
    output wire tlp_sop_o,tlp_eop_o,tlp_valid_o,
    input wire tlp_ready_i,
    output reg [11:0] sequence_o,
    output reg [3:0] reserved_o,
    output reg packet_good_o,packet_bad_o
`ifdef SOC_PCIE_SEQ_RX_REG
    // docs/combined-timing.md section 19: the next-cycle value of
    // state!=EMIT && !packet_bad_o (packet_good_o rises only with EMIT).
    ,output reg open_next_o
`endif
);
    localparam integer CAP=MAX_TLP_DWORDS*4;
    localparam integer CW=$clog2(CAP+7);
    localparam [1:0] IDLE=0,COLLECT=1,DROP=2,EMIT=3;
    reg [1:0] state;
    reg [CW-1:0] received,length,index;
    reg [7:0] bytes [0:CAP-1];
    reg [31:0] crc;
    wire [31:0] crc_next;
    soc_pcie_crc32_byte update_crc(.state_i(rx_sop_i ? 32'hffffffff : crc),
                                  .data_i(rx_data_i),.state_o(crc_next));
    // Eight reflected CRC steps are invertible. Reversing DEBB20E3 yields
    // 00BE26ED before the byte XOR. This tests the identical residue without
    // placing the entire byte-update XOR network on the late EOP verdict path.
    wire crc_residue_ok=((rx_sop_i ? 32'hffffffff : crc) ^
                         {24'b0,rx_data_i})==32'h00be26ed;
    assign rx_ready_o=rst_ni && state!=EMIT;
    assign tlp_valid_o=rst_ni && state==EMIT;
    // Byte store ports. Bytes are written one cycle after acceptance from a
    // registered one-hot select and a registered byte; a stored TLP byte is
    // read no earlier than the cycle after the accepted EOP, which follows
    // its last data byte by four LCRC bytes. The output byte is a register
    // holding bytes[index]: loaded with byte 0 while not emitting, and with
    // the next byte (selected by a one-hot cursor of index+1) when a byte
    // is taken mid-frame. Nothing is written while emitting.
    reg [CAP-1:0] write_at,cursor;
    reg [7:0] write_data,out_byte;
    wire [CAP-1:0] cursor_next={cursor[CAP-2:0],1'b0};
    reg [7:0] following;
    integer f,w,wi;
    always @* begin
        following=0;
        for(f=0;f<CAP;f=f+1) if(cursor_next[f]) following=following|bytes[f];
    end
    wire taken=state==EMIT && tlp_ready_i;
    always @(posedge clk_i) begin
        write_data<=rx_data_i;
        for(w=0;w<CAP;w=w+1) if(write_at[w]) bytes[w]<=write_data;
        out_byte<=state!=EMIT ? bytes[0] : (taken && !tlp_eop_o) ? following : out_byte;
    end
    always @(posedge clk_i or negedge rst_ni)
        if(!rst_ni) cursor<={{(CAP-1){1'b0}},1'b1};
        else if(state!=EMIT || (taken && tlp_eop_o)) cursor<={{(CAP-1){1'b0}},1'b1};
        else if(taken) cursor<=cursor_next;
    assign tlp_data_o=out_byte;
    assign tlp_sop_o=state==EMIT && index==0;
    assign tlp_eop_o=state==EMIT && index==length-1'b1;
`ifdef SOC_PCIE_SEQ_RX_REG
    // The control branches of the block below, for state and packet_bad_o
    // only: 1 where the edge leaves state!=EMIT and packet_bad_o low.
    always @* begin
        open_next_o=1'b1;
        if (state==EMIT) open_next_o=tlp_ready_i && tlp_eop_o;
        else if (rx_valid_i) begin
            if (rx_sop_i) open_next_o=!(state==COLLECT || rx_error_i || rx_eop_i);
            else if (state==IDLE) open_next_o=1'b0;
            else if (state==DROP) open_next_o=1'b1;
            else if (rx_error_i || 32'(received)==CAP+6) open_next_o=1'b0;
            else open_next_o=!rx_eop_i;
        end
    end
`endif
    generate if (MAX_TLP_DWORDS<3 || MAX_TLP_DWORDS>1028) begin: invalid_capacity
        initial $error("MAX_TLP_DWORDS must be 3..1028");
    end endgenerate
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state<=IDLE;received<=0;length<=0;index<=0;crc<=32'hffffffff;
            sequence_o<=0;reserved_o<=0;packet_good_o<=0;packet_bad_o<=0;write_at<=0;
        end else begin
            packet_good_o<=0;packet_bad_o<=0;write_at<=0;
            if (state==EMIT) begin
                if (tlp_ready_i) begin
                    if (tlp_eop_o) begin state<=IDLE;index<=0;end
                    else index<=index+1'b1;
                end
            end else if (rx_valid_i) begin
                if (rx_sop_i) begin
                    if (state==COLLECT) packet_bad_o<=1;
                    received<=1;crc<=crc_next;index<=0;
                    reserved_o<=rx_data_i[7:4];sequence_o<={rx_data_i[3:0],8'b0};
                    if (rx_error_i || rx_eop_i) begin
                        packet_bad_o<=1;state<=rx_eop_i ? IDLE : DROP;
                    end else state<=COLLECT;
                end else if (state==IDLE) begin
                    packet_bad_o<=1;state<=rx_eop_i ? IDLE : DROP;
                end else if (state==DROP) begin
                    if (rx_eop_i) state<=IDLE;
                end else if (rx_error_i || 32'(received)==CAP+6) begin
                    packet_bad_o<=1;state<=rx_eop_i ? IDLE : DROP;
                end else begin
                    crc<=crc_next;received<=received+1'b1;
                    if (received==1) sequence_o[7:0]<=rx_data_i;
                    for(wi=0;wi<CAP;wi=wi+1) if(received==CW'(wi+2)) write_at[wi]<=1;
                    if (rx_eop_i) begin
                        if (received>=17 && received[1:0]==1 && crc_residue_ok) begin
                            length<=received-5;state<=EMIT;index<=0;packet_good_o<=1;
                        end else begin state<=IDLE;packet_bad_o<=1;end
                    end
                end
            end
        end
    end
endmodule
`default_nettype wire
