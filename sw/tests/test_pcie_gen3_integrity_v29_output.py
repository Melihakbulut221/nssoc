# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual output ownership, serial packet oracle and fault-edge contents."""
from pathlib import Path
import json
import re
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT/'hw/soc/rtl/pcie'
DENSE = 'sustained_minimum_packets_exceed_every_buffer'
FAULTS = {
    'bypass_descriptor': ('output_data<=retire_data;output_keep<=retire_keep;',
                          'output_data<=read_data;output_keep<=retire_keep;', DENSE),
    'lose_keep': ('output_data<=retire_data;output_keep<=retire_keep;',
                  "output_data<=retire_data;output_keep<=0;", DENSE),
    'lose_sequence': ('output_dllp<=retire_dllp;output_sequence<=retire_sequence;',
                      'output_dllp<=retire_dllp;output_sequence<=0;', DENSE),
    'overwrite_stalled': ('end else if(retire_pop && retire_has_data) begin',
                          'end else if(retire_valid && retire_has_data) begin',
                          'bounded_stalls_preserve_all_wide_metadata'),
    'fault_output_survives': ('state<=TOKEN;current_valid<=0;next_valid<=0;output_valid<=0;ending<=0;',
                             'state<=TOKEN;current_valid<=0;next_valid<=0;output_valid<=1;ending<=0;',
                             'descriptor_parser_fault_cancels_queue_after_sampling_edge'),
}


def prepare(directory, fault=None):
    base = runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_integrity_v28_payload.py'))
    base['prepare'](directory)
    text = (RTL/'soc_pcie_gen3_framer_rx_integrity_v29.v').read_text()
    if fault:
        before,after,_ = FAULTS[fault]
        assert text.count(before) == 1
        text = text.replace(before,after)
    text = text.replace('module soc_pcie_gen3_framer_rx_integrity_v29 #(',
                        'module soc_pcie_gen3_framer_rx_integrity_v27 #(')
    (directory/'soc_pcie_gen3_framer_rx_integrity_v26.v').write_text(text)
    top = directory/'soc_pcie_gen3_continuous_rx_integrity_v26.v'
    fields = ('data','keep','sop','eop','dllp','sequence')
    def bundle(prefix, bank):
        return '{'+','.join(prefix+'.'+bank+'_'+n for n in fields)+'}'
    observer = r'''
reg [239:0] v29_before,v29_expected,v29_reference_before;
reg v29_fault,v29_copy,v29_stall;
integer v29_copies=0,v29_fault_copies=0,v29_fault_changes=0,v29_stalls=0;
always @(posedge clk_i) begin
 v29_before=CONTENTS;
 v29_reference_before=REFERENCE;
 v29_copy=(rst_ni===1'b1 && framer.retire_pop===1'b1 && framer.retire_has_data===1'b1);
 v29_fault=v29_copy && framer.fault_now===1'b1;
 v29_stall=(rst_ni===1'b1 && framer.enabled===1'b1 && framer.active_o===1'b1 &&
             framer.output_valid===1'b1 && ready_i===1'b0);
 v29_expected=v29_before;
 if(!rst_ni) v29_expected=0;
 else if(v29_copy) v29_expected=DESCRIPTOR;
 #0.008;
 if(CONTENTS !== v29_expected) $fatal(1,"V29_EXACT_OUTPUT_TRANSFER");
 if(v29_copy) v29_copies=v29_copies+1;
 if(v29_stall) begin
   v29_stalls=v29_stalls+1;
   if(CONTENTS !== v29_before) $fatal(1,"V29_STALLED_OUTPUT_CHANGED");
 end
 if(v29_fault) begin
   v29_fault_copies=v29_fault_copies+1;
   if(CONTENTS !== v29_before) v29_fault_changes=v29_fault_changes+1;
   if(REFERENCE !== v29_reference_before) $fatal(1,"V29_REFERENCE_FAULT_CONTENTS");
   if({framer.active_o,framer.output_valid,framer.retire_valid} !== 0 || !halted_o)
     $fatal(1,"V29_OUTPUT_FAULT_OWNERSHIP");
 end
end
final $display("V29_OUTPUT_WITNESS copies=%0d fault_copies=%0d fault_changes=%0d stalls=%0d",
 v29_copies,v29_fault_copies,v29_fault_changes,v29_stalls);
'''.replace('CONTENTS',bundle('framer','output')).replace('REFERENCE',bundle('reference.framer','output')).replace('DESCRIPTOR',bundle('framer','retire'))
    # Restore diagnostics after replacing standalone HDL expression tokens.
    observer = observer.replace('V29_'+bundle('reference.framer','output')+'_FAULT_'+bundle('framer','output'),
                                'V29_REFERENCE_FAULT_CONTENTS')
    top.write_text(top.read_text().replace('endmodule',observer+'\nendmodule',1))
    return directory


def test_exact_v29_inverse():
    g = runpy.run_path(str(ROOT/'scripts/generate_pcie_integrity_output_v29.py'))
    text,edits = g['generate']()
    assert len(edits) == 4 and text == (RTL/'soc_pcie_gen3_framer_rx_integrity_v29.v').read_text()


@pytest.mark.parametrize('fault',[None,*FAULTS],ids=['positive',*FAULTS])
def test_actual_output_epoch_quarantine(tmp_path, fault):
    h = runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v26.py'))
    result,record,_,out = h['run'](tmp_path,rtl=prepare(tmp_path/'rtl',fault),case=FAULTS[fault][2] if fault else None)
    log = (out/'simulation.log').read_text()
    if fault:
        assert result.returncode != 0 and record['status'] == 'FAIL'
        # The existing V27 ownership observer runs before the V29 payload
        # observer and must catch a surviving owner even when active is clear.
        diagnostic = (r'V27_FAULT_FRONTIER_QUARANTINE' if fault == 'fault_output_survives'
                      else r'V(27_PUBLIC_(CONTROL|PAYLOAD)_CYCLE|29_(EXACT_OUTPUT_TRANSFER|STALLED_OUTPUT_CHANGED|OUTPUT_FAULT_OWNERSHIP))')
        assert re.search(diagnostic,log),log
        assert 'syntax error' not in log.lower()
    else:
        assert result.returncode == 0 and record['tests'] == dict(passed=19,failed=0,skipped=0),record
        match = re.search(r'V29_OUTPUT_WITNESS copies=(\d+) fault_copies=(\d+) fault_changes=(\d+) stalls=(\d+)',log)
        assert match
        copies,fault_copies,fault_changes,stalls = map(int,match.groups())
        assert copies > 100 and stalls > 10
        assert fault_copies > 0 and fault_changes > 0, (copies,fault_copies,fault_changes,stalls)
        cycles = re.search(r'V27_FRONTIER_WITNESS cycles=(\d+)',log)
        assert cycles and int(cycles[1]) > 1000
        (out/'output-witness.json').write_text(json.dumps(dict(copies=copies,fault_copies=fault_copies,
            fault_changes=fault_changes,stalls=stalls,public_cycles=int(cycles[1])),indent=2)+'\n')
