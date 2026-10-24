#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind completed-route analysis to exact original gates and current route inputs."""
import ast,hashlib,json
from pathlib import Path
from cloud_mainchip_route12_postroute import controls
from check_final_native_antenna_counts import controls as antenna_controls
from check_mainchip_route12_completed_source import controls as completed_controls
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
methods=json.loads((ROOT/'scripts/mainchip-route12-postroute-methods.json').read_text())
for name,h in methods.items():
    b=(ROOT/name).read_bytes();assert sha(b)==h,name
    if name.endswith('.py'):ast.parse(b,filename=name)
delta=json.loads((ROOT/'scripts/mainchip-route12-postroute-delta.json').read_text())
for entry in delta['files']:
    raw=(ROOT/entry['baseline']).read_bytes();assert sha(raw)==entry['baseline_sha256']
    text=raw.decode();parts=[];cursor=0
    for c in entry['changes']:
        lo,hi=c['start'],c['end'];assert cursor<=lo<=hi<=len(text)
        parts.extend([text[cursor:lo],c['replacement']]);cursor=hi
    parts.append(text[cursor:]);candidate=(ROOT/entry['candidate']).read_bytes()
    assert candidate==''.join(parts).encode()and sha(candidate)==entry['candidate_sha256']
old=ast.parse((ROOT/'scripts/cloud_mainchip_repair_deep_postroute.py').read_text())
new=ast.parse((ROOT/'scripts/cloud_mainchip_route12_postroute.py').read_text())
functions=lambda tree:{n.name:ast.dump(n)for n in tree.body if isinstance(n,ast.FunctionDef)}
a,b=functions(old),functions(new)
for name in ('timing_gate','controls','source_hash','sha','api'):assert a[name]==b[name],name
print(json.dumps(dict(status='PASS_ROUTE12_POSTROUTE_SOURCES_AND_NEGATIVE_CONTROLS_NOT_ROUTE_OR_TIMING_ACCEPTANCE',
    timing=controls(),antenna=antenna_controls(),completed=completed_controls())))
