#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""V23-derived experimental registered parser-to-ring command stage.

This changes public payload latency; it is not a cycle-equivalent replacement.
The inverse restores the entire frozen V23 body. No baseline is overwritten.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v'
TARGET = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v25.v'
BASE_SHA = '505db8d1daa5c5263a16a3584175bc89a73d1b6e35f16e10b64f1f9f6483dde6'

DECLARATIONS = ''' // BEGIN V25 REGISTERED PARSER TO RING COMMAND
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
'''

CAPTURE = ''' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP
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
'''

OLD_WRITES = '''         for(w=0;w<4;w=w+1) begin
           slot_data[(write_ptr+w)&(RING_DWORDS-1)]<=write_data[w*32+:32];
           slot_keep[(write_ptr+w)&(RING_DWORDS-1)]<=write_keep[w*4+:4];
           slot_sop[(write_ptr+w)&(RING_DWORDS-1)]<=write_sop[w*4+:4];
           slot_eop[(write_ptr+w)&(RING_DWORDS-1)]<=write_eop[w*4+:4];
           slot_dllp[(write_ptr+w)&(RING_DWORDS-1)]<=write_dllp[w*4+:4];
           slot_sequence[(write_ptr+w)&(RING_DWORDS-1)]<=write_sequence[w*12+:12];
           slot_tag[(write_ptr+w)&(RING_DWORDS-1)]<=write_tags[w*PW+:PW];
           if(verdict_enable[w]) verdict[verdict_tags[w*PW+:PW]]<=verdict_value[w];
         end
'''

APPLY = '''       // BEGIN V25 APPLY OLD COMMAND
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
'''


def generate():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    text = original
    edits = []

    def replace(before, after, count=1):
        nonlocal text
        assert before != after and text.count(before) == count, before
        text = text.replace(before, after)
        edits.append(dict(before=before, after=after, count=count))

    replace('module soc_pcie_gen3_framer_rx_integrity_v23 #(',
            'module soc_pcie_gen3_framer_rx_integrity_v25 #(')
    replace(' reg slot_verdict [0:RING_DWORDS-1];\n',
            ' reg slot_verdict [0:RING_DWORDS-1];\n' + DECLARATIONS)
    replace('wire [PW-1:0] committed=commit_ptr-read_ptr;',
            'wire [PW-1:0] committed=visible_commit_ptr-read_ptr;')
    replace('assign cache_write_old_verdict[cache_read_lane]=verdict[write_tags[cache_read_lane*PW+:PW]];',
            'assign cache_write_old_verdict[cache_read_lane]=verdict[command_tags[cache_read_lane*PW+:PW]];')
    replace('if(((write_ptr+write_lane)&(RING_DWORDS-1))==cache_slot)',
            'if(((command_address+write_lane)&(RING_DWORDS-1))==cache_slot)')
    replace('effective_tag=write_tags[write_lane*PW+:PW];',
            'effective_tag=command_tags[write_lane*PW+:PW];')
    replace('if(verdict_enable[verdict_lane] && verdict_tags[verdict_lane*PW+:PW]==effective_tag)\n'
            '         next_value=verdict_value[verdict_lane];',
            'if(command_verdict_enable[verdict_lane] && command_verdict_tags[verdict_lane*PW+:PW]==effective_tag)\n'
            '         next_value=command_verdict_value[verdict_lane];')
    replace('if(step) slot_verdict[cache_slot]<=next_value; // V22 invalid cache content is quarantined.',
            'if(enabled && active_o && command_valid) slot_verdict[cache_slot]<=next_value; // V25 fault-invalid cache remains quarantined.')
    replace(' // BEGIN V23 ACCEPTED STREAM PREDECESSOR\n',
            CAPTURE + ' // BEGIN V23 ACCEPTED STREAM PREDECESSOR\n')
    replace(' integer w;\n', ' integer command_lane;\n')
    replace('write_ptr<=0;read_ptr<=0;commit_ptr<=0;',
            'write_ptr<=0;read_ptr<=0;commit_ptr<=0;visible_commit_ptr<=0;', 3)
    replace('     end else if(active_o) begin\n       if(!output_valid || ready_i) output_valid<=0;',
            '     end else if(active_o) begin\n' + APPLY +
            '       if(!output_valid || ready_i) output_valid<=0;')
    replace(OLD_WRITES, '         // V25 ring writes apply from the prior complete command above.\n')
    replace('if(ending && read_ptr==write_ptr && !retire_valid && (!output_valid || ready_i)) begin',
            'if(ending && !command_valid && visible_commit_ptr==commit_ptr && read_ptr==write_ptr && !retire_valid && (!output_valid || ready_i)) begin')
    assert inverse(text, edits) == original
    return text, edits


def inverse(text, edits):
    for edit in reversed(edits):
        assert text.count(edit['after']) == edit['count'], edit['after']
        text = text.replace(edit['after'], edit['before'])
    return text


if __name__ == '__main__':
    output, ledger = generate()
    with TARGET.open('x') as stream:
        stream.write(output)
    record = dict(status='DRAFT_V25_WHOLE_FRAMER_INVERSE_PASS_NOT_FUNCTIONAL_APPROVAL',
                  baseline=dict(path=str(BASE), sha256=BASE_SHA),
                  candidate=dict(path=str(TARGET), bytes=len(output.encode()),
                                 sha256=hashlib.sha256(output.encode()).hexdigest()),
                  edits=ledger, latency_changed=True, tests_run=False, native_started=False)
    path = ROOT / 'hw/soc/out/pcie-integrity-v25-20261006/source-bridge-initial01.json'
    with path.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(candidate=record['candidate'], edits=len(ledger), inverse=True)))
