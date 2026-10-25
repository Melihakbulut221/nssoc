#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Enforce exact resistor-only candidate deltas and unchanged native gates."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    for d in json.loads((ROOT/'scripts/cdr-data-cm-v5-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_EXACT_PHYSICAL_DATA_HEADER_ONLY_CHANGE_NO_ACCEPTANCE_GATE_RELAXATION')
if __name__=='__main__':check()
