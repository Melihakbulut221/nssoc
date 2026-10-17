#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replace shared parser-fault accumulation with four independent known-bit flags."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v28.v'
BASE_SHA = 'fd514c1e4b3e05ebf87b9a706d5fd1409686610fadc67608b37265fc2770a6b7'


def generate():
    original = BASE.read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == BASE_SHA
    edits = [
        ('module soc_pcie_gen3_framer_rx_integrity_v28 #(',
         'module soc_pcie_gen3_framer_rx_integrity_v30 #(',1),
        (' reg token_failure;',
         ' // V30 flags are assigned only literal0/1 under the original procedural guards.\n'
         ' // Balanced OR preserves the sticky failure of the complete four-word slice.\n'
         ' reg [3:0] token_failures;\n'
         ' wire token_failure=(token_failures[0]|token_failures[1])|\n'
         '                    (token_failures[2]|token_failures[3]);',1),
        ('token_failure=0;',"token_failures=4'b0000;",1),
        ('token_failure=1;','token_failures[j]=1;',4),
    ]
    text = original
    for before,after,count in edits:
        assert text.count(before)==count
        text=text.replace(before,after)
    inverse=text
    for before,after,count in reversed(edits):
        assert inverse.count(after)==count
        inverse=inverse.replace(after,before)
    assert inverse==original
    return text,edits


if __name__=='__main__':
    text,_=generate()
    with BASE.with_name(BASE.name.replace('_v28','_v30')).open('x') as f:f.write(text)
    wrapper=BASE.with_name('soc_pcie_gen3_continuous_rx_integrity_v28.v')
    with wrapper.with_name(wrapper.name.replace('_v28','_v30')).open('x') as f:
        f.write(wrapper.read_text().replace('_v28','_v30'))
