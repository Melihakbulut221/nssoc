#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""V25 derivative: canonical verdict writes follow fault-invalid cache ownership.

No latency, pointer, payload, cache, commit or parser change. Differences on an
invalidated fault edge require the declared temporal and public leak controls.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v25.v'
TARGET = ROOT / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v26.v'
BASE_SHA = 'fc1acf939c737364e189fc941ade7ef5eea5ed674290d91600836cc5a5740b0f'
WRITER = ''' // BEGIN V26 CANONICAL VERDICT FAULT QUARANTINE
 // Only old-command verdict contents can additionally change on fault_now.
 // That edge invalidates every owning frontier; the already copied public
 // output samples old state. New-owner closure updates all matching caches
 // together with visible_commit in one NBA edge before a later retirement.
 // Preserve literal X/Z values, indexed writes and last-lane priority.
 integer v26_verdict_lane;
 always @(posedge clk_i) begin
   if(rst_ni && enabled && active_o && command_valid) begin
     for(v26_verdict_lane=0;v26_verdict_lane<4;v26_verdict_lane=v26_verdict_lane+1) begin
       if(command_verdict_enable[v26_verdict_lane])
         verdict[command_verdict_tags[v26_verdict_lane*PW+:PW]]<=command_verdict_value[v26_verdict_lane];
     end
   end
 end
 // END V26 CANONICAL VERDICT FAULT QUARANTINE
'''


def inverse(text, edits):
    for edit in reversed(edits):
        assert text.count(edit['after']) == 1
        text = text.replace(edit['after'], edit['before'])
    return text


def generate():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    text, edits = original, []

    def replace(before, after):
        nonlocal text
        assert text.count(before) == 1 and before != after
        text = text.replace(before, after)
        edits.append(dict(before=before, after=after, count=1))

    replace('module soc_pcie_gen3_framer_rx_integrity_v25 #(',
            'module soc_pcie_gen3_framer_rx_integrity_v26 #(')
    replace('           if(command_verdict_enable[command_lane]) verdict[command_verdict_tags[command_lane*PW+:PW]]<=command_verdict_value[command_lane];\n',
            '           // V26 canonical verdict has a separate fault-quarantined writer.\n')
    replace(' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP\n',
            WRITER + ' // BEGIN V25 COMMAND CAPTURE AND EPOCH OWNERSHIP\n')
    assert inverse(text, edits) == original
    return text, edits


if __name__ == '__main__':
    text, edits = generate()
    with TARGET.open('x') as stream:
        stream.write(text)
    record = dict(status='DRAFT_V26_COMPLETE_V25_INVERSE_NOT_FUNCTIONAL_APPROVAL',
                  baseline=dict(path=str(BASE), sha256=BASE_SHA),
                  candidate=dict(path=str(TARGET), bytes=len(text.encode()),
                                 sha256=hashlib.sha256(text.encode()).hexdigest()),
                  edits=edits, latency_changed=False, tests_run=False, native_started=False)
    path = ROOT / 'hw/soc/out/pcie-integrity-v26-20261006/source-bridge-initial01.json'
    with path.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(candidate=record['candidate'], edits=len(edits), inverse=True)))
