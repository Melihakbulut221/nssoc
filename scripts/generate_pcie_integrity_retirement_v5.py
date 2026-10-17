#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve exact ring verdict semantics while caching the indirect lookup."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v4.v'
SOURCE_SHA = 'c7805937b44c03707c1f9c4c3d5a8fc7ee90b78b8fc9a48ae47dde8eb132bded'


def cache():
    return ''' // BEGIN V5 SLOT VERDICT CACHE
 // The stored bit equals verdict[slot_tag] after every initialized slot write.
 // Simultaneous writes select the NEW slot tag, then apply the four verdict
 // writes in exactly the original last-writer order. Nonwritten slots follow
 // matching verdict updates. Faulted/aborted steps cannot update either array.
 reg slot_verdict [0:RING_DWORDS-1];
 genvar cache_slot;
 generate for(cache_slot=0;cache_slot<RING_DWORDS;cache_slot=cache_slot+1) begin:verdict_cache
   reg [PW-1:0] effective_tag;
   reg next_value;
   integer write_lane,verdict_lane;
   always @* begin
     effective_tag=slot_tag[cache_slot];next_value=slot_verdict[cache_slot];
     for(write_lane=0;write_lane<4;write_lane=write_lane+1) begin
       if(((write_ptr+write_lane)&(RING_DWORDS-1))==cache_slot) begin
         effective_tag=write_tags[write_lane*PW+:PW];
         next_value=verdict[write_tags[write_lane*PW+:PW]];
       end
     end
     for(verdict_lane=0;verdict_lane<4;verdict_lane=verdict_lane+1) begin
       if(verdict_enable[verdict_lane] && verdict_tags[verdict_lane*PW+:PW]==effective_tag)
         next_value=verdict_value[verdict_lane];
     end
   end
   // The original ring metadata and verdict arrays have no reset; pointer and
   // valid resets quarantine unwritten entries. Keep the same reset boundary.
   always @(posedge clk_i) begin
     if(step && !fault_now) slot_verdict[cache_slot]<=next_value;
   end
 end endgenerate
 // END V5 SLOT VERDICT CACHE
'''


def candidate():
    source = SOURCE.read_text()
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    before = 'verdict[slot_tag[read_address]]'
    assert source.count(before) == 1
    source = source.replace(before, 'slot_verdict[read_address]')
    marker = ' integer w;\n'
    assert source.count(marker) == 1
    source = source.replace(marker, cache() + marker)
    # Declaration precedes the retirement reader, including under Icarus14.
    declaration = ' reg slot_verdict [0:RING_DWORDS-1];\n'
    source = source.replace(declaration, '')
    source = source.replace(' reg output_valid;\n', declaration + ' reg output_valid;\n')
    return source.replace('integrity_v4', 'integrity_v5')


if __name__ == '__main__':
    (ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v5.v').write_text(candidate())
