#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for d in json.loads((ROOT/'scripts/cdr-xor-power-access-v4-source-delta.json').read_text())['files']:
    raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
    for e in d['edits']:
        assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
    raw=(ROOT/d['candidate_path']).read_bytes();assert raw==s.encode() and hashlib.sha256(raw).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_XOR_POWER_ACCESS_DELTA_AND_UNCHANGED_NATIVE_GATES')
