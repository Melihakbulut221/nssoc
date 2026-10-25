# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual accepted-block transaction scoreboards at minimum and normal rings.

Inherited V23 scalar packet encoder/byte scoreboard, with all cycle comparisons
removed explicitly. The candidate is the sole consumer. No internal forcing.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import resource
import runpy
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'hw/soc/rtl/pcie'
PARENT = ROOT / 'sw/tests/test_pcie_gen3_integrity_v23_block_burst.py'
ARCH = ROOT / 'sw/tests/test_pcie_gen3_integrity_v26_architecture.py'


def stimulus(minimum):
    old = runpy.run_path(str(PARENT))
    if not minimum:
        return old['stimulus']()
    # The minimum-ring traffic is 128 real minimum TLPs with no ready stalls;
    # the original scalar encoder remains the independent source of bytes.
    import ast
    import zlib
    bench = old['BENCH']
    names = {'crc4', 'tlp', 'wire_tlp'}
    body = [node for node in ast.parse(bench.read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {n.name for n in body} == names
    namespace = {'zlib': zlib}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(bench), 'exec'), namespace)
    packets = [namespace['tlp'](0x100 + n) for n in range(128)]
    raw = bytes(60) + b''.join(namespace['wire_tlp'](p) for p in packets)
    raw += bytes((60 - len(raw)) % 64) + bytes.fromhex('1f809000')
    blocks = [sum(raw[off+4*w+l] << (128*l+8*w) for l in range(4) for w in range(16))
              for off in range(0, len(raw), 64)]
    expected = [(byte, i == 0, i == len(p)-1, int.from_bytes(p[:2], 'big'))
                for p in packets for i, byte in enumerate(p)]
    return blocks, expected, len(packets)


def bench(blocks, expected, packets, minimum):
    old = runpy.run_path(str(PARENT))
    s = old['bench'](blocks, expected, packets)
    # Keep the entire independent byte/metadata and promotion scoreboard. The
    # architecture changes latency, so remove exactly the whole public cycle
    # miter and the old reference instance, never relax a failed comparison.
    lines = s.splitlines(keepends=True)
    removed = [line for line in lines if ' reference(' in line or 'V23_FRAMER_PUBLIC_MITER' in line]
    assert len(removed) == 2
    s = ''.join(line for line in lines if line not in removed)
    s = s.replace('soc_pcie_gen3_framer_rx_integrity_v23', 'soc_pcie_gen3_framer_rx_integrity_v26')
    s = s.replace('reference.step', 'candidate.step').replace('reference.slice', 'candidate.slice').replace('reference.next_valid', 'candidate.next_valid')
    s = s.replace('V23_', 'V25_')
    ring = 16 if minimum else 64
    maximum = 18 if minimum else 150
    s = s.replace('.MAX_ENCODED_BYTES(150),.RING_DWORDS(64)', f'.MAX_ENCODED_BYTES({maximum}),.RING_DWORDS({ring})')
    s = s.replace('module tb;', f'module tb;\nlocalparam RING_DWORDS={ring};')
    if minimum:
        before = 'ready_i=!(cycle_no%31==10 || cycle_no%31==11 || cycle_no%31==12);'
        assert s.count(before) == 1
        s = s.replace(before, 'ready_i=1;')
        s = s.replace(' || held_outputs<1', '')
    # Real line-rate parser runs, pending reservation and full extended-tag wraps.
    witness = r'''
integer v25_run=0,v25_longest=0,v25_accepted_blocks=0;
always @(posedge clk_i) begin
 if(rst_ni && !stream_start_i && candidate.step) begin
  v25_run=v25_run+1;if(v25_run>v25_longest) v25_longest=v25_run;
 end else v25_run=0;
 if(rst_ni && block_valid_i && block_ready_o) v25_accepted_blocks=v25_accepted_blocks+1;
end
final begin
 if(v25_longest<16 || v25_wraps<1 || v25_ending_applies!=1 || v25_replacements<16)
  $fatal(1,"V25_REAL_LINE_RATE_WRAP_OR_FINAL_COMMAND_WITNESS");
 $display("V25_REAL_LINE_RATE longest=%0d accepted=%0d extended_wraps=%0d",v25_longest,v25_accepted_blocks,v25_wraps);
end
'''
    observer = runpy.run_path(str(ARCH))['observer']().replace('candidate.framer.', 'candidate.')
    s = s.replace('endmodule', observer + witness + '\nendmodule')
    return s, removed


FAULTS = {
    'header_promote_stale': ('current_header_relation<=next_header_relation;', 'current_header_relation<=current_header_relation;', 'V25_FRAMER_PROMOTION_RELATION'),
    'ignore_reserved_pending': ('wire [PW-1:0] occupied=write_ptr-read_ptr;', 'wire [PW-1:0] occupied=write_ptr-read_ptr-(command_valid?4:0);', 'V25_RESERVED_CAPACITY_OCCUPANCY'),
}



