#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Same native XOR campaign; only two physical resistor lengths differ."""
from pathlib import Path
import cloud_cdr_xor as trial
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
original=ROOT/'hw/soc/analog/pcie/tx_mux54_passive_drive_v10.spice'
core=ROOT/'hw/soc/analog/pcie/cdr_xor_core_load_v2.spice'
wrapper=ROOT/'hw/soc/analog/pcie/cdr_xor_hbt_load_v2.spice'
assert sha(Path(trial.__file__))=='3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'
assert sha(original)=='56b50efbbc138e8af973c63809799574da4ffb9c79b9ff5b5732c44e7e234df8'
old=[l for l in original.read_text().splitlines()if l and not l.startswith('*')]
new=[l for l in core.read_text().splitlines()if l and not l.startswith('*')]
assert len(old)==len(new)
changed=[]
for a,b in zip(old,new):
    expected=a.replace('nssoc_tx_mux54_passive_drive_v10','nssoc_cdr_xor_core_load_v2')
    if a.startswith(('XD0007 ','XD0008 ')):
        assert a.count('l=1.1u ')==1
        expected=expected.replace('l=1.1u ','l=1.4u ');changed.append(a.split()[0])
    assert b==expected,'Undeclared physical primitive change'
assert changed==['XD0007','XD0008']
trial.COMPONENT=core;trial.WRAPPER=wrapper
trial.COMPONENT_SHA='09a9ee6003add2f26b61d0e27d09c0a273ae359d263f3eeb6a37b243910c3411';trial.36675fe728928ac9ce144f641a518647ae70afb0bbd55ad5d789abfd476b0e64='36675fe728928ac9ce144f641a518647ae70afb0bbd55ad5d789abfd476b0e64'
trial.OUTPUT_STEM='cloud-cdr-xor-load';trial.TOP='nssoc_cdr_xor_hbt_load_v2'
trial.EXTRA_INPUTS=[Path(__file__),original]
trial.main()
