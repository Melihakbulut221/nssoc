module fc_miter # (parameter REFRESH=128)(
input wire clk,rst,link,training,p1,p2,ready,
input wire [23:0] hl,input wire [35:0] dl);
wire [77:0] a,b;
soc_pcie_fc_tx #(.REFRESH_CYCLES(REFRESH)) dut(
.clk_i(clk),.rst_ni(rst),.link_up_i(link),.training_i(training),
.peer_init1_done_i(p1),.peer_init2_seen_i(p2),.header_limit_i(hl),.data_limit_i(dl),
.local_init_done_o(a[77]),.local_init2_sent_o(a[76]),.sent_header_o(a[75:52]),.sent_data_o(a[51:16]),
.sent_valid_o(a[15]),.sent_phase_o(a[14:13]),.sent_class_o(a[12:11]),
.tx_data_o(a[10:3]),.tx_sop_o(a[2]),.tx_eop_o(a[1]),.tx_valid_o(a[0]),.tx_ready_i(ready));
soc_pcie_fc_tx_reference #(.REFRESH_CYCLES(REFRESH)) ref_dut(
.clk_i(clk),.rst_ni(rst),.link_up_i(link),.training_i(training),
.peer_init1_done_i(p1),.peer_init2_seen_i(p2),.header_limit_i(hl),.data_limit_i(dl),
.local_init_done_o(b[77]),.local_init2_sent_o(b[76]),.sent_header_o(b[75:52]),.sent_data_o(b[51:16]),
.sent_valid_o(b[15]),.sent_phase_o(b[14:13]),.sent_class_o(b[12:11]),
.tx_data_o(b[10:3]),.tx_sop_o(b[2]),.tx_eop_o(b[1]),.tx_valid_o(b[0]),.tx_ready_i(ready));

function [15:0] expected_data_crc;
 input [7:0] v;
 reg [15:0] c;integer k;
 begin
 c=0;
 for(k=0;k<8;k=k+1)c=(c>>1)^({16{c[0]^v[k]}}&16'hd008);
 expected_data_crc=c;
 end
endfunction
always @* begin
 assert(a==b);
 assert(dut.crc==ref_dut.crc);
 assert(dut.index==ref_dut.index);
 assert(dut.active==ref_dut.active);
 assert(dut.phase==ref_dut.phase);
 assert(dut.class_index==ref_dut.class_index);
 assert(dut.refresh==ref_dut.refresh);
 assert(dut.first_triplet==ref_dut.first_triplet);
 assert(dut.second_triplet==ref_dut.second_triplet);
 assert(dut.header==ref_dut.header);
 assert(dut.data_credit==ref_dut.data_credit);
 assert(dut.frame_phase==ref_dut.frame_phase);
 assert(dut.frame_class==ref_dut.frame_class);
 assert(dut.index<=5 && ref_dut.index<=5);
 assert(dut.phase<=2 && ref_dut.phase<=2);
 assert(dut.class_index<=2 && ref_dut.class_index<=2);
 assert(dut.frame_phase<=2 && dut.frame_class<=2);
 if(dut.active)begin
  assert(dut.payload_crc0==expected_data_crc((dut.frame_phase==0 ? 8'h40 : dut.frame_phase==1 ? 8'hc0 : 8'h80)|{2'b00,dut.frame_class,4'b0000}));
  assert(dut.payload_crc1==expected_data_crc({2'b00,dut.header[7:2]}));
  assert(dut.payload_crc2==expected_data_crc({dut.header[1:0],2'b00,dut.data_credit[11:8]}));
  assert(dut.payload_crc3==expected_data_crc(dut.data_credit[7:0]));
 end
end
endmodule
