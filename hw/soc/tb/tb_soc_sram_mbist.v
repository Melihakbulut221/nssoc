// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
`default_nettype none
module tb_soc_sram_mbist;
    parameter integer WIDTH=4, DEPTH=4, LATENCY=1;
    localparam integer AW=(DEPTH>1)?$clog2(DEPTH):1;
    reg clk=0, reset_n=0, start=0, abort_test=0;
    always #5 clk=~clk;
    wire req, we, busy, done, failed, aborted;
    wire [AW-1:0] addr, fail_addr;
    wire [WIDTH-1:0] wdata, fail_expected, fail_actual;
    wire [2:0] fail_phase;
    wire [7:0] fail_background;
    reg [WIDTH-1:0] mem[0:DEPTH-1], pipe[0:LATENCY-1];
    soc_sram_mbist #(.WIDTH(WIDTH),.DEPTH(DEPTH),.READ_LATENCY(LATENCY)) dut (
        .clk_i(clk),.rst_ni(reset_n),.start_i(start),.abort_i(abort_test),
        .rdata_i(pipe[LATENCY-1]),.req_o(req),.we_o(we),.addr_o(addr),.wdata_o(wdata),
        .busy_o(busy),.done_o(done),.failed_o(failed),.aborted_o(aborted),
        .fail_addr_o(fail_addr),.fail_expected_o(fail_expected),.fail_actual_o(fail_actual),
        .fail_phase_o(fail_phase),.fail_background_o(fail_background));
    integer fault=0, victim=0, vb=0, aggressor=1, ab=1, polarity=0, forced=0;
    integer mode=0, cycles=0, requests=0, physical, k, saved_requests, unused;
    reg [WIDTH-1:0] before_write, incoming;
    reg transition;
    always @(posedge clk) begin
        cycles=cycles+1;
        if(cycles>200000) $fatal(1,"MBIST exceeded bounded execution");
        for(k=LATENCY-1;k>0;k=k-1) pipe[k]<=pipe[k-1];
        if(req) begin
            if(!reset_n || abort_test || !busy || addr>=DEPTH) $fatal(1,"illegal request");
            requests=requests+1;
            $display("ACCESS %0d %0d %h",we,addr,wdata);
            physical=(fault==5 && addr==victim)?aggressor:addr;
            if(we) begin
                before_write=mem[physical]; incoming=wdata;
                if(physical==victim) begin
                    if(fault==1) incoming[vb]=0;
                    if(fault==2) incoming[vb]=1;
                    if(fault==3 && !before_write[vb]) incoming[vb]=0;
                    if(fault==4 && before_write[vb]) incoming[vb]=1;
                end
                transition=before_write[ab]!=incoming[ab];
                mem[physical]=incoming;
                // Persistent inversion coupling after either aggressor transition.
                if((fault==6 || fault==7) && physical==aggressor && transition)
                    mem[victim][vb]=~mem[victim][vb];
                if((fault==8 || fault==10) && mem[aggressor][ab]==polarity[0])
                    mem[victim][vb]=forced[0];
            end else begin
                if(fault==9) pipe[0]<={WIDTH{1'bx}};
                else pipe[0]<=mem[physical];
                if(fault==9) $display("RETURN x");
                else $display("RETURN %h",mem[physical]);
            end
        end
    end
    task launch;
        begin
            @(negedge clk); start=0;
            @(negedge clk); start=1;
            @(negedge clk);
            if(!busy || done || failed || aborted) $fatal(1,"start did not clear results");
        end
    endtask
    initial begin
        unused=$value$plusargs("fault=%d",fault);
        unused=$value$plusargs("victim=%d",victim);
        unused=$value$plusargs("vb=%d",vb);
        unused=$value$plusargs("aggressor=%d",aggressor);
        unused=$value$plusargs("ab=%d",ab);
        unused=$value$plusargs("polarity=%d",polarity);
        unused=$value$plusargs("forced=%d",forced);
        unused=$value$plusargs("mode=%d",mode);
        for(k=0;k<DEPTH;k=k+1) mem[k]={WIDTH{1'b1}};
        repeat(3) @(negedge clk);
        reset_n=1;
        launch();
        if(mode==1 || mode==2 || mode==4) begin
            // Interrupt after a read request, with response still outstanding.
            if(mode!=4) begin
                wait(req && !we); @(posedge clk); @(negedge clk);
            end
            saved_requests=requests;
            if(mode!=2) abort_test=1; else reset_n=0;
            #1; if(req) $fatal(1,"interrupted request leaked");
            repeat(3) @(negedge clk);
            if(requests!=saved_requests || busy) $fatal(1,"interrupted access");
            if(mode!=2 && (!done || !aborted || failed)) $fatal(1,"abort result");
            if(mode==2 && (done || aborted || failed)) $fatal(1,"reset result");
            start=0; abort_test=0; reset_n=1;
            launch();
        end
        if(mode==3) begin
            start=0; repeat(2) @(negedge clk); start=1;
        end
        wait(done); @(negedge clk);
        $display("RESULT %0d %0d %0d %h %h %0d %0d",failed,aborted,fail_addr,
                 fail_expected,fail_actual,fail_phase,fail_background);
        if(busy || aborted) $fatal(1,"bad terminal state");
        if(!failed) for(k=0;k<DEPTH;k=k+1)
            if(mem[k]!=={WIDTH{1'b0}}) $fatal(1,"success without cleared memory");
        saved_requests=requests;
        repeat(20) @(negedge clk);
        if(busy || !done || requests!=saved_requests) $fatal(1,"held start retriggered");
        $display("PASS protocol requests=%0d",requests);
        $finish;
    end
endmodule
`default_nettype wire
