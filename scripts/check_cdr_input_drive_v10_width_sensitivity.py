#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_input_drive_v10_streamed_sources import check as baseline
    from cdr_input_drive_v10_width_sensitivity import check_contract
    baseline()
    spec=json.loads((ROOT/'scripts/cdr-input-drive-v10-width-sensitivity-source-delta.json').read_text())
    original=(ROOT/spec['baseline_path']).read_bytes()
    assert hashlib.sha256(original).hexdigest()==spec['baseline_sha256']
    text=original.decode()
    for e in spec['edits']:
        assert text.count(e['before'])==e['count']
        text=text.replace(e['before'],e['after'])
    actual=(ROOT/spec['candidate_path']).read_bytes()
    assert actual==text.encode()and hashlib.sha256(actual).hexdigest()==spec['candidate_sha256']
    for path,digest in spec['dependencies'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    pin=json.loads((ROOT/'docs/evidence/cdr-input-drive-v10-mim-composition-pass-20261019.json').read_text())
    check_contract(pin['report']['composition'])
    print('PASS_DIAGNOSTIC_ONLY_EXACT24_INTRINSIC_WIDTHS_ORIGINAL_ALL_BIT_PHASE_DEVICE_GATES_PRESERVED')
if __name__=='__main__':check()
