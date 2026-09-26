// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
`default_nettype none
module tb_soc_sram_test_port;
    parameter integer WIDTH=16, DEPTH=512;
    localparam integer AW=$clog2(DEPTH);
    reg clk=0, reset_n=0, test_mode=0, start=0, abort_test=0;
    reg f_req=1, f_we=1;
    reg [AW-1:0] f_addr=0;
    reg [WIDTH-1:0] f_data={WIDTH{1'b1}}, f_mask={WIDTH{1'b1}};
    wire ready, req, we, busy, done, failed, aborted;
    wire [AW-1:0] addr, fail_addr;
    wire [WIDTH-1:0] data, mask, raw_read, fail_expected, fail_actual;
    wire [2:0] fail_phase;
    wire [7:0] fail_background;
    integer mode=0, fault=0, unused, count=0, cycles=0, k;
    wire [WIDTH-1:0] observed_read=raw_read ^ (fault!=0 ? {{(WIDTH-1){1'b0}},1'b1} : {WIDTH{1'b0}});
    always #5 clk=~clk;
    soc_sram_test_port
`ifndef MBIST_GATE
        #(.WIDTH(WIDTH),.DEPTH(DEPTH))
`endif
        dut (
        .clk_i(clk),.rst_ni(reset_n),.test_mode_i(test_mode),.start_i(start),.abort_i(abort_test),
        .func_req_i(f_req),.func_we_i(f_we),.func_addr_i(f_addr),.func_wdata_i(f_data),
        .func_wmask_i(f_mask),.functional_ready_o(ready),.mem_req_o(req),.mem_we_o(we),
        .mem_addr_o(addr),.mem_wdata_o(data),.mem_wmask_o(mask),.mem_rdata_i(observed_read),
        .busy_o(busy),.done_o(done),.failed_o(failed),.aborted_o(aborted),
        .fail_addr_o(fail_addr),.fail_expected_o(fail_expected),.fail_actual_o(fail_actual),
        .fail_phase_o(fail_phase),.fail_background_o(fail_background));
`ifdef MBIST_NATIVE
    `MBIST_MACRO macro_ram (
        .A_CLK(clk),.A_MEN(req),.A_WEN(we),.A_REN(req && !we),.A_ADDR(addr),
        .A_DIN(data),.A_BM(mask),.A_DLY(1'b1),.A_DOUT(raw_read),
        .A_BIST_CLK(1'b0),.A_BIST_EN(1'b0),.A_BIST_MEN(1'b0),.A_BIST_WEN(1'b0),
        .A_BIST_REN(1'b0),.A_BIST_ADDR({AW{1'b0}}),.A_BIST_DIN({WIDTH{1'b0}}),
        .A_BIST_BM({WIDTH{1'b0}}));
`else
    reg [WIDTH-1:0] memory[0:DEPTH-1];
    reg [WIDTH-1:0] read_q;
    assign raw_read=read_q;
    always @(posedge clk) if(req) begin
        if(we) memory[addr]<=(memory[addr]&~mask)|(data&mask);
        else read_q<=memory[addr];
    end
`endif
    always @(posedge clk) begin
        cycles=cycles+1;
        if(cycles>1000000) $fatal(1,"timeout");
        if(!reset_n && (req || we || ready)) $fatal(1,"reset isolation");
        if(test_mode && ready) $fatal(1,"functional owner leaked into test");
        if(we && !req) $fatal(1,"unqualified write");
        if(busy && req) begin
            count=count+1;
            if(!test_mode || abort_test) $fatal(1,"request after ownership revoked");
            if(we && mask!=={WIDTH{1'b1}}) $fatal(1,"test mask incomplete");
        end
        if(!we && mask!=={WIDTH{1'b0}}) $fatal(1,"idle write mask");
    end
    task launch;
        begin
            @(negedge clk); start=0; test_mode=1;
            @(negedge clk); start=1;
            @(negedge clk);
            if(!busy || done || ready) $fatal(1,"start/ownership");
        end
    endtask
    initial begin
        unused=$value$plusargs("mode=%d",mode);
        unused=$value$plusargs("fault=%d",fault);
        repeat(3) @(negedge clk); reset_n=1;
        @(negedge clk); f_data=0; f_mask={{(WIDTH-1){1'b0}},1'b1};
        @(negedge clk); f_we=0;
        @(negedge clk);
        if(raw_read!=={{(WIDTH-1){1'b1}},1'b0}) $fatal(1,"functional mask not preserved");
        // Keep an opposing functional write asserted throughout MBIST.
        f_we=1; f_data={WIDTH{1'b1}}; f_mask={WIDTH{1'b1}};
        launch();
        if(mode!=0) begin
            wait(req && !we); @(posedge clk); @(negedge clk);
            if(mode==1) abort_test=1;
            if(mode==2) test_mode=0;
            if(mode==3) reset_n=0;
            #1; if(req || we) $fatal(1,"revocation not immediate");
            @(negedge clk);
            if(busy) $fatal(1,"revocation did not stop MBIST");
            if(mode!=3 && (!done || !aborted || failed)) $fatal(1,"abort receipt");
            if(mode==3 && (done || aborted || failed)) $fatal(1,"reset receipt");
            count=0; abort_test=0; reset_n=1;
            launch();
        end
        wait(done); @(negedge clk);
        if(busy || aborted || failed!=(fault!=0)) $fatal(1,"terminal result");
        if(fault==0 && count!=10*DEPTH*($clog2(WIDTH)+2)) $fatal(1,"incomplete March");
        if(fault!=0 && (fail_addr!=0 || fail_expected!=0 || fail_actual!=1 ||
                        fail_phase!=1 || fail_background!=0)) $fatal(1,"first-fault receipt");
        repeat(10) @(negedge clk);
        if(req || ready || !done) $fatal(1,"terminal ownership/held start");
        // Release the array only after the functional master stops writing.
        start=0; f_we=0; test_mode=0;
        if(fault==0) for(k=0;k<DEPTH;k=k+1) begin
            f_addr=AW'(k); @(negedge clk);
            if(!ready || raw_read!=={WIDTH{1'b0}}) $fatal(1,"cleared-array readback");
        end
        $display("PASS test-port width=%0d depth=%0d mode=%0d fault=%0d accesses=%0d",
                 WIDTH,DEPTH,mode,fault,count);
        $finish;
    end
endmodule
`default_nettype wire
