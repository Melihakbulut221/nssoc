#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Move V27 ring payload contents into a separate epoch-quarantined writer."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v27.v'
BASE_SHA = '58337691af84bc9ef4e02bae94144aee5d4699d63eebef294fd9efb4154721e2'


def generate():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    start = original.index('       // BEGIN V25 APPLY OLD COMMAND')
    end = original.index('       // END V25 APPLY OLD COMMAND',start)
    end += len('       // END V25 APPLY OLD COMMAND\n')
    old = original[start:end]
    loop_start = old.index('         for(command_lane=')
    loop_end = old.index('         end\n',loop_start)+len('         end\n')
    loop = old[loop_start:loop_end].replace('command_lane','v28_payload_lane')
    writer = ''' // BEGIN V28 RING PAYLOAD EPOCH QUARANTINE
 // Contents may change on a parser-fault edge, but active, command,
 // descriptor and output ownership still clear in the original controller.
 // A fresh epoch overwrites all fields before publishing its frontier.
 // Preserve original lane priority, wrap addressing and literal X/Z data.
 integer v28_payload_lane;
 always @(posedge clk_i) begin
   if(rst_ni && enabled && active_o && command_valid) begin
''' + loop + '''   end
 end
 // END V28 RING PAYLOAD EPOCH QUARANTINE
'''
    edits = [
        ('module soc_pcie_gen3_framer_rx_integrity_v27 #(',
         'module soc_pcie_gen3_framer_rx_integrity_v28 #('),
        (old, '       // V28 pending payload contents are written separately.\n'),
        (' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP\n',
         writer+' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP\n'),
    ]
    text = original
    for before,after in edits:
        assert text.count(before)==1
        text=text.replace(before,after)
    inverse=text
    for before,after in reversed(edits):
        assert inverse.count(after)==1
        inverse=inverse.replace(after,before)
    assert inverse==original
    return text,edits


if __name__=='__main__':
    text,_=generate()
    with BASE.with_name(BASE.name.replace('_v27','_v28')).open('x') as f:f.write(text)
    wrapper=BASE.with_name('soc_pcie_gen3_continuous_rx_integrity_v27.v')
    with wrapper.with_name(wrapper.name.replace('_v27','_v28')).open('x') as f:
        f.write(wrapper.read_text().replace('_v27','_v28'))
