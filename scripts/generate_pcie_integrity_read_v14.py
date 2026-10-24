#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Constant-slot parallel read decode, directly from the frozen V11 baseline."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v11.v"
SOURCE_SHA = "d4f0419f035c45bb159c9653f6b0aa5a68d1e03e41436ad219ce1f26481dbd24"
FIELDS = {"data": 32, "keep": 4, "sop": 4, "eop": 4, "dllp": 4, "sequence": 12}


def original_read():
    text = SOURCE.read_text()
    start = text.index(" integer r,read_address;\n")
    end = text.index(" wire retire=", start)
    return text[start:end]


def parallel_read():
    text = """ // BEGIN V14 PARALLEL CONSTANT-SLOT READ
 // Each physical slot contributes through one shared address/valid decode.
 // Exactly one slot can match each lane; OR combines disjoint contributions.
 // Procedural if preserves the old X-as-not-true masking behavior for unknown
 // keep/verdict/select conditions. The ring contents and all control stay V11.
 integer r,read_address,read_slot;
 always @* begin
   read_count=(committed>=4)?3'd4:committed;
   read_data=0;read_keep=0;read_sop=0;read_eop=0;read_dllp=0;read_sequence=0;
   for(r=0;r<4;r=r+1) begin
     read_address=(read_ptr+r)&(RING_DWORDS-1);
     for(read_slot=0;read_slot<RING_DWORDS;read_slot=read_slot+1) begin
       if(r<read_count && read_address==read_slot && slot_keep[read_slot]!=0 && slot_verdict[read_slot]) begin
"""
    for name, width in FIELDS.items():
        word = f"read_{name}[r*{width}+:{width}]"
        text += f"         {word}={word}|slot_{name}[read_slot];\n"
    return text + """       end
     end
   end
 end
 // END V14 PARALLEL CONSTANT-SLOT READ
"""


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    old = original_read()
    assert text.count(old) == 1
    return text.replace(old, parallel_read()).replace("integrity_v11", "integrity_v14")


if __name__ == "__main__":
    SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v14.v").write_text(candidate())
