#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_via_rich_v7_streamed_sources import check as prior
    prior()
    from check_cdr_collector_v8_mim_composition_sources import check as audit
    audit()
    for d in json.loads((ROOT/'scripts/cdr-collector-v8-streamed-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
        s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count']
            s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes()
        assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    for p,h in json.loads((ROOT/'scripts/cdr-collector-v8-streamed-source-delta.json').read_text())['unchanged_dependencies'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    print('PASS_EXACT_NEW_GEOMETRY_CENSUS_AND_PROVENANCE_ORIGINAL_FULL_WAVE_GATES_RETAINED')
if __name__=='__main__':check()
