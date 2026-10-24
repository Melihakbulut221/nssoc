module reference(
 input clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input active_o,enabled,step,fault_now,ending,
 input [4:0] write_ptr,commit_n,
 input [127:0] write_data,
 input [15:0] write_keep,write_sop,write_eop,write_dllp,
 input [47:0] write_sequence,
 input [19:0] write_tags,verdict_tags,
 input [3:0] verdict_enable,verdict_value);
 localparam RING_DWORDS=16,PW=5;
 reg [31:0] slot_data [0:RING_DWORDS-1];
 reg [3:0] slot_keep [0:RING_DWORDS-1];
 reg [3:0] slot_sop [0:RING_DWORDS-1];
 reg [3:0] slot_eop [0:RING_DWORDS-1];
 reg [3:0] slot_dllp [0:RING_DWORDS-1];
 reg [11:0] slot_sequence [0:RING_DWORDS-1];
 reg [PW-1:0] slot_tag [0:RING_DWORDS-1];
 // Tags use the SOP's extended write pointer. Two ring spans prevent reuse
 // while an earlier packet's tail can remain after its SOP slot has retired.
 reg verdict [0:2*RING_DWORDS-1];
 reg slot_verdict [0:RING_DWORDS-1];
 reg [PW-1:0] visible_commit_ptr;

 // BEGIN V6 SHARED OLD VERDICT READS
 // Four physical read values are common to every slot update. Explicit
 // wires avoid a whole verdict-array sensitivity expansion in every slot.
 wire [3:0] cache_write_old_verdict;
 genvar cache_read_lane;
 generate for(cache_read_lane=0;cache_read_lane<4;cache_read_lane=cache_read_lane+1) begin:cache_reads
   assign cache_write_old_verdict[cache_read_lane]=verdict[write_tags[cache_read_lane*PW+:PW]];
 end endgenerate
 // END V6 SHARED OLD VERDICT READS
 // BEGIN V5 SLOT VERDICT CACHE
 // The stored bit equals verdict[slot_tag] after every initialized slot write.
 // Simultaneous writes select the NEW slot tag, then apply the four verdict
 // writes in exactly the original last-writer order. Nonwritten slots follow
 // matching verdict updates. V22 permits cache-only writes in a fault-invalidated epoch.
 genvar cache_slot;
 generate for(cache_slot=0;cache_slot<RING_DWORDS;cache_slot=cache_slot+1) begin:verdict_cache
   // BEGIN V7 SCALAR SLOT READS
   // Constant array elements are the same values. Explicit wires keep
   // simulator @* sensitivity local to these two elements.
   wire [PW-1:0] resident_tag=slot_tag[cache_slot];
   wire resident_verdict=slot_verdict[cache_slot];
   // END V7 SCALAR SLOT READS
   reg [PW-1:0] effective_tag;
   reg next_value;
   integer write_lane,verdict_lane;
   always @* begin
     effective_tag=resident_tag;next_value=resident_verdict;
     for(write_lane=0;write_lane<4;write_lane=write_lane+1) begin
       if(((write_ptr+write_lane)&(RING_DWORDS-1))==cache_slot) begin
         effective_tag=write_tags[write_lane*PW+:PW];
         next_value=cache_write_old_verdict[write_lane];
       end
     end
     for(verdict_lane=0;verdict_lane<4;verdict_lane=verdict_lane+1) begin
       if(verdict_enable[verdict_lane] && verdict_tags[verdict_lane*PW+:PW]==effective_tag)
         next_value=verdict_value[verdict_lane];
     end
   end
   // The original ring metadata and verdict arrays have no reset; pointer and
   // valid resets quarantine unwritten entries. Keep the same reset boundary.
   always @(posedge clk_i) begin
     if(step) slot_verdict[cache_slot]<=next_value; // V22 invalid cache content is quarantined.
   end
 end endgenerate
 // END V5 SLOT VERDICT CACHE
 integer w;
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) visible_commit_ptr<=0;
   else if(flush_i || stream_start_i) visible_commit_ptr<=0;
   else if((stream_abort_i && active_o) || fault_now) visible_commit_ptr<=0;
   else if(active_o) begin
       if(step) begin
         visible_commit_ptr<=commit_n;
         for(w=0;w<4;w=w+1) begin
           slot_data[(write_ptr+w)&(RING_DWORDS-1)]<=write_data[w*32+:32];
           slot_keep[(write_ptr+w)&(RING_DWORDS-1)]<=write_keep[w*4+:4];
           slot_sop[(write_ptr+w)&(RING_DWORDS-1)]<=write_sop[w*4+:4];
           slot_eop[(write_ptr+w)&(RING_DWORDS-1)]<=write_eop[w*4+:4];
           slot_dllp[(write_ptr+w)&(RING_DWORDS-1)]<=write_dllp[w*4+:4];
           slot_sequence[(write_ptr+w)&(RING_DWORDS-1)]<=write_sequence[w*12+:12];
           slot_tag[(write_ptr+w)&(RING_DWORDS-1)]<=write_tags[w*PW+:PW];
           if(verdict_enable[w]) verdict[verdict_tags[w*PW+:PW]]<=verdict_value[w];
         end
       end

   end
 end
