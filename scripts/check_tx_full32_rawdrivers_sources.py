#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require actual64 native driver expansion and unchanged original waveform gates."""
import ast,hashlib,json
from pathlib import Path
from check_tx_p4_drive3_wave_sources import check as prior
ROOT=Path(__file__).resolve().parents[1]
def check():
    prior()
    m=json.loads((ROOT/'scripts/tx-full32-rawdrivers-source-delta.json').read_text())
    for row in m['files']:
        raw=(ROOT/row['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['baseline_sha256']
        text=raw.decode()
        for e in row['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        candidate=(ROOT/row['candidate_path']).read_bytes()
        assert candidate==text.encode() and hashlib.sha256(candidate).hexdigest()==row['candidate_sha256']
    for path,digest in m['protected'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    row=m['adapter'];raw=(ROOT/row['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['baseline_sha256']
    def function(source):
        matches=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name==row['function']]
        assert len(matches)==1
        return ast.get_source_segment(source,matches[0])
    text=function(raw.decode())
    for e in row['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    candidate=(ROOT/row['candidate_path']).read_bytes()
    assert hashlib.sha256(candidate).hexdigest()==row['candidate_sha256']
    assert function(candidate.decode())==text
    print('PASS_ALL64_RAW100_DRIVER_EXPANSION_ORIGINAL_FULL32_STIMULUS_AND_DEVICE_GATES')
if __name__=='__main__':check()
