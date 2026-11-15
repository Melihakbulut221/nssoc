module lcrc_compare_formal(input clk, input rst_n,
 input [7:0] data, input sop,eop,error,valid,ready);
 wire ar,br,as,bs,ae,be,av,bv,ag,bg,ab,bb;
 wire [7:0] ad,bd;wire [11:0] aq,bq;wire [3:0] ax,bx;
 wire ao,bo;
 soc_pcie_lcrc_rx_ref a(.clk_i(clk),.rst_ni(rst_n),.rx_data_i(data),.rx_sop_i(sop),.rx_eop_i(eop),.rx_error_i(error),.rx_valid_i(valid),.rx_ready_o(ar),.tlp_data_o(ad),.tlp_sop_o(as),.tlp_eop_o(ae),.tlp_valid_o(av),.tlp_ready_i(ready),.sequence_o(aq),.reserved_o(ax),.packet_good_o(ag),.packet_bad_o(ab),.open_next_o(ao));
 soc_pcie_lcrc_rx b(.clk_i(clk),.rst_ni(rst_n),.rx_data_i(data),.rx_sop_i(sop),.rx_eop_i(eop),.rx_error_i(error),.rx_valid_i(valid),.rx_ready_o(br),.tlp_data_o(bd),.tlp_sop_o(bs),.tlp_eop_o(be),.tlp_valid_o(bv),.tlp_ready_i(ready),.sequence_o(bq),.reserved_o(bx),.packet_good_o(bg),.packet_bad_o(bb),.open_next_o(bo));
 always @* begin
  if ($initstate) assume(!rst_n);
  assert({ar,as,ae,av,ag,ab,aq,ax,ao}=={br,bs,be,bv,bg,bb,bq,bx,bo});
  if (av) assert(ad==bd);
 end
endmodule
