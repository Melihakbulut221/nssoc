# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual fault-edge payload writes, public cycle miter and packet oracle."""
from pathlib import Path
import json
import re
import runpy

import pytest

ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'hw/soc/rtl/pcie'
CASE='sustained_minimum_packets_exceed_every_buffer'
FAULTS={
    'bypass_pending_data':('<=command_data[v28_payload_lane*32+:32];','<=write_data[v28_payload_lane*32+:32];',CASE),
    'drop_byte_mask':('<=command_keep[v28_payload_lane*4+:4];',"<=4'b0;",CASE),
    'advance_write_address':('(command_address+v28_payload_lane)&(RING_DWORDS-1)',
                             '(write_ptr+v28_payload_lane)&(RING_DWORDS-1)',CASE),
    'lose_packet_tag':('<=command_tags[v28_payload_lane*PW+:PW];',"<=0;",'cache_fault_write_and_new_epoch_reuse'),
    'drop_final_payload':('if(rst_ni && enabled && active_o && command_valid) begin\n         for(v28_payload_lane=',
                          'if(rst_ni && enabled && active_o && command_valid && !ending) begin\n         for(v28_payload_lane=',
                          'edb_quarantine_and_eds_release_drain'),
}


def prepare(directory,fault=None):
    base=runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_integrity_v27_frontier.py'))
    base['prepare'](directory)
    text=(RTL/'soc_pcie_gen3_framer_rx_integrity_v28.v').read_text()
    if fault:
        before,after,_=FAULTS[fault]
        assert text.count(before)==(7 if fault=='advance_write_address' else 1)
        text=text.replace(before,after)
    # Test fixture alias only: the frozen V27 wrapper invokes this V28 logic.
    text=text.replace('module soc_pcie_gen3_framer_rx_integrity_v28 #(',
                      'module soc_pcie_gen3_framer_rx_integrity_v27 #(')
    (directory/'soc_pcie_gen3_framer_rx_integrity_v26.v').write_text(text)
    top=directory/'soc_pcie_gen3_continuous_rx_integrity_v26.v'
    s=top.read_text()
    observer=r'''
localparam V28PW=$clog2(RING_DWORDS)+1;
reg [59+V28PW:0] v28_expected[0:RING_DWORDS-1],v28_before[0:RING_DWORDS-1];
integer v28_i,v28_address,v28_changed,v28_faults=0,v28_payload_changes=0;
reg v28_fault;
always @(posedge clk_i) begin
 v28_fault=(rst_ni===1'b1 && framer.enabled===1'b1 && framer.active_o===1'b1 &&
            framer.command_valid===1'b1 && framer.fault_now===1'b1);
 if(v28_fault) begin
  for(v28_i=0;v28_i<RING_DWORDS;v28_i=v28_i+1) begin
   v28_expected[v28_i]={framer.slot_data[v28_i],framer.slot_keep[v28_i],framer.slot_sop[v28_i],framer.slot_eop[v28_i],framer.slot_dllp[v28_i],framer.slot_sequence[v28_i],framer.slot_tag[v28_i]};
   v28_before[v28_i]={reference.framer.slot_data[v28_i],reference.framer.slot_keep[v28_i],reference.framer.slot_sop[v28_i],reference.framer.slot_eop[v28_i],reference.framer.slot_dllp[v28_i],reference.framer.slot_sequence[v28_i],reference.framer.slot_tag[v28_i]};
  end
  for(v28_i=0;v28_i<4;v28_i=v28_i+1) begin
   v28_address=(framer.command_address+v28_i)&(RING_DWORDS-1);
   v28_expected[v28_address]={framer.command_data[v28_i*32+:32],framer.command_keep[v28_i*4+:4],framer.command_sop[v28_i*4+:4],framer.command_eop[v28_i*4+:4],framer.command_dllp[v28_i*4+:4],framer.command_sequence[v28_i*12+:12],framer.command_tags[v28_i*V28PW+:V28PW]};
  end
 end
 #0.006;
 if(v28_fault) begin
  v28_faults=v28_faults+1;v28_changed=0;
  if({framer.active_o,framer.command_valid,framer.output_valid,framer.retire_valid}!==0 || !halted_o)
   $fatal(1,"V28_PAYLOAD_OWNERSHIP_QUARANTINE");
  for(v28_i=0;v28_i<RING_DWORDS;v28_i=v28_i+1) begin
   if({framer.slot_data[v28_i],framer.slot_keep[v28_i],framer.slot_sop[v28_i],framer.slot_eop[v28_i],framer.slot_dllp[v28_i],framer.slot_sequence[v28_i],framer.slot_tag[v28_i]} !== v28_expected[v28_i])
     $fatal(1,"V28_EXACT_PENDING_PAYLOAD_WRITE");
   if({reference.framer.slot_data[v28_i],reference.framer.slot_keep[v28_i],reference.framer.slot_sop[v28_i],reference.framer.slot_eop[v28_i],reference.framer.slot_dllp[v28_i],reference.framer.slot_sequence[v28_i],reference.framer.slot_tag[v28_i]} !== v28_before[v28_i])
     $fatal(1,"V28_REFERENCE_FAULT_BANK_CHANGED");
   if(v28_expected[v28_i] !== v28_before[v28_i]) v28_changed=1;
  end
  if(v28_changed) v28_payload_changes=v28_payload_changes+1;
 end
end
final $display("V28_PAYLOAD_WITNESS faults=%0d changed=%0d",v28_faults,v28_payload_changes);
'''
    top.write_text(s.replace('endmodule',observer+'\nendmodule',1))
    return directory


def test_exact_v28_inverse():
    g=runpy.run_path(str(ROOT/'scripts/generate_pcie_integrity_payload_v28.py'))
    text,edits=g['generate']()
    assert len(edits)==3 and text==(RTL/'soc_pcie_gen3_framer_rx_integrity_v28.v').read_text()


@pytest.mark.parametrize('fault',[None,*FAULTS],ids=['positive',*FAULTS])
def test_actual_payload_epoch_quarantine(tmp_path,fault):
    h=runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v26.py'))
    result,record,_,out=h['run'](tmp_path,rtl=prepare(tmp_path/'rtl',fault),case=FAULTS[fault][2] if fault else None)
    log=(out/'simulation.log').read_text()
    if fault:
        assert result.returncode!=0 and record['status']=='FAIL'
        assert re.search(r'V2[78]_(PUBLIC_CONTROL_CYCLE|PUBLIC_PAYLOAD_CYCLE|EXACT_PENDING_PAYLOAD_WRITE|PAYLOAD_OWNERSHIP_QUARANTINE)',log),log
        assert 'syntax error' not in log.lower()
    else:
        assert result.returncode==0 and record['tests']==dict(passed=19,failed=0,skipped=0),record
        m=re.search(r'V28_PAYLOAD_WITNESS faults=(\d+) changed=(\d+)',log);assert m
        faults,changed=map(int,m.groups());assert faults>=8 and changed>=8
        cycles=re.search(r'V27_FRONTIER_WITNESS cycles=(\d+)',log);assert cycles and int(cycles[1])>1000
        (out/'payload-witness.json').write_text(json.dumps(dict(faults=faults,changed=changed,public_cycles=int(cycles[1])),indent=2)+'\n')
