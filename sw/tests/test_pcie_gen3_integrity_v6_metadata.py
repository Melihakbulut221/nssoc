# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual parallel-origin parser comparison to the frozen serial metadata."""
from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / 'hw/soc/rtl/pcie'
GEN = runpy.run_path(str(ROOT / 'scripts/generate_pcie_integrity_metadata_v6.py'))
OLD = runpy.run_path(str(ROOT / 'sw/tests/test_pcie_gen3_integrity_v3_crc.py'))


def test_exact_generated_inverse_and_wrapper_bridge():
    source = (RTL / 'soc_pcie_gen3_framer_rx_integrity_v6.v').read_text()
    assert source == GEN['candidate']()
    source = source.replace(GEN['metadata'](), '').replace(GEN['shared_reads'](), '')
    for before, after in GEN['CHANGES']:
        assert source.count(after) == 1
        source = source.replace(after, before)
    assert source.replace('integrity_v6','integrity_v5') == GEN['SOURCE'].read_text()
    for name in ['hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v5.v',
                 'scripts/check_pcie_gen3_continuous_rx_integrity_v5.py',
                 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v5.py',
                 'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v5']:
        assert (ROOT/name.replace('_v5','_v6')).read_text().replace('integrity_v6','integrity_v5') == (ROOT/name).read_text()


@pytest.mark.parametrize('fault',[None,'payload_alias','loses_latest','look_uses_new_tag','dllp_sequence'])
def test_actual_v5_v6_all_parser_outputs(tmp_path,fault):
    source = (RTL/'soc_pcie_gen3_framer_rx_integrity_v6.v').read_text()
    changes = {
        'payload_alias': ('(control_modes[metadata_word][0] || control_modes[metadata_word][2])', "1'b1"),
        'loses_latest': ('~((4\'b0001<<(metadata_prior+1))-1\'b1)', '~((4\'b0001<<metadata_prior)-1\'b1)'),
        'look_uses_new_tag': ('tag_n=metadata_tag_before[j];', 'tag_n=metadata_start[j]?metadata_position[j]:metadata_tag_before[j];'),
        'dllp_sequence': ("{crc_word[metadata_word][19:16],crc_word[metadata_word][31:24]}:12'b0;", "{crc_word[metadata_word][19:16],crc_word[metadata_word][31:24]}:12'hfff;"),
    }
    if fault:
        before,after=changes[fault]
        assert source.count(before)==1
        source=source.replace(before,after)
    p=tmp_path/'candidate.v';p.write_text(source)
    bench=OLD['parser_miter']().replace('_v3','_v6').replace('_v2','_v5')
    result,log=OLD['simulate'](tmp_path,bench,[RTL/'soc_pcie_gen3_framer_rx_integrity_v5.v',p])
    if fault:
        assert result.returncode!=0 and 'PARSER_ARBITRARY_STATE_MISMATCH' in log
    else:
        assert result.returncode==0 and 'PASS 32768 ACTUAL_FULL_PARSER_CASES' in log


@pytest.mark.parametrize('fault',[False,True])
def test_actual_shared_lookup_wires(tmp_path,fault):
    source=(RTL/'soc_pcie_gen3_framer_rx_integrity_v6.v').read_text()
    body=source.split(' // BEGIN V6 SHARED OLD VERDICT READS\n',1)[1].split(' // END V6 SHARED OLD VERDICT READS\n',1)[0]
    if fault:
        before='verdict[write_tags[cache_read_lane*PW+:PW]]'
        assert body.count(before)==1
        body=body.replace(before,'verdict[write_tags[((cache_read_lane+1)%4)*PW+:PW]]')
    tb='''module tb;
localparam PW=7;
reg verdict[0:127];reg[27:0] write_tags;
'''+body+'''
integer sample,i,seed=9485388;
initial begin
for(sample=0;sample<4096;sample=sample+1) begin
 for(i=0;i<128;i=i+1) verdict[i]=$random(seed);
 write_tags=$random(seed);#1;
 for(i=0;i<4;i=i+1)
 if(cache_write_old_verdict[i]!==verdict[write_tags[i*7+:7]]) $fatal(1,"SHARED_LOOKUP_WIRE");
end
$display("PASS 16384 ACTUAL_SHARED_LOOKUPS");$finish;end endmodule
'''
    result,log=OLD['simulate'](tmp_path,tb)
    if fault:
        assert result.returncode!=0 and 'SHARED_LOOKUP_WIRE' in log
    else:
        assert result.returncode==0 and 'PASS 16384' in log
