#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for d in json.loads((ROOT/'scripts/tx-v5-return-composition-source-delta.json').read_text())['files']:
    raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
    for e in d['edits']:
        assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
    actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
print('PASS_EXACT_NATIVE_TX_COMPOSITION_AND_RETURN_SOLVER_DELTA')
