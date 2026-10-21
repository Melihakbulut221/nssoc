#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze fresh native MIM capture, original controls and exact live prerequisite identity."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_input_access_v26_mim_parent_rc.py': 'c145e813ac95dca7909c4ec1c7142057be548bacfca4bc1e7fb9fa8da322e3a3', 'scripts/cloud_cdr_input_access_v26_mim_capture_stage.py': 'b091679c30647d264c626cee4732cd76af10285bd9dc934f600e093da970114c', '.github/workflows/cdr-input-access-v26-mim-parent-rc-cloud.yml': '1069f5e0df4a59baea710da1cf781106858bf431b3a2521eae431f42fdd90856', 'docs/evidence/cdr-input-access-v26-mim-capture-input-20261021.json': 'b831d0e486439d634efb1072dddd087246dec6a690eef68778d961d7ccd4813a', 'scripts/cdr-input-access-v26-mim-capture-methods.json': '57183448329ba97a7a4c57e62d6ac56df60b4422e155a021f2949efd3d1319f8', 'docs/evidence/cdr-input-access-v26-parent-physical-pass-20261021.json': 'd353b76bdc3f590084aa8a977964b27614919b66893c0331ecee2796244e8be0', 'scripts/cloud_cdr_input_access_v26_extraction_stage.py': 'acf7b3abffeaddeb9003364390f9394f0f3fa4bfe9bbb9576ea6f51d1754f63c', 'scripts/check_cdr_input_access_v26_extraction_sources.py': '56caa6b916621263ca9f8aec191c06e1f0ef49272454c87a1b9f2f13b31c18ec'}
def check():
    sha=lambda b:hashlib.sha256(b).hexdigest()
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert sha(data)==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    methods=json.loads((ROOT/'scripts/cdr-input-access-v26-mim-capture-methods.json').read_text())
    for path,m in methods.items():
        raw=(ROOT/m['baseline_path']).read_bytes();assert sha(raw)==m['baseline_sha256']
        text=raw.decode();parts=[];cursor=0
        for edit in m['changes']:
            lo,hi=edit['start'],edit['end'];assert cursor<=lo<=hi<=len(text)
            parts.extend([text[cursor:lo],edit['replacement']]);cursor=hi
        parts.append(text[cursor:]);candidate=(ROOT/path).read_bytes()
        assert candidate==''.join(parts).encode() and sha(candidate)==m['candidate_sha256']
    print('PASS_FROZEN_V26_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
