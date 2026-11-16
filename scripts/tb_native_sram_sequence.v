`timescale 1ns/1ps
module tb_sram_sequence;
reg clk=0; always #5 clk=~clk;
reg men=0,wen=0,ren=0,started=0;
reg [10:0] addr=0;reg [63:0] din=0,bm=0;
wire [63:0] dout;reg [63:0] captured,expected,previous;
wire [8:0] ct;assign ct[0]=clk;
wire [575:0] cell_captures;
genvar depth,bitidx;generate for(depth=0;depth<9;depth=depth+1)begin: depth_probe
 if(depth>0)begin: cb sg13g2_buf_1 b(.A(ct[depth-1]),.X(ct[depth]));end
 for(bitidx=0;bitidx<64;bitidx=bitidx+1)begin: data_bit
 sg13g2_dfrbpq_1 ff(.Q(cell_captures[depth*64+bitidx]),.D(dout[bitidx]),.RESET_B(1'b1),.CLK(ct[depth]));
 end
end endgenerate
reg [63:0] memory[0:2047];
integer cycles=0,i,k;reg [31:0] random_state=32'h91a42d37;
RM_IHPSG13_1P_2048x64_c2_bm_bist dut(.A_CLK(clk),.A_MEN(men),.A_WEN(wen),.A_REN(ren),.A_ADDR(addr),.A_DIN(din),.A_BM(bm),.A_DLY(1'b1),.A_DOUT(dout),.A_BIST_CLK(1'b0),.A_BIST_EN(1'b0),.A_BIST_MEN(1'b0),.A_BIST_WEN(1'b0),.A_BIST_REN(1'b0),.A_BIST_ADDR(11'b0),.A_BIST_DIN(64'b0),.A_BIST_BM(64'b0));
always @(posedge clk) captured<=dout;
always @(posedge clk) if(started) begin
 previous=expected;
 if(men && wen) for(k=0;k<64;k=k+1) if(bm[k]) memory[addr][k]=din[k];
 if(men && ren) begin
`ifdef MUTATE_ADDRESS
  expected=memory[addr^11'd1];
`else
  expected=memory[addr];
`endif
 end
 #1;
 if(dout!==expected || captured!==previous || cell_captures!=={9{previous}}) begin
  $display("SRAM_COMPARE_FLAGS dout=%b rtl=%b cells=%b",dout!==expected,captured!==previous,cell_captures!=={9{previous}});
  $display("SRAM_COMPARE_BITS dout=%b expected=%b rtl=%b previous=%b cells=%b replicated=%b",dout,expected,captured,previous,cell_captures,{9{previous}});
  for(k=0;k<9;k=k+1) $display("SRAM_COMPARE_BANK depth=%0d mismatch=%b bits=%b",k,cell_captures[k*64+:64]!==previous,cell_captures[k*64+:64]);
  $display("SRAM_SEQUENCE_FAIL cycle=%0d addr=%h got=%h expected=%h capture=%h previous=%h cell_captures=%h",cycles,addr,dout,expected,captured,previous,cell_captures);$fatal(1,"SRAM sequence or capture latency mismatch");
 end
 $display("SRAM_TRACE %0d %h %h %h",cycles,dout,captured,cell_captures);cycles=cycles+1;
end
task access(input m,input w,input r,input [10:0] ad,input [63:0] data,input [63:0] mask);
 begin @(negedge clk);started=1;men=m;wen=w;ren=r;addr=ad;din=data;bm=mask;end
endtask
initial begin
 access(1,0,1,11'd1023,0,0);
 for(i=0;i<2048;i=i+1) access(1,1,0,i,{32'h5a170000^i,32'hc3b20000+i},64'hffffffffffffffff);
 for(i=0;i<2048;i=i+1) access(1,0,1,i,0,0);
 for(i=0;i<2048;i=i+1) access(1,1,0,i,{32'h9e370000+i,32'h24680000^i},64'h00ff00ffff00ff00);
 for(i=0;i<2048;i=i+1) access(1,0,1,2047-i,0,0);
 for(i=0;i<4096;i=i+1) begin
  random_state={random_state[30:0],random_state[31]^random_state[21]^random_state[1]^random_state[0]};
  access((i%17)!=0,random_state[15],!random_state[15],random_state[10:0],{random_state,~random_state},(i%13)==0?64'b0:{random_state,random_state});
 end
 @(negedge clk);started=0;
 if(cycles!=12289)$fatal(1,"Wrong test census");
 $display("SRAM_SEQUENCE_PASS cycles=%0d",cycles);$finish;
end
initial begin #200000;$fatal(1,"Timeout");end
endmodule
