# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare all public ports against v1 across asynchronous epoch changes."""

import json
import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest

from test_pcie_gen3_receive_prefetch import bench

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_prefetch.v'
NEW = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_prefetch_v2.v'
INPUTS = ('clk_i rst_ni flush_i stream_start_i stream_abort_i block_valid_i '
          'headers_i payload_i block_error_i ready_i').split()
OUTPUTS = dict(block_ready_o=1, valid_o=1, data_o=8, sop_o=1, eop_o=1,
               dllp_o=1, packet_good_o=1, packet_nullified_o=1, sequence_o=12,
               framing_error_o=1, stream_end_o=1, active_o=1, halted_o=1)


def miter(candidate):
    original = OLD.read_text()
    name = 'soc_pcie_gen3_framer_rx_prefetch'
    header = original.split(' localparam', 1)[0].replace('output reg', 'output wire')
    declarations = '\n'.join(f'wire [{width-1}:0] candidate_{port};'
                              for port, width in OUTPUTS.items())
    reference_ports = ','.join(f'.{p}({p})' for p in INPUTS + list(OUTPUTS))
    candidate_ports = ','.join(f'.{p}({p})' for p in INPUTS) + ',' + ','.join(
        f'.{p}(candidate_{p})' for p in OUTPUTS)
    left = ','.join(OUTPUTS)
    right = ','.join('candidate_' + p for p in OUTPUTS)
    return original.replace('module ' + name, 'module reference_prefetch') + '\n' + candidate + '\n' + header + f'''
{declarations}
reference_prefetch #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) reference({reference_ports});
{name}_v2 #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES)) candidate({candidate_ports});
// Sample after nonblocking assignments settle, also on asynchronous controls.
always @(posedge clk_i or negedge clk_i or negedge rst_ni or
         posedge flush_i or posedge stream_start_i or posedge stream_abort_i) begin
  #1;
  if({{{left}}} !== {{{right}}}) $fatal(1,"PUBLIC_PORT_EQUIVALENCE_MISMATCH");
end
endmodule
'''


def exercise(tmp_path, capacity, candidate):
    stimulus = bench(capacity)
    anchor = '   tick;tick;rst_ni=1;stream_start_i=1;tick;stream_start_i=0;'
    assert stimulus.count(anchor) == 1
    # First exercise arbitrary public combinations without using the packet
    # scoreboard, then reset and replay its complete capacity-boundary stream.
    stimulus = stimulus.replace('integer received=0,', 'integer random_index;reg [31:0] rng=32\'h193ca572;integer received=0,')
    chaos = '''
   for(random_index=0;random_index<12000;random_index=random_index+1) begin
     rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
     rst_ni=(random_index%127!=0);
     flush_i=(random_index%113==0);stream_start_i=(random_index%109==0);
     stream_abort_i=(random_index%107==0);block_error_i=(random_index%103==0);
     block_valid_i=rng[3];ready_i=rng[7];headers_i=8'haa;
     payload_i=blocks[0];
     #3;clk_i=1;#3;clk_i=0;#3;
   end
   rst_ni=0;flush_i=0;stream_start_i=0;stream_abort_i=0;block_error_i=0;
   block_valid_i=0;ready_i=0;payload_i=0;
'''
    stimulus = stimulus.replace(anchor, chaos + anchor)
    source = tmp_path / 'miter.v'; source.write_text(miter(candidate))
    tb = tmp_path / 'tb.v'; tb.write_text(stimulus)
    installed = shutil.which('iverilog')
    tools = Path(installed).parent if installed else ROOT / 'hw/soc/tools/oss-cad-suite/bin'
    def pin(p):
        return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    pins = {str(p): pin(p) for p in (OLD, NEW, source, tb, tools/'iverilog', tools/'vvp')}
    compile_run = subprocess.run([str(tools/'iverilog'), '-g2012', '-s', 'tb', '-o',
                                  str(tmp_path/'sim.vvp'), str(source), str(tb)],
                                 capture_output=True, text=True, timeout=30)
    (tmp_path/'compile.log').write_text(compile_run.stdout + compile_run.stderr)
    assert compile_run.returncode == 0, compile_run.stderr
    run = subprocess.run([str(tools/'vvp'), str(tmp_path/'sim.vvp')],
                         capture_output=True, text=True, timeout=30)
    (tmp_path/'simulation.log').write_text(run.stdout + run.stderr)
    assert pins == {p: pin(Path(p)) for p in pins}
    (tmp_path/'result.json').write_text(json.dumps(dict(inputs=pins, returncode=run.returncode,
        capacity=capacity, arbitrary_control_cycles=12000, all_public_ports=True), indent=2)+'\n')
    return run


@pytest.mark.parametrize('capacity', [18, 31, 32, 33, 150, 4118])
def test_complete_public_ports_match_under_epoch_changes(tmp_path, capacity):
    result = exercise(tmp_path, capacity, NEW.read_text())
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('before,after', [
    ('wire enabled=rst_ni && !flush_i', 'wire enabled=rst_ni && 1\'b1'),
    ('if(flush_i || stream_start_i)', 'if(flush_i)'),
    ('if(read_next_pos==packet_bytes)', 'if(read_next_pos+1==packet_bytes)'),
])
def test_actual_epoch_or_retirement_fault_breaks_equivalence(tmp_path, before, after):
    candidate = NEW.read_text()
    assert candidate.count(before) == 1
    result = exercise(tmp_path, 150, candidate.replace(before, after))
    assert result.returncode != 0 and 'PUBLIC_PORT_EQUIVALENCE_MISMATCH' in result.stdout
