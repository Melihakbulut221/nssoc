#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin declared physical circuit/geometry changes while preserving native gates."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    rows=json.loads((ROOT/'scripts/cdr-sampler-hybrid-physical-delta.json').read_text())['files']
    for row in rows:
        raw=(ROOT/row['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['baseline_sha256']
        text=raw.decode()
        for e in row['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/row['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==row['candidate_sha256']
    assert hashlib.sha256((ROOT/'hw/soc/analog/pcie/rx_sampler_hybrid_tail_v1.spice').read_bytes()).hexdigest()=='dcf0b8ee36f2b4ed181c64a80ae4998f47376043204d9e15a42b0d5b05d20ae5'
    print('PASS_EXACT_HYBRID_PHYSICAL_SOURCE_DELTAS_NATIVE_GATES_UNRELAXED')
if __name__=='__main__':check()
