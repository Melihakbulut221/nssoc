// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
primitive p_buf(q,d);
 output q; input d;
 table
  0 : 0;
  1 : 1;
 endtable
endprimitive
module tb;
 reg a,b,sel,clk,rstn,d;
 reg q;
 reg [7:0] mem [0:3];
 wire resolved,uq;
 wire [3:0] merged=sel ? 4'b1010 : 4'b1001;
 assign resolved=a;
 assign resolved=b;
 p_buf u(uq,a);
 integer errors,checks;
 always @(posedge clk or negedge rstn)
   if (!rstn) q<=0; else q<=d;
 task check;
  input pass;
  input [255:0] name;
  begin
   checks=checks+1;
   if (pass !== 1'b1) begin errors=errors+1; $display("FAIL %s",name); end
   $display("TRACE %0d %b",checks,pass);
  end
 endtask
 initial begin
  errors=0;checks=0;
  #1;check(q===1'bx,"uninitialized flop");check(mem[0]===8'hxx,"uninitialized memory");
  a=1'bz;b=1'bz;#1;check(resolved===1'bz,"floating net");check(uq===1'bx,"UDP Z becomes X");
  a=0;#1;check(resolved===0,"single zero driver");check(uq===0,"UDP zero");
  a=1;#1;check(resolved===1,"single one driver");check(uq===1,"UDP one");
  b=0;#1;check(resolved===1'bx,"driver conflict");
  a=1'bx;#1;check(resolved===1'bx,"unknown driver");check(uq===1'bx,"UDP unknown");
  sel=1'bx;#1;check(merged===4'b10xx,"unknown conditional merge");
  sel=1'bz;#1;check(merged===4'b10xx,"Z conditional merge");
  clk=0;rstn=0;d=1;#1;check(q===0,"async reset");
  rstn=1;#1;check(q===0,"reset release holds");
  clk=1;#1;check(q===1,"posedge capture");
  clk=0;d=1'bx;#1;check(q===1,"negedge holds");
  clk=1;#1;check(q===1'bx,"capture unknown");
  rstn=0;#1;check(q===0,"reset clears unknown");
  mem[1]=8'h5a;#1;check(mem[1]===8'h5a,"memory write");check(mem[0]===8'hxx,"other memory unknown");
  $display("PROBE_RESULT checks=%0d errors=%0d",checks,errors);
  $finish;
 end
endmodule
