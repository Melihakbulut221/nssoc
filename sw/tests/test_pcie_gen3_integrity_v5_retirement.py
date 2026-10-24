# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal cache transition and unchanged-cycle ring semantics controls."""
import runpy
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'hw/soc/rtl/pcie'
GEN = runpy.run_path(str(ROOT / 'scripts/generate_pcie_integrity_retirement_v5.py'))
SIM = runpy.run_path(str(ROOT / 'sw/tests/test_pcie_gen3_integrity_v3_crc.py'))['simulate']


def test_exact_generated_inverse_and_wrapper_bridge():
    source = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v5.v').read_text()
    assert source == GEN['candidate']()
    cache = GEN['cache']().replace(' reg slot_verdict [0:RING_DWORDS-1];\n', '')
    source = source.replace(cache, '').replace(' reg slot_verdict [0:RING_DWORDS-1];\n', '')
    source = source.replace('slot_verdict[read_address]', 'verdict[slot_tag[read_address]]')
    assert source.replace('integrity_v5', 'integrity_v4') == GEN['SOURCE'].read_text()
    for name in ['hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v4.v',
                 'scripts/check_pcie_gen3_continuous_rx_integrity_v4.py',
                 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v4.py',
                 'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v4']:
        old = ROOT / name
        new = ROOT / name.replace('_v4', '_v5')
        assert new.read_text().replace('integrity_v5', 'integrity_v4') == old.read_text()


@pytest.mark.parametrize('fault', [None, 'old_tag_on_write', 'first_verdict_wins',
                                  'missed_broadcast', 'faulted_step_update',
                                  'new_write_forces_zero'])
def test_actual_cache_transition_and_read_relation(tmp_path, fault):
    source = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v5.v').read_text()
    body = source.split(' // BEGIN V5 SLOT VERDICT CACHE\n', 1)[1].split(' // END V5 SLOT VERDICT CACHE\n', 1)[0]
    edits = {
        'old_tag_on_write': ('effective_tag=write_tags[write_lane*PW+:PW];', 'effective_tag=slot_tag[cache_slot];'),
        'first_verdict_wins': ('verdict_lane=0;verdict_lane<4;verdict_lane=verdict_lane+1', 'verdict_lane=3;verdict_lane>=0;verdict_lane=verdict_lane-1'),
        'missed_broadcast': ('verdict_enable[verdict_lane] &&', 'verdict_enable[verdict_lane] && cache_slot==0 &&'),
        'faulted_step_update': ('step && !fault_now', 'step'),
        'new_write_forces_zero': ('next_value=verdict[write_tags[write_lane*PW+:PW]];', "next_value=1'b0;"),
    }
    if fault:
        old, new = edits[fault]
        assert body.count(old) == 1
        body = body.replace(old, new)
    tb = '''`timescale 1ns/1ps
`default_nettype none
module tb;
localparam RING_DWORDS=64, PW=7;
reg clk_i=0,step=0,fault_now=0;
reg [PW-1:0] write_ptr=0;
reg [4*PW-1:0] write_tags=0,verdict_tags=0;
reg [3:0] verdict_enable=0,verdict_value=0;
reg [PW-1:0] slot_tag[0:RING_DWORDS-1];
reg verdict[0:2*RING_DWORDS-1];
reg slot_verdict[0:RING_DWORDS-1];
''' + body + '''
integer n,i,j,k,seed=5813006,read_ptr,committed,read_count,a;
reg [15:0] old_read_keep,new_read_keep;
reg [3:0] keep[0:RING_DWORDS-1];
reg [PW-1:0] expected_tag[0:RING_DWORDS-1];
reg expected_verdict[0:2*RING_DWORDS-1];
initial begin
 for(n=0;n<16384;n=n+1) begin
   clk_i=0;step=0;fault_now=0;
   for(i=0;i<128;i=i+1) begin verdict[i]=$random(seed);expected_verdict[i]=verdict[i];end
   for(i=0;i<64;i=i+1) begin
     slot_tag[i]=$random(seed);expected_tag[i]=slot_tag[i];
     slot_verdict[i]=verdict[slot_tag[i]];keep[i]=$random(seed);
   end
   write_ptr=$random(seed);write_tags={$random(seed),$random(seed)};
   verdict_tags={$random(seed),$random(seed)};
   verdict_enable=n[3:0];verdict_value=n[7:4];
   // Directed same-tag collisions, slot wrap, and new/old-tag overlap coexist
   // with arbitrary binary ring contents; matching later writes must win.
   if(n[8]) begin
     for(j=0;j<4;j=j+1) begin
       if(n[j+9]) verdict_tags[j*PW+:PW]=write_tags[(j%2)*PW+:PW];
       else verdict_tags[j*PW+:PW]=slot_tag[(write_ptr+j)&63];
     end
   end
   step=n[13:12]!=0;fault_now=n[12:11]==3;
   read_ptr=$random(seed)&127;committed=$random(seed)&127;
   read_count=committed>=4?4:committed;
   #1;
   old_read_keep=0;new_read_keep=0;
   for(j=0;j<4;j=j+1) begin
     a=(read_ptr+j)&63;
     if(j<read_count && keep[a]!=0 && verdict[slot_tag[a]]) old_read_keep[j*4+:4]=keep[a];
     if(j<read_count && keep[a]!=0 && slot_verdict[a]) new_read_keep[j*4+:4]=keep[a];
   end
   if(old_read_keep!==new_read_keep) $fatal(1,"CACHE_READ_RELATION %0d",n);
   if(step && !fault_now) begin
     for(j=0;j<4;j=j+1) begin
       expected_tag[(write_ptr+j)&63]=write_tags[j*PW+:PW];
       if(verdict_enable[j]) expected_verdict[verdict_tags[j*PW+:PW]]=verdict_value[j];
     end
   end
   clk_i=1;#1;
   for(i=0;i<64;i=i+1)
     if(slot_verdict[i]!==expected_verdict[expected_tag[i]])
       $fatal(1,"CACHE_NEXT_RELATION sample=%0d slot=%0d",n,i);
 end
 $display("PASS 16384 LITERAL_CACHE_TRANSITIONS 1048576 SLOT_RELATIONS");$finish;
end
endmodule
`default_nettype wire
'''
    result, log = SIM(tmp_path, tb)
    if fault:
        assert result.returncode != 0 and 'CACHE_NEXT_RELATION' in log
    else:
        assert result.returncode == 0 and 'PASS 16384 LITERAL_CACHE_TRANSITIONS' in log
