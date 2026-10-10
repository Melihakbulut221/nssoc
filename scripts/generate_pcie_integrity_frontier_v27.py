#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate the V26 visible frontier from the combinational parser fault path.

The inactive epoch quarantines a possibly changed frontier on the fault edge.
Reset/start/flush/abort clear it; inactive clears it on the following edge.
This is an experimental timing candidate, not PHY or integration acceptance.
"""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v26.v'
BASE_SHA = 'b41fb5c1b8e74e582fa98d9e89cca65be2b0bee3e156cc2b1501ea05cd289a0a'
WRITER = ''' // BEGIN V27 VISIBLE FRONTIER EPOCH QUARANTINE
 // A parser fault clears active/output/retire/command ownership in the
 // original controller. The old command can update this inaccessible pointer
 // on that edge. No new retirement/output is accepted from that epoch;
 // restart clears the pointer before active can become true again.
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) visible_commit_ptr<=0;
   else if(flush_i || stream_start_i || stream_abort_i || !active_o)
     visible_commit_ptr<=0;
   else if(enabled && command_valid) visible_commit_ptr<=command_commit;
 end
 // END V27 VISIBLE FRONTIER EPOCH QUARANTINE
'''


def generate():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    text = original
    edits = []

    def replace(old, new, count=1):
        nonlocal text
        assert text.count(old) == count
        text = text.replace(old, new)
        edits.append(dict(before=old, after=new, count=count))

    replace('module soc_pcie_gen3_framer_rx_integrity_v26 #(',
            'module soc_pcie_gen3_framer_rx_integrity_v27 #(')
    # Replace complete statements, retaining every other reset/ownership bit.
    replace('commit_ptr<=0;visible_commit_ptr<=0;', 'commit_ptr<=0; /* V27 frontier reset is separate. */', 3)
    replace('         visible_commit_ptr<=command_commit;\n',
            '         // V27 frontier application is in its separate writer.\n')
    replace(' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP\n',
            WRITER + ' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP\n')
    recovered = text
    for edit in reversed(edits):
        assert recovered.count(edit['after']) == edit['count']
        recovered = recovered.replace(edit['after'], edit['before'])
    assert recovered == original
    return text, edits


if __name__ == '__main__':
    text, _ = generate()
    target = BASE.with_name(BASE.name.replace('_v26', '_v27'))
    with target.open('x') as stream:
        stream.write(text)
    wrapper = BASE.with_name('soc_pcie_gen3_continuous_rx_integrity_v26.v')
    with wrapper.with_name(wrapper.name.replace('_v26', '_v27')).open('x') as stream:
        stream.write(wrapper.read_text().replace('_v26', '_v27'))
