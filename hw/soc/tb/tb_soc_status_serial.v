// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
`timescale 1ns/1ps
`default_nettype none
module tb_soc_status_serial;
    reg clk=0, rst=1, tclk=0, req=0;
    reg run_source=1;
    reg [191:0] status=0;
    wire ready, data;
    always #7 if (run_source) clk=~clk;
    soc_status_serial dut(.clk_i(clk),.rst_ni(rst),.status_i(status),
        .test_clk_i(tclk),.test_req_i(req),.test_ready_o(ready),.test_data_o(data));
    task tick;
        begin #11; tclk=1; #13; tclk=0; #3; end
    endtask
    task capture;
        input [191:0] expected;
        integer n;
        reg [191:0] got;
        begin
            status=expected; req=~req; #1;
            if (ready !== 0 || data !== 0) $fatal(1,"old frame exposed after request");
            n=0;
            fork
                begin wait(dut.ack === req); #1; status=~expected; end
                begin while (ready !== 1 && n<40) begin tick; n=n+1; end end
            join
            if (ready !== 1) $fatal(1,"snapshot timeout");
            // Source changed before serial acknowledgement: receiver needs
            // the held source-domain snapshot, never the live status bus.
            for (n=0;n<192;n=n+1) begin
                got[n]=data;
                if (n==53) #117; // stopped test clock must retain the frame
                tick;
            end
            if (got !== expected) $fatal(1,"torn, shifted or incorrect snapshot");
            repeat(8) begin
                if (data !== 0) $fatal(1,"serial overflow did not zero-fill");
                tick;
            end
        end
    endtask
    initial begin
        #1; rst=0; #17; rst=1; #3;
        repeat(5) tick;
        if (ready !== 0 || data !== 0) $fatal(1,"unsolicited frame");
        capture(192'h123456789abcdef00123456789abcdefcafefeed00000001);
        capture(192'hfedcba9876543210ffeeddccbbaa99887766554433221100);
        capture(0);
        capture({192{1'b1}});
        // Missing source clock must not acknowledge a new request.
        @(negedge clk); run_source=0; req=~req; #1;
        repeat(20) begin tick; if (ready !== 0) $fatal(1,"false ready with stopped source"); end
        run_source=1;
        repeat(20) tick;
        if (ready !== 1) $fatal(1,"source restart failed");
        // Asynchronous POR invalidates a partial frame in both domains.
        rst=0; #1;
        if (ready !== 0 || data !== 0) $fatal(1,"reset leaked status");
        req=0; #19; rst=1;
        repeat(5) tick;
        if (ready !== 0) $fatal(1,"reset invented request");
        capture(192'h0123456789abcdef0123456789abcdef0123456789abcdef);
        $display("PASS status serial: coherent frames, repeated requests, idle, overflow, stopped clocks and POR");
        $finish;
    end
    initial begin #100000; $fatal(1,"timeout"); end
endmodule
`default_nettype wire
