#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
from check_cdr_collector_v8_parent_sources import check
ROOT=Path(__file__).resolve().parents[1]
def main():
    check()
    d=json.loads((ROOT/'scripts/cdr-collector-v8-planes-source-delta.json').read_text())
    raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
    for e in d['edits']:
        assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
    actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    print('PASS_EXACT_COLLECTOR_PARENT_BINDING_ORIGINAL158_PLANES_AND19_CONTROLS')
if __name__=='__main__':main()
