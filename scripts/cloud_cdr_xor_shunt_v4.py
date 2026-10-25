#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Same native XOR campaign; only two physical resistor lengths differ."""
from pathlib import Path
import cloud_cdr_xor as trial
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
original=ROOT/'hw/soc/analog/pcie/cdr_xor_core_load_v3.spice'
core=ROOT/'hw/soc/analog/pcie/cdr_xor_core_shunt_v4.spice'
wrapper=ROOT/'hw/soc/analog/pcie/cdr_xor_hbt_shunt_v4.spice'
assert sha(Path(trial.__file__))=='3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'
assert sha(original)=='b41dc7fee0bdf48165f1890bc84ff72e14a98155a7fd602de23deed968bda189'
old=[l for l in original.read_text().splitlines()if l and not l.startswith('*')]
new=[l for l in core.read_text().splitlines()if l and not l.startswith('*')]
assert len(old)==len(new)
changed=[]
for a,b in zip(old,new):
    expected=a.replace('nssoc_cdr_xor_core_load_v3','nssoc_cdr_xor_core_shunt_v4')
    if a.startswith(('XD0003 ','XD0004 ')):
        assert a.count('l=4.5u ')==1
        expected=expected.replace('l=4.5u ','l=8.0u ');changed.append(a.split()[0])
    assert b==expected,'Undeclared physical primitive change'
assert changed==['XD0003','XD0004']
trial.COMPONENT=core;trial.WRAPPER=wrapper
trial.COMPONENT_SHA='47d444e7c6b28dc1d15960a534dced500604fee1c52d8d0ee4b38e55a14e55de';trial.WRAPPER_SHA='670d7cf57a2e5bb986ba6347f4908a3b6e837303a6c94e9396fd3d5a64296ac7'
trial.OUTPUT_STEM='cloud-cdr-xor-shunt-v4';trial.TOP='nssoc_cdr_xor_hbt_shunt_v4'
trial.EXTRA_INPUTS=[Path(__file__),original]
trial.main()