endmodule
module candidate(
 input clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input active_o,enabled,step,fault_now,ending,
 input [4:0] write_ptr,commit_n,
 input [127:0] write_data,
 input [15:0] write_keep,write_sop,write_eop,write_dllp,
 input [47:0] write_sequence,
 input [19:0] write_tags,verdict_tags,
 input [3:0] verdict_enable,verdict_value);
 localparam RING_DWORDS=16,PW=5;
 reg [31:0] slot_data [0:RING_DWORDS-1];
 reg [3:0] slot_keep [0:RING_DWORDS-1];
 reg [3:0] slot_sop [0:RING_DWORDS-1];
 reg [3:0] slot_eop [0:RING_DWORDS-1];
 reg [3:0] slot_dllp [0:RING_DWORDS-1];
 reg [11:0] slot_sequence [0:RING_DWORDS-1];
 reg [PW-1:0] slot_tag [0:RING_DWORDS-1];
 // Tags use the SOP's extended write pointer. Two ring spans prevent reuse
 // while an earlier packet's tail can remain after its SOP slot has retired.
 reg verdict [0:2*RING_DWORDS-1];
 reg slot_verdict [0:RING_DWORDS-1];
 // BEGIN V25 REGISTERED PARSER TO RING COMMAND
 // The parser reserves addresses immediately. Ring contents and their visible
 // commit frontier advance together when the previous command is applied.
 reg command_valid;
 reg [PW-1:0] command_address,command_commit,visible_commit_ptr;
 reg [127:0] command_data;
 reg [15:0] command_keep,command_sop,command_eop,command_dllp;
 reg [47:0] command_sequence;
 reg [4*PW-1:0] command_tags,command_verdict_tags;
 reg [3:0] command_verdict_enable,command_verdict_value;
 // END V25 REGISTERED PARSER TO RING COMMAND
 // BEGIN V6 SHARED OLD VERDICT READS
 // Four physical read values are common to every slot update. Explicit
 // wires avoid a whole verdict-array sensitivity expansion in every slot.
 wire [3:0] cache_write_old_verdict;
 genvar cache_read_lane;
 generate for(cache_read_lane=0;cache_read_lane<4;cache_read_lane=cache_read_lane+1) begin:cache_reads
   assign cache_write_old_verdict[cache_read_lane]=verdict[command_tags[cache_read_lane*PW+:PW]];
 end endgenerate
 // END V6 SHARED OLD VERDICT READS
 // BEGIN V5 SLOT VERDICT CACHE
 // The stored bit equals verdict[slot_tag] after every initialized slot write.
 // Simultaneous writes select the NEW slot tag, then apply the four verdict
 // writes in exactly the original last-writer order. Nonwritten slots follow
 // matching verdict updates. V22 permits cache-only writes in a fault-invalidated epoch.
 genvar cache_slot;
 generate for(cache_slot=0;cache_slot<RING_DWORDS;cache_slot=cache_slot+1) begin:verdict_cache
   // BEGIN V7 SCALAR SLOT READS
   // Constant array elements are the same values. Explicit wires keep
   // simulator @* sensitivity local to these two elements.
   wire [PW-1:0] resident_tag=slot_tag[cache_slot];
   wire resident_verdict=slot_verdict[cache_slot];
   // END V7 SCALAR SLOT READS
   reg [PW-1:0] effective_tag;
   reg next_value;
   integer write_lane,verdict_lane;
   always @* begin
     effective_tag=resident_tag;next_value=resident_verdict;
     for(write_lane=0;write_lane<4;write_lane=write_lane+1) begin
       if(((command_address+write_lane)&(RING_DWORDS-1))==cache_slot) begin
         effective_tag=command_tags[write_lane*PW+:PW];
         next_value=cache_write_old_verdict[write_lane];
       end
     end
     for(verdict_lane=0;verdict_lane<4;verdict_lane=verdict_lane+1) begin
       if(command_verdict_enable[verdict_lane] && command_verdict_tags[verdict_lane*PW+:PW]==effective_tag)
         next_value=command_verdict_value[verdict_lane];
     end
   end
   // The original ring metadata and verdict arrays have no reset; pointer and
   // valid resets quarantine unwritten entries. Keep the same reset boundary.
   always @(posedge clk_i) begin
     if(enabled && active_o && command_valid) slot_verdict[cache_slot]<=next_value; // V25 fault-invalid cache remains quarantined.
   end
 end endgenerate
 // END V5 SLOT VERDICT CACHE
 integer command_lane;
 // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP
 // Unqualified payload capture may change inaccessible bits on a fault edge.
 // Validity follows the original explicit procedural fault priority; a new
 // owner overwrites every field. A bubble consumes the old command only once.
 always @(posedge clk_i) begin
   if(step) begin
     command_address<=write_ptr;command_commit<=commit_n;
     command_data<=write_data;command_keep<=write_keep;
     command_sop<=write_sop;command_eop<=write_eop;command_dllp<=write_dllp;
     command_sequence<=write_sequence;command_tags<=write_tags;
     command_verdict_enable<=verdict_enable;
     command_verdict_tags<=verdict_tags;command_verdict_value<=verdict_value;
   end
 end
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) command_valid<=0;
   else if(flush_i || stream_start_i) command_valid<=0;
   else if((stream_abort_i && active_o) || fault_now) command_valid<=0;
   else if(active_o) begin
     // Match the procedural apply gate, including unknown external controls:
     // if enabled is X, neither apply nor replacement occurs; retain ownership.
     if(enabled) begin
       command_valid<=0;
       if(step) command_valid<=1;
     end
   end
 end
 // END V25 COMMAND CAPTURE AND EPOCH OWNERSHIP
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) visible_commit_ptr<=0;
   else if(flush_i || stream_start_i) visible_commit_ptr<=0;
   else if((stream_abort_i && active_o) || fault_now) visible_commit_ptr<=0;
   else if(active_o) begin
       // BEGIN V25 APPLY OLD COMMAND
       // This must run during parser bubbles and pending EDS drain. NBA reads
       // the old complete command while capture can replace it on this edge.
       if(enabled && command_valid) begin
         visible_commit_ptr<=command_commit;
         for(command_lane=0;command_lane<4;command_lane=command_lane+1) begin
           slot_data[(command_address+command_lane)&(RING_DWORDS-1)]<=command_data[command_lane*32+:32];
           slot_keep[(command_address+command_lane)&(RING_DWORDS-1)]<=command_keep[command_lane*4+:4];
           slot_sop[(command_address+command_lane)&(RING_DWORDS-1)]<=command_sop[command_lane*4+:4];
           slot_eop[(command_address+command_lane)&(RING_DWORDS-1)]<=command_eop[command_lane*4+:4];
           slot_dllp[(command_address+command_lane)&(RING_DWORDS-1)]<=command_dllp[command_lane*4+:4];
           slot_sequence[(command_address+command_lane)&(RING_DWORDS-1)]<=command_sequence[command_lane*12+:12];
           slot_tag[(command_address+command_lane)&(RING_DWORDS-1)]<=command_tags[command_lane*PW+:PW];
           if(command_verdict_enable[command_lane]) verdict[command_verdict_tags[command_lane*PW+:PW]]<=command_verdict_value[command_lane];
         end
       end
       // END V25 APPLY OLD COMMAND
   end
 end
