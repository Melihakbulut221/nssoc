#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Balanced known-eligibility/payload mux tree from the frozen V11 baseline."""

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


def balanced_read():
    fields = ",".join("slot_" + n + "[read_slot]" for n in FIELDS)
    outputs = ",".join(f"read_{n}[r*{w}+:{w}]" for n, w in FIELDS.items())
    return """ // BEGIN V15 BALANCED KNOWN-ELIGIBILITY PAYLOAD TREE
 // Procedural leaf flags are always known0/1, including unknown address,
 // keep or verdict. At most one physical slot matches each lane address.
 // Payload muxes preserve literal X/Z; a payload OR would convert Z to X.
 // A complete binary tree has log2(RING_DWORDS) selection levels in RTL;
 // emitted native depth must be measured separately, not inferred from RTL.
 integer r,read_address,read_slot,read_node,read_base;
 reg read_eligible_tree[0:8*RING_DWORDS-1];
 reg [59:0] read_payload_tree[0:8*RING_DWORDS-1];
 always @* begin
   read_count=(committed>=4)?3'd4:committed;
   read_data=0;read_keep=0;read_sop=0;read_eop=0;read_dllp=0;read_sequence=0;
   for(r=0;r<4;r=r+1) begin
     read_address=(read_ptr+r)&(RING_DWORDS-1);
     read_base=r*2*RING_DWORDS;
     read_eligible_tree[read_base]=0;read_payload_tree[read_base]=0;
     for(read_slot=0;read_slot<RING_DWORDS;read_slot=read_slot+1) begin
       read_eligible_tree[read_base+RING_DWORDS+read_slot]=0;
       read_payload_tree[read_base+RING_DWORDS+read_slot]=0;
       if(read_address==read_slot && slot_keep[read_slot]!=0 && slot_verdict[read_slot]) begin
         read_eligible_tree[read_base+RING_DWORDS+read_slot]=1;
         read_payload_tree[read_base+RING_DWORDS+read_slot]={FIELDS};
       end
     end
     for(read_node=RING_DWORDS-1;read_node>0;read_node=read_node-1) begin
       read_eligible_tree[read_base+read_node]=read_eligible_tree[read_base+2*read_node]|read_eligible_tree[read_base+2*read_node+1];
       read_payload_tree[read_base+read_node]=read_eligible_tree[read_base+2*read_node]?
         read_payload_tree[read_base+2*read_node]:read_payload_tree[read_base+2*read_node+1];
     end
     if(r<read_count) begin
       {OUTPUTS}=read_payload_tree[read_base+1];
     end
   end
 end
 // END V15 BALANCED KNOWN-ELIGIBILITY PAYLOAD TREE
""".replace("{FIELDS}", "{" + fields + "}").replace("{OUTPUTS}", "{" + outputs + "}")


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    old = original_read()
    assert text.count(old) == 1
    return text.replace(old, balanced_read()).replace("integrity_v11", "integrity_v15")


if __name__ == "__main__":
    SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v15.v").write_text(candidate())
