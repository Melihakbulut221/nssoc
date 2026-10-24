#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Remove full/pop fanout only from data invalidated by the same overflow edge."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "hw/soc/rtl/pcie"
SOURCE = RTL / "soc_pcie_gen3_ingress.v"
SOURCE_SHA = "d34847efb81b7f6afc77d7165e0c5eb451656e10aaae73465355342d0f0505d2"
FRAMER_SHA = "d07ff44a9b3707e5b6dc6ba06792690c83e46b1c803d6facd74927517d137f8b"
WRAPPER_SHA = "3d232f3a7cf8a7a6ceddf0e93469fab2483cc270a2cf239099a237a4efcbde85"
OLD_WRITE = "       blocks[wr_ptr]<=completed;\n"
NEW_WRITE = "       // V11 payload contents use the separate quarantined writer.\n"


def writer():
    return """ // BEGIN V11 QUARANTINED INGRESS PAYLOAD WRITER
 // Full+pop still writes the same slot. Full without pop faults and invalidates
 // every queue entry at this edge; only then may the inaccessible contents
 // differ. Queue pointers/count/overflow and all public valid timing are the
 // original equations. A new epoch writes each slot before making it valid.
 always @(posedge clk_i) begin
   if(enabled && complete_block) blocks[wr_ptr]<=completed;
 end
 // END V11 QUARANTINED INGRESS PAYLOAD WRITER
"""


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    assert text.count(OLD_WRITE) == 1 and text.count(" integer k;\n") == 1
    text = text.replace(OLD_WRITE, NEW_WRITE).replace(
        " integer k;\n", writer() + " integer k;\n"
    )
    text = text.replace(
        "module soc_pcie_gen3_ingress #(",
        "`default_nettype none\nmodule soc_pcie_gen3_ingress_integrity_v11 #(",
        1,
    )
    return text + "`default_nettype wire\n"


def framer():
    p = RTL / "soc_pcie_gen3_framer_rx_integrity_v10.v"
    text = p.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == FRAMER_SHA
    return text.replace("integrity_v10", "integrity_v11")


def wrapper():
    p = RTL / "soc_pcie_gen3_continuous_rx_integrity_v10.v"
    text = p.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == WRAPPER_SHA
    assert text.count("soc_pcie_gen3_ingress #(") == 1
    return text.replace("integrity_v10", "integrity_v11").replace(
        "soc_pcie_gen3_ingress #(", "soc_pcie_gen3_ingress_integrity_v11 #("
    )


if __name__ == "__main__":
    for name, body in [
        ("soc_pcie_gen3_ingress_integrity_v11", candidate()),
        ("soc_pcie_gen3_framer_rx_integrity_v11", framer()),
        ("soc_pcie_gen3_continuous_rx_integrity_v11", wrapper()),
    ]:
        (RTL / (name + ".v")).write_text(body)
