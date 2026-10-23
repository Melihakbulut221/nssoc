#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze the8088 whole-parent adaptation while retaining the original gates."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_tx_output8088_power128return32_prepared_sources import check as original_check
    original_check()
    d=json.loads((ROOT/'scripts/tx-output8088-power128return64-prepared-source-delta.json').read_text())
    raw=(ROOT/d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    text=raw.decode()
    for e in d['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    actual=(ROOT/d['candidate_path']).read_bytes()
    assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    adapter=d['adapter_derivation']
    text=(ROOT/adapter['baseline_path']).read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==adapter['baseline_sha256']
    for e in adapter['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    assert text==(ROOT/adapter['candidate_path']).read_text()
    assert hashlib.sha256(text.encode()).hexdigest()==adapter['candidate_sha256']
    for p,h in d['frozen_inputs'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
        if p.endswith('.py'):ast.parse((ROOT/p).read_text())
    pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64-interfaces-pass-20261023.json').read_text())
    assert pin['run']==39905858535 and pin['summary_sha256']=='b9b7b64adf5f8289a4982094ba0173e35e34310004f1e09a44ce1e483c887d54'
    assert pin['report']['sources_unchanged'] and pin['report']['counts']['native_terminals']==28620
    print('PASS_EXACT8088_POWER128RETURN64_BENCH_ADAPTATION_ORIGINAL_STIMULI_LOADS_AND_GATES_PRESERVED')
if __name__=='__main__':check()
