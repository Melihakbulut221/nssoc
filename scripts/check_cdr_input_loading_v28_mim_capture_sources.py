#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze fresh native MIM capture, original controls and exact live prerequisite identity."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_input_loading_v28_mim_parent_rc.py': '709e0269ca86ea5729e4a6b25b0e77b83331b54d385fca50d193d6b4d6305b7b', 'scripts/cloud_cdr_input_loading_v28_mim_capture_stage.py': '5bb173eb2ac8868a95e88f7d3cd4778cf9392f437d43609b68fdbf4cb8e40946', '.github/workflows/cdr-input-loading-v28-mim-parent-rc-cloud.yml': 'dfd56a6fc9c73112a409a4ed30d2df9cfa85fad81a3321f15ff00df22aab1027', 'docs/evidence/cdr-input-loading-v28-mim-capture-input-20261021.json': 'cf7e5f486bc04249f002e88ce5fe1f226a7c8e654c1e09452b311ce978b62fcb', 'scripts/cdr-input-loading-v28-mim-capture-methods.json': '1d8d0adbd7b000ba1d5710b16dc9329d042b076f6db53bdbcabc3d51aa15b3cd', 'docs/evidence/cdr-input-loading-v28-parent-physical-pass-20261021.json': '9bc9df38ec77f1fbce3622757db646d686b8819e13b84cf94438091bf3dec60c', 'scripts/cloud_cdr_input_loading_v28_extraction_stage.py': '39dab298b5c3db0e46e720ba09eb1d74e830a7cf6d010ab7d1ac6f8f0ecb4c27', 'scripts/check_cdr_input_loading_v28_extraction_sources.py': '699ac34454e155911ed08865ce15987a1d1afd1e74df52878777ee31e3564aca', 'scripts/cdr-input-loading-v28-extraction-pins.json': 'e0e1a5d30f4a01e6c79d8e0223df3470159499bb3bf977f8f809c2020ac5dffb'}
def check():
    sha=lambda b:hashlib.sha256(b).hexdigest()
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert sha(data)==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    methods=json.loads((ROOT/'scripts/cdr-input-loading-v28-mim-capture-methods.json').read_text())
    for path,m in methods.items():
        raw=(ROOT/m['baseline_path']).read_bytes();assert sha(raw)==m['baseline_sha256']
        text=raw.decode();parts=[];cursor=0
        for edit in m['changes']:
            lo,hi=edit['start'],edit['end'];assert cursor<=lo<=hi<=len(text)
            parts.extend([text[cursor:lo],edit['replacement']]);cursor=hi
        parts.append(text[cursor:]);candidate=(ROOT/path).read_bytes()
        assert candidate==''.join(parts).encode() and sha(candidate)==m['candidate_sha256']
    print('PASS_FROZEN_V28_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
