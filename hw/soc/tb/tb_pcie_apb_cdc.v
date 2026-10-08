// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_pcie_apb_cdc;
 parameter SOURCE_HALF=2,DESTINATION_HALF=10;
 reg sc=0,dc=0,rn=0,source_run=1,destination_run=1;
 always #(SOURCE_HALF) if(source_run) sc=~sc;
 initial begin #1;forever #(DESTINATION_HALF) if(destination_run) dc=~dc;end
 reg ss=0,se=0,sw=0;
 reg [11:0] sa=0;
 reg [31:0] sd=0;
 reg [3:0] st=0;
 wire sr,sx,ms,me,mw;
 wire [31:0] sq,md;
 wire [11:0] ma;
 wire [3:0] mt;
 reg ready=0,err=0;
 wire [31:0] reply=md ^ {16'hbcda,ma,mt};
 soc_pcie_apb_cdc dut(.source_clk_i(sc),.destination_clk_i(dc),.reset_ni(rn),
   .s_psel_i(ss),.s_penable_i(se),.s_pwrite_i(sw),.s_paddr_i(sa),.s_pwdata_i(sd),.s_pstrb_i(st),
   .s_pready_o(sr),.s_pslverr_o(sx),.s_prdata_o(sq),
   .m_psel_o(ms),.m_penable_o(me),.m_pwrite_o(mw),.m_paddr_o(ma),.m_pwdata_o(md),.m_pstrb_o(mt),
   .m_pready_i(ready),.m_pslverr_i(err),.m_prdata_i(reply));
 integer seen=0,waits=0,i,n,baseline;
 reg [48:0] expected,held;
 reg expecting=0,held_valid=0,block_slave=0;
 always @(negedge dc) begin
   if(!rn || !ms || !me) begin ready=0;waits=0;end
   else begin waits=waits+1;ready=(waits>=3) && !block_slave;end
   err=ma[2];
 end
 always @(posedge dc) if(rn) begin
   if(ms && !me) begin
     if({mw,ma,md,mt}!==expected || !expecting)$fatal(1,"request payload/setup mismatch");
     held={mw,ma,md,mt};held_valid=1;
   end
   if(ms && me) begin
     if(!held_valid || held!=={mw,ma,md,mt})$fatal(1,"APB setup/stability violation");
     if(ready)begin
       if(!expecting)$fatal(1,"duplicate or unsolicited destination transfer");
       expecting=0;seen=seen+1;held_valid=0;
     end
   end
 end else held_valid=0;
 task request;
   input integer index;
   begin
     @(negedge sc);ss=1;se=0;sw=index[0];sa=index*4;sd=32'hac190000+index;st=index[3:0];
     expected={sw,sa,sd,st};expecting=1;
     @(negedge sc);se=1;
   end
 endtask
 task response;
   begin : wait_response
     for(n=0;n<1000;n=n+1)begin
       @(negedge sc);
       if(sr)begin
         if(sq!==(sd ^ {16'hbcda,sa,st}) || sx!==sa[2])$fatal(1,"response data/error mismatch");
         @(posedge sc);#0.1;
         disable wait_response;
       end
     end
     $fatal(1,"source response cycle bound");
   end
 endtask
 task reset;
   begin
     rn=0;ss=0;se=0;expecting=0;
     #0.1;if(sr || ms || me)$fatal(1,"reset did not isolate both buses");
     repeat(5)@(negedge sc);
     rn=1;
     repeat(8)@(negedge sc);
   end
 endtask
 initial begin
   #0.2;reset();
   for(i=0;i<96;i=i+1)begin
     request(i);response();
     // Hold old ACCESS after acknowledgement: timeout-style parking must
     // not duplicate the already-completed peripheral transaction.
     repeat(20)begin @(negedge sc);if(sr)$fatal(1,"repeated acknowledgement");end
   end
   @(negedge sc);ss=0;se=0;
   repeat(30)@(negedge dc);
   if(seen!=96)$fatal(1,"lost or duplicated transaction");
   // Reset with destination clock stopped and an unobserved request.
   @(negedge dc);destination_run=0;baseline=seen;
   request(111);repeat(10)@(negedge sc);reset();destination_run=1;
   repeat(20)@(negedge dc);
   if(seen!=baseline)$fatal(1,"stale request crossed reset");
   // Reset during a genuine destination ACCESS wait, then retry fresh.
   block_slave=1;request(112);
   wait(ms && me);#0.3;reset();block_slave=0;
   repeat(20)@(negedge dc);
   if(seen!=baseline)$fatal(1,"cancelled wait committed");
   request(113);response();@(negedge sc);ss=0;se=0;
   repeat(30)@(negedge dc);
   if(seen!=97)$fatal(1,"post-reset recovery failed");
   $display("PASS_PCIE_APB_CDC transfers=%0d source_half=%0d destination_half=%0d",seen,SOURCE_HALF,DESTINATION_HALF);
   $finish;
 end
 initial begin #1000000;$fatal(1,"finite simulation bound");end
endmodule
