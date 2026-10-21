#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
pins=json.loads((root/'scripts/cdr-v27-clean-parent-pins.json').read_text())
for name,digest in pins.items():
    raw=(root/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==digest,name
    if name.endswith('.py'):ast.parse(raw,filename=name)
print('PASS_EXACT_CLEAN_PARENT_METHODS_AND_UNCHANGED_NATIVE_PHYSICAL_GATES')
