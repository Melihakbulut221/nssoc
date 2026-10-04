// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`default_nettype none
// Two same-clock APB masters. Capture a complete request, issue a fresh SETUP,
// and lock ownership through ACCESS. A withdrawn request cancels without an
// acknowledgement. Round robin changes only after a completed transaction.
// This is arbitration, not a clock-domain bridge or an access-control table.
module soc_pcie_apb_arbiter (
    input wire clk_i,rst_ni,
    input wire m0_psel_i,m0_penable_i,m0_pwrite_i,
    input wire [19:0] m0_paddr_i,
    input wire [31:0] m0_pwdata_i,
    input wire [3:0] m0_pstrb_i,
    output wire m0_pready_o,m0_pslverr_o,
    output wire [31:0] m0_prdata_o,
    input wire m1_psel_i,m1_penable_i,m1_pwrite_i,
    input wire [19:0] m1_paddr_i,
    input wire [31:0] m1_pwdata_i,
    input wire [3:0] m1_pstrb_i,
    output wire m1_pready_o,m1_pslverr_o,
    output wire [31:0] m1_prdata_o,
    output wire psel_o,penable_o,
    output reg pwrite_o,
    output reg [19:0] paddr_o,
    output reg [31:0] pwdata_o,
    output reg [3:0] pstrb_o,
    input wire pready_i,pslverr_i,
    input wire [31:0] prdata_i
);
    localparam [1:0] IDLE=0,SETUP=1,ACCESS=2;
    reg [1:0] state;
    reg owner,prefer_one;
    // The CPU timeout bridge deliberately parks ACCESS until reset. A late
    // completion must never be recaptured as another peripheral transaction.
    // A genuine new SETUP (or deselection) rearms the corresponding master.
    reg served_zero,served_one;
    wire request_zero=m0_psel_i && !served_zero;
    wire request_one=m1_psel_i && !served_one;
    wire choose_one=request_one && (!request_zero || prefer_one);
    wire present=owner ? m1_psel_i : m0_psel_i;
    wire enabled=owner ? m1_penable_i : m0_penable_i;
    // Do not let a stale request survive a master's reset/link withdrawal.
    assign psel_o=rst_ni && state!=IDLE && present;
    assign penable_o=psel_o && state==ACCESS && enabled;
    wire done=penable_o && pready_i;
    assign m0_pready_o=done && !owner;
    assign m1_pready_o=done && owner;
    assign m0_pslverr_o=m0_pready_o && pslverr_i;
    assign m1_pslverr_o=m1_pready_o && pslverr_i;
    assign m0_prdata_o=m0_pready_o ? prdata_i : 32'b0;
    assign m1_prdata_o=m1_pready_o ? prdata_i : 32'b0;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            state<=IDLE;owner<=0;prefer_one<=0;served_zero<=0;served_one<=0;
            paddr_o<=0;pwdata_o<=0;pwrite_o<=0;pstrb_o<=0;
        end else begin
          if(!m0_psel_i || !m0_penable_i) served_zero<=0;
          if(!m1_psel_i || !m1_penable_i) served_one<=0;
          case(state)
            IDLE: if(request_zero || request_one) begin
                owner<=choose_one;
                paddr_o<=choose_one ? m1_paddr_i : m0_paddr_i;
                pwdata_o<=choose_one ? m1_pwdata_i : m0_pwdata_i;
                pwrite_o<=choose_one ? m1_pwrite_i : m0_pwrite_i;
                pstrb_o<=choose_one ? m1_pstrb_i : m0_pstrb_i;
                state<=SETUP;
            end
            SETUP: state<=present ? ACCESS : IDLE;
            ACCESS: if(!present) state<=IDLE;
                    else if(done) begin
                        state<=IDLE;prefer_one<=!owner;
                        if(owner) served_one<=1;else served_zero<=1;
                    end
            default: state<=IDLE;
          endcase
        end
    end
endmodule
`default_nettype wire
