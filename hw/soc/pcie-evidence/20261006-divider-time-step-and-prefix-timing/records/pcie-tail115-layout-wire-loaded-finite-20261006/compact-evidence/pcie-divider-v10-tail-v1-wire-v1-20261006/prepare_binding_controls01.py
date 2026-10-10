# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare path-only copied-input controls; freeze only after fresh geometry."""
from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent
OLD = B.parent / 'pcie-divider-v9-bias-v1-wire-v1-20261006'
C = B / 'binding-controls01'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


assert not C.exists()
C.mkdir()
parent = OLD / 'binding-controls01/run.py'
text = parent.read_text()
changes = [
    ('nssoc-div4-v9-bias-v1-', 'nssoc-div4-v10-tail-v1-'),
    ('PASS_DIVIDER_V9_BIAS8_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY',
     'PASS_DIVIDER_V10_TAIL115_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'),
]
ledger = []
for old, new in changes:
    count = text.count(old)
    assert count > 0 and new not in text
    ledger.append(dict(old=old, new=new, count=count))
    text = text.replace(old, new)
inverse = text
for row in reversed(ledger):
    inverse = inverse.replace(row['new'], row['old'])
assert inverse == parent.read_text()
target = C / 'run.py'
target.write_text(text)
(C / 'source-bridge.json').write_text(json.dumps(dict(
    parent=str(parent), parent_pin=pin(parent), child=str(target), child_pin=pin(target),
    replacements=ledger, full_inverse_byte_exact=True, source_only_preparation=True,
    criteria_relaxed=False, same_four_one_edit_faults=True,
), indent=2) + '\n')
print(pin(target))
