`timescale 1ns/1ps
module tb_data;
    reg [7:0] stimulus;
    wire [7:0] pads = stimulus;
    supply1 vp;
    supply0 vn;
    nssoc_chip dut(.VDD(vp), .VSS(vn), .IOVDD(vp), .IOVSS(vn),
                   .pad_eth_rxd_i(pads));

    task check(input [7:0] value);
        begin
            stimulus = value;
            #5;
            if (dut.u_core.eth_rxd_i !== value)
                $fatal(1, "GMII RX input mismatch expected=%h observed=%h",
                       value, dut.u_core.eth_rxd_i);
        end
    endtask
    integer lane;
    initial begin
        check(8'h00);
        for (lane = 0; lane < 8; lane = lane + 1) begin
            check(8'h01 << lane);
            check(~(8'h01 << lane));
        end
        check(8'hff);
        $display("PASS GMII RX eight input lanes");
        $finish;
    end
endmodule
