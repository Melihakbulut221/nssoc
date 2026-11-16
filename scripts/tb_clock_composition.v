`timescale 1ns/1ps
module clock_composition;
reg clk=0;always #5 clk=~clk;
reg rst=0,enable=0;reg [7:0] din=0;reg [31:0] lfsr=32'h81234567;
wire gclk,bclk,bclk2;wire [7:0] buffer2_q1,direct_q2;wire [7:0] source_q,direct_q,gated_q,buffer_q,buffer2_q;
reg [7:0] source_ref,direct_ref,gated_ref;integer i,cycles=0,ideal_mismatches=0;
sg13g2_lgcp_1 icg(.GCLK(gclk),.GATE(enable),.CLK(clk));
sg13g2_buf_1 cb1(.X(bclk),.A(clk));sg13g2_buf_1 cb2(.X(bclk2),.A(bclk));
genvar k;generate for(k=0;k<8;k=k+1)begin: lane
 sg13g2_dfrbpq_1 source_ff(.Q(source_q[k]),.D(din[k]),.RESET_B(rst),.CLK(clk));
 sg13g2_dfrbpq_1 direct_ff(.Q(direct_q[k]),.D(source_q[k]),.RESET_B(rst),.CLK(clk));
 sg13g2_dfrbpq_1 gated_ff(.Q(gated_q[k]),.D(source_q[k]),.RESET_B(rst),.CLK(gclk));
 sg13g2_dfrbpq_1 buffer_ff(.Q(buffer_q[k]),.D(source_q[k]),.RESET_B(rst),.CLK(bclk));
 sg13g2_dfrbpq_2 buffer2_ff(.Q(buffer2_q[k]),.D(source_q[k]),.RESET_B(rst),.CLK(bclk2));
 sg13g2_dfrbpq_1 buffer2_ff1(.Q(buffer2_q1[k]),.D(source_q[k]),.RESET_B(rst),.CLK(bclk2));
 sg13g2_dfrbpq_2 direct_ff2(.Q(direct_q2[k]),.D(source_q[k]),.RESET_B(rst),.CLK(clk));
end endgenerate
always @(posedge clk or negedge rst) begin
 if(!rst)begin source_ref<=0;direct_ref<=0;gated_ref<=0;end
 else begin source_ref<=din;direct_ref<=source_ref;if(enable)gated_ref<=source_ref;end
end
always @(posedge clk)begin
 #1;
 if(source_q!==source_ref || direct_q!==direct_ref || gated_q!==gated_ref || buffer_q!==direct_ref || buffer2_q!==direct_ref || buffer2_q1!==direct_ref || direct_q2!==direct_ref)ideal_mismatches=ideal_mismatches+1;
 $display("COMPOSITION_TRACE %0d %h %h %h %h %h %h %h %h %h %h",cycles,source_q,direct_q,gated_q,buffer_q,buffer2_q,source_ref,direct_ref,gated_ref,buffer2_q1,direct_q2);
 cycles=cycles+1;
end
initial begin
 for(i=0;i<512;i=i+1)begin
  @(negedge clk);lfsr={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
  rst=(i%31)!=0;enable=(i%5)!=0;din=lfsr[7:0];
 end
 @(negedge clk);if(cycles!=513)$fatal(1,"Wrong composition census");
 $display("COMPOSITION_DONE cycles=%0d ideal_mismatches=%0d",cycles,ideal_mismatches);$finish;
end
initial begin #10000;$fatal(1,"Timeout");end
endmodule
