#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Move modular capacity arithmetic before the late retirement predicate."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v6.v'
SOURCE_SHA = '66d899c6ab3791342770396893d14b97466fefab52ab7def4c5363ec9b2ab794'


def capacity():
    return ''' // BEGIN V7 PARALLEL CAPACITY ARITHMETIC
 // Preserve both PW+1-bit modular arithmetic branches, including unreachable
 // overfull pointer values. Retire selects only the already computed result.
 wire [PW:0] capacity_without_retire=RING_DWORDS-{1'b0,occupied};
 wire [PW:0] capacity_with_retire=capacity_without_retire+read_count;
 wire capacity_overflow=retire ? (capacity_with_retire<4) :
                                  (capacity_without_retire<4);
 // END V7 PARALLEL CAPACITY ARITHMETIC
'''


def scalar_reads():
    return '''   // BEGIN V7 SCALAR SLOT READS
   // Constant array elements are the same values. Explicit wires keep
   // simulator @* sensitivity local to these two elements.
   wire [PW-1:0] resident_tag=slot_tag[cache_slot];
   wire resident_verdict=slot_verdict[cache_slot];
   // END V7 SCALAR SLOT READS
'''


CHANGES = (
    ('!ending && current_valid && space_after_retire<4;',
     '!ending && current_valid && capacity_overflow;'),
    ('effective_tag=slot_tag[cache_slot];next_value=slot_verdict[cache_slot];',
     'effective_tag=resident_tag;next_value=resident_verdict;'),
)


def candidate():
    source = SOURCE.read_text()
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    for before, after in CHANGES:
        assert source.count(before) == 1
        source = source.replace(before, after)
    before = " wire [PW:0] space_after_retire=RING_DWORDS-{1'b0,occupied}+(retire?read_count:0);\n"
    assert source.count(before) == 1
    source = source.replace(before, before + capacity())
    before = '   reg [PW-1:0] effective_tag;\n'
    assert source.count(before) == 1
    source = source.replace(before, scalar_reads() + before)
    return source.replace('integrity_v6', 'integrity_v7')


if __name__ == '__main__':
    (ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v7.v').write_text(candidate())
