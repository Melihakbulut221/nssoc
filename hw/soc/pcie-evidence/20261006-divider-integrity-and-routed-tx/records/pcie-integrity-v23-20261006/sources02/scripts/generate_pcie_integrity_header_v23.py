#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Register adjacent accepted STP/header relation before the parser control cone."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v22.v'
SOURCE_SHA='b18c84d1cd1a7db7a6681939624a96a07af8f1cda1726bde987a4b08e89ad5d6'
RELATION_DECL=''' // BEGIN V23 REGISTERED ADJACENT HEADER RELATION
 // Relation is independent of parser ownership. A consumed first TLP header
 // necessarily follows its accepted STP; unused predecessor values cannot
 // authorize a packet. The observer tracks old predecessor ownership perbank.
 reg [12:0] accepted_tail_encoded;
 reg accepted_tail_valid;
 reg [15:0] current_header_relation,next_header_relation;
 reg packet_header_mismatch,packet_header_mismatch_n;
 function automatic [15:0] adjacent_header_relation;
   input [511:0] decoded;
   input [12:0] previous_encoded;
   integer index;
   reg [12:0] predecessor;
   begin
     for(index=0;index<16;index=index+1) begin
       if(index==0) predecessor=previous_encoded;
       else predecessor=decoded[(index-1)*32+19+:13];
       adjacent_header_relation[index]=decoded[index*32+18] ||
         (predecessor!=decoded[index*32+5+:13]);
     end
   end
 endfunction
 wire [15:0] input_header_relation=adjacent_header_relation(input_predecode,accepted_tail_encoded);
 // END V23 REGISTERED ADJACENT HEADER RELATION
'''
TAIL_WRITER=''' // BEGIN V23 ACCEPTED STREAM PREDECESSOR
 // Data may change on a fault edge, just as the V10 data banks do. Its
 // ownership marker clears; only a fresh accepted block establishes nexttail.
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) accepted_tail_encoded<=0;
   else if(enabled && active_o && block_valid_i && block_ready_o)
     accepted_tail_encoded<=input_predecode[15*32+19+:13];
 end
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) accepted_tail_valid<=0;
   else if(flush_i || stream_start_i || (stream_abort_i && active_o) || fault_now)
     accepted_tail_valid<=0;
   else if(enabled && active_o && block_valid_i && block_ready_o)
     accepted_tail_valid<=1;
 end
 // END V23 ACCEPTED STREAM PREDECESSOR
'''
EDITS=[
(' // END V9 REGISTERED WORD DECODE\n',' // END V9 REGISTERED WORD DECODE\n'+RELATION_DECL),
(' wire control_carried_header_bad=header_first ?\n   (current_predecode[18] || packet_bytes!=control_expected0) :\n   (header_bad || packet_bytes!=expected_bytes);',' wire control_carried_header_bad=header_first ?\n   current_header_relation[0] : packet_header_mismatch;'),
('   expected_n=expected_bytes;remaining_n=remaining;sequence_n=packet_sequence;','   expected_n=expected_bytes;remaining_n=remaining;sequence_n=packet_sequence;\n   packet_header_mismatch_n=packet_header_mismatch;'),
('               header_first_n=1;header_bad_n=0;expected_n=0;state_n=TLP;','               header_first_n=1;header_bad_n=0;expected_n=0;state_n=TLP;\n               packet_header_mismatch_n=0;'),
('             if(control_header_first[j]) begin\n','             if(control_header_first[j]) begin\n               packet_header_mismatch_n=current_header_relation[j];\n'),
(' // BEGIN V10 QUARANTINED BANK WRITER\n',TAIL_WRITER+' // BEGIN V10 QUARANTINED BANK WRITER\n'),
('     current_predecode<=predecode_block(512\'b0);next_predecode<=predecode_block(512\'b0);','     current_predecode<=predecode_block(512\'b0);next_predecode<=predecode_block(512\'b0);\n     current_header_relation<=16\'hffff;next_header_relation<=16\'hffff;'),
('         if(next_valid) begin current_block<=next_block;current_predecode<=next_predecode;end','         if(next_valid) begin current_block<=next_block;current_predecode<=next_predecode;\n           current_header_relation<=next_header_relation;end'),
('         current_predecode<={{4{predecode_word(32\'b0)}},current_predecode[511:128]};','         current_predecode<={{4{predecode_word(32\'b0)}},current_predecode[511:128]};\n         current_header_relation<={4\'b1111,current_header_relation[15:4]};'),
('         current_block<=payload_i;current_predecode<=input_predecode;','         current_block<=payload_i;current_predecode<=input_predecode;\n         current_header_relation<=input_header_relation;'),
('       end else begin next_block<=payload_i;next_predecode<=input_predecode;end','       end else begin next_block<=payload_i;next_predecode<=input_predecode;\n         next_header_relation<=input_header_relation;end'),
('     remaining<=0;packet_sequence<=0;header_first<=0;header_bad<=0;ending<=0;','     remaining<=0;packet_sequence<=0;header_first<=0;header_bad<=0;ending<=0;\n     packet_header_mismatch<=0;'),
('     if(flush_i || stream_start_i) begin\n','     if(flush_i || stream_start_i) begin\n       packet_header_mismatch<=0;\n'),
('     end else if((stream_abort_i && active_o) || fault_now) begin\n','     end else if((stream_abort_i && active_o) || fault_now) begin\n       packet_header_mismatch<=0;\n'),
('         header_first<=header_first_n;header_bad<=header_bad_n;ending<=ending_n;','         header_first<=header_first_n;header_bad<=header_bad_n;ending<=ending_n;\n         packet_header_mismatch<=packet_header_mismatch_n;'),
]
def candidate():
 text=SOURCE.read_text();assert hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA
 for before,after in EDITS:
  assert text.count(before)==1,(before,text.count(before));text=text.replace(before,after)
 return text.replace('integrity_v22','integrity_v23')
def inverse(text):
 text=text.replace('integrity_v23','integrity_v22')
 for before,after in reversed(EDITS):
  assert text.count(after)==1,(after,text.count(after));text=text.replace(after,before)
 assert hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA
 return text
if __name__=='__main__':
 text=candidate();assert inverse(text)==SOURCE.read_text()
 SOURCE.with_name('soc_pcie_gen3_framer_rx_integrity_v23.v').write_text(text)
