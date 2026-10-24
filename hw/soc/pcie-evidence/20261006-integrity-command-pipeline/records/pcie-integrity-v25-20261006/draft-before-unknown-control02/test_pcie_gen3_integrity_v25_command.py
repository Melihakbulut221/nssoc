# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual extracted writers: explicit one-edge relation and epoch ownership.

This is a component relation, not a full-DUT equivalence or timing claim.
"""
from pathlib import Path
import importlib.util
import os
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'hw/soc/rtl/pcie'
spec = importlib.util.spec_from_file_location(
    'v25_generator', ROOT / 'scripts/generate_pcie_integrity_command_v25.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def marked(text, begin, end):
    start = text.index(begin)
    finish = text.index(end, start) + len(end)
    return text[start:finish]


def writer(name, text, candidate):
    arrays = marked(text, ' reg [31:0] slot_data',
                    ' reg slot_verdict [0:RING_DWORDS-1];')
    cache = marked(text, ' // BEGIN V6 SHARED OLD VERDICT READS',
                   ' // END V5 SLOT VERDICT CACHE')
    header = '''module NAME(
 input clk_i,rst_ni,flush_i,stream_start_i,stream_abort_i,
 input active_o,enabled,step,fault_now,ending,
 input [4:0] write_ptr,commit_n,
 input [127:0] write_data,
 input [15:0] write_keep,write_sop,write_eop,write_dllp,
 input [47:0] write_sequence,
 input [19:0] write_tags,verdict_tags,
 input [3:0] verdict_enable,verdict_value);
 localparam RING_DWORDS=16,PW=5;
'''.replace('NAME', name)
    if candidate:
        declarations = marked(text, ' // BEGIN V25 REGISTERED PARSER TO RING COMMAND',
                              ' // END V25 REGISTERED PARSER TO RING COMMAND')
        capture = marked(text, ' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP',
                         ' // END V25 COMMAND CAPTURE AND EPOCH OWNERSHIP')
        apply = marked(text, '       // BEGIN V25 APPLY OLD COMMAND',
                       '       // END V25 APPLY OLD COMMAND')
        body = ' integer command_lane;\n' + capture + '\n'
    else:
        declarations = ' reg [PW-1:0] visible_commit_ptr;\n'
        body = ' integer w;\n'
        assert text.count(generator.OLD_WRITES) == 1
        apply = ('       if(step) begin\n'
                 '         visible_commit_ptr<=commit_n;\n' +
                 generator.OLD_WRITES + '       end\n')
    body += ''' always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) visible_commit_ptr<=0;
   else if(flush_i || stream_start_i) visible_commit_ptr<=0;
   else if((stream_abort_i && active_o) || fault_now) visible_commit_ptr<=0;
   else if(active_o) begin
''' + apply + '\n   end\n end\n'
    return header + arrays + '\n' + declarations + '\n' + cache + '\n' + body + 'endmodule\n'


TB = r'''
module tb;
 reg clk_i=0,rst_ni=0,flush_i=0,stream_start_i=0,stream_abort_i=0;
 reg active_o=1,drive=0,fault_now=0,ending=0;
 wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;
 wire step=enabled && active_o && drive && !ending;
 reg [4:0] write_ptr=0,commit_n=0;
 reg [127:0] write_data=0;
 reg [15:0] write_keep=0,write_sop=0,write_eop=0,write_dllp=0;
 reg [47:0] write_sequence=0;
 reg [19:0] write_tags=0,verdict_tags=0;
 reg [3:0] verdict_enable=0,verdict_value=0;
 reference ref_dut(.*);
 candidate dut(.*);
 reg [64:0] saved_slot[0:15];
 reg saved_cache[0:15],saved_verdict[0:31];
 reg [4:0] saved_commit;
 integer i,t,l,seed=19373,comparisons=0,bubbles=0,replace_count=0,ending_apply=0;
 integer old_valid,epoch_checks=0;
 task tick;
 input compare_arrays;
 begin
  clk_i=0;#1;
  for(i=0;i<16;i=i+1) begin
   saved_slot[i]={ref_dut.slot_data[i],ref_dut.slot_keep[i],ref_dut.slot_sop[i],
    ref_dut.slot_eop[i],ref_dut.slot_dllp[i],ref_dut.slot_sequence[i],ref_dut.slot_tag[i]};
   saved_cache[i]=ref_dut.slot_verdict[i];
  end
  for(i=0;i<32;i=i+1) saved_verdict[i]=ref_dut.verdict[i];
  saved_commit=ref_dut.visible_commit_ptr;old_valid=dut.command_valid;
  if(compare_arrays && old_valid===1 && step===1) replace_count=replace_count+1;
  if(compare_arrays && old_valid===1 && step===0) bubbles=bubbles+1;
  if(compare_arrays && old_valid===1 && ending===1) ending_apply=ending_apply+1;
  clk_i=1;#1;
  if(compare_arrays) begin
   for(i=0;i<16;i=i+1) begin
    if({dut.slot_data[i],dut.slot_keep[i],dut.slot_sop[i],dut.slot_eop[i],
       dut.slot_dllp[i],dut.slot_sequence[i],dut.slot_tag[i]} !== saved_slot[i])
      $fatal(1,"V25_COMMAND_SLOT_DELAY trial=%0d slot=%0d",t,i);
    if(dut.slot_verdict[i] !== saved_cache[i])
      $fatal(1,"V25_COMMAND_CACHE_DELAY trial=%0d slot=%0d",t,i);
   end
   for(i=0;i<32;i=i+1) if(dut.verdict[i] !== saved_verdict[i])
     $fatal(1,"V25_COMMAND_VERDICT_DELAY trial=%0d tag=%0d",t,i);
   if(dut.visible_commit_ptr !== saved_commit)
     $fatal(1,"V25_COMMAND_COMMIT_DELAY trial=%0d",t);
   if(dut.command_valid !== (step===1'b1))
     $fatal(1,"V25_COMMAND_BUBBLE_VALID trial=%0d",t);
   comparisons=comparisons+1;
  end
  clk_i=0;#1;
 end
 endtask
 initial begin
  tick(0);rst_ni=1;
  for(t=0;t<4096;t=t+1) begin
   drive=(t%7)!=6;ending=0;
   write_ptr=t*4;commit_n=write_ptr+4;
   write_data={$random(seed),$random(seed),$random(seed),$random(seed)};
   write_keep=$random(seed);write_sop=$random(seed);write_eop=$random(seed);
   write_dllp=$random(seed);write_sequence={$random(seed),$random(seed)};
   for(l=0;l<4;l=l+1) begin
    write_tags[l*5+:5]=(t/3+l)%32;
    verdict_tags[l*5+:5]=(t/5+(l%2))%32;
   end
   verdict_enable=t;verdict_value=t>>4;
   // Literal X/Z in every command payload/metadata class. Unknown verdict
   // enable/tag values retain the actual original procedural-if semantics.
   case(t%16)
    0:write_data[13]=1'bz;
    1:write_keep[7]=1'bx;
    2:write_sop[2]=1'bz;
    3:write_eop[15]=1'bx;
    4:write_dllp[9]=1'bz;
    5:write_sequence[33]=1'bz;
    6:write_tags[0]=1'bx;
    7:verdict_tags[8]=1'bz;
    8:verdict_enable[1]=1'bx;
    9:verdict_value[2]=1'bz;
    10:commit_n[0]=1'bx;
    default:begin end
   endcase
   tick(1);
  end
  // Explicitly capture a pending final command, then apply it while ending.
  drive=1;ending=0;write_ptr=4;commit_n=8;write_data=~write_data;
  write_keep=16'hffff;write_tags=20'habcde;
  tick(1);drive=0;ending=1;tick(1);ending=0;tick(1);
  if(comparisons!=4099 || bubbles==0 || replace_count==0 || ending_apply!=1)
   $fatal(1,"V25_COMMAND_REQUIRED_RELATION_WITNESS");
  // Epoch controls are a separate validity/frontier property. Discarded raw
  // array contents need not equal the old immediate writer after a fault.
  for(t=0;t<5;t=t+1) begin
   drive=1;write_data=128'h123456789abcdef;tick(0);
   if(dut.command_valid!==1) $fatal(1,"V25_COMMAND_PENDING_EPOCH_WITNESS");
   drive=0;
   case(t)
    0:flush_i=1;
    1:stream_start_i=1;
    2:stream_abort_i=1;
    3:fault_now=1;
    4:rst_ni=0;
   endcase
   tick(0);
   if(dut.command_valid!==0 || dut.visible_commit_ptr!==0)
    $fatal(1,"V25_COMMAND_EPOCH_DISCARD kind=%0d",t);
   flush_i=0;stream_start_i=0;stream_abort_i=0;fault_now=0;rst_ni=1;
   tick(0);
   if(dut.command_valid!==0 || dut.visible_commit_ptr!==0)
    $fatal(1,"V25_COMMAND_STALE_EPOCH_REPLAY kind=%0d",t);
   epoch_checks=epoch_checks+1;
  end
  $display("V25_COMMAND_RELATION_PASS comparisons=%0d bubbles=%0d replace=%0d ending=%0d epochs=%0d",
    comparisons,bubbles,replace_count,ending_apply,epoch_checks);
  $finish;
 end
endmodule
'''

FAULTS = (
    ('data_zero', 'command_data<=write_data;', "command_data<=128'b0;", 'V25_COMMAND_SLOT_DELAY'),
    ('tag_zero', 'command_tags<=write_tags;', "command_tags<=0;", 'V25_COMMAND_SLOT_DELAY'),
    ('verdict_invert', 'command_verdict_value<=verdict_value;', 'command_verdict_value<=~verdict_value;', 'V25_COMMAND_CACHE_DELAY'),
    ('commit_early', 'visible_commit_ptr<=command_commit;', 'visible_commit_ptr<=commit_n;', 'V25_COMMAND_COMMIT_DELAY'),
    ('apply_needs_step', 'if(enabled && command_valid) begin', 'if(enabled && command_valid && step) begin', 'V25_COMMAND_SLOT_DELAY'),
    ('ending_blocks', 'if(enabled && command_valid) begin', 'if(enabled && command_valid && !ending) begin', 'V25_COMMAND_SLOT_DELAY'),
    ('bubble_replays', 'command_valid<=0;\n     if(step) command_valid<=1;', 'command_valid<=command_valid;\n     if(step) command_valid<=1;', 'V25_COMMAND_BUBBLE_VALID'),
    ('flush_survives', 'else if(flush_i || stream_start_i) command_valid<=0;', 'else if(flush_i || stream_start_i) command_valid<=command_valid;', 'V25_COMMAND_EPOCH_DISCARD'),
    ('fault_survives', 'else if((stream_abort_i && active_o) || fault_now) command_valid<=0;', 'else if((stream_abort_i && active_o) || fault_now) command_valid<=command_valid;', 'V25_COMMAND_EPOCH_DISCARD'),
)


def test_complete_v25_inverse():
    generated, edits = generator.generate()
    actual = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v25.v').read_text()
    assert actual == generated
    assert generator.inverse(actual, edits) == generator.BASE.read_text()


@pytest.mark.parametrize('fault', (None, *FAULTS), ids=('positive', *(row[0] for row in FAULTS)))
def test_actual_command_temporal_relation(tmp_path, fault):
    old = generator.BASE.read_text()
    new = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v25.v').read_text()
    if fault:
        _, before, after, _ = fault
        assert new.count(before) == 1
        new = new.replace(before, after)
    source = tmp_path / 'command.v'
    source.write_text(writer('reference', old, False) + writer('candidate', new, True) + TB)
    compiler, runtime = shutil.which('iverilog'), shutil.which('vvp')
    assert compiler and runtime, 'Actual Icarus required; never skip'
    binary = tmp_path / 'command.vvp'
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE')}
    with (tmp_path / 'compile.log').open('w') as stream:
        compile_result = subprocess.run([compiler, '-g2012', '-s', 'tb', '-o', str(binary), str(source)],
                                        stdout=stream, stderr=subprocess.STDOUT, env=environment)
    assert compile_result.returncode == 0, (tmp_path / 'compile.log').read_text()
    with (tmp_path / 'simulation.log').open('w') as stream:
        result = subprocess.run([runtime, str(binary)], stdout=stream,
                                stderr=subprocess.STDOUT, env=environment)
    log = (tmp_path / 'simulation.log').read_text()
    if fault:
        assert result.returncode != 0 and fault[3] in log, log
        assert 'V25_COMMAND_RELATION_PASS' not in log
    else:
        assert result.returncode == 0, log
        assert 'V25_COMMAND_RELATION_PASS comparisons=4099' in log and 'ending=1 epochs=5' in log
