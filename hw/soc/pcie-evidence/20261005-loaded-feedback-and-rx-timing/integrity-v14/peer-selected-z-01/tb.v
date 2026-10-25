module old_read(input[4:0]read_ptr,committed,output reg[2:0]read_count,output reg[127:0]read_data,output reg[15:0]read_keep,output reg[15:0]read_sop,output reg[15:0]read_eop,output reg[15:0]read_dllp,output reg[47:0]read_sequence);
localparam RING_DWORDS=16,PW=5;
reg slot_verdict[0:RING_DWORDS-1];
reg[31:0]slot_data[0:RING_DWORDS-1];
reg[3:0]slot_keep[0:RING_DWORDS-1];
reg[3:0]slot_sop[0:RING_DWORDS-1];
reg[3:0]slot_eop[0:RING_DWORDS-1];
reg[3:0]slot_dllp[0:RING_DWORDS-1];
reg[11:0]slot_sequence[0:RING_DWORDS-1]; integer r,read_address;
 always @* begin
   read_count=(committed>=4)?3'd4:committed;
   read_data=0;read_keep=0;read_sop=0;read_eop=0;read_dllp=0;read_sequence=0;
   for(r=0;r<4;r=r+1) begin
     read_address=(read_ptr+r)&(RING_DWORDS-1);
     if(r<read_count && slot_keep[read_address]!=0 && slot_verdict[read_address]) begin
       read_data[r*32+:32]=slot_data[read_address];
       read_keep[r*4+:4]=slot_keep[read_address];
       read_sop[r*4+:4]=slot_sop[read_address];
       read_eop[r*4+:4]=slot_eop[read_address];
       read_dllp[r*4+:4]=slot_dllp[read_address];
       read_sequence[r*12+:12]=slot_sequence[read_address];
     end
   end
 end
endmodule
module new_read(input[4:0]read_ptr,committed,output reg[2:0]read_count,output reg[127:0]read_data,output reg[15:0]read_keep,output reg[15:0]read_sop,output reg[15:0]read_eop,output reg[15:0]read_dllp,output reg[47:0]read_sequence);
localparam RING_DWORDS=16,PW=5;
reg slot_verdict[0:RING_DWORDS-1];
reg[31:0]slot_data[0:RING_DWORDS-1];
reg[3:0]slot_keep[0:RING_DWORDS-1];
reg[3:0]slot_sop[0:RING_DWORDS-1];
reg[3:0]slot_eop[0:RING_DWORDS-1];
reg[3:0]slot_dllp[0:RING_DWORDS-1];
reg[11:0]slot_sequence[0:RING_DWORDS-1]; // BEGIN V14 PARALLEL CONSTANT-SLOT READ
 // Each physical slot contributes through one shared address/valid decode.
 // Exactly one slot can match each lane; OR combines disjoint contributions.
 // Procedural if preserves the old X-as-not-true masking behavior for unknown
 // keep/verdict/select conditions. The ring contents and all control stay V11.
 integer r,read_address,read_slot;
 always @* begin
   read_count=(committed>=4)?3'd4:committed;
   read_data=0;read_keep=0;read_sop=0;read_eop=0;read_dllp=0;read_sequence=0;
   for(r=0;r<4;r=r+1) begin
     read_address=(read_ptr+r)&(RING_DWORDS-1);
     for(read_slot=0;read_slot<RING_DWORDS;read_slot=read_slot+1) begin
       if(r<read_count && read_address==read_slot && slot_keep[read_slot]!=0 && slot_verdict[read_slot]) begin
         read_data[r*32+:32]=read_data[r*32+:32]|slot_data[read_slot];
         read_keep[r*4+:4]=read_keep[r*4+:4]|slot_keep[read_slot];
         read_sop[r*4+:4]=read_sop[r*4+:4]|slot_sop[read_slot];
         read_eop[r*4+:4]=read_eop[r*4+:4]|slot_eop[read_slot];
         read_dllp[r*4+:4]=read_dllp[r*4+:4]|slot_dllp[read_slot];
         read_sequence[r*12+:12]=read_sequence[r*12+:12]|slot_sequence[read_slot];
       end
     end
   end
 end
 // END V14 PARALLEL CONSTANT-SLOT READ
