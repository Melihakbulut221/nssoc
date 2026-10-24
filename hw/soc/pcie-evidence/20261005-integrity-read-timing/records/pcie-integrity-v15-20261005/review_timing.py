# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reduce every native path group using the frozen corrected V4 parser."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

B = Path(__file__).resolve().parent
P = B.parent / 'pcie-integrity-v4-20261005/review_timing_groups.py'
assert hashlib.sha256(P.read_bytes()).hexdigest() == 'b2a14a5b82b5da7bf1a0de483d6a2877fe234873a0c6035b144c5e12eac818f3'
spec = importlib.util.spec_from_file_location('frozen_groups', P)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
log = Path('/dev/shm/nssoc-integrity-v15-balanced-sta-01/rx/native.log')
text = log.read_text()
rows = parser.parse(text)
prior = json.loads((B.parent / 'pcie-integrity-v11-20261005/timing-comparison.json').read_text())
old = {(r['corner'], r['direction']): r['worst_slack_ns'] for r in prior['groups'] if r['stage'] == 'PREPLACEMENT_REPAIRED'}
delta = {r['corner']+'_'+r['direction']: r['worst_slack_ns']-old[r['corner'], r['direction']] for r in rows if r['stage'] == 'PREPLACEMENT_REPAIRED'}
markers = list(parser.MARKER.finditer(text))
i, marker = next((i,m) for i,m in enumerate(markers) if m.groups() == ('PREPLACEMENT_REPAIRED','slow','max'))
chunk = text[marker.end():markers[i+1].start()]
paths = [p for p in re.split(r'(?=^Startpoint:)', chunk, flags=re.M) if parser.SLACK.search(p)]
worst = min(paths, key=lambda p: float(parser.SLACK.search(p)[1]))
assert float(parser.SLACK.search(worst)[1]) == next(r['worst_slack_ns'] for r in rows if (r['stage'],r['corner'],r['direction']) == ('PREPLACEMENT_REPAIRED','slow','max'))
(B/'slow-critical-path.txt').write_text(worst)
report = dict(status='PREPLACEMENT_ALL_GROUPS_SCREEN_COMPLETE', native_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(), parser_sha256=hashlib.sha256(P.read_bytes()).hexdigest(), groups=rows, same_constraint='Original four-nanosecond v2 profile: same PDK corners, port delays, loads, transitions and preplacement repair.', delta_vs_v11=delta, acceptance=False, scope='All reported path groups and observed slack signs retained. Preplacement screen only; no placement, CTS, route, RC, full mapped functional equivalence or mapped port replay.')
(B/'timing-comparison.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'delta_vs_v11':delta,'repaired':[r for r in rows if r['stage']=='PREPLACEMENT_REPAIRED']},indent=2))
