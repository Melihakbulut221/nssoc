# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare exact path/status derivative; no extraction, freeze or acceptance."""
from pathlib import Path
import difflib
import hashlib
import json

W = Path(__file__).resolve().parent
OLD = W.parent / 'pcie-divider-v9-bias-v1-wire-rc-v1-20261006'
B = W.parent / 'pcie-divider-v10-tail-v1-wire-rc-v1-20261006'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


assert not B.exists()
B.mkdir()
bridges = []
for name in ['run_native_rc.py', 'audit_wire_rc.py', 'check_native_mutations_v2.py']:
    parent = OLD / name
    source = parent.read_text()
    result = source.replace('v9-bias-v1', 'v10-tail-v1').replace('V9_BIAS8', 'V10_TAIL115')
    assert result != source
    assert result.replace('v10-tail-v1', 'v9-bias-v1').replace('V10_TAIL115', 'V9_BIAS8') == source
    child = B / name
    child.write_text(result)
    bridges.append(dict(parent=str(parent), parent_pin=pin(parent), new=str(child),
        new_pin=pin(child), substitutions=[['v9-bias-v1', 'v10-tail-v1'], ['V9_BIAS8', 'V10_TAIL115']],
        full_unified_diff=''.join(difflib.unified_diff(source.splitlines(True), result.splitlines(True))),
        inverse_byte_exact=True))
(B / 'draft-source-bridge.json').write_text(json.dumps(bridges, indent=2) + '\n')
source = (OLD / 'freeze_source.py').read_text()
result = source.replace('v9-bias-v1', 'v10-tail-v1').replace('V9_BIAS8', 'V10_TAIL115')
result = result.replace("OLD = B.parent / 'pcie-divider-v8-cap-v1-wire-rc-v1-20261006'", "OLD = B.parent / 'pcie-divider-v9-bias-v1-wire-rc-v1-20261006'")
result = result.replace('Fresh bias8-divider wire RC; exact two L8 pull-downs and retained cap24 intrinsic models/body boundary retained.', 'Fresh tail115-divider wire RC; exact second-stage L11.5 reference, two L8 pull-downs and retained cap24 intrinsic models/body boundary retained.')
(B / 'freeze_source.py').write_text(result)
ops = [dict(tag=t, before=''.join(source.splitlines(True)[i:j]), after=''.join(result.splitlines(True)[k:l]))
       for t, i, j, k, l in difflib.SequenceMatcher(None, source.splitlines(True), result.splitlines(True), autojunk=False).get_opcodes()]
assert ''.join(o['before'] for o in ops) == source and ''.join(o['after'] for o in ops) == result
(B / 'freezer-source-bridge.json').write_text(json.dumps(dict(parent=str(OLD / 'freeze_source.py'), parent_pin=pin(OLD / 'freeze_source.py'),
    child=str(B / 'freeze_source.py'), child_pin=pin(B / 'freeze_source.py'), full_opcodes=ops), indent=2) + '\n')
print('Prepared only:', B)
