// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
module tb_soc_sram_zero_check;
    parameter integer WIDTH=16, ADDR_WIDTH=3, PIPELINE_COMPARE=1;
    localparam integer DEPTH=1<<ADDR_WIDTH;
    reg clk=0, rst=0, start=0;
    always #5 clk=~clk;
    reg [WIDTH-1:0] data=0;
    wire req, done, failed;
    wire [ADDR_WIDTH-1:0] addr;
    integer fault=0, victim=0, bitno=0, perturb=0, reset_capture=0;
    integer illegal_state=0;
    integer accesses=0, cycles=0, expected_accesses, saved_cycles;
    reg prior_req=0, count_enable=0;
    soc_sram_zero_check #(.WIDTH(WIDTH),.ADDR_WIDTH(ADDR_WIDTH),
        .PIPELINE_COMPARE(PIPELINE_COMPARE)) dut(
        .clk_i(clk),.rst_ni(rst),.start_i(start),.rdata_i(data),
        .req_o(req),.addr_o(addr),.done_o(done),.failed_o(failed));
    always @(posedge clk) begin
        if (rst && count_enable) begin
            cycles=cycles+1;
            if(req) begin
                if(addr !== ADDR_WIDTH'(accesses)) $fatal(1,"Address sequence mismatch");
                accesses=accesses+1;
            end
        end
        if (!rst) begin data<=0; prior_req<=0; end
        else begin
            prior_req<=req;
            if(req) begin
                data<=0;
                if(addr==ADDR_WIDTH'(victim)) begin
                    if(fault==1) data <= {{(WIDTH-1){1'b0}},1'b1} << bitno;
                    if(fault==2) data <= {WIDTH{1'bx}};
                    if(fault==3) data <= {WIDTH{1'bz}};
                end
            end else if(perturb && prior_req) begin
                // Changes AFTER the capture edge, BEFORE the decision edge.
                // A live-input comparison would invert the expected verdict.
                data <= (fault && accesses-1==victim) ? 0 : {WIDTH{1'b1}};
            end
        end
    end
    initial begin
        if($value$plusargs("fault=%d",fault)) begin end
        if($value$plusargs("victim=%d",victim)) begin end
        if($value$plusargs("bitno=%d",bitno)) begin end
        if($value$plusargs("perturb=%d",perturb)) begin end
        if($value$plusargs("reset_capture=%d",reset_capture)) begin end
        if($value$plusargs("illegal_state=%d",illegal_state)) begin end
        #1; rst=1; #1; rst=0; #1;
        if(req || done || failed || addr!==0) $fatal(1,"Asynchronous reset failed");
        repeat(3) @(negedge clk);
        rst=1;
        repeat(4) begin @(negedge clk); if(req || done || failed) $fatal(1,"Premature start"); end
        if(illegal_state) begin
            if(illegal_state==8) force dut.state_q=3'bxxx;
            else force dut.state_q=3'(illegal_state);
            @(posedge clk); #1;
            if(req || !done || !failed) $fatal(1,"Illegal state did not fail closed");
            @(negedge clk); release dut.state_q;
            repeat(3) @(negedge clk);
            if(req || !done || !failed) $fatal(1,"Illegal-state failure not sticky");
            $display("PASS zero-check illegal-state=%0d",illegal_state);
            $finish;
        end
        start=1; count_enable=1;
        if(reset_capture) begin
            wait(req); @(posedge clk); @(posedge clk); #1;
            rst=0; #1;
            if(req || done || failed || addr!==0) $fatal(1,"Capture reset did not cancel");
            @(negedge clk); start=0; count_enable=0; accesses=0; cycles=0;
            @(negedge clk); rst=1;
            repeat(2) @(negedge clk);
            start=1; count_enable=1;
        end
        @(negedge clk); start=0;
        wait(done); #1; count_enable=0;
        expected_accesses=fault ? victim+1 : DEPTH;
        if(failed !== (fault!=0)) $fatal(1,"Fault verdict mismatch");
        if(accesses!=expected_accesses || addr!==ADDR_WIDTH'(expected_accesses-1))
            $fatal(1,"First-failure address/count mismatch");
        if(cycles!=1+expected_accesses*(2+PIPELINE_COMPARE))
            $fatal(1,"Unexpected latency %0d",cycles);
        saved_cycles=cycles;
        start=1; data={WIDTH{1'b1}};
        repeat(5) begin
            @(negedge clk);
            if(req || !done || failed!==(fault!=0) || accesses!=expected_accesses)
                $fatal(1,"Completion is not sticky");
        end
        $display("PASS zero-check accesses=%0d cycles=%0d failed=%0d",accesses,saved_cycles,failed);
        $finish;
    end
    initial begin #1000000; $fatal(1,"Test hung"); end
endmodule
