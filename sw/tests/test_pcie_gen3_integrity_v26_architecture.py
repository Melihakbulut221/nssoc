# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Versioned command-stage observer and restricted nominal +1 payload relation.

Public transactions use the independent serial byte oracle. A V23 cycle miter
is deliberately not used for stalls, capacity faults or EDS completion.
"""
from pathlib import Path
import ast
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
PAYLOAD = tuple(list(OUTPUTS)[:7])
EVENTS = ('packet_good_o', 'packet_nullified_o', 'packet_crc_bad_o', 'packet_dllp_o', 'packet_sequence_o')
FIELDS = ('address', 'commit', 'data', 'keep', 'sop', 'eop', 'dllp', 'sequence', 'tags',
          'verdict_enable', 'verdict_tags', 'verdict_value')
SOURCES = ('write_ptr', 'commit_n', 'write_data', 'write_keep', 'write_sop', 'write_eop',
           'write_dllp', 'write_sequence', 'write_tags', 'verdict_enable', 'verdict_tags', 'verdict_value')


def observer():
    command = '{' + ','.join('candidate.framer.command_' + x for x in FIELDS) + '}'
    source = '{' + ','.join('candidate.framer.' + x for x in SOURCES) + '}'
    return r'''
localparam CPW=$clog2(RING_DWORDS)+1;
localparam COMMAND_BITS=10*CPW+248;
reg v25_model_valid=0;reg [COMMAND_BITS-1:0] v25_model_payload;
reg [CPW-1:0] v25_model_commit=0;
reg v25_pre_pending,v25_pre_apply,v25_pre_ending,v25_pre_step;
integer v25_commands=0,v25_applies=0,v25_bubble_applies=0,v25_ending_applies=0;
integer v25_replacements=0,v25_wraps=0,v25_zero_keep_applies=0,v25_epoch_pending[0:5];
integer v25_o;reg [CPW-1:0] v25_last_address=0;
initial for(v25_o=0;v25_o<6;v25_o=v25_o+1) v25_epoch_pending[v25_o]=0;
always @(posedge clk_i) begin
 v25_pre_pending=(candidate.framer.command_valid===1'b1);
 v25_pre_apply=0;v25_pre_ending=candidate.framer.ending;v25_pre_step=candidate.framer.step;
 if(rst_ni===1'b1 && candidate.framer.command_valid !== v25_model_valid)
  $fatal(1,"V25_COMMAND_VALID_OWNERSHIP");
 if(rst_ni===1'b1 && v25_model_valid && COMMAND !== v25_model_payload)
  $fatal(1,"V25_COMMAND_ATOMIC_FIELDS");
 if(!rst_ni) begin
  if(v25_model_valid) v25_epoch_pending[0]=v25_epoch_pending[0]+1;
  v25_model_valid=0;v25_model_commit=0;v25_last_address=0;
 end else if(flush_i || stream_start_i) begin
  if(v25_pre_pending) begin
   if(flush_i) v25_epoch_pending[1]=v25_epoch_pending[1]+1;
   if(stream_start_i) v25_epoch_pending[2]=v25_epoch_pending[2]+1;
  end
  v25_model_valid=0;v25_model_commit=0;v25_last_address=0;
 end else if((stream_abort_i && candidate.framer.active_o) || candidate.framer.fault_now) begin
  if(v25_pre_pending) begin
   if(stream_abort_i) v25_epoch_pending[3]=v25_epoch_pending[3]+1;
   if(candidate.framer.fault_now) v25_epoch_pending[4]=v25_epoch_pending[4]+1;
   if(candidate.framer.ring_overflow_now) v25_epoch_pending[5]=v25_epoch_pending[5]+1;
  end
  v25_model_valid=0;v25_model_commit=0;v25_last_address=0;
 end else if(candidate.framer.active_o) begin
  if(candidate.framer.enabled) begin
   if(v25_model_valid) begin
    v25_pre_apply=1;
    v25_model_commit=v25_model_payload[COMMAND_BITS-CPW-1-:CPW];
    v25_applies=v25_applies+1;
    if(!candidate.framer.step) v25_bubble_applies=v25_bubble_applies+1;
    if(candidate.framer.ending) v25_ending_applies=v25_ending_applies+1;
    if(candidate.framer.command_keep==0) v25_zero_keep_applies=v25_zero_keep_applies+1;
   end
   v25_model_valid=0;
   if(candidate.framer.step) begin
    v25_model_valid=1;v25_model_payload=SOURCE;
    v25_commands=v25_commands+1;
    if(v25_pre_pending) v25_replacements=v25_replacements+1;
    if(candidate.framer.write_ptr<v25_last_address) v25_wraps=v25_wraps+1;
    v25_last_address=candidate.framer.write_ptr;
   end
  end
 end
 #0.002;
 if(candidate.framer.command_valid !== v25_model_valid)
  $fatal(1,"V25_COMMAND_VALID_TRANSITION");
 if(candidate.framer.visible_commit_ptr !== v25_model_commit)
  $fatal(1,"V25_COMMAND_VISIBLE_COMMIT_EDGE");
 if(v25_model_valid && COMMAND !== v25_model_payload)
  $fatal(1,"V25_COMMAND_ATOMIC_CAPTURE");
 if(candidate.framer.committed !== ((v25_model_commit-candidate.framer.read_ptr)&((2*RING_DWORDS)-1)))
  $fatal(1,"V25_COMMAND_VISIBLE_RETIRE_FRONTIER");
 if(candidate.framer.active_o && v25_model_valid &&
    candidate.framer.write_ptr !== ((candidate.framer.command_address+4)&((2*RING_DWORDS)-1)))
  $fatal(1,"V25_COMMAND_RESERVED_ADDRESS");
 if(stream_end_o && (candidate.framer.command_valid ||
    candidate.framer.visible_commit_ptr!==candidate.framer.commit_ptr))
  $fatal(1,"V25_COMMAND_PREMATURE_EDS");
end
final $display("V25_COMMAND_DUT_WITNESSES commands=%0d applies=%0d bubble=%0d ending=%0d replacements=%0d wraps=%0d zero=%0d epochs=%0d,%0d,%0d,%0d,%0d,%0d",
 v25_commands,v25_applies,v25_bubble_applies,v25_ending_applies,v25_replacements,v25_wraps,
 v25_zero_keep_applies,v25_epoch_pending[0],v25_epoch_pending[1],v25_epoch_pending[2],v25_epoch_pending[3],v25_epoch_pending[4],v25_epoch_pending[5]);
'''.replace('COMMAND !==', command + ' !==').replace('=SOURCE;', '=' + source + ';')



def cache_observer():
    return r'''
integer v25_fault_command_events=0,v25_invalid_cache_change_events=0;
integer v25_cache_i,v25_cache_changed;reg v25_cache_fault_edge=0;
reg v25_cache_before[0:RING_DWORDS-1];
reg [3:0] v25_old_good_verdict;
always @(posedge clk_i) begin
 v25_cache_fault_edge=(rst_ni===1'b1 && candidate.framer.enabled===1'b1 &&
   candidate.framer.active_o===1'b1 && candidate.framer.command_valid===1'b1 &&
   candidate.framer.fault_now===1'b1);
 if(v25_cache_fault_edge) begin
  v25_old_good_verdict=candidate.framer.command_verdict_enable & candidate.framer.command_verdict_value;
  for(v25_cache_i=0;v25_cache_i<RING_DWORDS;v25_cache_i=v25_cache_i+1)
   v25_cache_before[v25_cache_i]=candidate.framer.slot_verdict[v25_cache_i];
 end
 #0.002;
 if(v25_cache_fault_edge) begin
  if({candidate.framer.command_valid,candidate.framer.visible_commit_ptr,
      candidate.framer.commit_ptr,candidate.framer.write_ptr,candidate.framer.read_ptr,
      candidate.framer.output_valid,candidate.framer.retire_valid,candidate.framer.active_o}!==0 ||
      candidate.framer.halted_o!==1)
   $fatal(1,"V25_FAULT_COMMAND_CACHE_QUARANTINE");
  if(v25_old_good_verdict!=0) begin
   v25_fault_command_events=v25_fault_command_events+1;v25_cache_changed=0;
   for(v25_cache_i=0;v25_cache_i<RING_DWORDS;v25_cache_i=v25_cache_i+1)
    if(candidate.framer.slot_verdict[v25_cache_i] !== v25_cache_before[v25_cache_i]) v25_cache_changed=1;
   if(v25_cache_changed) v25_invalid_cache_change_events=v25_invalid_cache_change_events+1;
  end
 end
end
'''



def canonical_observer():
    return '// Read-only V25/V26 known-public-control comparison and actual fault write.\ninteger v26_public_cycles=0,v26_fault_commands=0,v26_canonical_changes=0;\ninteger v26_c,v26_l,v26_changed;\nreg v26_fault_edge;\nreg [3:0] v26_enable_before,v26_value_before;\nreg [4*CPW-1:0] v26_tags_before;\nreg v26_before[0:2*RING_DWORDS-1],v26_reference_before[0:2*RING_DWORDS-1];\nreg v26_expected[0:2*RING_DWORDS-1];\nalways @(posedge clk_i) begin\n v26_fault_edge=(rst_ni===1\'b1 && candidate.framer.enabled===1\'b1 &&\n   candidate.framer.active_o===1\'b1 && candidate.framer.command_valid===1\'b1 &&\n   candidate.framer.fault_now===1\'b1);\n if(v26_fault_edge) begin\n  v26_enable_before=candidate.framer.command_verdict_enable;\n  v26_value_before=candidate.framer.command_verdict_value;\n  v26_tags_before=candidate.framer.command_verdict_tags;\n  for(v26_c=0;v26_c<2*RING_DWORDS;v26_c=v26_c+1) begin\n   v26_before[v26_c]=candidate.framer.verdict[v26_c];\n   v26_reference_before[v26_c]=v26_reference.framer.verdict[v26_c];\n   v26_expected[v26_c]=candidate.framer.verdict[v26_c];\n  end\n  for(v26_l=0;v26_l<4;v26_l=v26_l+1)\n   if(v26_enable_before[v26_l]) v26_expected[v26_tags_before[v26_l*CPW+:CPW]]=v26_value_before[v26_l];\n end\n #0.004;\n if(rst_ni===1\'b1) begin\n  if({valid_o,packet_good_o,packet_nullified_o,packet_crc_bad_o,packet_dllp_o,packet_sequence_o,framing_error_o,stream_end_o,active_o,halted_o,overflow_o} !== {v26_gold_valid_o,v26_gold_packet_good_o,v26_gold_packet_nullified_o,v26_gold_packet_crc_bad_o,v26_gold_packet_dllp_o,v26_gold_packet_sequence_o,v26_gold_framing_error_o,v26_gold_stream_end_o,v26_gold_active_o,v26_gold_halted_o,v26_gold_overflow_o}) $fatal(1,"V26_PUBLIC_CONTROL_CYCLE");\n  if(valid_o && {data_o,keep_o,sop_o,eop_o,dllp_o,sequence_o} !== {v26_gold_data_o,v26_gold_keep_o,v26_gold_sop_o,v26_gold_eop_o,v26_gold_dllp_o,v26_gold_sequence_o}) $fatal(1,"V26_PUBLIC_OWNED_PAYLOAD_CYCLE");\n  v26_public_cycles=v26_public_cycles+1;\n end\n if(v26_fault_edge) begin\n  v26_changed=0;\n  for(v26_c=0;v26_c<2*RING_DWORDS;v26_c=v26_c+1) begin\n   if(candidate.framer.verdict[v26_c] !== v26_expected[v26_c])\n    $fatal(1,"V26_CANONICAL_OLD_COMMAND_WRITE");\n   if(v26_reference.framer.verdict[v26_c] !== v26_reference_before[v26_c])\n    $fatal(1,"V26_REFERENCE_FAULT_CANONICAL_HOLD");\n   if(v26_before[v26_c]===1\'b0 && v26_reference_before[v26_c]===1\'b0 &&\n      candidate.framer.verdict[v26_c]===1\'b1 && v26_reference.framer.verdict[v26_c]===1\'b0)\n    v26_changed=1;\n  end\n  if((v26_enable_before & v26_value_before)!=0) begin\n   v26_fault_commands=v26_fault_commands+1;\n   if(v26_changed) v26_canonical_changes=v26_canonical_changes+1;\n  end\n end\nend\nfinal $display("V26_CANONICAL_WITNESSES public_cycles=%0d fault_commands=%0d zero_to_one_reference_held=%0d",v26_public_cycles,v26_fault_commands,v26_canonical_changes);\n'

def header_observer():
    # Literal independent temporal observer from the retained V23 source; use
    # this candidate's parser as the reference late expression (not its cached
    # result), because the parser remains byte-identical and ring timing moved.
    path = ROOT / 'sw/tests/test_pcie_gen3_integrity_v23_miter.py'
    body = ast.parse(path.read_text()).body
    rows = [n for n in body if isinstance(n, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id == 'HEADER_OBSERVER' for t in n.targets)]
    assert len(rows) == 1
    return ast.literal_eval(rows[0].value).replace('reference.framer', 'candidate.framer').replace('v23_', 'v25_').replace('V23_', 'V25_')


def wrap(directory, nominal=False, fault=None):
    directory.mkdir()
    for name in ('soc_pcie_gen3_ingress_integrity_v11', 'soc_pcie_gen3_data_descrambler',
                 'soc_pcie_gen3_framer_rx_integrity_v26'):
        shutil.copyfile(RTL / (name + '.v'), directory / (name + '.v'))
    wrapper = (RTL / (TOP + '.v')).read_text()
    header = wrapper.split(');', 1)[0] + ');\n'
    core = wrapper.replace('module ' + TOP + ' #(', 'module ' + TOP + '_core #(', 1)
    def instance(module, name, prefix=''):
        pairs = [f'.{n}({n})' for n in INPUTS] + [f'.{n}({prefix}{n})' for n in OUTPUTS]
        return module + ' #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) ' + name + '(' + ','.join(pairs) + ');'
    pieces = ['`timescale 1ns/1ps', header, instance(TOP + '_core', 'candidate'), observer(), header_observer(), cache_observer()]
    pieces += ['wire ' + (f'[{w-1}:0] ' if w > 1 else '') + 'v26_gold_' + n + ';' for n, w in OUTPUTS.items()]
    pieces.append(instance(TOP.replace('_v26', '_v25'), 'v26_reference', 'v26_gold_'))
    pieces.append(canonical_observer())
    aliases = {'retire_valid': 1, 'retire_has_data': 1, 'output_valid': 1, 'retire_pop': 1,
               'retire': 1, 'fault_now': 1, 'command_valid': 1,
               'read_ptr': '$clog2(RING_DWORDS)+1', 'write_ptr': '$clog2(RING_DWORDS)+1',
               'commit_ptr': '$clog2(RING_DWORDS)+1', 'visible_commit_ptr': '$clog2(RING_DWORDS)+1'}
    pieces.append('generate if(1) begin:framer')
    pieces += ['wire ' + (f'[{w}-1:0] ' if w != 1 else '') + n + '=candidate.framer.' + n + ';' for n, w in aliases.items()]
    pieces.append('end endgenerate')
    if nominal:
        pieces += ['wire ' + (f'[{w-1}:0] ' if w > 1 else '') + 'gold_' + n + ';' for n, w in OUTPUTS.items()]
        pieces.append(instance(TOP.replace('_v26', '_v23'), 'reference', 'gold_'))
        def bundle(names, prefix=''):
            return '{' + ','.join(prefix + n for n in names) + '}'
        width = sum(OUTPUTS[n] for n in PAYLOAD)
        pieces.append(f'''reg [{width-1}:0] v25_old_gold;reg v25_nominal_checked;
integer v25_nominal_comparisons=0,v25_nominal_payloads=0;
always @(posedge clk_i) begin
 v25_nominal_checked=rst_ni && !flush_i && !stream_start_i && !stream_abort_i && ready_i && active_o && gold_active_o;
 v25_old_gold={bundle(PAYLOAD,'gold_')};
 #0.003;
 if(v25_nominal_checked && active_o && gold_active_o) begin
  if(framing_error_o || gold_framing_error_o || overflow_o || gold_overflow_o) $fatal(1,"V25_NOMINAL_SCOPE_FAULT");
  if({bundle(PAYLOAD)} !== v25_old_gold) $fatal(1,"V25_NOMINAL_PLUS_ONE_PAYLOAD");
  if({bundle(EVENTS)} !== {bundle(EVENTS,'gold_')}) $fatal(1,"V25_NOMINAL_PARSER_EVENTS");
  if({{candidate.framer.write_ptr,candidate.framer.commit_ptr,candidate.framer.state,candidate.framer.current_valid,candidate.framer.next_valid}} !==
     {{reference.framer.write_ptr,reference.framer.commit_ptr,reference.framer.state,reference.framer.current_valid,reference.framer.next_valid}})
    $fatal(1,"V25_NOMINAL_PARSER_CADENCE");
  v25_nominal_comparisons=v25_nominal_comparisons+1;
  if(valid_o) v25_nominal_payloads=v25_nominal_payloads+1;
 end
end
final begin
 if(v25_nominal_comparisons<100 || v25_nominal_payloads<10) $fatal(1,"V25_NOMINAL_REQUIRED_COVERAGE");
 $display("V25_NOMINAL_PLUS_ONE_PASS cycles=%0d payloads=%0d",v25_nominal_comparisons,v25_nominal_payloads);
end''')
    pieces += ['endmodule', core]
    pieces += [(RTL / (TOP.replace('_v26', '_v25') + '.v')).read_text(),
               (RTL / 'soc_pcie_gen3_framer_rx_integrity_v25.v').read_text()]
    if nominal:
        pieces += [(RTL / (TOP.replace('_v26', '_v23') + '.v')).read_text(),
                   (RTL / 'soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()]
    if fault:
        before, after = FAULTS[fault][:2]
        p = directory / 'soc_pcie_gen3_framer_rx_integrity_v26.v'
        text = p.read_text()
        assert text.count(before) == 1, (fault, text.count(before))
        p.write_text(text.replace(before, after))
    (directory / (TOP + '.v')).write_text('\n'.join(pieces))
    return directory


FAULTS = {
    'visible_commit_early': ('wire [PW-1:0] committed=visible_commit_ptr-read_ptr;',
                             'wire [PW-1:0] committed=commit_ptr-read_ptr;', 'sustained_minimum_packets_exceed_every_buffer', 'V25_COMMAND_VISIBLE_RETIRE_FRONTIER'),
    'fault_command_survives': ('else if((stream_abort_i && active_o) || fault_now) command_valid<=0;',
                              'else if((stream_abort_i && active_o) || fault_now) command_valid<=command_valid;', 'descriptor_parser_fault_cancels_queue_after_sampling_edge', 'V25_COMMAND_VALID_TRANSITION'),
    'flush_command_survives': ('else if(flush_i || stream_start_i) command_valid<=0;',
                              'else if(flush_i || stream_start_i) command_valid<=command_valid;', 'command_pending_epoch_controls_and_fresh_reuse', 'V25_COMMAND_VALID_TRANSITION'),
    'apply_requires_step': ('if(rst_ni && enabled && command_valid) begin', 'if(rst_ni && enabled && command_valid && step) begin',
                           'sustained_minimum_packets_exceed_every_buffer', 'V25_COMMAND_VISIBLE_COMMIT_EDGE'),
    'ending_drops_command': ('if(rst_ni && enabled && command_valid) begin', 'if(rst_ni && enabled && command_valid && !ending) begin',
                            'edb_quarantine_and_eds_release_drain', 'V25_COMMAND_VISIBLE_COMMIT_EDGE'),
    'new_data_old_tag': ('command_tags<=write_tags;', 'command_tags<=command_tags;',
                         'sustained_minimum_packets_exceed_every_buffer', 'V25_COMMAND_ATOMIC_CAPTURE'),
    'replay_command': ('command_valid<=0;\n       if(step) command_valid<=1;',
                       'command_valid<=command_valid;\n       if(step) command_valid<=1;', 'sustained_minimum_packets_exceed_every_buffer', 'V25_COMMAND_VALID_TRANSITION'),
    'payload_bypass': ('slot_data[(command_address+command_lane)&(RING_DWORDS-1)]<=command_data[command_lane*32+:32];',
                       'slot_data[(command_address+command_lane)&(RING_DWORDS-1)]<=write_data[command_lane*32+:32];',
                       'sustained_minimum_packets_exceed_every_buffer', 'V25_NOMINAL_PLUS_ONE_PAYLOAD'),
}


def helper():
    return runpy.run_path(str(ROOT / 'sw/tests/test_pcie_gen3_continuous_rx_integrity_v26.py'))


def test_actual_all_public_transactions_with_command_and_bank_observers(tmp_path):
    r, record, cases, out = helper()['run'](tmp_path, rtl=wrap(tmp_path / 'rtl'))
    assert r.returncode == 0 and record['tests'] == {'passed': 19, 'failed': 0, 'skipped': 0}, record
    assert len(cases) == 19 and all(c.find('failure') is None for c in cases)
    text = (out / 'simulation.log').read_text()
    match = re.search(r'V25_COMMAND_DUT_WITNESSES commands=(\d+) applies=(\d+) bubble=(\d+) ending=(\d+) replacements=(\d+) wraps=(\d+) zero=(\d+) epochs=([0-9,]+)', text)
    assert match, text
    counts = [int(x) for x in match.groups()[:7]]
    epochs = [int(x) for x in match.group(8).split(',')]
    assert all(x > 0 for x in counts) and all(x > 0 for x in epochs), (counts, epochs)
    cache = re.search(r'V25_CACHE_QUARANTINE epochs=(\d+) actual_fault_steps=(\d+) invalid_cache_changes=(\d+)', text)
    assert cache, 'Mandatory V25 old-command cache observer was not visible at runtime'
    cache_counts = [int(x) for x in cache.groups()]
    assert cache_counts[0] == 8 and min(cache_counts[1:]) >= 8, cache_counts
    canonical = re.search(r'V26_CANONICAL_WITNESSES public_cycles=(\d+) fault_commands=(\d+) zero_to_one_reference_held=(\d+)', text)
    assert canonical, 'Mandatory V26/V25 canonical observer was not visible'
    canonical_counts = [int(x) for x in canonical.groups()]
    assert canonical_counts[0] > 100 and min(canonical_counts[1:]) >= 8, canonical_counts
    (out / 'v25-command-witnesses.json').write_text(json.dumps(dict(counts=counts, epoch_counts=epochs,
        cache_quarantine_counts=cache_counts, canonical_quarantine_counts=canonical_counts,
        scope='Actual 19 independent public transaction cases; no general V23 cycle equivalence.'), indent=2) + '\n')


@pytest.mark.parametrize('case', ('sustained_minimum_packets_exceed_every_buffer', 'tlp_crc_coverage_residue_nullification_and_successor'))
def test_actual_nominal_ready_one_plus_one(tmp_path, case):
    r, record, cases, out = helper()['run'](tmp_path, rtl=wrap(tmp_path / 'rtl', nominal=True), case=case)
    assert r.returncode == 0 and len(cases) == 1 and cases[0].find('failure') is None, record
    assert 'V25_NOMINAL_PLUS_ONE_PASS' in (out / 'simulation.log').read_text()


@pytest.mark.parametrize('fault', FAULTS)
def test_actual_full_dut_command_fault_rejected(tmp_path, fault):
    _, _, case, diagnostic = FAULTS[fault]
    r, record, cases, out = helper()['run'](tmp_path,
        rtl=wrap(tmp_path / 'rtl', nominal=fault == 'payload_bypass', fault=fault), case=case)
    text = (out / 'simulation.log').read_text()
    assert r.returncode != 0 and record['status'] == 'FAIL', record
    assert diagnostic in text, (fault, diagnostic, text)
    assert 'syntax error' not in text.lower()


def test_actual_restored_fault_qualification_rejected_by_canonical_witness(tmp_path):
    fault = 'canonical_fault_qualification_restored'
    FAULTS[fault] = ('if(rst_ni && enabled && active_o && command_valid) begin',
                     'if(rst_ni && enabled && active_o && command_valid && !fault_now) begin',
                     'cache_fault_write_and_new_epoch_reuse', 'V26_CANONICAL_OLD_COMMAND_WRITE')
    try:
        _, _, case, diagnostic = FAULTS[fault]
        r, record, cases, out = helper()['run'](tmp_path, rtl=wrap(tmp_path / 'rtl', fault=fault), case=case)
        text = (out / 'simulation.log').read_text()
        assert r.returncode != 0 and record['status'] == 'FAIL', record
        assert diagnostic in text and 'syntax error' not in text.lower(), text
    finally:
        del FAULTS[fault]
