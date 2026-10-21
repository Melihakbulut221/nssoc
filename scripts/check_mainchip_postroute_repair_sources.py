#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify exact native repair derivations and original timing/geometry guards."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
    d=json.loads((ROOT/'scripts/mainchip-postroute-repair-methods.json').read_text())
    for path,c in d['derivations'].items():
        original=(ROOT/c['baseline_path']).read_text()
        assert sha(ROOT/c['baseline_path'])==c['baseline_sha256']
        assert sha(ROOT/path)==c['candidate_sha256']
        out=[];cursor=0
        for e in c['changes']:
            assert cursor<=e['start']<=e['end']<=len(original)
            out.extend([original[cursor:e['start']],e['replacement']]);cursor=e['end']
        out.append(original[cursor:]);assert ''.join(out)==(ROOT/path).read_text()
        if path.endswith('.py'):ast.parse((ROOT/path).read_text())
    for path,h in d['frozen'].items():assert sha(ROOT/path)==h,path
    print('PASS_EXACT_COMPLETED_ROUTE_REPAIR_SOURCE_BINDING_NOT_NATIVE_ACCEPTANCE')
if __name__=='__main__':check()
