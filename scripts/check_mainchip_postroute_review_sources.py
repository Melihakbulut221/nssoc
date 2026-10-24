#!/usr/bin/env python3
"""Check immutable method bindings and original postroute rejection decisions."""
import ast,hashlib,json
from pathlib import Path
from cloud_mainchip_postroute_review import controls
from check_final_native_antenna_counts import controls as antenna_controls
ROOT=Path(__file__).resolve().parents[1]
methods=json.loads((ROOT/'scripts/mainchip-postroute-review-methods.json').read_text())
for name,expected in methods.items():
    data=(ROOT/name).read_bytes()
    assert hashlib.sha256(data).hexdigest()==expected,name
    if name.endswith('.py'):ast.parse(data,filename=name)
print(json.dumps(dict(status='PASS_POSTROUTE_METHODS_AND_REJECTION_CONTROLS_NOT_NATIVE_TIMING',
    timing=controls(),antenna=antenna_controls())))
