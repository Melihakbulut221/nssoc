from pathlib import Path
import hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent
fragment=(B/'prefix_candidate01.vh').read_text()
assert hashlib.sha256(fragment.encode()).hexdigest()=='eb05ce57875329d8b9321f08e2d87838d73a5523a8b6f725ed108d4e06a53b21'
functions='\n'.join(fragment.splitlines()[3:])+'\n'
block=''' function automatic [383:0] block_token_context;
   input [511:0] decoded;
   integer beat,lane;
   reg [63:0] token0,token1,token2;
   reg [31:0] word0,word1,word2;
   begin
     for(beat=0;beat<4;beat=beat+1) begin
       word0=decoded[(beat*4+0)*32+:32];
       word1=decoded[(beat*4+1)*32+:32];
       word2=decoded[(beat*4+2)*32+:32];
       // Prefixes end before word3. Only absolute word15 can qualify EDS,
       // so EDS is false in every token used by these three-word prefixes.
       token0=control_transition(word0[0],word0[1],word0[2],1'b0,word0[4],1'b0,1'b0);
       token1=control_transition(word1[0],word1[1],word1[2],1'b0,word1[4],1'b0,1'b0);
       token2=control_transition(word2[0],word2[1],word2[2],1'b0,word2[4],1'b0,1'b0);
       block_token_context[beat*96+:96]=token_prefix_context(token0,token1,token2);
     end
   end
 endfunction
 reg [383:0] current_token_context,next_token_context;
 wire [383:0] input_token_context=block_token_context(input_predecode);
 wire [383:0] empty_token_context=block_token_context(predecode_block(512'b0));
 wire [7:0] control_carried_column[0:2];
 genvar carried_word,carried_destination;
 generate for(carried_word=0;carried_word<3;carried_word=carried_word+1) begin:carried_prefix
   for(carried_destination=0;carried_destination<8;carried_destination=carried_destination+1) begin:destination
     assign control_carried_column[carried_word][carried_destination]=control_table[carried_word][carried_destination*8+1];
   end
 end endgenerate
'''
old=''' assign control_modes[1]=control_apply(control_table[0],control_modes[0]);
 assign control_prefix2=control_compose(control_table[1],control_table[0]);
 assign control_prefix3=control_compose(control_table[2],control_prefix2);
 assign control_modes[2]=control_apply(control_prefix2,control_modes[0]);
 assign control_modes[3]=control_apply(control_prefix3,control_modes[0]);'''
new='\n'.join(f' assign control_modes[{j}]=context_prefix_modes(current_token_context[95:0],control_modes[0],\n   control_carried_column[0],control_carried_column[1],control_carried_column[2],2\'d{j});'for j in(1,2,3))
edits=[
 (' wire [63:0] control_prefix2,control_prefix3;\n',''),
 (' assign control_modes[0]={4\'b0,state==DLLP,state==LOOK,state==TLP,state==TOKEN};',
  ' // BEGIN V24 ACCEPTED TOKEN PREFIX CONTEXT\n'+functions+block+' // END V24 ACCEPTED TOKEN PREFIX CONTEXT\n'+' assign control_modes[0]={4\'b0,state==DLLP,state==LOOK,state==TLP,state==TOKEN};'),
 (old,new),
 ("     current_header_relation<=16'hffff;next_header_relation<=16'hffff;", "     current_header_relation<=16'hffff;next_header_relation<=16'hffff;\n     current_token_context<=empty_token_context;next_token_context<=empty_token_context;"),
 ('           current_header_relation<=next_header_relation;end','           current_header_relation<=next_header_relation;\n           current_token_context<=next_token_context;end'),
 ("         current_header_relation<={4'b1111,current_header_relation[15:4]};", "         current_header_relation<={4'b1111,current_header_relation[15:4]};\n         current_token_context<={empty_token_context[95:0],current_token_context[383:96]};"),
 ('         current_header_relation<=input_header_relation;', '         current_header_relation<=input_header_relation;\n         current_token_context<=input_token_context;'),
 ('         next_header_relation<=input_header_relation;end','         next_header_relation<=input_header_relation;\n         next_token_context<=input_token_context;end'),
]
# Retain the otherwise unused declaration so every inverse edit has a unique nonempty target.
edits=edits[1:]
text='''#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Register exact token-only prefix matrices beside accepted block ownership."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v'
SOURCE_SHA='505db8d1daa5c5263a16a3584175bc89a73d1b6e35f16e10b64f1f9f6483dde6'
EDITS='''+repr(edits)+'''
def candidate():
 text=SOURCE.read_text();assert hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA
 for before,after in EDITS:
  assert text.count(before)==1,(before,text.count(before));text=text.replace(before,after)
 return text.replace('integrity_v23','integrity_v24')
def inverse(text):
 text=text.replace('integrity_v24','integrity_v23')
 for before,after in reversed(EDITS):
  assert text.count(after)==1,(after,text.count(after));text=text.replace(after,before)
 assert hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA
 return text
if __name__=='__main__':
 text=candidate();assert inverse(text)==SOURCE.read_text()
 SOURCE.with_name('soc_pcie_gen3_framer_rx_integrity_v24.v').write_text(text)
'''
p=R/'scripts/generate_pcie_integrity_prefix_v24.py';assert not p.exists();p.write_text(text)
print('Prepared seven exact product edits; inherited control matrices/branches remain untouched.')
