// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Replacement SRAM adapter: byte-uniform masks, vendor BIST disabled.
// Both DP ports support sequential MBIST read/write and FIFO operation.
// Physical/analog and timing qualification are separate from this RTL map.
module sp512_quad_byte_adapter(
 input wire clk, men, wen, ren,
 input wire [10:0] addr,
 input wire [63:0] din, bm,
 output wire [63:0] dout
);
 wire [63:0] bank_q [0:3];
 wire [7:0] bytes;
 genvar b;
 generate for(b=0;b<8;b=b+1) begin:mask
   assign bytes[b]=bm[8*b];
 end endgenerate
 genvar k;
 generate for(k=0;k<4;k=k+1) begin:bank
   wire [7:0] we=bytes & {8{men && wen && addr[10:9]==k}};
   SP6TSRAM512x64 mem(.clk(clk),.a(addr[8:0]),.d(din),.we(we),.q(bank_q[k]));
 end endgenerate
 reg [1:0] selected;
 reg live;
 reg [63:0] held;
 // The generated SRAM changes q on every edge, including writes. Save the
 // prior visible word whenever the native interface does not request a read.
 // A simultaneous read/write sees the updated word, matching vendor write-through.
 always @(posedge clk) begin
   if(live) held<=bank_q[selected];
   live<=men && ren;
   if(men && ren) selected<=addr[10:9];
 end
 assign dout=live ? bank_q[selected] : held;
endmodule

// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0

// Blackbox declaration for RM_IHPSG13_1P_2048x64_c2_bm_bist.
//
// Port list transcribed verbatim from the PDK's own behavioural model,
//   $PDK_ROOT/ihp-sg13g2/libs.ref/sg13g2_sram/verilog/RM_IHPSG13_1P_2048x64_c2_bm_bist.v
// with the body removed. Nothing is added and no port is renamed.
//
// Why a stub rather than the PDK file: the PDK model is a wrapper that
// instantiates SRAM_1P_behavioral_bm_bist, which lives in a different
// file, so handing the PDK model to the linter or to Yosys as a
// blackbox source drags in a submodule that is not wanted at synthesis
// time. This is hw/openlane/sram_pilot's finding, in
// docs/12 section 7: Verilator.Lint runs BEFORE synthesis and aborts
// with "Cannot find file containing module: RM_IHPSG13_1P_2048x64_c2_bm_bist"
// unless MACROS.<macro>.vh names a file like this one.
//
// Deliberately carries no power ports: the PDK's behavioural model has
// none either. The macro's supplies (VDD!, VSS!, VDDARRAY!) are LEF
// pins and reach the netlist through the ODB-generated powered netlist.

`default_nettype none


module RM_IHPSG13_1P_2048x64_c2_bm_bist (
    A_CLK,
    A_MEN,
    A_WEN,
    A_REN,
    A_ADDR,
    A_DIN,
    A_DLY,
    A_DOUT,
    A_BM,
    A_BIST_CLK,
    A_BIST_EN,
    A_BIST_MEN,
    A_BIST_WEN,
    A_BIST_REN,
    A_BIST_ADDR,
    A_BIST_DIN,
    A_BIST_BM
);

    input A_CLK;
    input A_MEN;
    input A_WEN;
    input A_REN;
    input [10:0] A_ADDR;
    input [63:0] A_DIN;
    input A_DLY;
    output [63:0] A_DOUT;
    input [63:0] A_BM;
    input A_BIST_CLK;
    input A_BIST_EN;
    input A_BIST_MEN;
    input A_BIST_WEN;
    input A_BIST_REN;
    input [10:0] A_BIST_ADDR;
    input [63:0] A_BIST_DIN;
    input [63:0] A_BIST_BM;

sp512_quad_byte_adapter bank_adapter(.clk(A_CLK),.men(A_MEN),.wen(A_WEN),.ren(A_REN),.addr(A_ADDR),.din(A_DIN),.bm(A_BM),.dout(A_DOUT));
endmodule

`default_nettype wire

// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Declaration of native SG13G2 two-port SRAM; no functional behavior.

module RM_IHPSG13_2P_256x16_c2_bm_bist (
    input wire A_CLK,
    input wire A_MEN,
    input wire A_WEN,
    input wire A_REN,
    input wire [7:0] A_ADDR,
    input wire [15:0] A_DIN,
    input wire A_DLY,
    output wire [15:0] A_DOUT,
    input wire [15:0] A_BM,
    input wire A_BIST_CLK,
    input wire A_BIST_EN,
    input wire A_BIST_MEN,
    input wire A_BIST_WEN,
    input wire A_BIST_REN,
    input wire [7:0] A_BIST_ADDR,
    input wire [15:0] A_BIST_DIN,
    input wire [15:0] A_BIST_BM,
    input wire B_CLK,
    input wire B_MEN,
    input wire B_WEN,
    input wire B_REN,
    input wire [7:0] B_ADDR,
    input wire [15:0] B_DIN,
    input wire B_DLY,
    output wire [15:0] B_DOUT,
    input wire [15:0] B_BM,
    input wire B_BIST_CLK,
    input wire B_BIST_EN,
    input wire B_BIST_MEN,
    input wire B_BIST_WEN,
    input wire B_BIST_REN,
    input wire [7:0] B_BIST_ADDR,
    input wire [15:0] B_BIST_DIN,
    input wire [15:0] B_BIST_BM
);

 wire [15:0] raw_a, raw_b;
 reg live_a, live_b;
 reg [15:0] held_a, held_b;
 DP8TSRAMDP256x16 mem(
   .clk1(A_CLK), .a1(A_ADDR), .d1(A_DIN),
   .we1({A_BM[8],A_BM[0]} & {2{A_MEN && A_WEN}}), .q1(raw_a),
   .clk2(B_CLK), .a2(B_ADDR), .d2(B_DIN),
   .we2({B_BM[8],B_BM[0]} & {2{B_MEN && B_WEN}}), .q2(raw_b));
 always @(posedge A_CLK) begin
   if (live_a) held_a <= raw_a;
   live_a <= A_MEN && A_REN;
 end
 always @(posedge B_CLK) begin
   if (live_b) held_b <= raw_b;
   live_b <= B_MEN && B_REN;
 end
 assign A_DOUT = live_a ? raw_a : held_a;
 assign B_DOUT = live_b ? raw_b : held_b;
endmodule
`default_nettype wire
