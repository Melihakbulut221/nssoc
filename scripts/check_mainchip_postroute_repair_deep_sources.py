#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Retain qualified repair guards; increase only the native iteration budget."""
import ast,hashlib,json
from pathlib import Path
from check_mainchip_postroute_repair_sources import check as original_check
ROOT=Path(__file__).resolve().parents[1]
def check():
    original_check()
    m=json.loads((ROOT/'scripts/mainchip-postroute-repair-deep-methods.json').read_text())
    for e in m['derivations']:
        s=(ROOT/e['baseline']).read_text()
        assert hashlib.sha256(s.encode()).hexdigest()==e['baseline_sha256']
        for c in e['changes']:
            assert s.count(c['before'])==c['count']
            s=s.replace(c['before'],c['after'])
        actual=(ROOT/e['candidate']).read_text()
        assert s==actual and hashlib.sha256(actual.encode()).hexdigest()==e['candidate_sha256']
        if e['candidate'].endswith('.py'):ast.parse(actual)
    print('PASS_ONLY_SETUP_ITERATION_BUDGET_CHANGED_ALL_NATIVE_GATES_RETAINED')
if __name__=='__main__':check()
