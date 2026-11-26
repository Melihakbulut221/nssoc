// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
module test;
reg [1023:0] data;
reg [255:0] checks,syndromes;
reg [4:0] address;
wire ok;
m dut(data,checks,syndromes,address,ok);
integer i,j,n,pattern;
initial begin
 for (pattern=0;pattern<3;pattern=pattern+1) begin
  for (i=0;i<32;i=i+1) data[32*i+:32]=$random;
  for (i=0;i<8;i=i+1) begin checks[32*i+:32]=$random; syndromes[32*i+:32]=$random; end
  if(pattern==1) begin data=0; checks=0; syndromes=0; end
  if(pattern==2) begin data[370+:32]=32'bx; checks[12+:8]=8'bz; end
  for(i=0;i<1024;i=i+1) begin
   n=i;
   for(j=0;j<5;j=j+1) begin
    case(n%4) 0: address[j]=0;1: address[j]=1;2: address[j]=1'bx;3: address[j]=1'bz;endcase
    n=n/4;
   end
   #1;
   if({dut.raw_b,dut.chk_b,dut.use_syn_b} !== {dut.rf_data[address],dut.rf_chk[address],dut.rf_syn[address]}) $fatal;
  end
 end
 $display("PASS 3072 four-state comparisons");
end
endmodule
