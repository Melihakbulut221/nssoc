# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restricted ready=1 +one-cycle relation, not stall/fault/epoch equivalence."""
from pathlib import Path
import re
import runpy
import shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'hw/soc/rtl/pcie'
TOP='soc_pcie_gen3_continuous_rx_integrity_v21'
INPUTS=('clk_i','rst_ni','flush_i','stream_start_i','stream_abort_i','word_i','ready_i')
OUTPUTS={'valid_o':1,'data_o':128,'keep_o':16,'sop_o':16,'eop_o':16,'dllp_o':16,'sequence_o':48,'packet_good_o':4,'packet_nullified_o':4,'packet_crc_bad_o':4,'packet_dllp_o':4,'packet_sequence_o':48,'framing_error_o':1,'stream_end_o':1,'active_o':1,'halted_o':1,'overflow_o':1}
PAYLOAD=tuple(list(OUTPUTS)[:7])
EVENTS=('packet_good_o','packet_nullified_o','packet_crc_bad_o','packet_dllp_o','packet_sequence_o')
CASES=('sustained_minimum_packets_exceed_every_buffer','tlp_crc_coverage_residue_nullification_and_successor')


def miter(directory,fault=None):
 directory.mkdir()
 for name in ('soc_pcie_gen3_ingress_integrity_v11','soc_pcie_gen3_data_descrambler','soc_pcie_gen3_framer_rx_integrity_v21'):
  shutil.copyfile(RTL/(name+'.v'),directory/(name+'.v'))
 wrapper=(RTL/(TOP+'.v')).read_text();header=wrapper.split(');',1)[0]+');\n'
 core=wrapper.replace('module '+TOP+' #(','module '+TOP+'_core #(',1)
 decl=['wire '+(f'[{w-1}:0] ' if w>1 else '')+'gold_'+n+';' for n,w in OUTPUTS.items()]
 def instance(module,name,gold):
  pairs=[f'.{x}({x})' for x in INPUTS]+[f'.{x}({"gold_" if gold else ""}{x})' for x in OUTPUTS]
  return module+' #(.MAX_ENCODED_BYTES(MAX_ENCODED_BYTES),.RING_DWORDS(RING_DWORDS)) '+name+'('+','.join(pairs)+');'
 def bundle(names,prefix=''):return '{'+','.join(prefix+x for x in names)+'}'
 width=sum(OUTPUTS[k] for k in PAYLOAD)
 compare=f'''reg [{width-1}:0] old_gold;reg checked;integer comparisons=0;
 always @(posedge clk_i) begin
 checked=rst_ni && !flush_i && !stream_start_i && !stream_abort_i && ready_i && active_o && gold_active_o;
 old_gold={bundle(PAYLOAD,'gold_')};
 #0.001;
 if(checked && active_o && gold_active_o) begin
  if(framing_error_o || gold_framing_error_o || overflow_o || gold_overflow_o) $fatal(1,"V21_NOMINAL_SCOPE_FAULT");
  if({bundle(PAYLOAD)} !== old_gold) $fatal(1,"V21_EXPLICIT_ONE_CYCLE_RELATION");
  if({bundle(EVENTS)} !== {bundle(EVENTS,'gold_')}) $fatal(1,"V21_NOMINAL_VERDICT_CADENCE");
  if({{candidate.framer.read_ptr,candidate.framer.write_ptr,candidate.framer.commit_ptr,candidate.framer.state,candidate.framer.current_valid,candidate.framer.next_valid}} !==
     {{reference.framer.read_ptr,reference.framer.write_ptr,reference.framer.commit_ptr,reference.framer.state,reference.framer.current_valid,reference.framer.next_valid}}) $fatal(1,"V21_NOMINAL_RING_CADENCE");
  comparisons=comparisons+1;
 end
 end
 final begin
 if(comparisons<100) $fatal(1,"V21_NOMINAL_COVERAGE");
 $display("V21_NOMINAL_ONE_CYCLE_COMPARE %0d",comparisons);
 end
'''
 text='`timescale 1ns/1ps\n'+'\n'.join([header,*decl,instance(TOP+'_core','candidate',False),instance(TOP.replace('_v21','_v17'),'reference',True),compare,'endmodule',core,(RTL/(TOP.replace('_v21','_v17')+'.v')).read_text(),(RTL/'soc_pcie_gen3_framer_rx_integrity_v17.v').read_text()])
 if fault:
  p=directory/'soc_pcie_gen3_framer_rx_integrity_v21.v';s=p.read_text()
  before='output_data<=retire_data;';after='output_data<=read_data;'
  assert fault=='bypass_registered_payload' and s.count(before)==1
  p.write_text(s.replace(before,after))
 (directory/(TOP+'.v')).write_text(text)
 return directory


@pytest.mark.parametrize('case',CASES)
def test_actual_ready_one_explicit_latency(tmp_path,case):
 helper=runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v21.py'))
 r,record,cases,out=helper['run'](tmp_path,rtl=miter(tmp_path/'rtl'),case=case)
 assert r.returncode==0 and len(cases)==1 and cases[0].find('failure') is None,record
 assert re.search(r'V21_NOMINAL_ONE_CYCLE_COMPARE [1-9][0-9]+',(out/'simulation.log').read_text())


def test_actual_latency_bypass_mutant_rejected(tmp_path):
 helper=runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v21.py'))
 r,record,cases,out=helper['run'](tmp_path,rtl=miter(tmp_path/'rtl','bypass_registered_payload'),case=CASES[0])
 log=(out/'simulation.log').read_text()
 assert r.returncode!=0 and record['status']=='FAIL' and 'V21_EXPLICIT_ONE_CYCLE_RELATION' in log,log
