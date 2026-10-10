#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Parallel packet-origin metadata for the frozen four-DWORD parser."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v5.v'
SOURCE_SHA = '6e2f4c1afacc3cae31e1efb44fa9a98da711bd86acc4e51c61d73eea3eb9afe5'


def metadata():
    return ''' // BEGIN V6 PARALLEL PACKET ORIGIN
 // A start is accepted only in an active TOKEN or LOOK word. Payload bit
 // patterns never replace origin. LOOK consumes its previous origin before
 // the current word can start another packet. Latest preceding start wins.
 wire [3:0] metadata_start;
 wire [PW-1:0] metadata_position[0:3],metadata_tag_before[0:3];
 wire [11:0] metadata_sequence[0:3],metadata_sequence_before[0:3];
 wire [3:0] metadata_origin[0:3];
 genvar metadata_word,metadata_prior;
 generate for(metadata_word=0;metadata_word<4;metadata_word=metadata_word+1) begin:metadata_decode
   assign metadata_start[metadata_word]=control_active[metadata_word] &&
     (control_modes[metadata_word][0] || control_modes[metadata_word][2]) &&
     (control_stp[metadata_word] || control_sdp[metadata_word]);
   assign metadata_position[metadata_word]=write_ptr+metadata_word;
   assign metadata_sequence[metadata_word]=control_stp[metadata_word]?
     {crc_word[metadata_word][19:16],crc_word[metadata_word][31:24]}:12'b0;
   assign metadata_origin[metadata_word][0]=
     !(|(metadata_start & ((4'b0001<<metadata_word)-1'b1)));
   for(metadata_prior=0;metadata_prior<3;metadata_prior=metadata_prior+1) begin:prior
     assign metadata_origin[metadata_word][metadata_prior+1]=(metadata_prior<metadata_word) &&
       metadata_start[metadata_prior] &&
       !(|(metadata_start & (((4'b0001<<metadata_word)-1'b1) &
                            ~((4'b0001<<(metadata_prior+1))-1'b1))));
   end
   assign metadata_tag_before[metadata_word]=
     (({PW{metadata_origin[metadata_word][0]}}&packet_tag)|
      ({PW{metadata_origin[metadata_word][1]}}&metadata_position[0]))|
     (({PW{metadata_origin[metadata_word][2]}}&metadata_position[1])|
      ({PW{metadata_origin[metadata_word][3]}}&metadata_position[2]));
   assign metadata_sequence_before[metadata_word]=
     (({12{metadata_origin[metadata_word][0]}}&packet_sequence)|
      ({12{metadata_origin[metadata_word][1]}}&metadata_sequence[0]))|
     (({12{metadata_origin[metadata_word][2]}}&metadata_sequence[1])|
      ({12{metadata_origin[metadata_word][3]}}&metadata_sequence[2]));
 end endgenerate
 // END V6 PARALLEL PACKET ORIGIN
'''


def shared_reads():
    return ''' // BEGIN V6 SHARED OLD VERDICT READS
 // Four physical read values are common to every slot update. Explicit
 // wires avoid a whole verdict-array sensitivity expansion in every slot.
 wire [3:0] cache_write_old_verdict;
 genvar cache_read_lane;
 generate for(cache_read_lane=0;cache_read_lane<4;cache_read_lane=cache_read_lane+1) begin:cache_reads
   assign cache_write_old_verdict[cache_read_lane]=verdict[write_tags[cache_read_lane*PW+:PW]];
 end endgenerate
 // END V6 SHARED OLD VERDICT READS
'''


CHANGES = (
    ('position=write_ptr+j;state_n=control_state[j];',
     'position=write_ptr+j;state_n=control_state[j];\n     tag_n=metadata_tag_before[j];sequence_n=metadata_sequence_before[j];'),
    ('next_value=verdict[write_tags[write_lane*PW+:PW]];',
     'next_value=cache_write_old_verdict[write_lane];'),
)


def candidate():
    source = SOURCE.read_text()
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    for before, after in CHANGES:
        assert source.count(before) == 1
        source = source.replace(before, after)
    before = ' // END V4 PARALLEL CONTROL\n'
    assert source.count(before) == 1
    source = source.replace(before, before + metadata())
    before = ' // BEGIN V5 SLOT VERDICT CACHE\n'
    assert source.count(before) == 1
    source = source.replace(before, shared_reads() + before)
    return source.replace('integrity_v5', 'integrity_v6')


if __name__ == '__main__':
    (ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v6.v').write_text(candidate())
