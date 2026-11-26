`timescale 1ns/1ps
module tb;
  reg txclk, rst;
  wire rxclkpad = txclk;
  wire resetpad = rst;
  wire txout;
  supply1 vp;
  supply0 vn;
  nssoc_chip dut(.VDD(vp), .IOVDD(vp), .VSS(vn), .IOVSS(vn),
    .pad_eth_tx_clk_i(rxclkpad), .pad_eth_gtx_clk_o(txout), .pad_rst_ni(resetpad));
  task check_path(input expected_clk, input expected_reset);
    begin
      #10;
      if ({dut.u_core.eth_tx_clk_i, dut.u_core.eth_gtx_clk_o, txout, dut.u_core.rst_ni}
          !== {expected_clk,expected_clk,expected_clk,expected_reset}) $fatal(1,"pad/core mismatch");
    end
  endtask
  initial begin
    txclk=0; rst=0; check_path(0,0);
    txclk=1; check_path(1,0);
    rst=1; check_path(1,1);
    txclk=0; check_path(0,1);
    $display("PASS mapped GMII TX clock pad loop and reset input"); $finish;
  end
endmodule
