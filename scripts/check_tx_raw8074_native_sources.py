#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze native process lifecycle and original full electrical review sources."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p,h in json.loads((ROOT/'scripts/tx-raw8074-native-methods.json').read_text()).items():
    raw=(ROOT/p).read_bytes();assert hashlib.sha256(raw).hexdigest()==h,p
    if p.endswith('.py'):ast.parse(raw.decode(),filename=p)
print('PASS_EXACT_ACTUAL8074_CHECKPOINT_AND_UNCHANGED_FULL_ELECTRICAL_REVIEW_SOURCES')
