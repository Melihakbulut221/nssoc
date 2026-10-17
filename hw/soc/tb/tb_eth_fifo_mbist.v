// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_eth_fifo_mbist;
    reg wc=0, rc=0, por=0, wrst=1, rrst=1, run_r=1;
    always #10 wc=~wc;
    always #4 if (run_r) rc=~rc;
    reg wen=0, ren=0;
    reg [10:0] wa=0, ra=0;
    reg [15:0] wd=0;
    wire [15:0] rd;
    wire done, failed;
    integer mode=0, fault_bank=0, i, counta=0, countb=0, xa=0, xb=0;
    soc_eth_fifo_sram dut(.wclk_i(wc),.rclk_i(rc),.por_ni(por),
        .wreset_i(wrst),.rreset_i(rrst),.wen_i(wen),.ren_i(ren),
        .waddr_i(wa),.raddr_i(ra),.wdata_i(wd),.rdata_o(rd),.done_o(done),.failed_o(failed));
    always @(posedge wc) if (por) begin
        if (dut.areq) counta=counta+1;
        if (dut.axreq) xa=xa+1;
        if (dut.am && dut.bm && (!dut.a_functional || !dut.b_functional))
            $fatal(1,"Test port ownership overlaps");
    end
    always @(posedge rc) if (por) begin
        if (dut.breq) countb=countb+1;
        if (dut.bxreq) xb=xb+1;
    end
    // Inject into physical output bus including an unused FIFO payload bit.
    wire [15:0] corrupt_a = dut.bank_a[dut.sel_a] ^ ((dut.sel_a==3'(fault_bank)) ? 16'h8000 : 0);
    wire [15:0] corrupt_b = dut.bank_b[dut.sel_b] ^ ((dut.sel_b==3'(fault_bank)) ? 16'h8000 : 0);
    initial begin
        if ($value$plusargs("MODE=%d",mode)) begin end
        if ($value$plusargs("BANK=%d",fault_bank)) begin end
        #1; por=1; #1; por=0; #91; por=1;
        if (mode==1) force dut.aq=corrupt_a;
        if (mode==2) begin wait(dut.bxdone); force dut.bq=corrupt_b; end
        if (mode==3) begin
            repeat(100) @(negedge wc);
            por=0; #53; counta=0; countb=0; xa=0; xb=0; por=1;
        end
        if (mode==4) begin
            run_r=0;
            wait(dut.adone); repeat(30) @(negedge wc);
            if (done || dut.a_functional || dut.b_functional) $fatal(1,"Missing clock released memory");
            run_r=1;
        end
        if (mode==5) begin wait(dut.adone); force dut.bq=corrupt_b; end
        if (mode==6) begin wait(dut.bdone); force dut.aq=corrupt_a; end
        if (mode==7) begin
            repeat(100) @(negedge wc); force dut.u_a.state_q=2'b11;
            @(negedge wc); release dut.u_a.state_q;
        end
        if (mode==8) begin
            wait(dut.bxdone); repeat(5) @(negedge rc); force dut.u_b.state_q=2'b11;
            @(negedge rc); release dut.u_b.state_q;
        end
        wait(done); #1;
        if (mode==1 || mode==2 || mode==5 || mode==6 || mode==7 || mode==8) begin
            if (!failed) $fatal(1,"Fault escaped");
            wrst=0; rrst=0; wen=1; ren=1;
            repeat(10) @(negedge wc);
            if (dut.am || dut.bm) $fatal(1,"Failed memory released functional ports");
            $display("PASS detected mode=%0d bank=%0d",mode,fault_bank);
            $finish;
        end else begin
            if (failed || counta!=122880 || countb!=122880 || xa!=2048 || xb!=2048)
                $fatal(1,"Coverage fail a=%0d b=%0d xa=%0d xb=%0d",counta,countb,xa,xb);
            repeat(5) @(negedge wc);
            wrst=0; rrst=0;
            for(i=0;i<2048;i=i+1) begin
                @(negedge rc); ren=1; ra=11'(i);
                @(posedge rc); #1; if(rd!==0) $fatal(1,"Nonzero initial row %0d",i);
            end
            @(negedge rc); ren=0;
            for(i=0;i<2048;i=i+1) begin
                @(negedge wc); wen=1; wa=11'(i); wd=16'(i)^16'ha5c3;
            end
            @(negedge wc); wen=0;
            for(i=0;i<2048;i=i+1) begin
                @(negedge rc); ren=1; ra=11'(i);
                @(posedge rc); #1;
                if(rd!==(16'(i)^16'ha5c3)) $fatal(1,"Cross-port data mismatch row %0d got %h",i,rd);
            end
            @(negedge rc); ren=0; ra=171;
            repeat(5) @(negedge rc);
            if(rd!==(16'd2047^16'ha5c3)) $fatal(1,"Read output changed without read enable");
            wrst=1; rrst=1;
            repeat(10) @(negedge wc);
            if(!done || failed || counta!=122880 || countb!=122880) $fatal(1,"Functional reset reran test");
            $display("PASS complete mode=%0d accesses=%0d",mode,counta+countb+xa+xb);
            $finish;
        end
    end
    initial begin #12000000; $fatal(1,"MBIST timeout"); end
endmodule