def pending_fault_campaign(text, blocks, expected, packets):
    text = text.replace('module tb;', '''module tb;
reg v25_fault_mode=0;integer v25_fault_kind,v25_hit,v25_boundary_bytes;
integer v25_badblock_pending=0,v25_overflow_pending=0,v25_recovered=0;
reg v25_pending_before_fault;
''')
    before = 'if(framing_error_o || overflow_o || halted_o) $fatal(1,"V25_FRAMER_UNEXPECTED_FAULT");'
    assert text.count(before) == 1
    text = text.replace(before, 'if(!v25_fault_mode && (framing_error_o || overflow_o || halted_o)) $fatal(1,"V25_FRAMER_UNEXPECTED_FAULT");')
    before = 'if(packet_nullified_o[i] || packet_crc_bad_o[i] || packet_dllp_o[i]) $fatal(1,"V25_FRAMER_UNEXPECTED_VERDICT");'
    assert text.count(before) == 1
    text = text.replace(before, 'if(!v25_fault_mode && (packet_nullified_o[i] || packet_crc_bad_o[i] || packet_dllp_o[i])) $fatal(1,"V25_FRAMER_UNEXPECTED_VERDICT");')
    extension = f'''
 // Three real whole-framer fault boundaries. The same-edge public transfer
 // remains a real accepted byte transfer; only unaccepted epoch contents drop.
 for(v25_fault_kind=0;v25_fault_kind<3;v25_fault_kind=v25_fault_kind+1) begin
  v25_fault_mode=1;rst_ni=0;block_valid_i=0;block_error_i=0;ready_i=0;cycle;
  rst_ni=1;stream_start_i=1;cycle;stream_start_i=0;
  offset=0;accepted=0;good_count=0;end_count=0;v25_hit=0;
  for(cycle_no=0;cycle_no<{blocks*4+100};cycle_no=cycle_no+1) begin
   block_valid_i=(accepted<{blocks});if(block_valid_i) payload_i=blocks[accepted];
   ready_i=0;#0.01;
   if(v25_fault_kind<2 && candidate.command_valid && valid_o && block_ready_o && block_valid_i) begin
    ready_i=(v25_fault_kind==1);block_error_i=1;#0.01;
   end
   if(candidate.fault_now) begin
    v25_pending_before_fault=candidate.command_valid;
    v25_boundary_bytes=(valid_o && ready_i)?$countones(keep_o):0;
    if(!v25_pending_before_fault) $fatal(1,"V25_ACTUAL_PENDING_FAULT_WITNESS");
    if(v25_fault_kind<2 && (!candidate.bad_block_now || candidate.ring_overflow_now))
      $fatal(1,"V25_ACTUAL_BADBLOCK_NOT_CAPACITY_REQUIRED");
    if(v25_fault_kind==2 && !candidate.ring_overflow_now)
      $fatal(1,"V25_ACTUAL_CAPACITY_FAULT_REQUIRED");
    if((v25_fault_kind==1) != (v25_boundary_bytes>0))
      $fatal(1,"V25_ACTUAL_BADBLOCK_SAMPLING_EDGE_HANDSHAKE");
    cycle;
    if(candidate.command_valid!==0 || candidate.visible_commit_ptr!==0 ||
       candidate.commit_ptr!==0 || candidate.write_ptr!==0 || candidate.read_ptr!==0 ||
       candidate.retire_valid!==0 || candidate.output_valid!==0 || active_o!==0 || halted_o!==1)
      $fatal(1,"V25_PENDING_FAULT_ATOMIC_QUARANTINE");
    if(v25_fault_kind<2) v25_badblock_pending=v25_badblock_pending+1;
    else v25_overflow_pending=v25_overflow_pending+1;
    v25_hit=1;cycle_no={blocks*4+100};
   end else begin cycle;if(accepted_now) accepted=accepted+1;end
  end
  if(!v25_hit) $fatal(1,"V25_PENDING_FAULT_NEVER_REACHED");
  // Restart from public controls only and drain a complete accepted stream.
  // Distinct-sequence reuse is separately checked by the serial public case.
  block_error_i=0;block_valid_i=0;stream_start_i=1;ready_i=1;cycle;
  stream_start_i=0;v25_fault_mode=0;offset=0;accepted=0;good_count=0;end_count=0;
  for(cycle_no=0;cycle_no<{blocks*4+100};cycle_no=cycle_no+1) begin
   block_valid_i=(accepted<{blocks});if(block_valid_i) payload_i=blocks[accepted];
   ready_i=1;cycle;if(accepted_now) accepted=accepted+1;
  end
  if(accepted!={blocks} || offset!={expected} || good_count!={packets} || end_count!=1 || active_o)
    $fatal(1,"V25_PENDING_FAULT_RESTART_SCOREBOARD");
  v25_recovered=v25_recovered+1;
 end
 if(v25_badblock_pending!=2 || v25_overflow_pending!=1 || v25_recovered!=3)
   $fatal(1,"V25_PENDING_FAULT_REQUIRED_COUNTS");
 $display("V25_PENDING_FAULTS_PASS badblocks=2 overflow=1 recoveries=3");
'''
    assert text.count(' $finish;') == 1
    text = text.replace(' $finish;', extension + '\n $finish;')
    # Four independent completed streams each include one EDS command.
    text = text.replace('v25_ending_applies!=1', 'v25_ending_applies!=4')
    return text


