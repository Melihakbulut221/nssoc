// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
// Negative regression fixture: unchanged 71-cell DED-counter cone extracted
// from bb0ea7d native-boot netlist, GitHub run 35548416066, artifact 10618972531.
// Cell models are external, untouched IHP models. This is not product RTL.
// Boundary: pwdata bit, decoded clear, DED event, clock and POR.
`timescale 1ns/1ps
module tb;
reg clk=0,rst=0,ev=0,sel=0; reg[11:0] addr=12'h010;wire[31:0] rd;
always #5 clk=~clk;
scrub_counter_clear_pre_fix dut(.clk_i(clk),.rst_por_sync_n(rst),._014624_(1'b1),._040474_(sel),._031540_(ev),.count(rd[15:0])); assign rd[31:16]=0;
initial begin
repeat(3) @(negedge clk);rst=1;
@(negedge clk);ev=1'bx;
repeat(3) @(negedge clk);ev=0;
repeat(3) @(negedge clk);$display("before=%h",rd);sel=1;addr=12'h020;
@(negedge clk);sel=0;addr=12'h010;
@(negedge clk);$display("after=%h",rd);if(rd!==0)$fatal(1,"Unknown startup count survives clear");
$display("CLEAR PASS");$finish;
end
endmodule
