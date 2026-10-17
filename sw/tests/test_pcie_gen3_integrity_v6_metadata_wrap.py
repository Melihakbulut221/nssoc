# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Literal metadata network versus serial origin updates across every PW12 wrap."""
from pathlib import Path
import runpy
import pytest

ROOT = Path(__file__).resolve().parents[2]
OLD = runpy.run_path(str(ROOT / 'sw/tests/test_pcie_gen3_integrity_v3_crc.py'))


@pytest.mark.parametrize('fault', [None, 'position_offset', 'carry_sequence'])
def test_actual_max_width_metadata_network(tmp_path, fault):
    source = (ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v6.v').read_text()
    body = source.split(' // BEGIN V6 PARALLEL PACKET ORIGIN\n', 1)[1].split(' // END V6 PARALLEL PACKET ORIGIN\n', 1)[0]
    mutations = {
        'position_offset': ('write_ptr+metadata_word;', "write_ptr+metadata_word+1'b1;"),
        'carry_sequence': ('&packet_sequence)', "&12'b0)"),
    }
    if fault:
        before, after = mutations[fault]
        assert body.count(before) == 1
        body = body.replace(before, after)
    bench = '''module tb;
localparam PW=12;
reg [PW-1:0] write_ptr,packet_tag;
reg [11:0] packet_sequence;
reg [3:0] control_active,control_stp,control_sdp;
reg [6:0] control_modes[0:3];
reg [31:0] crc_word[0:3];
''' + body + '''
integer position,mask,kind,mode,j,cases;
reg [11:0] expected_tag,expected_sequence,sequence_value;
initial begin
cases=0;
for(position=0;position<4096;position=position+1)
 for(mask=0;mask<16;mask=mask+1)
  for(kind=0;kind<2;kind=kind+1)
   for(mode=0;mode<4;mode=mode+1) begin
    write_ptr=position;packet_tag=position^12'h5a9;
    packet_sequence=position^12'haba;
    control_active=(mode==3)?0:15;
    for(j=0;j<4;j=j+1) begin
     control_modes[j]=(mode==0)?1:((mode==1)?4:2);
     control_stp[j]=mask[j] && ((j%2)==kind);
     control_sdp[j]=mask[j] && ((j%2)!=kind);
     sequence_value=position^(12'h123+j*12'h111);
     crc_word[j]=0;
     crc_word[j][19:16]=sequence_value[11:8];
     crc_word[j][31:24]=sequence_value[7:0];
    end
    #1;
    expected_tag=packet_tag;expected_sequence=packet_sequence;
    for(j=0;j<4;j=j+1) begin
     if(metadata_tag_before[j]!==expected_tag ||
        metadata_sequence_before[j]!==expected_sequence)
       $fatal(1,"METADATA_SERIAL_PREFIX_MISMATCH position=%0d mask=%0d kind=%0d mode=%0d j=%0d",position,mask,kind,mode,j);
     // Independent serial state update occurs AFTER this word's observation.
     if(mask[j] && mode<2) begin
      expected_tag=position+j;
      expected_sequence=((j%2)==kind)?(position^(12'h123+j*12'h111)):0;
     end
    end
    cases=cases+1;
   end
if(cases!=524288) $fatal(1,"CASE_COUNT");
$display("PASS 524288 MAX_WIDTH_SERIAL_ORIGIN_CASES 2097152_WORD_OBSERVATIONS");
$finish;end endmodule
'''
    result, log = OLD['simulate'](tmp_path, bench)
    if fault:
        assert result.returncode != 0 and 'METADATA_SERIAL_PREFIX_MISMATCH' in log
    else:
        assert result.returncode == 0 and 'PASS 524288 MAX_WIDTH_SERIAL_ORIGIN_CASES' in log
