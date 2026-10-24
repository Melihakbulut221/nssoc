#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate output contents from the unchanged V28 output ownership controller."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v28.v'
BASE_SHA = 'fd514c1e4b3e05ebf87b9a706d5fd1409686610fadc67608b37265fc2770a6b7'


def generate():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    writer = ''' // BEGIN V29 OUTPUT PAYLOAD EPOCH QUARANTINE
 // Transfer the old complete descriptor, preserving literal payload X/Z.
 // The original controller exclusively owns output_valid and fault priority.
 // On a fault, copied contents are inaccessible; new ownership always copies
 // every field. A stalled valid beat cannot be overwritten by this writer.
 always @(posedge clk_i or negedge rst_ni) begin
   if(!rst_ni) begin
     output_data<=0;output_keep<=0;output_sop<=0;output_eop<=0;
     output_dllp<=0;output_sequence<=0;
   end else if(retire_pop && retire_has_data) begin
     output_data<=retire_data;output_keep<=retire_keep;
     output_sop<=retire_sop;output_eop<=retire_eop;
     output_dllp<=retire_dllp;output_sequence<=retire_sequence;
   end
 end
 // END V29 OUTPUT PAYLOAD EPOCH QUARANTINE
'''
    edits = [
        ('module soc_pcie_gen3_framer_rx_integrity_v28 #(',
         'module soc_pcie_gen3_framer_rx_integrity_v29 #('),
        ('     output_valid<=0;output_data<=0;output_keep<=0;output_sop<=0;output_eop<=0;output_dllp<=0;output_sequence<=0;',
         '     output_valid<=0; // V29 output contents reset in their separate writer.'),
        ('           output_valid<=1;output_data<=retire_data;output_keep<=retire_keep;\n'
         '           output_sop<=retire_sop;output_eop<=retire_eop;output_dllp<=retire_dllp;output_sequence<=retire_sequence;',
         '           output_valid<=1; // V29 contents transfer from the same old descriptor.'),
        (' // END V21 ATOMIC RETIRE PAYLOAD CAPTURE\n',
         ' // END V21 ATOMIC RETIRE PAYLOAD CAPTURE\n'+writer),
    ]
    text = original
    for before,after in edits:
        assert text.count(before) == 1
        text = text.replace(before,after)
    inverse = text
    for before,after in reversed(edits):
        assert inverse.count(after) == 1
        inverse = inverse.replace(after,before)
    assert inverse == original
    return text,edits


if __name__ == '__main__':
    text,_ = generate()
    with BASE.with_name(BASE.name.replace('_v28','_v29')).open('x') as f:
        f.write(text)
    wrapper = BASE.with_name('soc_pcie_gen3_continuous_rx_integrity_v28.v')
    with wrapper.with_name(wrapper.name.replace('_v28','_v29')).open('x') as f:
        f.write(wrapper.read_text().replace('_v28','_v29'))
