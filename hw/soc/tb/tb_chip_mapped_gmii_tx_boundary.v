`timescale 1ns/1ps
module tb_tx;
    supply1 vp;
    supply0 vn;
    reg clk=0, reset_n=1;
    always #5 clk=~clk;
    wire clkpad=clk, resetpad=reset_n;
    wire [7:0] data;
    wire en;
    nssoc_chip dut(.VDD(vp),.IOVDD(vp),.VSS(vn),.IOVSS(vn),
                   .pad_clk_i(clkpad),.pad_rst_ni(resetpad),
                   .pad_eth_tx_clk_i(clkpad),.pad_eth_rx_clk_i(clkpad),
                   .pad_eth_txd_o(data),.pad_eth_tx_en_o(en));
    reg [7:0] driven;
    reg valid;
    integer i;
    task check_boundary(input [7:0] value,input enable);
        begin
            driven=value; valid=enable; #2;
            if (data !== value || en !== enable)
                $fatal(1,"TX pad mismatch expected=%h/%b observed=%h/%b",value,enable,data,en);
        end
    endtask
    initial begin
        #1; reset_n=0;
        repeat (8) @(negedge clk);
        reset_n=1;
        repeat (32) begin
            @(negedge clk);
            if (en !== 1'b0) $fatal(1,"unexpected TX_EN in unfed reset probe: %b",en);
        end
        $display("Observed 32 idle TX clocks after reset");
        force dut.u_core.eth_txd_o=driven;
        force dut.u_core.eth_tx_en_o=valid;
        check_boundary(8'h00,0);
        for (i=0;i<8;i=i+1) begin
            check_boundary(8'h01<<i,1);
            check_boundary(~(8'h01<<i),0);
        end
        release dut.u_core.eth_txd_o;
        release dut.u_core.eth_tx_en_o;
        $display("PASS forced TX boundary connectivity");
        $finish;
    end
endmodule
