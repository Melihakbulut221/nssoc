# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real serial traffic, V26 public-cycle comparison and V27 fault quarantine."""
from pathlib import Path
import json
import re
import runpy
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'hw/soc/rtl/pcie'
TOP = 'soc_pcie_gen3_continuous_rx_integrity_v26'
INPUTS = ('clk_i', 'rst_ni', 'flush_i', 'stream_start_i', 'stream_abort_i', 'word_i', 'ready_i')
OUTPUTS = {'valid_o': 1, 'data_o': 128, 'keep_o': 16, 'sop_o': 16, 'eop_o': 16,
           'dllp_o': 16, 'sequence_o': 48, 'packet_good_o': 4, 'packet_nullified_o': 4,
           'packet_crc_bad_o': 4, 'packet_dllp_o': 4, 'packet_sequence_o': 48,
           'framing_error_o': 1, 'stream_end_o': 1, 'active_o': 1, 'halted_o': 1, 'overflow_o': 1}
PAYLOAD = ('data_o', 'keep_o', 'sop_o', 'eop_o', 'dllp_o', 'sequence_o')
CONTROLS = tuple(n for n in OUTPUTS if n not in PAYLOAD)


def bundle(names, prefix=''):
    return '{' + ','.join(prefix+n for n in names) + '}'


def prepare(directory, fault=None):
    directory.mkdir()
    for n in ('soc_pcie_gen3_ingress_integrity_v11', 'soc_pcie_gen3_data_descrambler'):
        shutil.copyfile(RTL/(n+'.v'), directory/(n+'.v'))
    source = (RTL/'soc_pcie_gen3_framer_rx_integrity_v27.v').read_text()
    if fault:
        old, new, _ = FAULTS[fault]
        assert source.count(old) == 1
        source = source.replace(old, new)
    # The existing runner's filenames are retained; actual module names are
    # V27 plus an unchanged V26 reference. The existing 19-case oracle is not edited.
    (directory/'soc_pcie_gen3_framer_rx_integrity_v26.v').write_text(source)
    candidate = (RTL/'soc_pcie_gen3_continuous_rx_integrity_v27.v').read_text()
    candidate = candidate.replace('module '+TOP.replace('_v26','_v27'), 'module '+TOP)
    reference = (RTL/(TOP+'.v')).read_text().replace('module '+TOP, 'module v27_reference')
    wires = '\n'.join(f'wire [{width-1}:0] gold_{name};' for name,width in OUTPUTS.items())
    connections = [f'.{n}({n})' for n in INPUTS] + [f'.{n}(gold_{n})' for n in OUTPUTS]
    observer = wires + '\nv27_reference #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) reference(' + ','.join(connections) + ');\n'
    observer += '''
integer v27_cycles=0,v27_faults=0,v27_frontier_differences=0;
reg v27_fault_edge;
always @(posedge clk_i) begin
 v27_fault_edge=(rst_ni===1'b1 && framer.enabled===1'b1 &&
   framer.active_o===1'b1 && framer.command_valid===1'b1 && framer.fault_now===1'b1);
 #0.004;
 if(rst_ni===1'b1) begin
   if(CONTROL !== GOLD_CONTROL) $fatal(1,"V27_PUBLIC_CONTROL_CYCLE");
   if(valid_o && PAYLOAD !== GOLD_PAYLOAD) $fatal(1,"V27_PUBLIC_PAYLOAD_CYCLE");
   if(active_o && framer.visible_commit_ptr !== reference.framer.visible_commit_ptr)
     $fatal(1,"V27_ACTIVE_FRONTIER_DIFFERENCE");
   v27_cycles=v27_cycles+1;
 end
 if(!rst_ni || flush_i || stream_start_i || stream_abort_i)
   if(framer.visible_commit_ptr !== 0) $fatal(1,"V27_EPOCH_FRONTIER_RESET");
 if(v27_fault_edge) begin
   v27_faults=v27_faults+1;
   if({framer.command_valid,framer.active_o,framer.retire_valid,framer.output_valid}!==0 || !halted_o)
     $fatal(1,"V27_FAULT_FRONTIER_QUARANTINE");
   if(framer.visible_commit_ptr !== reference.framer.visible_commit_ptr)
     v27_frontier_differences=v27_frontier_differences+1;
 end
end
final $display("V27_FRONTIER_WITNESS cycles=%0d faults=%0d changed=%0d",v27_cycles,v27_faults,v27_frontier_differences);
'''.replace('GOLD_CONTROL',bundle(CONTROLS,'gold_')).replace('CONTROL',bundle(CONTROLS)).replace('GOLD_PAYLOAD',bundle(PAYLOAD,'gold_')).replace('PAYLOAD !==',bundle(PAYLOAD)+' !==')
    # Token replacement must not alter the exact failure diagnostics.
    observer = observer.replace('V27_PUBLIC_'+bundle(CONTROLS)+'_CYCLE', 'V27_PUBLIC_CONTROL_CYCLE')
    assert candidate.count('endmodule') == 1
    candidate = candidate.replace('endmodule',observer+'\nendmodule')
    (directory/(TOP+'.v')).write_text(candidate+'\n'+reference+'\n'+(RTL/'soc_pcie_gen3_framer_rx_integrity_v26.v').read_text())
    return directory


