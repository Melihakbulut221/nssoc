// Independent owner/decoder observer: compare current/next companion against
// the frozen reference bank, then compare every actually consumed mode.
function automatic [383:0] v24_expected_context;
 input [511:0] decoded;
 reg [63:0] transition[0:2];
 reg [63:0] prefix,suffix;
 reg [31:0] word_bits;
 integer beat,word_no,destination,source_no;
 begin
  v24_expected_context=0;
  for(beat=0;beat<4;beat=beat+1) begin
   for(word_no=0;word_no<3;word_no=word_no+1) begin
    word_bits=decoded[(beat*4+word_no)*32+:32];
    transition[word_no]=reference.framer.control_transition(word_bits[0],word_bits[1],word_bits[2],1'b0,word_bits[4],1'b0,1'b0);
   end
   for(word_no=0;word_no<3;word_no=word_no+1) begin
    if(word_no==0) prefix=transition[0];
    else prefix=reference.framer.control_compose(transition[word_no],prefix);
    for(source_no=0;source_no<3;source_no=source_no+1)
     for(destination=0;destination<8;destination=destination+1)
      v24_expected_context[beat*96+word_no*24+source_no*8+destination]=prefix[destination*8+(source_no==0?0:source_no+1)];
   end
   suffix=reference.framer.control_compose(transition[2],transition[1]);
   for(destination=0;destination<8;destination=destination+1) begin
    v24_expected_context[beat*96+72+destination]=transition[1][destination*8+2];
    v24_expected_context[beat*96+80+destination]=suffix[destination*8+2];
    v24_expected_context[beat*96+88+destination]=transition[2][destination*8+2];
   end
  end
 end
endfunction
integer v24_context_current_checks=0,v24_context_next_checks=0,v24_context_shifts=0;
integer v24_context_promotions=0,v24_context_changed_promotions=0,v24_context_concurrent=0;
integer v24_context_carry0=0,v24_context_carry1=0,v24_context_carry2=0,v24_context_carry3=0;
integer v24_context_mode_checks=0,v24_context_final_eds=0,v24_context_word;
always @(posedge clk_i) begin
 if(rst_ni===1'b1) begin
  if(candidate.framer.current_valid===1'b1) begin
   if(candidate.framer.current_token_context !== v24_expected_context(reference.framer.current_predecode))
    $fatal(1,"V24_CONTEXT_BANK current");
   v24_context_current_checks=v24_context_current_checks+1;
  end
  if(candidate.framer.next_valid===1'b1) begin
   if(candidate.framer.next_token_context !== v24_expected_context(reference.framer.next_predecode))
    $fatal(1,"V24_CONTEXT_BANK next");
   v24_context_next_checks=v24_context_next_checks+1;
  end
  if(candidate.framer.step===1'b1) begin
   for(v24_context_word=0;v24_context_word<4;v24_context_word=v24_context_word+1) begin
    if(candidate.framer.control_modes[v24_context_word] !== reference.framer.control_modes[v24_context_word])
      $fatal(1,"V24_CONTEXT_CONSUMED_MODE word=%0d",v24_context_word);
    v24_context_mode_checks=v24_context_mode_checks+1;
   end
   if(reference.framer.control_carry_end[0]) v24_context_carry0=v24_context_carry0+1;
   if(reference.framer.control_carry_end[1]) v24_context_carry1=v24_context_carry1+1;
   if(reference.framer.control_carry_end[2]) v24_context_carry2=v24_context_carry2+1;
   if(reference.framer.control_carry_end[3]) v24_context_carry3=v24_context_carry3+1;
   if(reference.framer.control_eds[3] && reference.framer.control_active[3]) v24_context_final_eds=v24_context_final_eds+1;
   if(reference.framer.slice!=3) v24_context_shifts=v24_context_shifts+1;
   else if(reference.framer.next_valid) begin
    v24_context_promotions=v24_context_promotions+1;
    if(candidate.framer.current_token_context!==candidate.framer.next_token_context)
     v24_context_changed_promotions=v24_context_changed_promotions+1;
    if(reference.framer.block_valid_i && reference.framer.block_ready_o)
     v24_context_concurrent=v24_context_concurrent+1;
   end
  end
 end
end
final $display("V24_CONTEXT_WITNESSES current=%0d next=%0d shifts=%0d promotions=%0d changed=%0d concurrent=%0d modes=%0d carry=%0d/%0d/%0d/%0d eds=%0d",v24_context_current_checks,v24_context_next_checks,v24_context_shifts,v24_context_promotions,v24_context_changed_promotions,v24_context_concurrent,v24_context_mode_checks,v24_context_carry0,v24_context_carry1,v24_context_carry2,v24_context_carry3,v24_context_final_eds);