endmodule

module tb;
 reg clk_i=0,rst_ni=0,flush_i=0,stream_start_i=0,stream_abort_i=0;
 reg active_o=1,drive=0,fault_now=0,ending=0;
 wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;
 wire step=enabled && active_o && drive && !ending;
 reg [4:0] write_ptr=0,commit_n=0;
 reg [127:0] write_data=0;
 reg [15:0] write_keep=0,write_sop=0,write_eop=0,write_dllp=0;
 reg [47:0] write_sequence=0;
 reg [19:0] write_tags=0,verdict_tags=0;
 reg [3:0] verdict_enable=0,verdict_value=0;
 reference ref_dut(.*);
 candidate dut(.*);
 reg [64:0] saved_slot[0:15];
 reg saved_cache[0:15],saved_verdict[0:31];
 reg [4:0] saved_commit;
 integer i,t,l,seed=19373,comparisons=0,bubbles=0,replace_count=0,ending_apply=0;
 integer old_valid,epoch_checks=0,previous_verdict=0,duplicate_priority=0,wraps=0;
 integer unknown_holds=0,unknown_fault_applies=0;
 reg [4:0] last_address=0;
 reg [64:0] held_slot[0:15];reg held_cache[0:15],held_verdict[0:31];
 reg [4:0] held_commit;
 task tick;
 input compare_arrays;
 begin
  clk_i=0;#1;
  for(i=0;i<16;i=i+1) begin
   saved_slot[i]={ref_dut.slot_data[i],ref_dut.slot_keep[i],ref_dut.slot_sop[i],
    ref_dut.slot_eop[i],ref_dut.slot_dllp[i],ref_dut.slot_sequence[i],ref_dut.slot_tag[i]};
   saved_cache[i]=ref_dut.slot_verdict[i];
  end
  for(i=0;i<32;i=i+1) saved_verdict[i]=ref_dut.verdict[i];
  saved_commit=ref_dut.visible_commit_ptr;old_valid=dut.command_valid;
  if(compare_arrays && old_valid===1 && step===1) replace_count=replace_count+1;
  if(compare_arrays && old_valid===1 && step===0) bubbles=bubbles+1;
  if(compare_arrays && old_valid===1 && ending===1) ending_apply=ending_apply+1;
  if(compare_arrays && step===1) begin
   if(write_ptr<last_address) wraps=wraps+1;
   last_address=write_ptr;
  end
  clk_i=1;#1;
  if(compare_arrays) begin
   for(i=0;i<16;i=i+1) begin
    if({dut.slot_data[i],dut.slot_keep[i],dut.slot_sop[i],dut.slot_eop[i],
       dut.slot_dllp[i],dut.slot_sequence[i],dut.slot_tag[i]} !== saved_slot[i])
      $fatal(1,"V25_COMMAND_SLOT_DELAY trial=%0d slot=%0d",t,i);
    if(dut.slot_verdict[i] !== saved_cache[i])
      $fatal(1,"V25_COMMAND_CACHE_DELAY trial=%0d slot=%0d",t,i);
   end
   for(i=0;i<32;i=i+1) if(dut.verdict[i] !== saved_verdict[i])
     $fatal(1,"V25_COMMAND_VERDICT_DELAY trial=%0d tag=%0d",t,i);
   if(dut.visible_commit_ptr !== saved_commit)
     $fatal(1,"V25_COMMAND_COMMIT_DELAY trial=%0d",t);
   if(dut.command_valid !== (step===1'b1))
     $fatal(1,"V25_COMMAND_BUBBLE_VALID trial=%0d",t);
   comparisons=comparisons+1;
  end
  clk_i=0;#1;
 end
 endtask
 initial begin
  tick(0);rst_ni=1;
  for(t=0;t<4096;t=t+1) begin
   drive=(t%7)!=6;ending=0;
   write_ptr=t*4;commit_n=write_ptr+4;
   write_data={$random(seed),$random(seed),$random(seed),$random(seed)};
   write_keep=$random(seed);write_sop=$random(seed);write_eop=$random(seed);
   write_dllp=$random(seed);write_sequence={$random(seed),$random(seed)};
   for(l=0;l<4;l=l+1) begin
    write_tags[l*5+:5]=(t/3+l)%32;
    verdict_tags[l*5+:5]=(t/5+(l%2))%32;
   end
   verdict_enable=t;verdict_value=t>>4;
   // Literal X/Z in every command payload/metadata class. Unknown verdict
   // enable/tag values retain the actual original procedural-if semantics.
   case(t%16)
    0:write_data[13]=1'bz;
    1:write_keep[7]=1'bx;
    2:write_sop[2]=1'bz;
    3:write_eop[15]=1'bx;
    4:write_dllp[9]=1'bz;
    5:write_sequence[33]=1'bz;
    6:write_tags[0]=1'bx;
    7:verdict_tags[8]=1'bz;
    8:verdict_enable[1]=1'bx;
    9:verdict_value[2]=1'bz;
    10:commit_n[0]=1'bx;
    default:begin end
   endcase
   tick(1);
  end
  // A command writes one verdict tag four times; lane3 wins. The very next
  // command has no verdict write and must read that previous command's value
  // for four newly owned slots. No testbench writes any DUT array directly.
  drive=1;write_ptr=0;commit_n=4;write_tags={4{5'd5}};
  verdict_tags={4{5'd5}};verdict_enable=4'b1111;verdict_value=4'b1010;
  tick(1);
  write_ptr=4;commit_n=8;verdict_enable=0;
  tick(1);
  if(dut.verdict[5]!==1) $fatal(1,"V25_COMMAND_DUPLICATE_PRIORITY");
  duplicate_priority=duplicate_priority+1;
  drive=0;tick(1);
  for(l=4;l<8;l=l+1) begin
   if(dut.slot_verdict[l]!==1) $fatal(1,"V25_COMMAND_PREVIOUS_VERDICT_LOOKUP");
   previous_verdict=previous_verdict+1;
  end
  // Explicitly capture a pending final command, then apply it while ending.
  drive=1;ending=0;write_ptr=4;commit_n=8;write_data=~write_data;
  write_keep=16'hffff;write_tags=20'habcde;
  tick(1);drive=0;ending=1;tick(1);ending=0;tick(1);
  if(comparisons!=4102 || bubbles==0 || replace_count==0 || ending_apply!=1 ||
     previous_verdict!=4 || duplicate_priority!=1 || wraps<400)
   $fatal(1,"V25_COMMAND_REQUIRED_RELATION_WITNESS");
  // Epoch controls are a separate validity/frontier property. Discarded raw
  // array contents need not equal the old immediate writer after a fault.
  for(t=0;t<5;t=t+1) begin
   drive=1;write_data=128'h123456789abcdef;tick(0);
   if(dut.command_valid!==1) $fatal(1,"V25_COMMAND_PENDING_EPOCH_WITNESS");
   drive=0;
   case(t)
    0:flush_i=1;
    1:stream_start_i=1;
    2:stream_abort_i=1;
    3:fault_now=1;
    4:rst_ni=0;
   endcase
   tick(0);
   if(dut.command_valid!==0 || dut.visible_commit_ptr!==0)
    $fatal(1,"V25_COMMAND_EPOCH_DISCARD kind=%0d",t);
   flush_i=0;stream_start_i=0;stream_abort_i=0;fault_now=0;rst_ni=1;
   tick(0);
   if(dut.command_valid!==0 || dut.visible_commit_ptr!==0)
    $fatal(1,"V25_COMMAND_STALE_EPOCH_REPLAY kind=%0d",t);
   epoch_checks=epoch_checks+1;
  end
  // Original procedural if semantics: an unknown external inhibit makes
  // enabled unknown, so no write step is accepted. A pending owner must be
  // held, not consumed. Test X and Z for flush/start/abort/reset/active.
  for(t=0;t<10;t=t+1) begin
   drive=1;write_ptr=8;commit_n=12;write_data={4{32'h12340000+t}};
   write_keep=16'hffff;write_tags={4{5'd7}};verdict_enable=0;tick(0);
   if(dut.command_valid!==1) $fatal(1,"V25_COMMAND_UNKNOWN_PENDING_WITNESS");
   drive=0;
   for(i=0;i<16;i=i+1) begin
    held_slot[i]={dut.slot_data[i],dut.slot_keep[i],dut.slot_sop[i],dut.slot_eop[i],
      dut.slot_dllp[i],dut.slot_sequence[i],dut.slot_tag[i]};
    held_cache[i]=dut.slot_verdict[i];
   end
   for(i=0;i<32;i=i+1) held_verdict[i]=dut.verdict[i];
   held_commit=dut.visible_commit_ptr;
   case(t/2)
    0:flush_i=(t%2)?1'bz:1'bx;
    1:stream_start_i=(t%2)?1'bz:1'bx;
    2:stream_abort_i=(t%2)?1'bz:1'bx;
    3:rst_ni=(t%2)?1'bz:1'bx;
    4:active_o=(t%2)?1'bz:1'bx;
   endcase
   tick(0);
   if(dut.command_valid!==1 || dut.visible_commit_ptr!==held_commit)
    $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_HOLD kind=%0d",t);
   for(i=0;i<16;i=i+1) begin
    if({dut.slot_data[i],dut.slot_keep[i],dut.slot_sop[i],dut.slot_eop[i],
       dut.slot_dllp[i],dut.slot_sequence[i],dut.slot_tag[i]}!==held_slot[i] ||
       dut.slot_verdict[i]!==held_cache[i]) $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_WRITES");
   end
   for(i=0;i<32;i=i+1) if(dut.verdict[i]!==held_verdict[i])
     $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_VERDICT");
   flush_i=0;stream_start_i=0;stream_abort_i=0;rst_ni=1;active_o=1;tick(0);
   if(dut.command_valid!==0 || dut.visible_commit_ptr!==12 ||
      dut.slot_data[8] !== (32'h12340000+t))
     $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_RESUME");
   unknown_holds=unknown_holds+1;
  end
  // An unknown fault expression falls through the original procedural branch;
  // enabled remains true, so the pending command applies and is consumed.
  for(t=0;t<2;t=t+1) begin
   drive=1;write_ptr=12;commit_n=16;write_data={4{32'habcd0000+t}};tick(0);
   drive=0;fault_now=t?1'bz:1'bx;tick(0);
   if(dut.command_valid!==0 || dut.visible_commit_ptr!==16 ||
      dut.slot_data[12] !== (32'habcd0000+t))
    $fatal(1,"V25_COMMAND_UNKNOWN_FAULT_FALLTHROUGH");
   fault_now=0;unknown_fault_applies=unknown_fault_applies+1;
  end
  $display("V25_COMMAND_RELATION_PASS comparisons=%0d bubbles=%0d replace=%0d ending=%0d epochs=%0d previous_verdict=%0d duplicate=%0d wraps=%0d unknown_holds=%0d unknown_fault_applies=%0d",
    comparisons,bubbles,replace_count,ending_apply,epoch_checks,previous_verdict,
    duplicate_priority,wraps,unknown_holds,unknown_fault_applies);
  $finish;
 end
endmodule
