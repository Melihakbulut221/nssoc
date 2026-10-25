#!/usr/bin/env python3
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'scripts/mainchip-postroute-inputs-source-delta.json').read_text())
old=(ROOT/d['baseline_path']).read_text();new=(ROOT/d['candidate_path']).read_text()
assert hashlib.sha256(old.encode()).hexdigest()==d['baseline_sha256']
assert hashlib.sha256(new.encode()).hexdigest()==d['candidate_sha256']
pieces=[];cursor=0
for c in d['changes']:
    assert cursor<=c['start']<=c['end']<=len(old)
    pieces.extend([old[cursor:c['start']],c['replacement']]);cursor=c['end']
pieces.append(old[cursor:]);assert ''.join(pieces)==new
ast.parse(new)
helper=(ROOT/d['dependency_helper']).read_bytes()
assert hashlib.sha256(helper).hexdigest()==d['dependency_helper_sha256']
ast.parse(helper)
assert 'OnehotFreshFanoutRoute'not in new and 'fresh-routing-input'not in new
print('PASS_EXACT_CURRENT_FANOUT_ANCESTRY_TO_INPUT_PACKAGE_NO_NEW_ROUTE')
