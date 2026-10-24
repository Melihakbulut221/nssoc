#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'scripts/cdr-selector-small-v24-parent-pins.json'
for name,digest in json.loads(p.read_text()).items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, name
print('PASS_EXACT_V24_PARENT_SOURCE_AND_UNCHANGED_NATIVE_PHYSICAL_GATES')
