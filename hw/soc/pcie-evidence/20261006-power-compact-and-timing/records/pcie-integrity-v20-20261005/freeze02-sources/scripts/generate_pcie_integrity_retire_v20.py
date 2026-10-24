#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Use known read eligibility for retire control; preserve literal payloads."""
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v19.v'
SOURCE_SHA = 'f9025c41e9c2aa5f6208f852e30286384bbc9462b164923485d0498600f9daea'
REPLACEMENTS = (
    (' wire [59:0] read_payload_root[0:3];\n',
     ' wire [59:0] read_payload_root[0:3];\n'
     ' // V20 known eligibility separates retire control from payload selection.\n'
     ' wire [3:0] read_eligible_root;\n reg read_any;\n'),
    ('   assign read_payload_root[read_lane]=read_payload_tree[1];\n',
     '   assign read_payload_root[read_lane]=read_payload_tree[1];\n'
     '   assign read_eligible_root[read_lane]=read_eligible_tree[1];\n'),
    ('   read_data=0;read_keep=0;read_sop=0;read_eop=0;read_dllp=0;read_sequence=0;\n',
     '   read_data=0;read_keep=0;read_sop=0;read_eop=0;read_dllp=0;read_sequence=0;\n'
     '   read_any=0;\n'),
    ('     if(r<read_count) begin\n',
     '     if(r<read_count) begin\n'
     '       if(read_eligible_root[r]) read_any=1;\n'),
    (' || read_keep==0);', ' || !read_any);'),
)

def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    for before, after in REPLACEMENTS:
        assert text.count(before) == 1
        text = text.replace(before, after)
    return text.replace('integrity_v19', 'integrity_v20')

def original(text):
    text = text.replace('integrity_v20', 'integrity_v19')
    for before, after in reversed(REPLACEMENTS):
        assert text.count(after) == 1
        text = text.replace(after, before)
    return text

FIELDS = {'data': 32, 'keep': 4, 'sop': 4, 'eop': 4, 'dllp': 4, 'sequence': 12}

def read_body(text):
    return text[text.index(' // BEGIN V17 STATIC BALANCED'):text.index(' wire retire=')]

def original_read():
    return read_body(SOURCE.read_text())

def balanced_read():
    return read_body(candidate())

if __name__ == '__main__':
    SOURCE.with_name('soc_pcie_gen3_framer_rx_integrity_v20.v').write_text(candidate())
