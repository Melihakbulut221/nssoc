`timescale 1ns/1ps
module tb;
parameter REFRESH=128;
reg clk=0;always #2 clk=~clk;
reg rst=0,link=0,training=0,p1=0,p2=0,ready=0;
reg [23:0] hl=0;reg [35:0] dl=0;
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
integer i,seed,frames=0,stalls=0,initialized=0,links=0,phases[0:2];
integer byteval,basis;reg [15:0] cs=0;reg [7:0] cd=0;
wire [15:0] joint,stateonly,dataonly;
soc_pcie_crc16_byte j(cs,cd,joint),s(cs,8'b0,stateonly),d(16'b0,cd,dataonly);
initial begin
 if(!$value$plusargs("SEED=%d",seed))seed=17;
 phases[0]=0;phases[1]=0;phases[2]=0;
 for(byteval=0;byteval<256;byteval=byteval+1)
 for(basis=0;basis<17;basis=basis+1)begin
  cs=basis==16 ? 0 : 16'b1<<basis;cd=byteval;#0.001;
  if(joint!==(stateonly^dataonly))$fatal(1,"CRC_LINEAR_MISMATCH");
 end
 for(i=0;i<40000;i=i+1)begin
  @(negedge clk);
  rst=(i%5000)>1;link=rst && (i%5000)>8;
  training=(i%503)<19; p1=(i%5000)>90;p2=(i%5000)>180;
  ready=(i%197)>=31 && (($random(seed)&7)!=0);
  if((i%701)<450)begin hl=$random(seed);dl={$random(seed),$random(seed)};end
  @(posedge clk);#0.1;
  if(a!==b || dut.crc!==ref_dut.crc || dut.index!==ref_dut.index)
   $fatal(1,"FC_DIFFERENTIAL_MISMATCH cycle=%0d a=%h b=%h",i,a,b);
  if(dut.active && dut.index<4 && dut.next_crc!==ref_dut.next_crc)
   $fatal(1,"FC_CRC_CONTRIBUTION_MISMATCH cycle=%0d",i);
  if(a[15])begin frames=frames+1;phases[a[14:13]]=phases[a[14:13]]+1;end
  if(a[0]&&!ready)stalls=stalls+1;
  if(a[77])initialized=initialized+1;
  if(!link)links=links+1;
 end
 if(frames<500||stalls<500||initialized<1000||links<10||
    phases[0]<3||phases[1]<3||phases[2]<100)$fatal(1,"INSUFFICIENT_COVERAGE");
 $display("FC_CRC_SNAPSHOT_PASS cycles=40000 frames=%0d stalls=%0d initialized=%0d phases=%0d/%0d/%0d",frames,stalls,initialized,phases[0],phases[1],phases[2]);
 $finish;
end
endmodule
