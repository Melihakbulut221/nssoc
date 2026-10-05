#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Remove only aborting capacity qualification from quarantined slot contents."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v12.v"
SOURCE_SHA = "eb9eeb7123be347808239a6614ea9efe59ed342fe18fd96b5984a073aa76db09"
CHANGES = (
    (
        " wire last_slice=step && slice==3;",
        " // V13: the only extra content write is a same-edge overflow abort.\n"
        " wire slot_content_step=enabled && active_o && !ending && current_valid;\n"
        " wire last_slice=step && slice==3;",
    ),
    (
        "     if(step) slot_verdict[cache_slot]<=next_value; // V12 quarantined cache",
        "     if(slot_content_step) slot_verdict[cache_slot]<=next_value; // V13 overflow quarantine",
    ),
    (
        " integer slot_write_lane;\n always @(posedge clk_i) begin\n   if(step) begin\n",
        " integer slot_write_lane;\n always @(posedge clk_i) begin\n   if(slot_content_step) begin\n",
    ),
)


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    for before, after in CHANGES:
        assert text.count(before) == 1
        text = text.replace(before, after)
    return text.replace("integrity_v12", "integrity_v13")


def writer():
    text = candidate()
    start = text.index(" // BEGIN V12 QUARANTINED SLOT WRITER\n")
    end = text.index(" // END V12 QUARANTINED SLOT WRITER\n", start)
    return text[start:end] + " // END V12 QUARANTINED SLOT WRITER\n"


if __name__ == "__main__":
    SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v13.v").write_text(candidate())
