#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
from cloud_mainchip_repair_deep_postroute import controls
from check_final_native_antenna_counts import controls as antenna_controls
from check_mainchip_repair_deep_completed_source import controls as completed_controls
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
methods=json.loads((ROOT/'scripts/mainchip-repair-deep-postroute-methods.json').read_text())
for name,h in methods.items():
    b=(ROOT/name).read_bytes();assert sha(b)==h,name
    if name.endswith('.py'):ast.parse(b,filename=name)
m=json.loads((ROOT/'scripts/mainchip-repair-deep-postroute-delta.json').read_text())
old=(ROOT/m['baseline_path']).read_bytes();assert sha(old)==m['baseline_sha256']
text=old.decode();parts=[];cursor=0
for change in m['changes']:
    lo,hi=change['start'],change['end'];assert cursor<=lo<=hi<=len(text)
    parts.extend([text[cursor:lo],change['replacement']]);cursor=hi
parts.append(text[cursor:]);new=(ROOT/m['candidate_path']).read_bytes()
assert new==''.join(parts).encode()and sha(new)==m['candidate_sha256']
old_functions={n.name:ast.dump(n)for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)}
new_functions={n.name:ast.dump(n)for n in ast.parse(new).body if isinstance(n,ast.FunctionDef)}
for key in ('timing_gate','controls','source_hash','sha','api'):assert old_functions[key]==new_functions[key],key
a=(ROOT/'scripts/check_onehot_native_fanout_routed_topology.py').read_text()
b=(ROOT/'scripts/check_mainchip_repair_deep_routed_topology.py').read_text()
assert b==a.replace('==152762','==153130').replace('c005764c949e088b96cea5583f3a86fe901772b5e0eafc9d93bba506a151f2b7','6bf5a055467ffea2e4fb0059ffcac4293d939171b0e17af6e224aee13b41c00c')
a=(ROOT/'scripts/export_mainchip_completed_def.py').read_text()
b=(ROOT/'scripts/export_mainchip_repair_deep_completed_def.py').read_text()
assert b==a.replace('==152762','==153130')
print(json.dumps(dict(status='PASS_BOUND_REPAIRED_POSTROUTE_CONTROLS_NOT_NATIVE_ANALYSIS',
    timing=controls(),antenna=antenna_controls(),completed=completed_controls())))
