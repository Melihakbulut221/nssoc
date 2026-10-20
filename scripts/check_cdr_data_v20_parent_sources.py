#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind parent replacement code to exact v19 sources and unchanged native gates."""
import hashlib,json,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
runpy.run_path(str(root/'scripts/check_cdr_localbus_v12_parent_sources.py'),run_name='__main__')
m=json.loads((root/'scripts/cdr-data-v20-parent-source-delta.json').read_text())
for path,digest in m['protected'].items():assert sha((root/path).read_bytes())==digest
for e in m['files']:
    old=(root/e['baseline']).read_bytes();assert sha(old)==e['baseline_sha256']
    text=old.decode();parts=[];cursor=0
    for c in e['changes']:
        lo,hi=c['start'],c['end'];assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],c['replacement']]);cursor=hi
    parts.append(text[cursor:]);actual=(root/e['candidate']).read_bytes()
    assert actual==''.join(parts).encode()and sha(actual)==e['candidate_sha256']
print('PASS_EXACT_DATA4_PARENT_REPLACEMENT_WITH_UNCHANGED_NATIVE_PHYSICAL_GATES')
