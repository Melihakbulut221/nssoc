// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: Apache-2.0
`timescale 1ns/1ps
module tb_pcie_gen12_codec;
 reg [7:0] data;reg kin,erd;wire [9:0] code;wire erdo,kerr;
 reg [9:0] rcode;reg drd;wire [7:0] decoded;wire kout,drdo,cerr,derr;
 soc_pcie_gen12_8b10b_encode enc(data,kin,erd,code,erdo,kerr);
 soc_pcie_gen12_8b10b_decode dec(rcode,drd,decoded,kout,drdo,cerr,derr);
 reg [21:0] ev[0:1023];reg [22:0] dv[0:2047];reg [77:0] cv[0:2047];
 reg [48:0] lv[0:4095];
 reg [9:0] ec;reg eo,ee;
 reg [7:0] ed;reg ek,edo,ece,ede;
 reg crd;reg [3:0] ck;reg [31:0] cd;reg [39:0] expected_codes;
 reg expected_end;
 wire [39:0] cc;wire [31:0] cdecoded;wire [3:0] decoded_k,cek,cde,cdd;
 wire [4:0] ce_rd,cd_rd;
 assign ce_rd[0]=crd;assign cd_rd[0]=crd;
 genvar g;
 generate for(g=0;g<4;g=g+1)begin:chain
  soc_pcie_gen12_8b10b_encode e(cd[g*8+:8],ck[g],ce_rd[g],cc[g*10+:10],ce_rd[g+1],cek[g]);
  soc_pcie_gen12_8b10b_decode d(cc[g*10+:10],cd_rd[g],cdecoded[g*8+:8],decoded_k[g],cd_rd[g+1],cde[g],cdd[g]);
 end endgenerate
 reg txclk=0,rxclk=0,trst=0,rrst=0,ten=0,ren=0,tk=0;
 reg [7:0] td=0;reg [9:0] rc=0;
 wire [9:0] tc;wire tv,te,trd;wire [7:0] rd;wire rk,rv,rce,rde,rrd;
 soc_pcie_gen12_codec_lane lane(txclk,trst,ten,td,tk,tc,tv,te,trd,
  rxclk,rrst,ren,rc,rd,rk,rv,rce,rde,rrd);
 reg [9:0] etc;reg etrd,etv,ete;
 reg [7:0] erd_data;reg erk,errd,erv,erce,erde;
 integer i;
 initial begin
  data=0;kin=0;erd=0;rcode=0;drd=0;crd=0;ck=0;cd=0;
  $readmemh("encode.mem",ev);$readmemh("decode.mem",dv);
  $readmemh("chain.mem",cv);$readmemh("lane.mem",lv);
  for(i=0;i<1024;i=i+1)begin
   {erd,kin,data,ec,eo,ee}=ev[i];#1;
   if({code,erdo,kerr}!=={ec,eo,ee})
    $fatal(1,"ENC vector %0d got %h expected %h",i,{code,erdo,kerr},{ec,eo,ee});
  end
  for(i=0;i<2048;i=i+1)begin
   {drd,rcode,ed,ek,edo,ece,ede}=dv[i];#1;
   if({decoded,kout,drdo,cerr,derr}!=={ed,ek,edo,ece,ede})
    $fatal(1,"DEC vector %0d code %b RD %b got %h expected %h",i,rcode,drd,{decoded,kout,drdo,cerr,derr},{ed,ek,edo,ece,ede});
  end
  for(i=0;i<2048;i=i+1)begin
   {crd,ck,cd,expected_codes,expected_end}=cv[i];#1;
   if(cc!==expected_codes || ce_rd[4]!==expected_end || cek!==0)
    $fatal(1,"CHAIN encoder vector %0d",i);
   if(cdecoded!==cd || decoded_k!==ck || cd_rd[4]!==expected_end || cde!==0 || cdd!==0)
    $fatal(1,"CHAIN decoder vector %0d",i);
  end
  // A real assertion edge is required before checking asynchronous reset.
  // Declaration initialization to zero is not a reset transition.
  trst=1;rrst=1;#1;trst=0;rrst=0;#1;
  for(i=0;i<4096;i=i+1)begin
   txclk=0;rxclk=0;
   {trst,rrst,ten,ren,tk,td,rc,etc,etrd,etv,ete,erd_data,erk,errd,erv,erce,erde}=lv[i];
   #1;
   if(!trst && {tc,tv,te,trd}!==0)$fatal(1,"Asynchronous TX reset vector %0d",i);
   if(!rrst && {rd,rk,rv,rce,rde,rrd}!==0)$fatal(1,"Asynchronous RX reset vector %0d",i);
   txclk=1;#1;rxclk=1;#1;
   if({tc,trd,tv,te}!=={etc,etrd,etv,ete})$fatal(1,"TX lane vector %0d",i);
   if({rd,rk,rrd,rv,rce,rde}!=={erd_data,erk,errd,erv,erce,erde})$fatal(1,"RX lane vector %0d",i);
  end
  $display("PASS_GEN12_CODEC_1024_ENCODE_2048_DECODE_2048_CHAIN_4096_LANE");
  $finish;
 end
endmodule
