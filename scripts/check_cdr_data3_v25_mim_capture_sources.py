#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Freeze fresh native MIM capture, original controls and exact live prerequisite identity."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_data3_v25_mim_parent_rc.py': '34d17dbf1724d95987939b4e93a9293ead59496cc82bd73395e5521f7fd7d53c', 'scripts/cloud_cdr_data3_v25_mim_capture_stage.py': '1ab5a661b5d57766196952ca034e69d3af9f93ed17d808b9afdfd3bd405a6f85', 'docs/evidence/cdr-data3-v25-mim-capture-input-20261021.json': 'aa1c60be15f41f6bf0bccd76e34a498a98572afb21be13921d8f5dac6d27426f', 'scripts/cdr-data3-v25-mim-capture-methods.json': 'ee690fa719f9853475b5fdea0e29b1a112e59b693a368ed2ff07fa1e267a8145', '.github/workflows/cdr-data3-v25-mim-parent-rc-cloud.yml': '8aaafdf90e1a64d728ee43d30c2bd7d4473e3a48ff61d74e7f7874503e2bcc16', 'docs/evidence/cdr-data3-v25-parent-physical-pass-20261021.json': '3b24f685b56f5a6a25b0eb3408635270b4229b6c1ea07a5273c9b8053ee5c3f0', 'scripts/cloud_cdr_data3_v25_extraction_stage.py': 'ad12f1e06951ba368233096ac0e9370070c767d9530c8faf7dca1775eaf77579', 'scripts/check_cdr_data3_v25_extraction_sources.py': 'ee2b445708ac597dfbf7b6b3b7bb543e72b0c87be7e9c38a7b0c997c32be7915'}
def check():
    sha=lambda b:hashlib.sha256(b).hexdigest()
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert sha(data)==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    methods=json.loads((ROOT/'scripts/cdr-data3-v25-mim-capture-methods.json').read_text())
    for path,m in methods.items():
        raw=(ROOT/m['baseline_path']).read_bytes();assert sha(raw)==m['baseline_sha256']
        text=raw.decode();parts=[];cursor=0
        for edit in m['changes']:
            lo,hi=edit['start'],edit['end'];assert cursor<=lo<=hi<=len(text)
            parts.extend([text[cursor:lo],edit['replacement']]);cursor=hi
        parts.append(text[cursor:]);candidate=(ROOT/path).read_bytes()
        assert candidate==''.join(parts).encode() and sha(candidate)==m['candidate_sha256']
    print('PASS_FROZEN_V25_MIM_CAPTURE_AND_ORIGINAL_NATIVE_GATES_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
