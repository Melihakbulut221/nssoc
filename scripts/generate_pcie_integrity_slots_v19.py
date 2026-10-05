#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Relocate only seven ring-content writes; all validity/verdict controls stay exact."""

import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v"
SOURCE_SHA = "7aeb0b29e6b56978bed7f83a48b14e8e11a005bf16342cfd8b616225ba9d8160"
FIELDS = ("data", "keep", "sop", "eop", "dllp", "sequence", "tag")
MARKER = "           // V19 only ring content writes moved to the step writer.\n"


def original_writes():
    text = SOURCE.read_text()
    first = text.index("           slot_data[(write_ptr+w)&(RING_DWORDS-1)]<=")
    last = text.index("           if(verdict_enable[w])", first)
    writes = text[first:last]
    assert len(writes.splitlines()) == 7
    assert all(writes.count("slot_" + field + "[") == 1 for field in FIELDS)
    return writes


def writer():
    writes = re.sub(r"\bw\b", "slot_content_lane", original_writes())
    return (
        " // BEGIN V19 SEVEN QUARANTINED RING CONTENT WRITES\n"
        " // Exact step keeps reset/start/flush/abort/capacity/ending guards.\n"
        " // Only a parser or accepted-block fault can add content writes; the\n"
        " // unchanged same-edge fault branch empties the ring and clears output.\n"
        " // A restarted epoch rewrites a slot before making it occupied. The\n"
        " // verdict array/cache retain their original fault-qualified writers.\n"
        " // Invalid slot contents may differ; occupied contents must not differ.\n"
        " integer slot_content_lane;\n"
        " always @(posedge clk_i) begin\n"
        "   if(step) begin\n"
        "     for(slot_content_lane=0;slot_content_lane<4;slot_content_lane=slot_content_lane+1) begin\n"
        + writes
        + "     end\n"
        "   end\n"
        " end\n"
        " // END V19 SEVEN QUARANTINED RING CONTENT WRITES\n"
    )


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    writes = original_writes()
    assert text.count(writes) == 1 and text.count(" integer w;\n") == 1
    text = text.replace(writes, MARKER)
    return text.replace(" integer w;\n", writer() + " integer w;\n").replace(
        "integrity_v17", "integrity_v19"
    )


if __name__ == "__main__":
    SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v19.v").write_text(candidate())