endmodule
module tb; reg[4:0]ptr=0,committed=1; wire[2:0]a_count,b_count;
wire[127:0]a_data,b_data;
wire[15:0]a_keep,b_keep;
wire[15:0]a_sop,b_sop;
wire[15:0]a_eop,b_eop;
wire[15:0]a_dllp,b_dllp;
wire[47:0]a_sequence,b_sequence;
old_read a(.read_ptr(ptr),.committed(committed),.read_count(a_count),.read_data(a_data),.read_keep(a_keep),.read_sop(a_sop),.read_eop(a_eop),.read_dllp(a_dllp),.read_sequence(a_sequence));
new_read b(.read_ptr(ptr),.committed(committed),.read_count(b_count),.read_data(b_data),.read_keep(b_keep),.read_sop(b_sop),.read_eop(b_eop),.read_dllp(b_dllp),.read_sequence(b_sequence));
integer k;initial begin
for(k=0;k<16;k=k+1)begin a.slot_verdict[k]=1;b.slot_verdict[k]=1;
a.slot_data[k]=32'h0;b.slot_data[k]=a.slot_data[k];
a.slot_keep[k]=4'hf;b.slot_keep[k]=a.slot_keep[k];
a.slot_sop[k]=4'h0;b.slot_sop[k]=a.slot_sop[k];
a.slot_eop[k]=4'h0;b.slot_eop[k]=a.slot_eop[k];
a.slot_dllp[k]=4'h0;b.slot_dllp[k]=a.slot_dllp[k];
a.slot_sequence[k]=12'h0;b.slot_sequence[k]=a.slot_sequence[k];
end
a.slot_data[0]=32'b0000000000000000000000000000000z;b.slot_data[0]=a.slot_data[0];#1;
if(a_data[0]!==1'bz || b_data[0]!==1'bx)$fatal(1,"UNEXPECTED_Z_RESULT data");
$display("CONFIRMED_SELECTED_Z_MISMATCH field=data old=%b new=%b",a_data[0],b_data[0]);
for(k=0;k<16;k=k+1)begin a.slot_verdict[k]=1;b.slot_verdict[k]=1;
a.slot_data[k]=32'h0;b.slot_data[k]=a.slot_data[k];
a.slot_keep[k]=4'hf;b.slot_keep[k]=a.slot_keep[k];
a.slot_sop[k]=4'h0;b.slot_sop[k]=a.slot_sop[k];
a.slot_eop[k]=4'h0;b.slot_eop[k]=a.slot_eop[k];
a.slot_dllp[k]=4'h0;b.slot_dllp[k]=a.slot_dllp[k];
a.slot_sequence[k]=12'h0;b.slot_sequence[k]=a.slot_sequence[k];
end
a.slot_keep[0]=4'b001z;b.slot_keep[0]=a.slot_keep[0];#1;
if(a_keep[0]!==1'bz || b_keep[0]!==1'bx)$fatal(1,"UNEXPECTED_Z_RESULT keep");
$display("CONFIRMED_SELECTED_Z_MISMATCH field=keep old=%b new=%b",a_keep[0],b_keep[0]);
for(k=0;k<16;k=k+1)begin a.slot_verdict[k]=1;b.slot_verdict[k]=1;
a.slot_data[k]=32'h0;b.slot_data[k]=a.slot_data[k];
a.slot_keep[k]=4'hf;b.slot_keep[k]=a.slot_keep[k];
a.slot_sop[k]=4'h0;b.slot_sop[k]=a.slot_sop[k];
a.slot_eop[k]=4'h0;b.slot_eop[k]=a.slot_eop[k];
a.slot_dllp[k]=4'h0;b.slot_dllp[k]=a.slot_dllp[k];
a.slot_sequence[k]=12'h0;b.slot_sequence[k]=a.slot_sequence[k];
end
a.slot_sop[0]=4'b000z;b.slot_sop[0]=a.slot_sop[0];#1;
if(a_sop[0]!==1'bz || b_sop[0]!==1'bx)$fatal(1,"UNEXPECTED_Z_RESULT sop");
$display("CONFIRMED_SELECTED_Z_MISMATCH field=sop old=%b new=%b",a_sop[0],b_sop[0]);
for(k=0;k<16;k=k+1)begin a.slot_verdict[k]=1;b.slot_verdict[k]=1;
a.slot_data[k]=32'h0;b.slot_data[k]=a.slot_data[k];
a.slot_keep[k]=4'hf;b.slot_keep[k]=a.slot_keep[k];
a.slot_sop[k]=4'h0;b.slot_sop[k]=a.slot_sop[k];
a.slot_eop[k]=4'h0;b.slot_eop[k]=a.slot_eop[k];
a.slot_dllp[k]=4'h0;b.slot_dllp[k]=a.slot_dllp[k];
a.slot_sequence[k]=12'h0;b.slot_sequence[k]=a.slot_sequence[k];
end
a.slot_eop[0]=4'b000z;b.slot_eop[0]=a.slot_eop[0];#1;
if(a_eop[0]!==1'bz || b_eop[0]!==1'bx)$fatal(1,"UNEXPECTED_Z_RESULT eop");
$display("CONFIRMED_SELECTED_Z_MISMATCH field=eop old=%b new=%b",a_eop[0],b_eop[0]);
for(k=0;k<16;k=k+1)begin a.slot_verdict[k]=1;b.slot_verdict[k]=1;
a.slot_data[k]=32'h0;b.slot_data[k]=a.slot_data[k];
a.slot_keep[k]=4'hf;b.slot_keep[k]=a.slot_keep[k];
a.slot_sop[k]=4'h0;b.slot_sop[k]=a.slot_sop[k];
a.slot_eop[k]=4'h0;b.slot_eop[k]=a.slot_eop[k];
a.slot_dllp[k]=4'h0;b.slot_dllp[k]=a.slot_dllp[k];
a.slot_sequence[k]=12'h0;b.slot_sequence[k]=a.slot_sequence[k];
end
a.slot_dllp[0]=4'b000z;b.slot_dllp[0]=a.slot_dllp[0];#1;
if(a_dllp[0]!==1'bz || b_dllp[0]!==1'bx)$fatal(1,"UNEXPECTED_Z_RESULT dllp");
$display("CONFIRMED_SELECTED_Z_MISMATCH field=dllp old=%b new=%b",a_dllp[0],b_dllp[0]);
for(k=0;k<16;k=k+1)begin a.slot_verdict[k]=1;b.slot_verdict[k]=1;
a.slot_data[k]=32'h0;b.slot_data[k]=a.slot_data[k];
a.slot_keep[k]=4'hf;b.slot_keep[k]=a.slot_keep[k];
a.slot_sop[k]=4'h0;b.slot_sop[k]=a.slot_sop[k];
a.slot_eop[k]=4'h0;b.slot_eop[k]=a.slot_eop[k];
a.slot_dllp[k]=4'h0;b.slot_dllp[k]=a.slot_dllp[k];
a.slot_sequence[k]=12'h0;b.slot_sequence[k]=a.slot_sequence[k];
end
a.slot_sequence[0]=12'b00000000000z;b.slot_sequence[0]=a.slot_sequence[0];#1;
if(a_sequence[0]!==1'bz || b_sequence[0]!==1'bx)$fatal(1,"UNEXPECTED_Z_RESULT sequence");
$display("CONFIRMED_SELECTED_Z_MISMATCH field=sequence old=%b new=%b",a_sequence[0],b_sequence[0]);
$finish;end endmodule
