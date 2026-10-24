#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze actual8074 adapter while preserving the whole original loaded controller."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    d=json.loads((ROOT/'scripts/tx-raw8074-prepared-source-delta.json').read_text())
    raw=(ROOT/d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    text=raw.decode()
    for e in d['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    actual=(ROOT/d['candidate_path']).read_bytes()
    assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    for p,h in d['frozen_inputs'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
        if p.endswith('.py'):ast.parse((ROOT/p).read_text())
    pin=json.loads((ROOT/'docs/evidence/tx-raw8074-interfaces-pass-20261021.json').read_text())
    assert pin['run']==39516735474 and pin['summary_sha256']=='a92c9e84d20f34d5c99a74b66750a6f5419f0427e22f98af068aa4f6489ca9df'
    assert pin['report']['sources_unchanged'] and len(pin['report']['controls'])==8 and len(pin['report']['actual_endpoint_faults'])==2
    print('PASS_EXACT8074_BENCH_ADAPTATION_ORIGINAL_STIMULI_AND_GATES_PRESERVED')
if __name__=='__main__':check()
