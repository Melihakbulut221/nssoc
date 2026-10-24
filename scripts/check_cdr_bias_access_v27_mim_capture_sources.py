#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze fresh native MIM capture, original controls and exact live prerequisite identity."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_bias_access_v27_mim_parent_rc.py': 'c8d4fd3ed092dee9df0b68678dd12391c97c211f79b5c99256016e10bd7cdc63', 'scripts/cloud_cdr_bias_access_v27_mim_capture_stage.py': 'b39f18f3d50398972be85db32d96f6f69025e700a6e8f1ec41cc169a1b2d19ed', '.github/workflows/cdr-bias-access-v27-mim-parent-rc-cloud.yml': 'c4f61107c04f5b2aa8c84939e530e6832f095ab2b0b7ee1864e1f47a8701d709', 'docs/evidence/cdr-bias-access-v27-mim-capture-input-20261021.json': '3dfb090667103c654dff1e76454a45ad5c6791990c7110f4864af2514a2a5cee', 'scripts/cdr-bias-access-v27-mim-capture-methods.json': 'eae96bd0aa09c124c77564bcffe0da55e236a3abbdac75df8b6958fde6fc334e', 'docs/evidence/cdr-bias-access-v27-clean-parent-pass-20261021.json': '44e8e9615a0d49b79f9a2b066c178ac6a1eb8f967eea8aea464fbe5775bd6714', 'scripts/cloud_cdr_bias_access_v27_extraction_stage.py': '698c65144c1e60933c585544cd586336d14ad326416feb4bf412e31deaa8d5c9', 'scripts/check_cdr_bias_access_v27_extraction_sources.py': 'ef3a3a303e3c85e7754c36fa464935992a1477d3e5d741b5c9c2c86cb98c6651'}
def check():
    sha=lambda b:hashlib.sha256(b).hexdigest()
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert sha(data)==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    methods=json.loads((ROOT/'scripts/cdr-bias-access-v27-mim-capture-methods.json').read_text())
    for path,m in methods.items():
        raw=(ROOT/m['baseline_path']).read_bytes();assert sha(raw)==m['baseline_sha256']
        text=raw.decode();parts=[];cursor=0
        for edit in m['changes']:
            lo,hi=edit['start'],edit['end'];assert cursor<=lo<=hi<=len(text)
            parts.extend([text[cursor:lo],edit['replacement']]);cursor=hi
        parts.append(text[cursor:]);candidate=(ROOT/path).read_bytes()
        assert candidate==''.join(parts).encode() and sha(candidate)==m['candidate_sha256']
    print('PASS_FROZEN_V27_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
