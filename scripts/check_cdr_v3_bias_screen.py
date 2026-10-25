#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove declared boundary-only edits preserve all native model and engineering gates."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def check():
    spec=json.loads((ROOT/'scripts/cdr-v3-bias-screen-source-delta.json').read_text())
    base=(ROOT/'scripts/cloud_cdr_mim_loaded_v3.py').read_bytes()
    candidate=(ROOT/'scripts/cloud_cdr_v3_bias_screen.py').read_bytes()
    helper=(ROOT/'scripts/cdr_v3_boundary_experiment.py').read_bytes()
    assert hashlib.sha256(base).hexdigest()==spec['base_sha256']
    assert hashlib.sha256(candidate).hexdigest()==spec['candidate_sha256']
    assert hashlib.sha256(helper).hexdigest()==spec['boundary_helper_sha256']
    expected=base.decode()
    for e in spec['edits']:
        assert expected.count(e['before'])==1
        expected=expected.replace(e['before'],e['after'])
    assert expected==candidate.decode()
    return dict(status='PASS_DECLARED_BOUNDARY_EDITS_ONLY_ORIGINAL_MODEL_BITS_TIMES_AND_GATES_RETAINED',**{k:v for k,v in spec.items()if k!='edits'})
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
