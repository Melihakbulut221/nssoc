#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve parser branches while balancing the four-lane commit selection."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v"
SOURCE_SHA = "7aeb0b29e6b56978bed7f83a48b14e8e11a005bf16342cfd8b616225ba9d8160"
DECLARATIONS = """ // BEGIN V18 PARALLEL COMMIT VALUES
 // Each lane records its last procedural commit assignment. The branches
 // themselves are unchanged, including their not-true treatment of X/Z.
 reg [3:0] commit_write;
 reg [4*PW-1:0] commit_value;
 reg [PW-1:0] commit_lower,commit_upper;
 // END V18 PARALLEL COMMIT VALUES
"""
REDUCTION = """   // BEGIN V18 BALANCED LAST COMMIT
   // Flags are always binary: zero by default and one only after an actual
   // procedural assignment. Known-select muxes preserve literal X/Z values.
   // Later lanes win; two adjacent pairs avoid the serial four-lane mux.
   commit_lower=commit_write[1]?commit_value[PW+:PW]:commit_value[0+:PW];
   commit_upper=commit_write[3]?commit_value[3*PW+:PW]:commit_value[2*PW+:PW];
   if(|commit_write[3:2]) commit_n=commit_upper;
   else if(|commit_write[1:0]) commit_n=commit_lower;
   else commit_n=commit_ptr;
   // END V18 BALANCED LAST COMMIT
"""
EDITS = (
    (" integer j;\n always @* begin\n", DECLARATIONS + " integer j;\n always @* begin\n", 1),
    ("state_n=state;commit_n=commit_ptr;", "state_n=state;commit_write=0;commit_value=0;", 1),
    ("commit_n=position+1'b1;", "begin commit_write[j]=1;commit_value[j*PW+:PW]=position+1'b1;end ", 4),
    ("commit_n=position;", "begin commit_write[j]=1;commit_value[j*PW+:PW]=position;end ", 1),
    ("   end\n end\n // BEGIN V6 SHARED OLD VERDICT READS", "   end\n" + REDUCTION + " end\n // BEGIN V6 SHARED OLD VERDICT READS", 1),
)


def candidate():
    source = SOURCE.read_text()
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    for before, after, count in EDITS:
        assert source.count(before) == count, (before, count)
        source = source.replace(before, after)
    return source.replace("integrity_v17", "integrity_v18")


def restore(source):
    source = source.replace("integrity_v18", "integrity_v17")
    for before, after, count in reversed(EDITS):
        assert source.count(after) == count, (after, count)
        source = source.replace(after, before)
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    return source


if __name__ == "__main__":
    SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v18.v").write_text(candidate())
