#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/'scripts/cdr-sampler-left-v1-delta.json').read_text())
raw=(ROOT/p['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==p['baseline_sha256'];text=raw.decode()
for edit in p['edits']:
    assert text.count(edit['before'])==edit['count'];text=text.replace(edit['before'],edit['after'])
actual=(ROOT/p['candidate_path']).read_bytes()
assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==p['candidate_sha256']
a=(ROOT/'hw/soc/flow/check_pcie_sampler_compact_v1.py').read_text()
b=(ROOT/'hw/soc/flow/check_pcie_sampler_left_v1.py').read_text()
assert a.count('from make_pcie_sampler_compact_v1 import')==1
assert b==a.replace('from make_pcie_sampler_compact_v1 import','from make_pcie_sampler_left_v1 import')
print('PASS_EXACT_LEFT_OUTPUT_GEOMETRY_DELTA_AND_UNCHANGED_NATIVE_GATES')
