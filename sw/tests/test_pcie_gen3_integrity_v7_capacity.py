# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exhaustive modular capacity arithmetic and literal scalar-array bindings."""
from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'hw/soc/rtl/pcie'
GEN = runpy.run_path(str(ROOT / 'scripts/generate_pcie_integrity_capacity_v7.py'))
OLD = runpy.run_path(str(ROOT / 'sw/tests/test_pcie_gen3_integrity_v3_crc.py'))


def test_exact_generated_inverse_and_wrapper_bridge():
    source = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v7.v').read_text()
    assert source == GEN['candidate']()
    source = source.replace(GEN['capacity'](), '').replace(GEN['scalar_reads'](), '')
    for before, after in GEN['CHANGES']:
        assert source.count(after) == 1
        source = source.replace(after, before)
    assert source.replace('integrity_v7', 'integrity_v6') == GEN['SOURCE'].read_text()
    for name in ['hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v6.v',
                 'scripts/check_pcie_gen3_continuous_rx_integrity_v6.py',
                 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v6.py',
                 'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v6']:
        assert (ROOT / name.replace('_v6', '_v7')).read_text().replace('integrity_v7', 'integrity_v6') == (ROOT / name).read_text()


@pytest.mark.parametrize('pw', [7, 12])
@pytest.mark.parametrize('fault', [None, 'retirement_ignored', 'inclusive_threshold', 'retirement_subtracted'])
def test_every_binary_modular_capacity_input(tmp_path, pw, fault):
    source = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v7.v').read_text()
    body = source.split(' // BEGIN V7 PARALLEL CAPACITY ARITHMETIC\n', 1)[1].split(' // END V7 PARALLEL CAPACITY ARITHMETIC\n', 1)[0]
    before = next(line for line in GEN['SOURCE'].read_text().splitlines() if 'wire [PW:0] space_after_retire=' in line)
    changes = {
        'retirement_ignored': ('capacity_overflow=retire ?', "capacity_overflow=1'b0 ?"),
        'inclusive_threshold': ('capacity_with_retire<4', 'capacity_with_retire<=4'),
        'retirement_subtracted': ('capacity_without_retire+read_count', 'capacity_without_retire-read_count'),
    }
    if fault:
        old, new = changes[fault]
        assert body.count(old) == 1
        body = body.replace(old, new)
    bench = f'''module tb;
localparam PW={pw};localparam integer RING_DWORDS=(1<<(PW-1));
reg[PW-1:0] occupied;reg[2:0] read_count;reg retire;
''' + before + '\n' + body + '''
integer o,c,r,cases;
initial begin
cases=0;
for(o=0;o<(1<<PW);o=o+1)
 for(c=0;c<8;c=c+1)
  for(r=0;r<2;r=r+1) begin
   occupied=o;read_count=c;retire=r;#1;
   if((space_after_retire<4)!==capacity_overflow)
    $fatal(1,"CAPACITY_MODULAR_MISMATCH occupied=%0d count=%0d retire=%0d",o,c,r);
   cases=cases+1;
  end
if(cases!=(1<<(PW+4))) $fatal(1,"CASE_COUNT");
$display("PASS EVERY_BINARY_CAPACITY_INPUT cases=%0d",cases);$finish;
end endmodule
'''
    result, log = OLD['simulate'](tmp_path, bench)
    if fault:
        assert result.returncode != 0 and 'CAPACITY_MODULAR_MISMATCH' in log
    else:
        assert result.returncode == 0 and f'PASS EVERY_BINARY_CAPACITY_INPUT cases={1 << (pw + 4)}' in log


@pytest.mark.parametrize('fault', [None, 'wrong_tag_slot', 'inverted_verdict'])
def test_literal_maximum_scalar_bindings(tmp_path, fault):
    source = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v7.v').read_text()
    body = source.split('   // BEGIN V7 SCALAR SLOT READS\n', 1)[1].split('   // END V7 SCALAR SLOT READS\n', 1)[0]
    changes = {
        'wrong_tag_slot': ('slot_tag[cache_slot]', 'slot_tag[(cache_slot+1)%RING_DWORDS]'),
        'inverted_verdict': ('resident_verdict=slot_verdict[cache_slot]', 'resident_verdict=~slot_verdict[cache_slot]'),
    }
    if fault:
        before, after = changes[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    bench = '''module tb;
localparam PW=12,RING_DWORDS=2048;
reg[PW-1:0] slot_tag[0:RING_DWORDS-1];
reg slot_verdict[0:RING_DWORDS-1];
wire[PW*RING_DWORDS-1:0] actual_tags;wire[RING_DWORDS-1:0] actual_verdicts;
genvar cache_slot;
generate for(cache_slot=0;cache_slot<RING_DWORDS;cache_slot=cache_slot+1) begin:bound
''' + body + '''
assign actual_tags[cache_slot*PW+:PW]=resident_tag;
assign actual_verdicts[cache_slot]=resident_verdict;
end endgenerate
integer i,trial,seed=1410405;
initial begin
for(trial=0;trial<64;trial=trial+1) begin
 for(i=0;i<RING_DWORDS;i=i+1) begin
  slot_tag[i]=$random(seed);slot_verdict[i]=$random(seed);
  if((i+trial)%31==0) slot_tag[i]=12'hxxx;
  if((i+trial)%29==0) slot_verdict[i]=1'bx;
 end
 #1;
 for(i=0;i<RING_DWORDS;i=i+1)
  if(actual_tags[i*PW+:PW]!==slot_tag[i] || actual_verdicts[i]!==slot_verdict[i])
   $fatal(1,"SCALAR_SLOT_BINDING_MISMATCH trial=%0d slot=%0d",trial,i);
end
$display("PASS 131072_MAXIMUM_SLOT_BINDINGS_WITH_X");$finish;
end endmodule
'''
    result, log = OLD['simulate'](tmp_path, bench)
    if fault:
        assert result.returncode != 0 and 'SCALAR_SLOT_BINDING_MISMATCH' in log
    else:
        assert result.returncode == 0 and 'PASS 131072_MAXIMUM_SLOT_BINDINGS_WITH_X' in log
