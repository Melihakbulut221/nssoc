#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Register ring retirement payload; explicit one-cycle output latency from V17."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v'
SOURCE_SHA = '7aeb0b29e6b56978bed7f83a48b14e8e11a005bf16342cfd8b616225ba9d8160'
DECLARATIONS = ''' // BEGIN V21 REGISTERED RETIRE DESCRIPTOR
 // Validity owns an atomic copy of committed ring data. The ring can reuse
 // copied slots while this extra stage waits for the public output register.
 reg retire_valid,retire_has_data;
 reg [127:0] retire_data;
 reg [15:0] retire_keep,retire_sop,retire_eop,retire_dllp;
 reg [47:0] retire_sequence;
 // END V21 REGISTERED RETIRE DESCRIPTOR
'''
RETIRE_CONTROL = ''' // BEGIN V21 REGISTERED RETIRE AVAILABILITY
 // Availability depends only on registered ownership and downstream ready.
 // Empty descriptors drain even when a nonempty public beat is held.
 wire retire_pop=enabled && active_o && retire_valid &&
                 (!retire_has_data || !output_valid || ready_i);
 wire retire_room=!retire_valid || retire_pop;
 wire retire=enabled && active_o && committed!=0 && retire_room;
 // END V21 REGISTERED RETIRE AVAILABILITY
'''
PAYLOAD_WRITER = ''' // BEGIN V21 ATOMIC RETIRE PAYLOAD CAPTURE
 // The original priority state machine clears descriptor validity on faults.
 // A simultaneous invalid payload copy cannot become visible: a later owner
 // must first copy every field again. No parser-fault enable on this data bank.
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     retire_data<=0;retire_keep<=0;retire_sop<=0;retire_eop<=0;
     retire_dllp<=0;retire_sequence<=0;
   end else if(retire) begin
     retire_data<=read_data;retire_keep<=read_keep;retire_sop<=read_sop;
     retire_eop<=read_eop;retire_dllp<=read_dllp;retire_sequence<=read_sequence;
   end
 end
 // END V21 ATOMIC RETIRE PAYLOAD CAPTURE
'''
OLD_RETIRE = '''       if(retire) begin
         read_ptr<=read_ptr+read_count;
         if(read_keep!=0) begin
           output_valid<=1;output_data<=read_data;output_keep<=read_keep;
           output_sop<=read_sop;output_eop<=read_eop;output_dllp<=read_dllp;output_sequence<=read_sequence;
         end
       end
'''
NEW_RETIRE = '''       // BEGIN V21 DESCRIPTOR OWNERSHIP AND OUTPUT TRANSFER
       // Nonblocking assignments transfer the old descriptor before replacing
       // it. Capture wins over simultaneous pop; literal payload X/Z survives.
       if(retire_pop) begin
         retire_valid<=0;
         if(retire_has_data) begin
           output_valid<=1;output_data<=retire_data;output_keep<=retire_keep;
           output_sop<=retire_sop;output_eop<=retire_eop;output_dllp<=retire_dllp;output_sequence<=retire_sequence;
         end
       end
       if(retire) begin
         read_ptr<=read_ptr+read_count;retire_valid<=1;
         retire_has_data<=0;
         if(read_keep!=0) retire_has_data<=1;
       end
       // END V21 DESCRIPTOR OWNERSHIP AND OUTPUT TRANSFER
'''
REPLACEMENTS = (
    (' reg output_valid;\n', DECLARATIONS + ' reg output_valid;\n'),
    (' wire retire=enabled && active_o && committed!=0 &&\n             ((!output_valid || ready_i) || read_keep==0);\n', RETIRE_CONTROL),
    (' integer w;\n initial begin\n', PAYLOAD_WRITER + ' integer w;\n initial begin\n'),
    ('     output_valid<=0;output_data<=0;output_keep<=0;output_sop<=0;output_eop<=0;output_dllp<=0;output_sequence<=0;\n',
     '     retire_valid<=0;retire_has_data<=0;\n     output_valid<=0;output_data<=0;output_keep<=0;output_sop<=0;output_eop<=0;output_dllp<=0;output_sequence<=0;\n'),
    ('       output_valid<=0;ending<=0;overflow_sticky<=0;active_o<=stream_start_i && !flush_i;halted_o<=0;\n',
     '       retire_valid<=0;retire_has_data<=0;\n       output_valid<=0;ending<=0;overflow_sticky<=0;active_o<=stream_start_i && !flush_i;halted_o<=0;\n'),
    ('       state<=TOKEN;current_valid<=0;next_valid<=0;output_valid<=0;ending<=0;\n',
     '       retire_valid<=0;retire_has_data<=0;\n       state<=TOKEN;current_valid<=0;next_valid<=0;output_valid<=0;ending<=0;\n'),
    (OLD_RETIRE, NEW_RETIRE),
    ('       if(ending && read_ptr==write_ptr && (!output_valid || ready_i)) begin\n',
     '       if(ending && read_ptr==write_ptr && !retire_valid && (!output_valid || ready_i)) begin\n'),
)


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    for before, after in REPLACEMENTS:
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    return text.replace('integrity_v17', 'integrity_v21')


def original(text):
    text = text.replace('integrity_v21', 'integrity_v17')
    for before, after in reversed(REPLACEMENTS):
        assert text.count(after) == 1, after
        text = text.replace(after, before)
    return text


if __name__ == '__main__':
    result = candidate()
    assert original(result) == SOURCE.read_text()
    (ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v21.v').write_text(result)
