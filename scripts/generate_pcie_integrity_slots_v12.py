#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Quarantine slot contents from parser-fault control without moving commit."""

import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v11.v"
SOURCE_SHA = "d4f0419f035c45bb159c9653f6b0aa5a68d1e03e41436ad219ce1f26481dbd24"


def original_writes():
    source = SOURCE.read_text()
    start = source.index("         for(w=0;w<4;w=w+1) begin\n")
    end = source.index("         if(slice==3) begin\n", start)
    return source[start:end]


def writer():
    # Replace only identifier tokens; 'write' in signal names is not a loop name.
    writes = re.sub(r"\bw\b", "slot_write_lane", original_writes())
    return (
        " // BEGIN V12 QUARANTINED SLOT WRITER\n"
        " // Contents may change on a faulted parser step. The unchanged control\n"
        " // clears all pointers/output validity and halts that epoch at the same\n"
        " // edge. New epochs overwrite every occupied slot before commit.\n"
        " // Data, metadata, tag, tag verdict and cached verdict advance together;\n"
        " // the public fault/abort/flush priority and retirement are unchanged.\n"
        " integer slot_write_lane;\n"
        " always @(posedge clk_i) begin\n"
        "   if(step) begin\n"
        + writes
        + "   end\n"
        " end\n"
        " // END V12 QUARANTINED SLOT WRITER\n"
    )


CHANGES = (
    (
        "     if(step && !fault_now) slot_verdict[cache_slot]<=next_value;",
        "     if(step) slot_verdict[cache_slot]<=next_value; // V12 quarantined cache",
    ),
    (
        " // matching verdict updates. Faulted/aborted steps cannot update either array.",
        " // matching verdict updates. V12 faulted-step contents remain quarantined.",
    ),
)


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    for before, after in CHANGES:
        assert text.count(before) == 1
        text = text.replace(before, after)
    old = original_writes()
    assert text.count(old) == 1
    text = text.replace(old, "         // V12 slot contents have a separate writer.\n")
    assert text.count(" integer w;\n") == 1
    return text.replace(" integer w;\n", writer()).replace("integrity_v11", "integrity_v12")


if __name__ == "__main__":
    SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v12.v").write_text(candidate())
