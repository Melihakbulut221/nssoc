#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    from check_cdr_collector_v8_binding_rc_sources import check as prior
    prior()
    from check_cdr_data_cm_v9_wire_inputs_source import check as inputs
    inputs()
    d=json.loads((ROOT/"scripts/cdr-data-cm-v9-binding-rc-source-delta.json").read_text())
    assert hashlib.sha256((ROOT/"scripts/build_cdr_parallel_v3_native_models.py").read_bytes()).hexdigest()==d["unchanged_model_converter_sha256"]
    for d in json.loads((ROOT/'scripts/cdr-data-cm-v9-binding-rc-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    assert 116+46+102+11+209==484 and 116*4+46*4+102*3+11*2+209*2==1394
    assert 116+46+102+209==473 and 1394-473+25==946
    print('PASS_EXACT_LOCAL484_BINDING_AND_RC_DELTAS_ORIGINAL_NATIVE_GATES_UNCHANGED')
if __name__=='__main__':check()