def run_burst(directory, minimum=False, fault=None, pending_faults=False):
    directory.mkdir()
    dut = RTL / 'soc_pcie_gen3_framer_rx_integrity_v26.v'
    source = dut.read_text()
    if fault:
        before, after, _ = FAULTS[fault]
        assert source.count(before) == 1
        source = source.replace(before, after)
    actual = directory / dut.name
    actual.write_text(source)
    # Pending-fault prelude uses the already passing normal ring64/stall stream.
    # The separate 128-packet ring16/ready1 cadence and explicit ready0 overflow
    # boundary remain unchanged; a dense unbounded stalled prelude can overflow.
    blocks, expected, packets = stimulus(minimum)
    tb, removed = bench(blocks, expected, packets, minimum)
    if pending_faults:
        tb = pending_fault_campaign(tb, len(blocks), len(expected), packets)
    # This equation independently forbids phantom free-space credit for a
    # command whose parser has already reserved all four physical addresses.
    tb = tb.replace('endmodule', '''always @(negedge clk_i) begin
 #0.001;
 if(rst_ni && candidate.occupied !== ((candidate.write_ptr-candidate.read_ptr)&((2*RING_DWORDS)-1)))
  $fatal(1,"V25_RESERVED_CAPACITY_OCCUPANCY");
end
endmodule''')
    top = directory / 'tb.v'
    top.write_text(tb)
    (directory / 'removed-cycle-comparison.json').write_text(json.dumps(dict(
        scope='Explicit candidate-only transaction scoreboard, not cycle equivalence', removed_lines=removed), indent=2) + '\n')
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE')}
    compiler, runtime = shutil.which('iverilog'), shutil.which('vvp')
    assert compiler and runtime
    image = directory / 'sim.vvp'
    with (directory / 'compile.log').open('x') as log:
        result = subprocess.run([compiler, '-g2012', '-s', 'tb', '-o', str(image), str(top), str(actual)],
                                stdout=log, stderr=subprocess.STDOUT, env=environment, preexec_fn=limits)
    assert result.returncode == 0, (directory / 'compile.log').read_text()
    with (directory / 'simulation.log').open('x') as log:
        result = subprocess.run([runtime, str(image)], stdout=log, stderr=subprocess.STDOUT,
                                env=environment, preexec_fn=limits)
    text = (directory / 'simulation.log').read_text()
    def pin(p):
        return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (directory / 'result.json').write_text(json.dumps(dict(returncode=result.returncode, fault=fault,
        ring=16 if minimum else 64, maximum=18 if minimum else 150, blocks=len(blocks), bytes=len(expected), packets=packets,
        inputs={str(p): pin(p) for p in (Path(__file__), PARENT, ARCH, actual, top)},
        outputs={str(p): pin(p) for p in (image, directory/'compile.log', directory/'simulation.log')}), indent=2) + '\n')
    if fault:
        assert result.returncode != 0 and FAULTS[fault][2] in text, text
    else:
        assert result.returncode == 0 and 'PASS_V25_FRAMER_BURST' in text and 'V25_REAL_LINE_RATE' in text, text
        assert re.search(r'extended_wraps=[1-9][0-9]*', text)
        if pending_faults:
            assert 'V25_PENDING_FAULTS_PASS badblocks=2 overflow=1 recoveries=3' in text


@pytest.mark.parametrize('minimum', (True, False), ids=('minimum_ring16', 'ring64_stalls'))
def test_actual_accepted_block_transaction_cadence(tmp_path, minimum):
    run_burst(tmp_path/'burst', minimum)


@pytest.mark.parametrize('fault', FAULTS)
def test_actual_block_contract_fault_rejected(tmp_path, fault):
    run_burst(tmp_path/'burst', fault=fault)


def test_actual_pending_badblock_fault_edge_and_capacity_quarantine(tmp_path):
    run_burst(tmp_path/'fault_epochs', pending_faults=True)