FAULTS = {
    'early_frontier': ('else if(enabled && command_valid) visible_commit_ptr<=command_commit;',
                       'else if(enabled && command_valid) visible_commit_ptr<=commit_n;',
                       'sustained_minimum_packets_exceed_every_buffer'),
    'missing_apply': ('else if(enabled && command_valid) visible_commit_ptr<=command_commit;',
                      'else if(1\'b0) visible_commit_ptr<=command_commit;',
                      'sustained_minimum_packets_exceed_every_buffer'),
    'drop_ending': ('else if(enabled && command_valid) visible_commit_ptr<=command_commit;',
                    'else if(enabled && command_valid && !ending) visible_commit_ptr<=command_commit;',
                    'edb_quarantine_and_eds_release_drain'),
    'restart_leak': ('else if(flush_i || stream_start_i || stream_abort_i || !active_o)',
                     'else if(stream_abort_i || !active_o)',
                     'descriptor_epoch_controls_discard_owned_payload'),
    'fault_epoch_alive': ('error_pulse<=1;active_o<=0;halted_o<=1;',
                          'error_pulse<=1;active_o<=1;halted_o<=1;',
                          'cache_fault_write_and_new_epoch_reuse'),
}


def test_generated_frontier_is_exact_derivative():
    g = runpy.run_path(str(ROOT/'scripts/generate_pcie_integrity_frontier_v27.py'))
    generated, edits = g['generate']()
    assert generated == (RTL/'soc_pcie_gen3_framer_rx_integrity_v27.v').read_text()
    assert len(edits) == 4


@pytest.mark.parametrize('fault', [None, *FAULTS], ids=['positive', *FAULTS])
def test_actual_public_frontier_cycles_and_fault_quarantine(tmp_path, fault):
    helper = runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v26.py'))
    result, record, cases, out = helper['run'](tmp_path, rtl=prepare(tmp_path/'rtl',fault),
                                            case=FAULTS[fault][2] if fault else None)
    log = (out/'simulation.log').read_text()
    if fault:
        assert result.returncode != 0 and record['status'] == 'FAIL'
        assert re.search(r'V27_(PUBLIC_CONTROL_CYCLE|PUBLIC_PAYLOAD_CYCLE|ACTIVE_FRONTIER_DIFFERENCE|EPOCH_FRONTIER_RESET|FAULT_FRONTIER_QUARANTINE)',log), log
        assert 'syntax error' not in log.lower()
    else:
        assert result.returncode == 0, record
        assert record['tests'] == dict(passed=19,failed=0,skipped=0)
        match = re.search(r'V27_FRONTIER_WITNESS cycles=(\d+) faults=(\d+) changed=(\d+)',log)
        assert match
        cycles,faults,changed = map(int,match.groups())
        assert cycles > 1000 and faults >= 8 and changed >= 8, (cycles,faults,changed)
        (out/'frontier-witness.json').write_text(json.dumps(dict(cycles=cycles,faults=faults,changed=changed,
            scope='Finite V26/V27 known-control public cycles and independent serial packet oracle; not all-state formal equivalence.'),indent=2)+'\n')
