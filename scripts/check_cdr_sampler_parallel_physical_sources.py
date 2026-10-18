#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin declared physical circuit/geometry changes while preserving native gates."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    rows=json.loads((ROOT/'scripts/cdr-sampler-parallel-physical-delta.json').read_text())['files']
    for row in rows:
        raw=(ROOT/row['baseline_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==row['baseline_sha256']
        text=raw.decode()
        for e in row['edits']:
            assert text.count(e['before'])==e['count']
            text=text.replace(e['before'],e['after'])
        actual=(ROOT/row['candidate_path']).read_bytes()
        assert actual==text.encode() and hashlib.sha256(actual).hexdigest()==row['candidate_sha256']
    assert hashlib.sha256((ROOT/'hw/soc/analog/pcie/rx_sampler_parallel_drive_v8.spice').read_bytes()).hexdigest()=='876bd1d55af65726ebfcb979d56036b83faccc691e3427f0fb09333d8100acc3'
    from check_cdr_sampler_hybrid_physical_sources import check as original_check
    from check_cdr_sampler_parallel_drive_source import check as electrical_check
    original_check(); electrical_check()
    print('PASS_EXACT_PARALLEL54_PHYSICAL_DELTAS_NATIVE_GATES_AND_EXTRA_SPLIT_FAULTS')
if __name__=='__main__':check()
