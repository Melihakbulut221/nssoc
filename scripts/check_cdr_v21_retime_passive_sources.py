#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,runpy
from pathlib import Path
runpy.run_path('scripts/check_cdr_v16_retime_passive_sources.py',run_name='__main__')
m=json.loads(Path('scripts/cdr-v21-retime-passive-source-deltas.json').read_text())
for p,h in m['protected'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
for d in m['files']:
    raw=Path(d['baseline_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256']
    s=raw.decode()
    for e in d['edits']:
        assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
    actual=Path(d['candidate_path']).read_bytes()
    assert actual==s.encode()and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
pin=json.loads(Path('docs/evidence/cdr-data-v20-fullwave-nominal_late-20261020.json').read_text())
assert pin['run']==39426217320 and pin['summary_sha256']=='02aa178de2b228771646e8e1829d30839413f4c7719bf6f9c4304c15095554a7'
assert pin['report']['status']=='REJECTED_WHOLE_MIM_PD484_LOADED'and pin['report']['sources_unchanged']
print('PASS_EXACT_V20_NATIVE_RETIME_NETWORK_SOURCE_BINDING_ORIGINAL_SOLVER_AND_TOPOLOGY_CONTROLS')
