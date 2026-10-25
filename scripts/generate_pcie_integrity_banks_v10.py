#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate quarantined bank contents from the unchanged parser fault priority."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v9.v"
SOURCE_SHA = "002f79700409de44ced29dc56aa5a1bac423e621c4bce039cd7cfdc956bac219"
CHANGES = (
    (
        "     state<=TOKEN;current_block<=0;next_block<=0;current_valid<=0;next_valid<=0;slice<=0;\n"
        "     current_predecode<=predecode_block(512'b0);next_predecode<=predecode_block(512'b0);",
        "     state<=TOKEN;current_valid<=0;next_valid<=0;slice<=0; // V10 reset control only",
    ),
    (
        "           if(next_valid) begin current_block<=next_block;current_predecode<=next_predecode;end\n",
        "           // Bank contents are updated in the separate V10 writer.\n",
    ),
    (
        "           current_block<={32'b0,current_block[511:416],32'b0,current_block[383:288],\n"
        "                           32'b0,current_block[255:160],32'b0,current_block[127:32]};\n"
        "           current_predecode<={{4{predecode_word(32'b0)}},current_predecode[511:128]};\n",
        "           // The original slice/valid control remains fault-qualified.\n",
    ),
    (
        "         if(!current_valid || (last_slice && !next_valid)) begin\n"
        "           current_block<=payload_i;current_predecode<=input_predecode;current_valid<=1;slice<=0;end\n"
        "         else begin next_block<=payload_i;next_predecode<=input_predecode;next_valid<=1;end",
        "         if(!current_valid || (last_slice && !next_valid)) begin current_valid<=1;slice<=0;end\n"
        "         else begin next_valid<=1;end",
    ),
)


def bank_writer():
    return """ // BEGIN V10 QUARANTINED BANK WRITER
 // Only contents bypass parser-fault qualification. All validity, slice,
 // packet/CRC state, commits and public fault/abort priority remain unchanged.
 // A fault edge can change inaccessible contents; both valid bits clear on
 // that edge, and a new epoch must load a bank before it can become visible.
 // Payload and its literal predecode companion always move together.
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     current_block<=0;next_block<=0;
     current_predecode<=predecode_block(512'b0);next_predecode<=predecode_block(512'b0);
   end else if(enabled && active_o) begin
     if(step) begin
       if(slice==3) begin
         if(next_valid) begin current_block<=next_block;current_predecode<=next_predecode;end
       end else begin
         current_block<={32'b0,current_block[511:416],32'b0,current_block[383:288],
                         32'b0,current_block[255:160],32'b0,current_block[127:32]};
         current_predecode<={{4{predecode_word(32'b0)}},current_predecode[511:128]};
       end
     end
     if(block_valid_i && block_ready_o) begin
       if(!current_valid || (last_slice && !next_valid)) begin
         current_block<=payload_i;current_predecode<=input_predecode;
       end else begin next_block<=payload_i;next_predecode<=input_predecode;end
     end
   end
 end
 // END V10 QUARANTINED BANK WRITER
"""


def candidate():
    text = SOURCE.read_text()
    assert hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA
    for before, after in CHANGES:
        assert text.count(before) == 1, before
        text = text.replace(before, after)
    anchor = " integer w;\n"
    assert text.count(anchor) == 1
    return text.replace(anchor, bank_writer() + anchor).replace(
        "integrity_v9", "integrity_v10"
    )


if __name__ == "__main__":
    (SOURCE.with_name("soc_pcie_gen3_framer_rx_integrity_v10.v")).write_text(
        candidate()
    )
